from chromadb.config import Settings
from chromadb import Client
from chromadb import PersistentClient
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from flask import current_app



path = "./chroma_data"

# Initialize ChromaDB client with the new configuration
def get_chroma_client():
    return PersistentClient(path=path)

# Get a specific collection
def get_collection(name):
    client = get_chroma_client()
    return client.get_or_create_collection(name)


def get_chroma_retriever(collection_name, model_name="xlm-roberta-base", k=5):
    # Access or initialize the cache
    cache = current_app.config.get('CACHE', {})
    retriever_cache_key = f"retriever_{collection_name}_{model_name}_{k}"

    # Check if the retriever is already cached
    if retriever_cache_key not in cache:
        # Create the embedding model
        embedding_model = HuggingFaceEmbeddings(model_name=model_name)
        
        # Create or load the vectorstore
        vectorstore = Chroma(
            collection_name=collection_name,
            embedding_function=embedding_model,
            persist_directory=path
        )
        
        # Create the retriever and cache it
        retriever = vectorstore.as_retriever(search_kwargs={"k": k})
        cache[retriever_cache_key] = retriever
        current_app.config['CACHE'] = cache
        
    # Return the cached retriever
    return cache[retriever_cache_key]




