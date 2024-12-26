import re
import time

import requests
from deep_translator import GoogleTranslator

from tasya.config import config

def translate_deepl(text: str, src: str, dst: str, formality = "prefer_less", tag_handling = "xml", use_free_api = True):
    print("trans", text)
    if use_free_api:
        url = "https://api-free.deepl.com/v2/translate"
    else:
        url = "https://api.deepl.com/v2/translate"
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
        time.sleep(1)
        return translate_deepl(text, src, dst, formality, tag_handling, use_free_api)
    elif resp.status_code == 456:  # Quota exceeded
        raise ValueError("Your API key exceeded your monthly limit")
    elif resp.status_code != 200:
        raise ValueError(resp.json()["message"])
    js = resp.json()
    print(js)
    return js["translations"][0]["text"]

def translate(text, src, dst):
    # try to use best, fallback to "just good"
    try:
        return fix_name(translate_deepl(text, src, dst))
    except ValueError:
        return fix_name(GoogleTranslator(source=src, target=dst).translate(text))

def fix_name(text):
    return re.sub(r'Tas.a',"Tasya",text)
