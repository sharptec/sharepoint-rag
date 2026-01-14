import os
import requests
from config import CLIENT_ID, CLIENT_SECRET, TENANT_ID, SHAREPOINT_SITE_ID, SHAREPOINT_DRIVE_ID
from azure.identity import ClientSecretCredential

def get_header():
    credential = ClientSecretCredential(
        tenant_id=TENANT_ID,
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET
    )
    token = credential.get_token("https://graph.microsoft.com/.default")
    return {"Authorization": f"Bearer {token.token}"}

def inspect_drive():
    headers = get_header()
    
    # Resolve Drive ID logic from ingest.py
    drive_id = SHAREPOINT_DRIVE_ID
    if not drive_id:
        if not SHAREPOINT_SITE_ID:
            print("No Site ID or Drive ID configured.")
            return
        print(f"Resolving drive for Site ID: {SHAREPOINT_SITE_ID}")
        url = f"https://graph.microsoft.com/v1.0/sites/{SHAREPOINT_SITE_ID}/drive"
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            print(f"Failed to resolve drive: {response.text}")
            return
        drive_id = response.json().get("id")
        print(f"Resolved Drive ID: {drive_id}")

    # List root children to find the exact folder
    url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/root/children?$top=100" # Increase top to catch it if many folders
    print(f"Listing root items to find 'ESSCom' from {url}...")
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
    except Exception as e:
        print(f"Request failed: {e}")
        return

    if response.status_code != 200:
        print(f"Error listing drive: {response.text}")
        return
        
    data = response.json()
    items = data.get("value", [])
    
    target_folder_id = None
    
    for item in items:
        name = item.get("name")
        if name.lower() == "esscom" and "folder" in item:
            print(f"Found Target Folder: {name}")
            print(f"ID: {item.get('id')}")
            target_folder_id = item.get('id')
            break
            
    if target_folder_id:
        print(f"TARGET_FOLDER_ID={target_folder_id}")
    else:
        print("Folder 'ESSCom' not found in root children.")

if __name__ == "__main__":
    inspect_drive()
