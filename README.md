# Tasya Core
The heart of Tasya, my (voice) assistant - or at least, a wrapper for it.

 - [Features](#features)
 - [Requirements](#requirements)
 - [How to use](#how-to-use)
 - [Helper scripts](#helper-scripts)

# Features
 - LLM RAG-backed responses
 - Text API endpoint
 - Voice API endpoint

### Agent list
 - Random chatting
 - Weather report
 - Internet search

# Requirements
## Hardware
 - A recent videocard with around 16GB of VRAM for all features. Could be trimmed down to ~6GB of VRAM for only text interface.

## Text interface
 - LLaMA-like model run with [ollama](https://github.com/ollama/ollama). LLaMA 3 is the preferred choice

## Voice interface
 - [whisper.cpp](https://github.com/ggerganov/whisper.cpp) instance
 - [xtts-api-server](https://github.com/daswer123/xtts-api-server) instance (subject to change)

## Additional features
 - Whispering voice generation: [Yandex.Speechkit](https://yandex.cloud/ru/services/speechkit) API key
 - Internet search: [Tavily](https://tavily.com/) API key
 - Weather information: [OpenWeatherMap](https://openweathermap.org/api) API key
 - Best-in-class translation: [DeepL](https://www.deepl.com/pro-api) API key

And last, but not least: `pip install -r requirements.txt`!

# How to use
## Text generation endpoint
```
POST /text_input
```
Generates a text response based on text input. Input should be formatted as JSON.
### Required parameters
At least one is required. If both are specified, query will be appended to the history.

**query**: `str` - user question for the AI  
**history**: `list[str]` - chat history for generation
> History is prepended as-is, so it should be formatted like `<|start_header_id|>assistant<|end_header_id|>AI message...<|eot_id|>` (LLaMA 3 format)
### Additional parameters
**session_id**: `str` - persistent key to save chat history on the server  
**translate**: `str` - two-letter language code to translate query and responses from and to
> Internally model and history are used with english language. This allows interactions with AI in other languages, with a bit of quality loss

## Voice generation endpoint
```
POST /voice_input
```
Generates a voice response based on text input. Input should be a `multipart/form-data`!
### Required parameters
**file**: `application/octet-stream` - WAV-encoded voice input  
### Additional parameters
**history**: `list[str]` - chat history for generation
> History is prepended as-is, so it should be formatted like `<|start_header_id|>assistant<|end_header_id|>AI message...<|eot_id|>` (LLaMA 3 format)

**session_id**: `str` - persistent key to save chat history on the server  
**translate**: `str` - two-letter language code to translate query and responses from and to
> Internally model and history are used with english language. This allows interactions with AI in other languages, with a bit of quality loss  

**return_file**: `bool` - whether to return the resulting audio file or play it directly on voice_player instance

# Helper scripts
### command.cpp
Trimmed down whisper.cpp client for voice_input endpoint. Should be compiled with [whisper.cpp](https://github.com/ggerganov/whisper.cpp) headers.
### player.py
Simple WAV audio player over network. Should be used with `VOICE_PLAYER_HOST` config variable.