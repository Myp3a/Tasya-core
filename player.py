import io
import pyaudio
import wave
from aiohttp import web

routes = web.RouteTableDef()

class AudioFile:
    chunk = 1024

    def __init__(self, file):
        """Init audio stream""" 
        self.wf = wave.open(file)
        self.p = pyaudio.PyAudio()
        self.stream = self.p.open(
            format = self.p.get_format_from_width(self.wf.getsampwidth()),
            channels = self.wf.getnchannels(),
            rate = self.wf.getframerate(),
            output = True
        )

    def play(self):
        """Play entire file"""
        data = self.wf.readframes(self.chunk)
        while data != b'':
            self.stream.write(data)
            data = self.wf.readframes(self.chunk)

    def close(self):
        """Graceful shutdown""" 
        self.stream.close()
        self.p.terminate()


@routes.post("/voice_play")
async def voice_play(req):
    data = await req.post()
    file_data = io.BytesIO(data["file"].file.read())
    af = AudioFile(file_data)
    af.play()
    af.close()
    return web.Response(text="ok")

app = web.Application()
app.add_routes(routes)
web.run_app(app)
