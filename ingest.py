import os
import requests
import mimetypes
from config import (
    CLIENT_ID, CLIENT_SECRET, TENANT_ID, 
    SHAREPOINT_SITE_ID, SHAREPOINT_DRIVE_ID, 
    SHAREPOINT_TARGET_FOLDER_ID,
    GOOGLE_API_KEY, PERSIST_DIRECTORY
)
from azure.identity import ClientSecretCredential
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_community.document_loaders import UnstructuredFileLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
import docx
from docx.text.paragraph import Paragraph
from docx.table import Table
from docx.oxml.text.paragraph import CT_P
from docx.oxml.table import CT_Tbl
from docx.document import Document as _Document

# Ensure upload directory exists
UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "downloads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

def get_header():
    credential = ClientSecretCredential(
        tenant_id=TENANT_ID,
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET
    )
    token = credential.get_token("https://graph.microsoft.com/.default")
    return {"Authorization": f"Bearer {token.token}"}

def get_drive_id(headers):
    if SHAREPOINT_DRIVE_ID:
        return SHAREPOINT_DRIVE_ID
    
    # If no Drive ID, try to get the default drive of the site
    if not SHAREPOINT_SITE_ID:
        raise ValueError("SHAREPOINT_SITE_ID or SHAREPOINT_DRIVE_ID must be provided")
    
    url = f"https://graph.microsoft.com/v1.0/sites/{SHAREPOINT_SITE_ID}/drive"
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json().get("id")

def list_files_recursive(headers, drive_id, item_id, path_prefix=""):
    url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/items/{item_id}/children"
    
    print(f"Scanning folder: {path_prefix}...")
    
    while url:
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()
            
            items = data.get("value", [])
            
            # Pass 1: Process Files First
            for item in items:
                if "file" in item:
                    name = item.get("name", "")
                    # Filter for PDF, Word, and Text
                    lower_name = name.lower()
                    if lower_name.endswith(".docx"):
                        print(f"Found relevant file: {name}")
                        item["local_path_rel"] = os.path.join(path_prefix, name)
                        yield item
            
            # Pass 2: Recurse into Folders
            for item in items:
                if "folder" in item:
                    name = item.get("name", "")
                    # optimization: skip system/code folders
                    lower_name = name.lower()
                    skip_keywords = ["bin", "obj", "script", "app_", "jquery", "image", "css", "style", "font", "vendor", "node_modules", "dist", "build"]
                    if any(k in lower_name for k in skip_keywords):
                        print(f"Skipping system folder: {name}")
                        continue
                        
                    new_prefix = os.path.join(path_prefix, name)
                    yield from list_files_recursive(headers, drive_id, item.get("id"), new_prefix)
            
            url = data.get("@odata.nextLink")
            
        except requests.exceptions.HTTPError as e:
            print(f"Error scanning {path_prefix}: {e}")
            break

def list_files(headers, drive_id, target_folder_id=None):
    if target_folder_id:
        root_id = target_folder_id
        print(f"Starting recursive scan from Target Folder ID: {root_id}")
    elif SHAREPOINT_TARGET_FOLDER_ID:
        root_id = SHAREPOINT_TARGET_FOLDER_ID
        print(f"Starting recursive scan from Configured Target Folder ID: {root_id}")
    else:
        root_id = "root"
        print(f"Starting recursive scan from Drive Root")

    return list_files_recursive(headers, drive_id, root_id)

def list_folders(headers, drive_id, parent_id="root"):
    url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/items/{parent_id}/children"
    folders = []
    
    while url:
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()
            
            for item in data.get("value", []):
                if "folder" in item:
                    folders.append({
                        "id": item.get("id"),
                        "name": item.get("name"),
                        "parentReference": item.get("parentReference", {})
                    })
            
            url = data.get("@odata.nextLink")
            
        except requests.exceptions.HTTPError as e:
            print(f"Error listing folders: {e}")
            break
            
    return folders

def get_folder_info(headers, drive_id, folder_id):
    if not folder_id or folder_id == "root":
        return {"id": "root", "name": "root"}
        
    url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/items/{folder_id}"
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        return {"id": data.get("id"), "name": data.get("name")}
    except Exception as e:
        print(f"Error getting folder info: {e}")
        return {"id": folder_id, "name": "Unknown"}

def download_file(headers, file_id, file_name):
    url = f"https://graph.microsoft.com/v1.0/drives/{SHAREPOINT_DRIVE_ID}/items/{file_id}/content"
    # Note: We need to ensure we have the correct drive ID here. 
    # If SHAREPOINT_DRIVE_ID was globally set, good. If not, we need to pass it.
    # Refactoring list_files to return parent drive_id or assume global variable usage.
    # For now, let's just use the url provided in the file item usually '@microsoft.graph.downloadUrl'
    # But sometimes downloadUrl is short lived.
    
    # Better approach: Use the download URL from the item property if available
    # Or construct it.
    pass 

def download_files(headers, files):
    downloaded_paths = []
    for file_item in files:
        name = file_item.get("name")
        download_url = file_item.get("@microsoft.graph.downloadUrl")
        
        if not download_url:
            print(f"Skipping {name}, no download URL found.")
            continue
            
        print(f"Downloading {name}...")
        response = requests.get(download_url) # Download URL is public-ish pre-signed or needs auth? 
        # Usually it works directly but let's check. 
        # Actually standard Graph download URL often doesn't need auth header if it's a pre-signed link, 
        # but safely we can use the /content endpoint with auth.
        
        if response.status_code != 200:
            # Try /content endpoint
            drive_id = file_item.get("parentReference", {}).get("driveId")
            item_id = file_item.get("id")
            url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/items/{item_id}/content"
            response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            file_path = os.path.join(UPLOAD_DIR, name)
            with open(file_path, "wb") as f:
                f.write(response.content)
            downloaded_paths.append(file_path)
        else:
            print(f"Failed to download {name}")
            
    return downloaded_paths

    return downloaded_paths

def load_docx_with_tables(file_path):
    """
    Load a DOCX file and convert tables to Markdown, preserving order.
    """
    try:
        doc = docx.Document(file_path)
    except Exception as e:
        print(f"Error opening DOCX {file_path}: {e}")
        return []

    full_text = []

    # Iterate through elements in the document body
    # This allows us to handle paragraphs and tables in their correct order
    def iter_block_items(parent):
        if isinstance(parent, _Document):
            parent_elm = parent.element.body
        # elif isinstance(parent, _Cell):
        #     parent_elm = parent._tc
        else:
            # Fallback (shouldn't happen for main doc body)
            return

        for child in parent_elm.iterchildren():
            if isinstance(child, CT_P):
                yield Paragraph(child, parent)
            elif isinstance(child, CT_Tbl):
                yield Table(child, parent)

    for block in iter_block_items(doc):
        if isinstance(block, Paragraph):
            if block.text.strip():
                full_text.append(block.text)
        elif isinstance(block, Table):
            # Convert table to Markdown
            md_table = []
            rows = block.rows
            if not rows: continue
            
            # Helper to clean cell text
            def clean_text(text):
                return text.strip().replace('\n', ' ').replace('|', '\\|')

            # Extract data
            table_data = [[clean_text(cell.text) for cell in row.cells] for row in rows]
            
            # We need at least one row
            if table_data:
                # Add a blank line before table
                full_text.append("") 
                
                # Header row
                headers = table_data[0]
                # If headers are empty, fill with generic? No, keep as is.
                md_table.append("| " + " | ".join(headers) + " |")
                
                # Separator row (required for valid MD table)
                md_table.append("| " + " | ".join(["---"] * len(headers)) + " |")
                
                # Data rows
                for row in table_data[1:]:
                     md_table.append("| " + " | ".join(row) + " |")
                
                full_text.append("\n".join(md_table))
                # Add a blank line after table
                full_text.append("")

    return [Document(page_content="\n".join(full_text), metadata={"source": file_path})]

def process_and_index(file_paths, agent_id="default"):
    if not file_paths:
        print("No files to process.")
        return

    documents = []
    for path in file_paths:
        print(f"Loading {path}...")
        try:
            if path.lower().endswith(".docx"):
                docs = load_docx_with_tables(path)
            else:
                # Fallback for other types (though we restricted to docx)
                loader = UnstructuredFileLoader(path)
                docs = loader.load()
            
            documents.extend(docs)
        except Exception as e:
            print(f"Error loading {path}: {e}")

    if not documents:
        return

    print("Splitting documents...")
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    splits = text_splitter.split_documents(documents)

    print("Creating embeddings and indexing...")
    # Use Local Embeddings (HuggingFace)
    embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    
    target_dir = os.path.join(PERSIST_DIRECTORY, agent_id)
    print(f"Persisting to {target_dir}")
    
    vectorstore = Chroma.from_documents(
        documents=splits,
        embedding=embeddings,
        persist_directory=target_dir
    )
    print("Ingestion complete.")

def main(target_folder_id=None, agent_id="default"):
    if not CLIENT_ID or not CLIENT_SECRET or not TENANT_ID:
        print("Please set CLIENT_ID, CLIENT_SECRET, and TENANT_ID in .env")
        return

    print("Authenticating...")
    headers = get_header()
    
    print("Resolving Drive ID...")
    drive_id = get_drive_id(headers)
    print(f"Using Drive ID: {drive_id}")
    
    print("Listing and Processing files...")
    
    files_generator = list_files(headers, drive_id, target_folder_id)
    
    # Process in batches
    batch_size = 1
    batch = []
    
    for file_item in files_generator:
        batch.append(file_item)
        if len(batch) >= batch_size:
            print(f"Processing batch of {len(batch)} files...")
            try:
                paths = download_files(headers, batch)
                process_and_index(paths, agent_id)
            except Exception as e:
                print(f"Error processing batch: {e}")
            batch = []
            
    # Process remaining
    if batch:
        print(f"Processing final batch of {len(batch)} files...")
        try:
            paths = download_files(headers, batch)
            process_and_index(paths, agent_id)
        except Exception as e:
            print(f"Error processing batch: {e}")
            
    print("Ingestion complete.")

if __name__ == "__main__":
    main()
