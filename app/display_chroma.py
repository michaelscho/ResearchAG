from chromadb.config import Settings
from chroma import get_chroma_client
from chromadb import Client

# Initialize ChromaDB client
#chroma_client = Client(Settings(persist_directory="./chroma_data"))
chroma_client = get_chroma_client()
# Force delete the collection
def delete_collection(collection_name):
    # Check if the collection exists
    collections = chroma_client.list_collections()
    print(collections)
        
# Call the function
delete_collection("source")
