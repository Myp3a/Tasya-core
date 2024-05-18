import asyncio
import re

import aiohttp
from deep_translator import GoogleTranslator

import config

DEEPL_TASYA_CONTEXT = "This is a chat message from a woman named Tasya. The message must be written from a female perspective."

async def translate_deepl(text: str, src: str, dst: str, formality = "prefer_less", context = None, preserve_formatting = True, use_free_api = True):
    if use_free_api:
        url = "https://api-free.deepl.com/v2/translate"
    else:
        url = "https://api.deepl.com/v2/translate"
    async with aiohttp.ClientSession() as sess:
        async with sess.post(
            url,
            json = {
                "text": [text],
                "source_lang": src,
                "target_lang": dst,
                "formality": formality,
                "context": context,
                "preserve_formatting": preserve_formatting,
            },
            headers = {
                "Authorization": f"DeepL-Auth-Key {config.DEEPL_KEY}"
            }
        ) as resp:
            if resp.status == 429:  # Too many requests
                await asyncio.sleep(1)
                return translate_deepl(text, src, dst, formality, context, preserve_formatting, use_free_api)
            elif resp.status == 456:  # Quota exceeded
                raise ValueError("Your API key exceeded your monthly limit")
            elif resp.status != 200:
                raise ValueError((await resp.json())["message"])
            js = await resp.json()
            return js["translations"][0]["text"]

async def translate(text, src, dst, context = None):
    # try to use best, fallback to "just good"
    try:
        return await translate_deepl(text, src, dst, context)
    except ValueError:
        return GoogleTranslator(source=src, target=dst).translate(text)

async def translate_tasya(text, src, dst):
    return await translate(text, src, dst, context = DEEPL_TASYA_CONTEXT)

def fix_name(text):
    return re.sub(r'Tas.a',"Tasya",text)
