import os
from dotenv import load_dotenv

load_dotenv()

# Microsoft Graph Credentials
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
TENANT_ID = os.getenv("TENANT_ID")
SHAREPOINT_SITE_ID = os.getenv("SHAREPOINT_SITE_ID") # Optional: Specific Site ID
SHAREPOINT_DRIVE_ID = os.getenv("SHAREPOINT_DRIVE_ID") # Optional: Specific Drive/Library ID
SHAREPOINT_TARGET_FOLDER_ID = os.getenv("SHAREPOINT_TARGET_FOLDER_ID") # Optional: Specific Folder ID

# Google Gemini Credentials
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# LLM Configuration
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "gemini") # "gemini" or "ollama"
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3")

# Vector DB Configuration
PERSIST_DIRECTORY = os.path.join(os.path.dirname(__file__), "chroma_db")
