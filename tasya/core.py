import logging

from tasya.generation import Generator
from tasya.history import AssistantMessage, Conversation
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

    def reply(self) -> AssistantMessage:
        log.debug(f"req {self.request_id}: replying")
        conv = self.conversation
        if self.lang != "en":
            log.info(f"Request {self.request_id}: translating from {self.lang}")
            conv.translate(self.lang, "en")
        log.info(f"Request {self.request_id}: passing to generation module")
        resp = self.generator.answer(conv)
        log.debug(f'req {self.request_id}: got reply "{oneliner(resp)}"')
        conv += resp
        log.debug(f"req {self.request_id}: updated history, it has {len(conv.messages)} messages")
        if self.lang != "en":
            log.info(f"Request {self.request_id}: translating to {self.lang}")
            conv.translate("en", self.lang)
        assert isinstance(conv.messages[-1], AssistantMessage)
        return conv.messages[-1]
