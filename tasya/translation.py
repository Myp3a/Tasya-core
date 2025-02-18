from copy import deepcopy
import logging
import re
import time

import requests
from deep_translator import GoogleTranslator

from tasya.config import config

log = logging.getLogger("tasya.translation")

class Translator:
    def __init__(self, request_id: str = "unknwn"):
        self.request_id = request_id

    def translate_deepl(self, text: str, src: str, dst: str, formality = "prefer_less", tag_handling = "xml", use_free_api = True):
        log.debug(f"req {self.request_id}: translating with DeepL")
        if use_free_api:
            url = "https://api-free.deepl.com/v2/translate"
        else:
            url = "https://api.deepl.com/v2/translate"
        log.debug(f'req {self.request_id}: params are {{"free_api": {use_free_api}, "src_lang": "{src}", "dst_lang": "{dst}", "formality": "{formality}", "tag_handling": "{tag_handling}"}}')
        resp = requests.post(
            url,
            json = {
                "text": [text],
                "source_lang": src,
                "target_lang": dst,
                "formality": formality,
                "tag_handling": tag_handling,
            },
            headers = {
                "Authorization": f"DeepL-Auth-Key {config.deepl_token}"
            }
        )
        if resp.status_code == 429:  # Too many requests
            log.debug(f"req {self.request_id}: hit the ratelimit")
            time.sleep(1)
            return self.translate_deepl(text, src, dst, formality, tag_handling, use_free_api)
        elif resp.status_code == 456:  # Quota exceeded
            log.debug(f"req {self.request_id}: api key exhausted")
            raise ValueError("Your API key exceeded your monthly limit")
        elif resp.status_code != 200:
            log.debug(f"req {self.request_id}: unexpected error")
            raise ValueError(resp.json()["message"])
        log.debug(f"req {self.request_id}: translation successful")
        js = resp.json()
        return js["translations"][0]["text"]

    def translate(self, text, src, dst):
        log.info(f"Request {self.request_id}: translating")
        # try to use best, fallback to "just good"
        try:
            return self.fix_name(self.translate_deepl(text, src, dst))
        except ValueError:
            log.debug(f"req {self.request_id}: translating with Google")
            tr = self.fix_name(GoogleTranslator(source=src, target=dst).translate(text))
            log.debug(f"req {self.request_id}: translation successful")
            return tr

    def fix_name(self, text):
        return re.sub(r'Tas.a',"Tasya",text)
