from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional
import os
import json
import ingest
import rag_app
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_ollama import ChatOllama
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate
from config import GOOGLE_API_KEY, PERSIST_DIRECTORY, LLM_PROVIDER, OLLAMA_BASE_URL, OLLAMA_MODEL

app = FastAPI()

# In-memory config storage (basic)
# In-memory config storage (basic)
# Deprecated in favor of agents.json, but keeping for backward compatibility if needed, 
# or we can remove it. Let's redirect config_store usage to the "default" agent.
AGENTS_FILE = os.path.join(os.path.dirname(__file__), "agents.json")

def load_agents():
    if os.path.exists(AGENTS_FILE):
        with open(AGENTS_FILE, "r") as f:
            return json.load(f)
    return []

def save_agents(agents):
    with open(AGENTS_FILE, "w") as f:
        json.dump(agents, f, indent=4)

@app.on_event("startup")
async def startup_event():
    print("Application starting up...")
    # Add any necessary startup logic here, e.g., validating agents.json
    if not os.path.exists(AGENTS_FILE):
        print("No agents.json found. Creating default if needed.")
        save_agents([{
            "id": "default",
            "name": "Default Agent",
            "folder_id": "", 
            "folder_name": "Not Configured"
        }])

SETTINGS_FILE = os.path.join(os.path.dirname(__file__), "settings.json")

def load_settings():
    if os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, "r") as f:
            return json.load(f)
    return {
        "llm_provider": os.getenv("LLM_PROVIDER", "gemini"),
        "ollama_base_url": os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
        "ollama_model": os.getenv("OLLAMA_MODEL", "llama3")
    }

def save_settings_to_file(settings):
    with open(SETTINGS_FILE, "w") as f:
        json.dump(settings, f, indent=4)


class AgentLLMConfig(BaseModel):
    provider: str = "gemini"
    ollama_base_url: Optional[str] = None
    ollama_model: Optional[str] = None

class Agent(BaseModel):
    id: str
    name: str
    folder_id: str
    folder_name: str
    llm_config: Optional[AgentLLMConfig] = None

class SettingsRequest(BaseModel):
    llm_provider: str
    ollama_base_url: str
    ollama_model: str

class ChatRequest(BaseModel):
    query: str
    agent_id: str = "default"
    
class IngestRequest(BaseModel):
    agent_id: str = "default"

class ChatResponse(BaseModel):
    answer: str
    sources: list[str]

# Global RAG Chain (Lazy loaded)
# Global Ingestion Status (Map agent_id -> status dict)
ingestion_status = {}

def update_ingestion_status(agent_id, status, message):
    ingestion_status[agent_id] = {
        "status": status,
        "message": message,
        "timestamp": str(os.times()) # Simple timestamp
    }

async def run_ingestion(target_folder_id, agent_id):
    try:
        update_ingestion_status(agent_id, "processing", "Starting ingestion...")
        ingest.main(target_folder_id=target_folder_id, agent_id=agent_id)
        update_ingestion_status(agent_id, "completed", "Ingestion complete")
        
        # Invalidate chain cache
        global qa_chains
        if agent_id in qa_chains:
            del qa_chains[agent_id]
            
    except Exception as e:
        update_ingestion_status(agent_id, "failed", str(e))

# Global RAG Chains (Map agent_id -> chain)
qa_chains = {}

def get_qa_chain(agent_id="default"):
    global qa_chains
    if agent_id in qa_chains:
        return qa_chains[agent_id]
    
    agent_persist_dir = os.path.join(PERSIST_DIRECTORY, agent_id)
    if not os.path.exists(agent_persist_dir) or not os.listdir(agent_persist_dir):
        # Allow default agent to fallback? Maybe not.
        return None

    embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    vectorstore = Chroma(persist_directory=agent_persist_dir, embedding_function=embeddings)
    retriever = vectorstore.as_retriever(search_kwargs={"k": 3})
    
    # Load Agent Specific Config
    agents = load_agents()
    agent = next((a for a in agents if a["id"] == agent_id), None)
    
    # Determine LLM settings
    provider = "gemini"
    ollama_base_url = "http://localhost:11434"
    ollama_model = "llama3"

    # 1. Prefer Agent Config
    if agent and "llm_config" in agent and agent["llm_config"]:
        config = agent["llm_config"]
        provider = config.get("provider", "gemini")
        ollama_base_url = config.get("ollama_base_url") or ollama_base_url
        ollama_model = config.get("ollama_model") or ollama_model
    else:
        # 2. Fallback to Global Settings
        settings = load_settings()
        provider = settings.get("llm_provider", "gemini")
        ollama_base_url = settings.get("ollama_base_url", ollama_base_url)
        ollama_model = settings.get("ollama_model", ollama_model)
    
    if provider == "ollama":
        print(f"[{agent_id}] Using Ollama with model {ollama_model} at {ollama_base_url}")
        llm = ChatOllama(
            model=ollama_model,
            base_url=ollama_base_url,
            temperature=0.3
        )
    else:
        # Default to Gemini
        print(f"[{agent_id}] Using Gemini")
        llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash",
            google_api_key=GOOGLE_API_KEY,
            temperature=0.3
        )

    prompt_template = """Use the following pieces of context to answer the question at the end. 
    If you don't know the answer, just say that you don't know, don't try to make up an answer.
    
    Context:
    {context}
    
    Question: {question}
    Answer:"""
    
    PROMPT = PromptTemplate(
        template=prompt_template, input_variables=["context", "question"]
    )
    
    chain = RetrievalQA.from_chain_type(
        llm=llm,
        chain_type="stuff",
        retriever=retriever,
        chain_type_kwargs={"prompt": PROMPT},
        return_source_documents=True
    )
    qa_chains[agent_id] = chain
    return chain

@app.get("/api/agents")
async def get_agents():
    return load_agents()

@app.post("/api/agents")
async def save_agent(agent: Agent):
    agents = load_agents()
    # Update existing or add new
    existing_index = next((i for i, a in enumerate(agents) if a["id"] == agent.id), -1)
    
    # Resolve folder name if unknown
    if agent.folder_id and (not agent.folder_name or agent.folder_name == "Unknown"):
        try:
            headers = ingest.get_header()
            drive_id = ingest.get_drive_id(headers)
            info = ingest.get_folder_info(headers, drive_id, agent.folder_id)
            agent.folder_name = info.get("name", "Unknown")
        except:
             pass

    agent_data = agent.dict()
    
    if existing_index >= 0:
        agents[existing_index] = agent_data
        # Invalidate chain cache for this agent
        if agent.id in qa_chains:
            del qa_chains[agent.id]
    else:
        agents.append(agent_data)
        
    save_agents(agents)
    return {"status": "success", "agent": agent_data}

@app.delete("/api/agents/{agent_id}")
async def delete_agent(agent_id: str):
    agents = load_agents()
    agents = [a for a in agents if a["id"] != agent_id]
    save_agents(agents)
    if agent_id in qa_chains:
        del qa_chains[agent_id]
    return {"status": "success"}

@app.get("/api/settings")
async def get_settings():
    return load_settings()

@app.post("/api/settings")
async def update_settings(settings: SettingsRequest):
    new_settings = settings.dict()
    save_settings_to_file(new_settings)
    
    # Reload chain on next request
    global qa_chains
    qa_chains = {}
    
    return {"status": "success", "message": "Settings saved and RAG chain reset"}

# Removed /api/config GET in favor of /api/agents

@app.post("/api/ingest")
async def trigger_ingest(request: IngestRequest, background_tasks: BackgroundTasks):
    agents = load_agents()
    agent = next((a for a in agents if a["id"] == request.agent_id), None)
    
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
        
    folder_id = agent.get("folder_id")
    if not folder_id:
        raise HTTPException(status_code=400, detail="Agent has no target folder set")
    
    # Run ingestion in background
    background_tasks.add_task(run_ingestion, target_folder_id=folder_id, agent_id=request.agent_id)
    return {"status": "started", "message": f"Ingestion triggered for agent {agent.get('name')}"}

@app.get("/api/ingest/status")
async def get_ingest_status(agent_id: str):
    return ingestion_status.get(agent_id, {"status": "idle", "message": "No ingestion record"})


@app.get("/api/browse")
async def browse_folders(parent_id: str = "root"):
    try:
        headers = ingest.get_header()
        drive_id = ingest.get_drive_id(headers)
        folders = ingest.list_folders(headers, drive_id, parent_id)
        return {"folders": folders, "parent_id": parent_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    chain = get_qa_chain(request.agent_id)
    if not chain:
        raise HTTPException(status_code=400, detail="Index not found. Please ingest documents first.")
    
    try:
        res = chain.invoke({"query": request.query})
        answer = res["result"]
        source_docs = res.get("source_documents", [])
        sources = [doc.metadata.get("source", "Unknown") for doc in source_docs]
        
        return ChatResponse(answer=answer, sources=sources)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Mount static files
# Mount static files
static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")

# Mount downloads for source access
if os.path.exists(ingest.UPLOAD_DIR):
    app.mount("/files", StaticFiles(directory=ingest.UPLOAD_DIR), name="files")
