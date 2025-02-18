import logging

from tasya.generation import Generator
from tasya.history import Conversation
from tasya.translation import Translator
from tasya.utils import oneliner

log = logging.getLogger("tasya.core")


class Core:
    def __init__(self, conversation: Conversation, lang: str = "en", request_id: str = "unknwn") -> None:
        self.conversation = conversation
        self.lang = lang
        self.request_id = request_id
        self.generator = Generator(request_id)
        self.translator = Translator(request_id)

    def reply(self) -> str:
        log.debug(f"req {self.request_id}: replying")
        conv = self.conversation
        if self.lang != "en":
            log.info(f"Request {self.request_id}: translating from {self.lang}")
            conv = Conversation.from_marked_block(self.translator.translate(conv.as_marked_block(), self.lang, "en"), self.request_id)
        log.info(f"Request {self.request_id}: passing to generation module")
        resp = self.generator.answer(conv)
        log.debug(f'req {self.request_id}: got reply "{oneliner(resp.content)}"')
        conv.add(resp.role, resp.content)
        log.debug(f"req {self.request_id}: updated history, it has {conv.count} messages")
        if self.lang != "en":
            log.info(f"Request {self.request_id}: translating to {self.lang}")
            conv = Conversation.from_marked_block(self.translator.translate(conv.as_marked_block(), "en", self.lang), self.request_id)
        return conv.messages[-1].content
