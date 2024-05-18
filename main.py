import aiohttp
import os
from aiohttp import web

from langchain.globals import set_debug

from history import get_history, MessagesWrapper
from llm import llm
import agents
import config
from ya_integration import is_whisper, get_whisper_audio
from translator import translate, translate_tasya

if config.DEBUG:
    set_debug(True)

routes = web.RouteTableDef()

used_agents_list: list[agents.Agent] = [
    agents.WeatherAgent(llm),
    agents.SearchAgent(llm),
    agents.ChatterAgent(llm),
]

def generate(history) -> str:
    supervisor = agents.SupervisorAgent(llm, used_agents_list)
    chosen_worker = supervisor.ask(history)
    match chosen_worker:
        case "meteorologist":
            resp = agents.WeatherAgent(llm).ask(history)
        case "researcher":
            resp = agents.SearchAgent(llm).ask(history)
        case "chatter":
            resp = agents.ChatterAgent(llm).ask(history)
        case _:
            resp = "I couldn't understand you. Please, try again."
    return resp

@routes.post("/text_input")
async def text_input(req: web.Request):
    data = await req.json()
    session_id = data.get("session_id", None)
    query = data.get("query", None)
    history = data.get("history", None)
    translate_to = data.get("translate", config.TRANSLATE)
    if not query and not history:
        return web.json_response({"error": "query or history is required"}, status=400)
    if not history:
        # Internal history isn't translated
        if session_id:
            history = get_history(session_id)
        else:
            history = MessagesWrapper([])
    else:
        if translate_to:
            history = await translate(history, translate_to, "en")
        history = MessagesWrapper(history.split("\n"))
    if query:
        if translate_to:
            query = await translate(query, translate_to, "en")
        history.add_user_message(query)
    
    resp = generate(history)
    
    if history:
        history.add_ai_message(resp)
    if translate_to:
        resp = await translate_tasya(resp, "en", translate_to)
    return web.json_response({"text": resp})

@routes.post("/voice_input")
async def voice_input(req):
    async with aiohttp.ClientSession() as sess:
        data = await req.post()
        if not (audio := data.get("file", None)):
            return web.json_response({"error": "file is required"}, status=400)
        session_id = data.get("session_id", None)
        history = data.get("history", None)
        translate_to = data.get("translate", config.TRANSLATE)
        return_file = data.get("return_file", False)

        if not history:
            if session_id:
                history = get_history(session_id)
            else:
                history = MessagesWrapper([])
        else:
            history = MessagesWrapper(history.split("\n"))
    
        async with sess.post(
            f"http://{config.WHISPER_HOST}:{config.WHISPER_PORT}/inference",
            data={"file": audio}
        ) as resp:
            found_text = (await resp.json()).get("text", None)
        if not found_text:
            return web.json_response({"error": "spoken text wasn't found"}, status=400)
        
        found_text = found_text.split(config.ASSISTANT_NAME)[-1]
        if found_text.startswith(", "):
            found_text = found_text.replace(", ", "", 1)

        if translate_to:
            found_text = await translate(found_text, translate_to, "en")
        history.add_user_message(found_text)

        if not os.path.isdir("tmp"):
            os.mkdir("tmp")
        with open("tmp/input.wav", "wb") as outf:
            outf.write(audio)
        whisper = await is_whisper("tmp/input.wav")
        
        resp = generate(history)

        if translate_to:
            resp = await translate_tasya(resp, "en", translate_to)

        if whisper:
            await get_whisper_audio(resp)
        else:
            async with sess.post(
                f"http://{config.XTTS_API_SERVER_HOST}:{config.XTTS_API_SERVER_PORT}/tts_to_audio/",
                json={
                    "text": resp,
                    "speaker_wav": config.ASSISTANT_VOICE_SAMPLE,
                    "language": translate_to if translate_to else "en"
                }
            ) as resp:
                with open('tmp/output.wav', "wb") as outf:
                    outf.write(await resp.read())
        with open('tmp/output.wav', "rb") as inf:
            if return_file:
                return web.Response(body=inf.read())
            else:
                async with sess.post(
                    f"http://{config.VOICE_PLAYER_HOST}:{config.VOICE_PLAYER_PORT}/voice_play",
                    data={"file": inf.read()}
                ) as req:
                    pass
    return web.HTTPOk()

app = web.Application()
app.add_routes(routes)
web.run_app(app, port=8085)
