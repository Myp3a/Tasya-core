from langchain_community.chat_message_histories import SQLChatMessageHistory
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.messages import AIMessage, HumanMessage

from llm import llm
from prompts import ROLE_START, ROLE_END, AI_NAME, USER_NAME, END_OF_TURN, SUMMARIZE_PROMPT

AI_HEADER = f"{ROLE_START}{AI_NAME}{ROLE_END}"
USER_HEADER = f"{ROLE_START}{USER_NAME}{ROLE_END}"

class MessagesWrapper():
    # Designed to workaround the issue that HumanMessage/AIMessage injected directly into prompt
    def __init__(self, messages: list[str]) -> None:
        self.messages = messages
    
    def add_user_message(self, message) -> None:
        self.messages.append(f"{ROLE_START}{USER_NAME}{ROLE_END}{message}{END_OF_TURN}")

    def add_ai_message(self, message) -> None:
        self.messages.append(f"{ROLE_START}{AI_NAME}{ROLE_END}{message}{END_OF_TURN}")
    
    def clear(self) -> None:
        self.messages = []
    
    def add_message(self, message) -> None:
        self.messages.append(message)
    
    def add_messages(self, messages) -> None:
        self.messages.extend(messages)

def get_history(session_id):
    return SQLChatMessageHistory(session_id=session_id, connection_string="sqlite:///messages.db")

def as_list_of_lines(history_obj: BaseChatMessageHistory | MessagesWrapper):
    history = history_obj.messages
    def str_and_prepend_message(message):
        if f"{ROLE_START}" in message and f"{ROLE_END}" in message:
            return message
        if isinstance(message, AIMessage):
            return f"{AI_HEADER}{message.content}{END_OF_TURN}"
        if isinstance(message, HumanMessage):
            return f"{USER_HEADER}{message.content}{END_OF_TURN}"
        return ""  # TODO: find a proper way to handle newlines
    res = [str_and_prepend_message(m) for m in history]
    return res

def as_history_like(history_obj: BaseChatMessageHistory | MessagesWrapper):
    return MessagesWrapper(as_list_of_lines(history_obj))

def as_text_block(history_obj: BaseChatMessageHistory | MessagesWrapper):
    return "\n".join(as_list_of_lines(history_obj))

def trim_if_long(history_obj: BaseChatMessageHistory | MessagesWrapper):
    if len(history_obj.messages) < 15:
        return history_obj
    keep = history_obj.messages[-5:]
    summarize = history_obj.messages[:-5]
    summarization_history = MessagesWrapper(summarize)
    summarize_chain = SUMMARIZE_PROMPT | llm
    history_summarized = summarize_chain.invoke({"chat_history": as_text_block(summarization_history)})
    history_obj.clear()
    history_obj.add_ai_message(history_summarized)
    history_obj.add_messages(keep)
    return history_obj
