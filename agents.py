import pyowm
from langchain_community.document_loaders import WebBaseLoader
from langchain_community.vectorstores.chroma import Chroma
from langchain_community.embeddings import OllamaEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

from history import as_text_block
import tools
import prompts

class Agent:
    def __init__(self, llm) -> None:
        self.llm = llm
        self.name = "dummy"

class SupervisorAgent(Agent):
    def __init__(self, llm, agent_list: list[Agent]) -> None:
        super().__init__(llm)
        self.agents = []
        for a in agent_list:
            self.agents.append(a.name)
        self.name = "supervisor"
    
    def ask(self, history, retry_count = 0) -> str:
        supervisor_prompt = prompts.SUPERVISOR_PROMPT.partial(agents=self.agents)
        supervisor_chain = supervisor_prompt | self.llm
        chosen_worker = supervisor_chain.invoke({"chat_history": as_text_block(history)})
        found_count = sum([name in chosen_worker for name in self.agents])
        if found_count != 1:
            if retry_count > 10:
                return "unknown"  # To prevent deadlocks
            retry_count += 1
            return self.ask(history, retry_count)
        else:
            for agent_name in self.agents:
                if agent_name in chosen_worker.lower():
                    return agent_name

class ContextAssistantAgent(Agent):
    def __init__(self, llm) -> None:
        super().__init__(llm)
        self.name = "assistant"
    
    def ask(self, history, context) -> str:
        prompt_w_context = prompts.CONTEXT_ASSISTANT_PROMPT.partial(context=context)
        assistant_chain = prompt_w_context | self.llm
        resp = assistant_chain.invoke({"chat_history": as_text_block(history)})
        return resp

class WeatherAgent(Agent):
    def __init__(self, llm) -> None:
        super().__init__(llm)
        self.name = "meteorologist"
    
    def parse_city(self, history) -> str:
        get_city_chain = prompts.WEATHER_GET_CITY_PROMPT | self.llm
        city = get_city_chain.invoke({"chat_history": as_text_block(history)})
        return city
    
    def get_weather(self, city) -> str:
        current_weather = tools.weather.invoke(city)
        return current_weather

    def provide_weather(self, history, weather_data) -> str:
        weather_prompt = prompts.WEATHER_AGENT_PROMPT.partial(weather_information=weather_data)
        weather_chain = weather_prompt | self.llm
        weather_resp = weather_chain.invoke({"chat_history": as_text_block(history)})
        return weather_resp
    
    def ask(self, history) -> str:
        city = self.parse_city(history)
        try:
            current_weather = self.get_weather(city)
        except:
            return "I can't determine the city from your request."
        weather_resp = self.provide_weather(history, current_weather)
        return weather_resp

class SearchAgent(Agent):
    def __init__(self, llm) -> None:
        super().__init__(llm)
        self.name = "researcher"
    
    def parse_query(self, history) -> str:
        get_query_chain = prompts.SEARCH_GET_QUERY_PROMPT | self.llm
        query = get_query_chain.invoke({"chat_history": as_text_block(history)})
        return query
    
    def get_links(self, query) -> list[str]:
        search_results = tools.search.invoke(query)
        links = [res["url"] for res in search_results]
        return links
    
    def load_into_db(self, links) -> Chroma:
        embedding_function = OllamaEmbeddings(model="llama3")
        documents = []
        for link in links:
            loader = WebBaseLoader(link)
            docs = loader.load()
            documents.extend(RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200).split_documents(docs))
        db = Chroma.from_documents(documents, embedding_function)
        return db
    
    def parse_db_for_context(self, query, db: Chroma) -> str:
        context = db.as_retriever().invoke(query)
        return "\n\n".join([doc.page_content for doc in context])
    
    def ask(self, history) -> str:
        search_query = self.parse_query(history)
        links = self.get_links(search_query)
        if not links:
            return "Sorry, couldn't find anything."
        db = self.load_into_db(links)
        context = self.parse_db_for_context(search_query, db)
        assistant = ContextAssistantAgent(self.llm)
        resp = assistant.ask(history, context)
        return resp
    
class ChatterAgent(Agent):
    def __init__(self, llm) -> None:
        super().__init__(llm)
        self.name = "chatter"

    def ask(self, history):
        chatter_chain = prompts.CHATTER_AGENT_PROMPT | self.llm
        resp = chatter_chain.invoke({"chat_history": as_text_block(history)})
        return resp
