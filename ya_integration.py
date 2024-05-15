import uuid
import subprocess
import json
import websockets

import config

from speechkit import model_repository, configure_credentials, creds
yandex_stt_token = config.SPEECHKIT_KEY
configure_credentials(
   yandex_credentials=creds.YandexCredentials(
      api_key=yandex_stt_token
   )
)

async def is_whisper(audio_file_path):
    payload_hello = {
        "event": {
            "header": {
                "namespace": "Vins",
                "name": "VoiceInput",
                "messageId": str(uuid.uuid4()),
                "streamId": 1
            },
        }
    }
    subprocess.run(["ffmpeg", "-y", "-i", audio_file_path, "-acodec", "libvorbis", "-ar", "48000", "-af", "silenceremove=1:0:-90dB", "input.webm"])
    async with websockets.connect("wss://uniproxy.alice.ya.ru/uni.ws") as ws:
        await ws.send(json.dumps(payload_hello))
        with open("tmp/input.webm", "rb") as inf:
            await ws.send(b"\x00\x00\x00\x01" + inf.read())
        resp = json.loads(await ws.recv())
        # try:
        is_whisper = resp["directive"]["payload"]["whisperInfo"]["isWhisper"]
        print(is_whisper)
        return is_whisper

async def get_whisper_audio(text):
    model = model_repository.synthesis_model()
    model.voice = 'marina'
    model.role = 'whisper'
    model.format = 'lpcm'
    result = model.synthesize(text, raw_format=False)
    result.export('output.wav', 'wav')
    return