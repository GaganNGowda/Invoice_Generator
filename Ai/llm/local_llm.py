from langchain.llms import Ollama

llm = Ollama(model="llama3")

def ask_llm(prompt: str) -> str:
    return llm.invoke(prompt)
