import os
import sys
from config import GOOGLE_API_KEY, PERSIST_DIRECTORY
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate

def main():
    if not GOOGLE_API_KEY:
        print("Please set GOOGLE_API_KEY in .env")
        return

    # Check if vector db exists
    if not os.path.exists(PERSIST_DIRECTORY) or not os.listdir(PERSIST_DIRECTORY):
        print("No index found. Please run 'python ingest.py' first.")
        return

    print("Loading vector store...")
    embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    vectorstore = Chroma(persist_directory=PERSIST_DIRECTORY, embedding_function=embeddings)
    
    # Setup Retriever
    retriever = vectorstore.as_retriever(search_kwargs={"k": 3})

    # Setup LLM
    print("Initializing Gemini-2.0-Flash...")
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.0-flash",
        google_api_key=GOOGLE_API_KEY,
        temperature=0.3
    )

    # Setup Retrieval QA Chain
    prompt_template = """Use the following pieces of context to answer the question at the end. 
    If you don't know the answer, just say that you don't know, don't try to make up an answer.
    
    Context:
    {context}
    
    Question: {question}
    Answer:"""
    
    PROMPT = PromptTemplate(
        template=prompt_template, input_variables=["context", "question"]
    )
    
    qa_chain = RetrievalQA.from_chain_type(
        llm=llm,
        chain_type="stuff",
        retriever=retriever,
        chain_type_kwargs={"prompt": PROMPT},
        return_source_documents=True
    )

    print("\n--- Staff Training Assistant (Type 'exit' to quit) ---")
    while True:
        query = input("\nQuestion: ")
        if query.lower() in ["exit", "quit", "q"]:
            break
            
        try:
            res = qa_chain.invoke({"query": query})
            answer = res["result"]
            source_docs = res["source_documents"]
            
            print(f"\nAnswer: {answer}")
            print("\nSources:")
            for doc in source_docs:
                print(f"- {doc.metadata.get('source', 'Unknown')}")
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    main()
