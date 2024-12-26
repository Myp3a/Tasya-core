import re
from typing import Literal

from pydantic import BaseModel

from tasya.config import config

class ToolCall(BaseModel):
    ...

class Message(BaseModel):
    role: Literal["assistant", "user", "system", "tool"]
    content: str
    tool_calls: list[ToolCall] | None = None

    def wrap(self) -> str:
        match self.role:
            case "assistant":
                return f"{config.token_assistant_start}{self.content.replace("\n", config.token_newline)}{config.token_assistant_end}"
            case "user":
                return f"{config.token_user_start}{self.content.replace("\n", config.token_newline)}{config.token_user_end}"
            case "system":
                return f"{config.token_system_start}{self.content.replace("\n", config.token_newline)}{config.token_system_end}"
            case "tool":
                return f"{config.token_tool_start}{self.content.replace("\n", config.token_newline)}{config.token_tool_end}"
    
    @staticmethod
    def unwrap(text: str) -> "Message":
        system = re.findall(rf"(?:^{config.token_system_start})(.*?)(?:{config.token_system_end}$)", text)
        assistant = re.findall(rf"(?:^{config.token_assistant_start})(.*?)(?:{config.token_assistant_end}$)", text)
        user = re.findall(rf"(?:^{config.token_user_start})(.*?)(?:{config.token_user_end}$)", text)
        tool = re.findall(rf"(?:^{config.token_tool_start})(.*?)(?:{config.token_tool_end}$)", text)
        if len(system + assistant + user + tool) != 1:
            raise RuntimeError("Can't unwrap message")
        if system:
            return Message(role="system", content=system[0].replace(config.token_newline, "\n"))
        elif assistant:
            return Message(role="assistant", content=assistant[0].replace(config.token_newline, "\n"))
        elif user:
            return Message(role="user", content=user[0].replace(config.token_newline, "\n"))
        elif tool:
            return Message(role="tool", content=tool[0].replace(config.token_newline, "\n"))


class Conversation:
    def __init__(self) -> None:
        self.messages: list[Message] = []

    def as_marked_block(self) -> str:
        return "\n".join([m.wrap() for m in self.messages])

    @staticmethod
    def from_marked_block(block: str) -> "Conversation":
        c = Conversation()
        c.messages = [Message.unwrap(m) for m in block.split("\n") if m]
        return c

    @staticmethod
    def from_dict(messages: list[dict[str, str]]) -> "Conversation":
        c = Conversation()
        c.messages = [Message(role=m["role"], content=m["content"]) for m in messages]
        return c
    
    @staticmethod
    def from_list(messages: list[Message]) -> "Conversation":
        c = Conversation()
        c.messages = messages
        return c
    
    @property
    def count(self) -> int:
        return len(self.messages)

    def add(self, role: Literal["assistant", "user", "system", "tool"], content: str, index: int | None = None) -> None:
        if index:
            self.messages.insert(index, Message(role=role, content=content))
        else:
            self.messages.append(Message(role=role, content=content))
