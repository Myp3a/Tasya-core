from aiohttp import web

from tasya.core import Core
from tasya.history import Conversation

routes = web.RouteTableDef()

@routes.post("/text")
async def text_input(req: web.Request) -> web.Response:
    data = await req.json()
    history = data.get("history", [])
    lang = data.get("lang", "en")

    if not history:
        return web.json_response({"error": "history is empty"}, status=400)
    
    conv = Conversation.from_dict(history)
    core = Core(conv, lang)

    reply = core.reply()

    return web.json_response({"role": "assistant", "content": reply})

app = web.Application()
app.add_routes(routes)
web.run_app(app, port=8085)
