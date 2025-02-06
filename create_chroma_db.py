from app.chroma import get_chroma_client

def setup_collections():
    client = get_chroma_client()
    collections = ["sources", "literature", "notes"]
    
    for name in collections:
        client.get_or_create_collection(name)
        print(f"Collection '{name}' initialized.")
    
if __name__ == "__main__":
    setup_collections()
