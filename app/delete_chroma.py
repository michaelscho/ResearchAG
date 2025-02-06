from chromadb.config import Settings
from chroma import get_chroma_client
from chromadb import Client

# Initialize ChromaDB client
#chroma_client = Client(Settings(persist_directory="./chroma_data"))
chroma_client = get_chroma_client()
# Force delete the collection
def delete_collection(collection_name):
    try:
        # Check if the collection exists
        collections = chroma_client.list_collections()
        print(collections)
        collection = chroma_client.get_collection(collection_name)
        
        if collection:
            chroma_client.delete_collection(collection_name)
            print(f"Collection '{collection_name}' deleted successfully.")
        else:
            print(f"Collection '{collection_name}' does not exist.")
    except Exception as e:
        print(f"Error deleting collection '{collection_name}': {str(e)}")

# Call the function
delete_collection("sources")
