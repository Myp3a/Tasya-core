import inspect
import json
from typing import Any, Callable

from pydantic import BaseModel

from tasya.history import AssistantToolCall, Message, UserMessage

def oneliner(msg: Message) -> str:
    if isinstance(msg, UserMessage) and isinstance(msg.content, list):
        content = next(e["text"] for e in msg.content if e["type"] == "text")
    elif isinstance(msg, AssistantToolCall):
        content = msg.tool_calls
        return json.dumps([t.model_dump() for t in msg.tool_calls])
    else:
        content = msg.content
    return content.replace('\n', " {br} ")

def function_to_tool(function: Callable, arguments_descr: list[str], required: list[str] | None = None) -> dict[str, Any]:
    type_mappings = {int: "integer", float: "number", str: "string"}
    docstr = inspect.getdoc(function)
    sig = inspect.signature(function)
    args = {p.name: {"type": type_mappings[p.annotation], "description": arguments_descr[num-1]} for num, p in enumerate(sig.parameters.values())}
    name = function.__name__
    tool = {
        "type": "function",
        "function": {
            "name": name,
            "description": docstr,
            "parameters": {
                "type": "object",
                "properties": args,
                "required": required,
            },
        },
    }
    return tool

def model_to_schema(model: type[BaseModel]) -> dict[str, Any]:
    def recursive_edit(root: dict[str, Any]) -> None:
        if "title" in root:
            root.pop("title")
        if root.get("type", "") == "object":
            root["additionalProperties"] = False
        for v in root.values():
            if isinstance(v, dict):
                recursive_edit(v)
    schema = model.model_json_schema()
    recursive_edit(schema)
    return schema
    