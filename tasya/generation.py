import json
from typing import Callable, Literal

from ollama import chat
from pydantic import BaseModel

from tasya.history import Conversation, Message
from tasya.tools import tavily_search, owm_current_weather, loc_by_str

class Worker(BaseModel):
    worker_name: Literal["meteorologist", "researcher", "chatter"]

class Query(BaseModel):
    user_query: str

class Location(BaseModel):
    user_location: str

def generate(model: Literal["qwq", "qwen2.5:32b-instruct-q4_K_M", "Luminum"], conv: Conversation, schema: BaseModel | None = None, tools: list[Callable] | None = None):
    if not tools:
        tools = []
    if schema:
        schema = schema.model_json_schema()
    resp = chat(model, messages=[m.model_dump(exclude_none=True) for m in conv.messages], stream=False, format=schema, tools=tools)
    print("inp", conv.messages)
    msg = Message(role="assistant", content=resp["message"]["content"], tool_calls=resp["message"].get("tool_calls", None))
    print("out", msg)
    return msg


def summarize(conv: Conversation, leave: int = 10) -> Conversation:
    tail = conv.messages[-leave:]
    to_summ = conv.messages[:conv.count - leave]
    summ_conv = Conversation.from_list([Message(role="system", content="You are a helpful assistant. Your task is to summarize the conversation between user and assistant. The conversation is provided below. Include as many specific details as you can. Speak in third person.")] + to_summ + [Message(role="user", content="What are we talking about?")])
    summ = generate("qwen2.5:32b-instruct-q4_K_M", summ_conv)
    trunc_conv = Conversation.from_list([summ] + tail)
    return trunc_conv


def extract_query(conv: Conversation) -> str:
    query_conv = Conversation.from_list([Message(role="system", content="You are a helpful assistant. Your task is to extract the user's request about searching for information. Find the user's latest request and output only the search term. Respond with JSON.")] + conv.messages)
    resp = generate("qwen2.5:32b-instruct-q4_K_M", query_conv, schema=Query)
    query = json.loads(resp.content)["user_query"]
    return query


def extract_location(conv: Conversation) -> str:
    loc_conv = Conversation.from_list([Message(role="system", content="You are a helpful assistant. Your task is to extract the user's location from the message. Respond with JSON.")] + conv.messages)
    resp = generate("qwen2.5:32b-instruct-q4_K_M", loc_conv, schema=Location)
    loc = json.loads(resp.content)["user_location"]
    return loc


def answer(conv: Conversation) -> Message:
    if conv.count > 20:
        conv = summarize(conv)
    classify_conv = Conversation.from_list([Message(role="system", content="""You are a supervisor tasked with managing a conversation between the following workers: meteorologist, researcher, chatter.
Given the following user request, respond with the worker to act next. Each worker will perform a task and respond with their results and status.
Available workers:
meteorologist: provides accurate information about current weather.
researcher: can answer complex questions.
chatter: just likes to chat and roleplay. Select this one if the request doesn't fall into other categories.
Respond with JSON.""")] + conv.messages)
    classify = generate("qwen2.5:32b-instruct-q4_K_M", classify_conv, schema=Worker)
    worker = json.loads(classify.content)["worker_name"]
    match worker:
        case "meteorologist":
            loc = extract_location(conv)
            lat, lon = loc_by_str(loc)
            weather = owm_current_weather(lat, lon)
            weather_conv = Conversation.from_list([Message(role="system", content=f"You are a helpful weather assistant. Answer user's request for current weather. You can use the provided inforamtion and chat history.\nThe weather conditions are: {weather["weather"]}, {weather["temp"]} degrees Celsius, {weather["wind"]} m/s wind")] + conv.messages)
            resp = generate("qwen2.5:32b-instruct-q4_K_M", weather_conv)
        case "researcher":
            query = extract_query(conv)
            results = tavily_search(query)
            answer_conv = Conversation.from_list([Message(role="system", content="You are a helpful assistant. Answer user's questions with the best of your ability. You can use the provided inforamtion and chat history." + "".join([f"\n{res}" for res in results]))] + conv.messages)
            resp = generate("qwen2.5:32b-instruct-q4_K_M", answer_conv)
        case "chatter":
            resp_conv = Conversation.from_list([Message(role="system", content="""Enter roleplay mode. Pretend to be Tasya, whose persona follows:
A young beautiful witch. Has long black hair. Sharp-tongued and cynic. Loves to flirt with people. Fit and short. Doesn't care about the world except for nature. Loves stars and believes in fortune.
You shall reply to the user while staying in character.""")] + conv.messages)
            resp = generate("Luminum", resp_conv)
    print()
    for msg in classify_conv.messages:
        print("msg", msg)
    print("resp", resp)
    print()
    return resp
