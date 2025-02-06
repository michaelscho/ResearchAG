from app.chroma import get_collection

def check_collection(collection_name):
    """
    Fetches and displays all data in a specified ChromaDB collection.
    """
    try:
        # Get the specified collection
        collection = get_collection(collection_name)

        # Query the collection
        results = collection.get(include=["documents", "metadatas"])

        # Extract and display documents and metadata
        documents = results.get("documents", [])
        metadatas = results.get("metadatas", [])

        print(f"\n=== Data in Collection: {collection_name} ===\n")
        for i, (doc, meta) in enumerate(zip(documents, metadatas), start=1):
            print(f"Entry {i}:")
            print(f"  Document (English Content): {doc}")
            print(f"  Metadata: {meta}")
            print("-" * 50)

        print(f"Total Entries: {len(documents)}")

        # Check if the collection exists and print its metadata
        print(f"Collection name: {collection.name}")
        print(f"Number of items in collection: {len(collection)}")


    except Exception as e:
        print(f"Error accessing collection '{collection_name}': {e}")


if __name__ == "__main__":
    # Replace 'sources' with the name of the collection you want to check
    collection_name = "source"
    check_collection(collection_name)
