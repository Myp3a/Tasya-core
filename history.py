from langchain_community.chat_message_histories import SQLChatMessageHistory
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.messages import AIMessage, HumanMessage

from prompts import ROLE_START, ROLE_END, AI_NAME, USER_NAME, END_OF_TURN

class MessagesWrapper():
    # Designed to workaround the issue that HumanMessage/AIMessage injected directly into prompt
    def __init__(self, messages_text) -> None:
        self.messages = messages_text

def get_history(session_id):
    return SQLChatMessageHistory(session_id=session_id, connection_string="sqlite:///messages.db")

def as_list_of_lines(history_obj: BaseChatMessageHistory):
    history = history_obj.messages
    def str_and_prepend_message(message):
        if f"{ROLE_START}" in message and f"{ROLE_END}" in message:
            return message
        if isinstance(message, AIMessage):
            return f"{ROLE_START}{AI_NAME}{ROLE_END}{message.content}{END_OF_TURN}"
        if isinstance(message, HumanMessage):
            return f"{ROLE_START}{USER_NAME}{ROLE_END}{message.content}{END_OF_TURN}"
        return ""
    res = [str_and_prepend_message(m) for m in history]
    return res

def as_history_like(history_obj: BaseChatMessageHistory):
    return MessagesWrapper(as_list_of_lines(history_obj))

def as_text_block(history_obj: BaseChatMessageHistory):
    return "\n".join(as_list_of_lines(history_obj))
