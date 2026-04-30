from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from dotenv import load_dotenv

load_dotenv()

# Aynı embedding modelini kullan
embeddings = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-MiniLM-L6-v2"
)

# Kaydedilen ChromaDB'yi yükle
vektor_db = Chroma(
    persist_directory="week1_rag/chroma_db",
    embedding_function=embeddings
)

# Retriever — en benzer 2 belgeyi getir
retriever = vektor_db.as_retriever(search_kwargs={"k": 2})

# Prompt şablonu
prompt = ChatPromptTemplate.from_template("""
Aşağıdaki bağlamı kullanarak soruyu Türkçe cevapla.
Bağlamda yoksa "Bu konuda bilgim yok" de.

Bağlam: {context}

Soru: {question}
""")

# LLM
llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0)

def belgeleri_birlestir(docs):
    return "\n\n".join(doc.page_content for doc in docs)

# RAG zinciri
rag_chain = (
    {
        "context": retriever | belgeleri_birlestir,
        "question": RunnablePassthrough()
    }
    | prompt
    | llm
)

if __name__ == "__main__":
    sorular = [
        "ChromaDB ne işe yarar?",
        "Embedding nedir?",
        "Python nedir?",
    ]

    for soru in sorular:
        print(f"\nSoru: {soru}")
        print(f"Cevap: {rag_chain.invoke(soru).content}")
        print("-" * 40)