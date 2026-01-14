import requests
from config import CLIENT_ID, CLIENT_SECRET, TENANT_ID
from azure.identity import ClientSecretCredential

def get_header():
    credential = ClientSecretCredential(
        tenant_id=TENANT_ID,
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET
    )
    token = credential.get_token("https://graph.microsoft.com/.default")
    return {"Authorization": f"Bearer {token.token}"}

def list_sites():
    print("Authenticating...")
    try:
        headers = get_header()
    except Exception as e:
        print(f"Authentication failed: {e}")
        return

    print("Searching for sites...")
    # Search for all sites
    url = "https://graph.microsoft.com/v1.0/sites?search=*"
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        
        sites = data.get("value", [])
        print(f"\nFound {len(sites)} sites:\n")
        
        for site in sites:
            print(f"Name: {site.get('displayName')}")
            print(f"ID: {site.get('id')}")
            print(f"URL: {site.get('webUrl')}")
            print("-" * 50)
            
    except Exception as e:
        print(f"Error listing sites: {e}")
        if 'response' in locals():
            print(f"Response content: {response.text}")

if __name__ == "__main__":
    list_sites()
