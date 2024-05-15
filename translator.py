import re
from deep_translator import GoogleTranslator, DeeplTranslator

import config

async def translate(text,src=None,dst=None):
    # try to use best, fallback to "just good"
    try:
        return DeeplTranslator(api_key=config.DEEPL_KEY, source=src, target=dst).translate(text)
    except:
        return GoogleTranslator(source=src, target=dst).translate(text)

def fix_name(text):
    return re.sub(r'Tas.a',"Tasya",text)
