import json
import logging
from typing import Callable, Literal

from ollama import chat
from pydantic import BaseModel

from tasya.history import Conversation, Message
from tasya.tools import Tools
from tasya.utils import oneliner

log = logging.getLogger("tasya.generation")


class Worker(BaseModel):
    worker_name: Literal["meteorologist", "researcher", "chatter"]

class Query(BaseModel):
    user_query: str

class Location(BaseModel):
    user_location: str

class Generator:
    def __init__(self, request_id: str = "unknwn"):
        self.request_id = request_id

    def generate(self, model: Literal["qwq", "qwen2.5:32b-instruct-q4_K_M", "Luminum"], conv: Conversation, schema: BaseModel | None = None, tools: list[Callable] | None = None):
        log.info(f"Request {self.request_id}: generating, using {model}")
        if not tools:
            tools = []
            log.debug(f"req {self.request_id}: available tools are {tools}")
        if schema:
            schema = schema.model_json_schema()
            log.debug(f"req {self.request_id}: will be generated according to schema")
        for msg in conv.messages:
            log.debug(f"req {self.request_id}: msg by {msg.role:>9} - {oneliner(msg.content)}")
        resp = chat(model, messages=[m.model_dump(exclude_none=True) for m in conv.messages], stream=False, format=schema, tools=tools)
        log.debug(f"req {self.request_id}: msg by assistant - {oneliner(resp["message"]["content"])}")
        msg = Message(role="assistant", content=resp["message"]["content"], tool_calls=resp["message"].get("tool_calls", None))
        return msg


    def summarize(self, conv: Conversation, leave: int = 10) -> Conversation:
        log.info(f"Request {self.request_id}: summarizing, leaving last {leave} messages")
        tail = conv.messages[-leave:]
        to_summ = conv.messages[:conv.count - leave]
        summ_conv = Conversation.from_list([Message(role="system", content="You are a helpful assistant. Your task is to summarize the conversation between user and assistant. The conversation is provided below. Include as many specific details as you can. Speak in third person.")] + to_summ + [Message(role="user", content="What are we talking about?")], self.request_id)
        summ = self.generate("qwen2.5:32b-instruct-q4_K_M", summ_conv)
        log.debug(f'req {self.request_id}: summarized previous messages as "{oneliner(summ.content)}"')
        trunc_conv = Conversation.from_list([summ] + tail, self.request_id)
        return trunc_conv


    def extract_query(self, conv: Conversation) -> str:
        log.info(f"Request {self.request_id}: extracting user query for search")
        query_conv = Conversation.from_list([Message(role="system", content="You are a helpful assistant. Your task is to extract the user's request about searching for information. Find the user's latest request and output only the search term. You can use previous messages as a context to refine the query, as the user's question may be a follow-up. However, if the context seems unrelated, prefer the latest message. Respond with JSON.")] + conv.messages, self.request_id)
        resp = self.generate("qwen2.5:32b-instruct-q4_K_M", query_conv, schema=Query)
        query = json.loads(resp.content)["user_query"]
        log.debug(f'req {self.request_id}: got query "{oneliner(query)}"')
        return query


    def extract_location(self, conv: Conversation) -> str:
        log.info(f"Request {self.request_id}: extracting location for weather")
        loc_conv = Conversation.from_list([Message(role="system", content="You are a helpful assistant. Your task is to extract the user's location from the message. Respond with JSON.")] + conv.messages, self.request_id)
        resp = self.generate("qwen2.5:32b-instruct-q4_K_M", loc_conv, schema=Location)
        loc = json.loads(resp.content)["user_location"]
        log.debug(f'req {self.request_id}: got location "{oneliner(loc)}"')
        return loc


    def answer(self, conv: Conversation) -> Message:
        log.info(f"Request {self.request_id}: passing to answering pipeline")
        tools = Tools(self.request_id)
        if conv.count > 20:
            log.debug(f"req {self.request_id}: too long, summarizing")
            conv = self.summarize(conv)
        log.debug(f"req {self.request_id}: classifying")
        classify_conv = Conversation.from_list([Message(role="system", content="""You are a supervisor tasked with managing a conversation between the following workers: meteorologist, researcher, chatter.
Given the following user request, respond with the worker to act next. Each worker will perform a task and respond with their results and status.
Available workers:
meteorologist: provides accurate information about current weather.
researcher: can answer complex questions.
chatter: just likes to chat and roleplay. Select this one if the request doesn't fall into other categories.
Respond with JSON.""")] + conv.messages, self.request_id)
        classify = self.generate("qwen2.5:32b-instruct-q4_K_M", classify_conv, schema=Worker)
        worker = json.loads(classify.content)["worker_name"]
        log.debug(f"req {self.request_id}: classified as {worker}")
        match worker:
            case "meteorologist":
                loc = self.extract_location(conv)
                lat, lon = tools.loc_by_str(loc)
                weather = tools.owm_current_weather(lat, lon)
                weather_conv = Conversation.from_list([Message(role="system", content=f"You are a helpful weather assistant. Answer user's request for current weather. You can use the provided inforamtion and chat history.\nThe weather conditions are: {weather["weather"]}, {weather["temp"]} degrees Celsius, {weather["wind"]} m/s wind")] + conv.messages, self.request_id)
                resp = self.generate("qwen2.5:32b-instruct-q4_K_M", weather_conv)
            case "researcher":
                query = self.extract_query(conv)
                results = tools.tavily_search(query)
                answer_conv = Conversation.from_list([Message(role="system", content="You are a helpful assistant. Answer user's questions with the best of your ability. You can use the provided inforamtion and chat history." + "".join([f"\n{res}" for res in results]))] + conv.messages, self.request_id)
                resp = self.generate("qwen2.5:32b-instruct-q4_K_M", answer_conv)
            case "chatter":
                resp_conv = Conversation.from_list([Message(role="system", content="""Enter roleplay mode. Pretend to be Tasya, whose persona follows:
A young beautiful witch. Has long black hair. Sharp-tongued and cynic. Loves to flirt with people. Fit and short. Doesn't care about the world except for nature. Loves stars and believes in fortune.
You shall reply to the user while staying in character.""")] + conv.messages, self.request_id)
                resp = self.generate("Luminum", resp_conv)
        log.info(f"Request {self.request_id}: generated an answer")
        log.debug(f'req {self.request_id}: answer is "{oneliner(resp.content)}')
        return resp
