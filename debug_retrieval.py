
import os
import sys
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

PERSIST_DIRECTORY = os.path.join(os.path.dirname(__file__), "chroma_db")
EMBEDDINGS = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

def text_wrap(text, width=80):
    return "\n".join([text[i:i+width] for i in range(0, len(text), width)])

def inspect_agent(agent_id):
    path = os.path.join(PERSIST_DIRECTORY, agent_id)
    print(f"\n--- Inspecting Agent: {agent_id} ---")
    print(f"Path: {path}")
    
    if not os.path.exists(path) or not os.listdir(path):
        print("Directory empty or does not exist.")
        return

    try:
        vectorstore = Chroma(persist_directory=path, embedding_function=EMBEDDINGS)
        # This might be slow if the DB is huge, but necessary to check contents
        # Chroma 0.4.x might not expose .get() easily without arguments.
        # We can use .get() to retrieve all.
        
        collection_data = vectorstore.get()
        ids = collection_data["ids"]
        metadatas = collection_data["metadatas"]
        
        print(f"Total documents indexed: {len(ids)}")
        
        # Check for specific document
        target_doc = "Installation of SSL Certificate.docx"
        target_doc_pdf = "Installation of SSL Certificate.pdf"
        
        found_count = 0
        for m in metadatas:
            source = m.get("source", "")
            if target_doc in source or target_doc_pdf in source:
                found_count += 1
                
        print(f"Chunks found for '{target_doc}' (or PDF): {found_count}")
        
        if found_count == 0:
            print("WARNING: Document NOT found in index.")
        else:
            print("Document appears to be indexed.")

        # Test Retrieval
        query = "Installation of SSL Certificate"
        print(f"\nQuerying: '{query}'")
        
        results = vectorstore.similarity_search_with_score(query, k=5)
        
        for i, (doc, score) in enumerate(results):
            print(f"\nResult {i+1} (Score: {score:.4f}):")
            print(f"Source: {doc.metadata.get('source', 'Unknown')}")
            print(f"Content Preview: {doc.page_content[:200]}...")

    except Exception as e:
        print(f"Error inspecting agent {agent_id}: {e}")

def main():
    if not os.path.exists(PERSIST_DIRECTORY):
        print(f"Persist directory {PERSIST_DIRECTORY} not found.")
        return

    # subdirs = [d for d in os.listdir(PERSIST_DIRECTORY) if os.path.isdir(os.path.join(PERSIST_DIRECTORY, d))]
    
    # Check specific known agents
    agents_to_check = ["technical-kb", "193aad23-ec42-4cab-bff4-9d2909f9e13d"]
    
    for agent_id in agents_to_check:
        inspect_agent(agent_id)

if __name__ == "__main__":
    main()
