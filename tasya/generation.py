import json
import logging
from typing import Any

from pydantic import BaseModel
import requests

from tasya.config import config
import tasya.prompts as prompts
from tasya.history import AssistantMessage, AssistantToolCall, Conversation, SystemMessage, ToolMessage, UserMessage
from tasya.tools import Tools
from tasya.utils import oneliner, model_to_schema

log = logging.getLogger("tasya.generation")


class HasResponse(BaseModel):
    has_response: bool
    missing_data: str

    def __bool__(self):
        return self.has_response

class Generator:
    def __init__(self, request_id: str = "unknwn"):
        self.request_id = request_id

    def generate(self, conv: Conversation, schema: dict[str, Any] | None = None, tools: list[dict[str, Any]] | None = None, args: dict[str, Any] | None = None):
        log.info(f"Request {self.request_id}: generating")
        if not tools:
            tools = []
            log.debug(f"req {self.request_id}: available tools are {tools}")
        if schema:
            log.debug(f"req {self.request_id}: will be generated according to schema")
        for msg in conv.messages:
            log.debug(f"req {self.request_id}: msg by {msg.role:>9} - {oneliner(msg)}")
        req_data = {
            "model": "gemma3-tasya",
            "messages": [m.model_dump(exclude_none=True) for m in conv.messages],
            "response_format": {"type": "json_object", "schema": schema} if schema else None,
            "stream": False,
            "tools": tools,
        }
        if args:
            req_data |= args
        resp = requests.post(
            f"http://{config.llamacpp_ip}:{config.llamacpp_port}/v1/chat/completions",
            json=req_data,
        )
        log.debug(f"raw req: {resp.request.body}")
        if not resp.ok:
            raise RuntimeError(f"failed to generate response: {resp.text}")
        js = resp.json()["choices"][0]
        log.debug(f"raw resp: {js}")
        match js["finish_reason"]:
            case "tool_calls":
                m = AssistantToolCall(tool_calls=js["message"]["tool_calls"])
            case "stop":
                m = AssistantMessage(content=js["message"]["content"])
            case _:
                raise RuntimeError(f"Unknown stop reason: {js['finish_reason']}")
        log.debug(f"req {self.request_id}: msg by assistant - {oneliner(m)}")
        return m
    
    def check_answer(self, conv: Conversation, orig_query: str) -> HasResponse:
        log.info(f"Request {self.request_id}: checking for answer")
        conv += SystemMessage(content=prompts.has_answer.fill([orig_query]))
        r = self.generate(conv, schema=model_to_schema(HasResponse))
        assert isinstance(r, AssistantMessage)
        m = HasResponse.model_validate_json(r.content, strict=True, extra="forbid")
        return m

    def answer(self, conv: Conversation) -> AssistantMessage:
        log.info(f"Request {self.request_id}: passing to answering pipeline")
        tools = Tools(self.request_id)
        assert isinstance(conv.messages[-1], UserMessage)
        orig_request = conv.messages[-1].content
        if isinstance(orig_request, list):
            orig_request = next(m["text"] for m in orig_request if m["type"] == "text")
        while not self.check_answer(conv, orig_request):
            resp = self.generate(conv, tools=tools.get_tools())
            conv += resp
            if isinstance(resp, AssistantToolCall):
                for call in resp.tool_calls:
                    match call.function.name:
                        case "time":
                            t = tools.time
                        case "tavily_search":
                            t = tools.tavily_search
                        case "owm_current_weather":
                            t = tools.owm_current_weather
                        case "loc_by_str":
                            t = tools.loc_by_str
                    tool_res = t(**call.function.arguments)
                    if not isinstance(tool_res, str):
                        tool_res = json.dumps(tool_res)
                    conv += ToolMessage(content=tool_res, name=call.function.name, tool_call_id=call.id_)
        if isinstance(conv.messages[-1], ToolMessage):
            conv += UserMessage(content="Explain the tool output in human language, please?")
            resp = self.generate(conv)
            conv += resp
        resp = conv.messages[-1]
        assert isinstance(resp, AssistantMessage)
        tasya_c = Conversation(self.request_id)
        tasya_c += SystemMessage(content=prompts.tasyafy.fill([]))
        tasya_c += UserMessage(content=resp.content)
        tasya_resp = self.generate(tasya_c)
        assert isinstance(tasya_resp, AssistantMessage)
        log.info(f"Request {self.request_id}: generated an answer")
        log.debug(f'req {self.request_id}: answer is "{oneliner(tasya_resp)}')
        return tasya_resp
