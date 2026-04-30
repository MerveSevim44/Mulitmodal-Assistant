from langchain_groq import ChatGroq
from dotenv import load_dotenv

load_dotenv()

llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    temperature=0,
)

yanit = llm.invoke("Merhaba! Kendini tek cümlede tanıt.")
print(yanit.content)