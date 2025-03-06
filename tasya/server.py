import asyncio
import logging
import random
import string

from aiohttp import web

from tasya.core import Core
from tasya.history import Conversation
from tasya.utils import oneliner

log = logging.getLogger("tasya.server")
routes = web.RouteTableDef()

@routes.post("/text")
async def text_input(req: web.Request) -> web.Response:
    req_id = "".join(random.choices(string.ascii_letters + string.digits, k=6))
    data = await req.json()
    log.info(f"Request {req_id}: received request for text generation")
    log.debug(f"req {req_id}: contents are {data}")
    history = data.get("history", [])
    lang = data.get("lang", "en")

    if not history:
        log.info(f"Request {req_id}: no data for generation, discarding")
        return web.json_response({"error": "history is empty"}, status=400)
    
    log.debug(f"req {req_id}: about to parse data")
    conv = Conversation.from_dict(history, req_id)
    log.debug(f"req {req_id}: parsed message history, got {conv.count} messages")
    core = Core(conv, lang, req_id)

    log.debug(f"req {req_id}: about to generate a reply")
    reply = await asyncio.to_thread(core.reply)
    log.debug(f'req {req_id}: got a reply "{oneliner(reply)}"')

    log.info(f"Request {req_id}: fulfilled, returning result")
    return web.json_response({"role": "assistant", "content": reply})

app = web.Application()
app.add_routes(routes)
log.info("Core init")
web.run_app(app, port=8085)
