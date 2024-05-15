# from langchain_community.llms.koboldai import KoboldApiLLM
from langchain_community.llms.ollama import Ollama

# llm = KoboldApiLLM(endpoint="http://asya.tail5fdaf.ts.net:5000", max_length=80)
llm = Ollama(model="llama3")