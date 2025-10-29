import json
import logging
import re
from typing import Any, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator

from tasya.config import config
from tasya.translation import Translator

log = logging.getLogger("tasya.history")


class ToolCall(BaseModel, frozen=True):
    name: str
    arguments: dict[str, Any]

    @field_serializer("arguments", mode="plain")
    def dump_arguments(self, args: dict[str, Any]):
        return json.dumps(args)
    
    @field_validator("arguments", mode="before")
    @classmethod
    def parse_arguments(cls, args: str):
        return json.loads(args)

class ToolWrapper(BaseModel, frozen=True):
    model_config = ConfigDict(serialize_by_alias=True)

    type: Literal["function"]
    function: ToolCall
    id_: str = Field(alias="id")

class Message(BaseModel, frozen=True):
    role: Literal["assistant", "user", "system", "tool"]
    content: str | list[dict[str, str]] | None

    def wrap(self) -> str:
        raise NotImplementedError()
    
    @classmethod
    def unwrap(cls, data: str) -> Self:
        raise NotImplementedError()

class SystemMessage(Message, frozen=True):
    role: Literal["system"] = Field(default="system")
    content: str

    def wrap(self) -> str:
        return f"{config.token_system_start}{self.content.replace("\n", config.token_newline)}{config.token_system_end}"
    
    @classmethod
    def unwrap(cls, data: str) -> Self:
        content = re.findall(rf"(?:^{config.token_system_start})(.*?)(?:{config.token_system_end}$)", data)
        if not content:
            raise RuntimeError(f"Can't unwrap message: {data}")
        return cls(content=content[0])

class UserMessage(Message, frozen=True):
    role: Literal["user"] = Field(default="user")
    content: str | list[dict[str, str]]

    def wrap(self) -> str:
        if isinstance(self.content, str):
            c = self.content
        else:
            c = next(e["text"] for e in self.content if e["type"] == "text")
        return f"{config.token_user_start}{c.replace("\n", config.token_newline)}{config.token_user_end}"
    
    @classmethod
    def unwrap(cls, data: str) -> Self:
        content = re.findall(rf"(?:^{config.token_user_start})(.*?)(?:{config.token_user_end}$)", data)
        if not content:
            raise RuntimeError(f"Can't unwrap message: {data}")
        return cls(content=content[0])

class AssistantMessage(Message, frozen=True):
    role: Literal["assistant"] = Field(default="assistant")
    content: str

    def wrap(self) -> str:
        return f"{config.token_assistant_start}{self.content.replace("\n", config.token_newline)}{config.token_assistant_end}"
    
    @classmethod
    def unwrap(cls, data: str) -> Self:
        content = re.findall(rf"(?:^{config.token_assistant_start})(.*?)(?:{config.token_assistant_end}$)", data)
        if not content:
            raise RuntimeError(f"Can't unwrap message: {data}")
        return cls(content=content[0])

class AssistantToolCall(Message, frozen=True):
    role: Literal["assistant"] = Field(default="assistant")
    content: None = None
    tool_calls: list[ToolWrapper]

    def wrap(self) -> str:
        return f"{config.token_tool_call_start}{config.token_tool_call_end}"
    
    @classmethod
    def unwrap(cls, data: str) -> Self:
        content = re.findall(rf"(?:^{config.token_tool_call_start})(.*?)(?:{config.token_tool_call_end}$)", data)
        if not content:
            raise RuntimeError(f"Can't unwrap message: {data}")
        return cls(content=content[0], tool_calls=[])

class ToolMessage(Message, frozen=True):
    role: Literal["tool"] = Field(default="tool")
    content: str
    name: str
    tool_call_id: str

    def wrap(self) -> str:
        return f"{config.token_tool_resp_start}{self.content.replace("\n", config.token_newline)}{config.token_tool_resp_end}"
    
    @classmethod
    def unwrap(cls, data: str) -> Self:
        content = re.findall(rf"(?:^{config.token_tool_resp_start})(.*?)(?:{config.token_tool_resp_end}$)", data)
        if not content:
            raise RuntimeError(f"Can't unwrap message: {data}")
        return cls(content=content[0], name="", tool_call_id="")

class Conversation:
    def __init__(self, request_id: str = "unknwn") -> None:
        self.messages: list[Message] = []
        self.request_id = request_id
        self.translator = Translator(self.request_id)
    
    def translate(self, from_lang: str, to_lang: str) -> None:
        log.debug(f"req {self.request_id}: translating history from {from_lang} to {to_lang}")
        block = "\n".join(m.wrap() for m in self.messages)
        translated = self.translator.translate(block, from_lang, to_lang)
        for ind, m in enumerate(translated.splitlines()):
            orig_msg = self.messages[ind]
            if config.token_system_start in m and config.token_system_end in m:
                self.messages[ind] = SystemMessage.unwrap(m)
            elif config.token_assistant_start in m and config.token_assistant_end in m:
                self.messages[ind] = AssistantMessage.unwrap(m)
            elif config.token_user_start in m and config.token_user_end in m:
                if isinstance(orig_msg.content, list):
                    tmp_msg = UserMessage.unwrap(m)
                    orig_att = orig_msg.content
                    att = [{"type": "text", "text": tmp_msg.content}]
                    for e in orig_att:
                        if e["type"] != "text":
                            att.append(e)
                    self.messages[ind] = UserMessage(content=att)
                else:
                    self.messages[ind] = UserMessage.unwrap(m)
            elif config.token_tool_call_start in m and config.token_tool_call_start in m:
                continue
            elif config.token_tool_resp_start in m and config.token_tool_resp_start in m:
                self.messages[ind] = ToolMessage.unwrap(m)

    @classmethod
    def from_dicts(cls, messages: list[dict[str, Any]], request_id: str = "unknwn") -> Self:
        log.debug(f"req {request_id}: creating history from dictionary")
        c = cls(request_id)
        for m in messages:
            match m["role"]:
                case "system":
                    c.messages.append(SystemMessage(content=m["content"]))
                case "user":
                    c.messages.append(UserMessage(content=m["content"]))
                case "assistant":
                    if (calls := m.get("tool_calls", None)):
                        c.messages.append(AssistantToolCall(tool_calls=calls))
                    else:
                        c.messages.append(AssistantMessage(content=m["content"]))
                case "tool":
                    c.messages.append(ToolMessage(content=m["content"], name=m["name"], tool_call_id=m["tool_call_id"]))
        return c

    def __add__(self, m: Message) -> "Conversation":
        c = Conversation(self.request_id)
        for pmsg in self.messages:
            c.messages.append(pmsg)
        c.messages.append(m)
        return c
