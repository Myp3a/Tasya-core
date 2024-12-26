from tasya.generation import answer
from tasya.history import Conversation
from tasya.translation import translate

class Core:
    def __init__(self, conversation: Conversation, lang: str = "en") -> None:
        self.conversation = conversation
        self.lang = lang

    def reply(self) -> str:
        conv = self.conversation
        if self.lang != "en":
            conv = Conversation.from_marked_block(translate(conv.as_marked_block(), self.lang, "en"))
        resp = answer(conv)
        conv.add(resp.role, resp.content)
        if self.lang != "en":
            conv = Conversation.from_marked_block(translate(conv.as_marked_block(), "en", self.lang))
        return conv.messages[-1].content
