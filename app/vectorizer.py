from transformers import AutoTokenizer, AutoModel
from sentence_transformers import SentenceTransformer
import torch

# Load the multilingual RoBERTa model and tokenizer
MULTILINGUAL_MODEL_NAME = "xlm-roberta-base"
tokenizer = AutoTokenizer.from_pretrained(MULTILINGUAL_MODEL_NAME)
model = AutoModel.from_pretrained(MULTILINGUAL_MODEL_NAME)

# Load the all-mpnet-v2 model for sources
ENGLISH_MODEL_NAME = "sentence-transformers/all-mpnet-base-v2"
english_model = SentenceTransformer(ENGLISH_MODEL_NAME)

# Use GPU if available
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model = model.to(device)


def vectorize_text(text):
    """
    Converts a piece of text into a vector using RoBERTa-XLM.
    Automatically uses GPU if available.
    """
    print(f"Starting vectorization with RoBERTa-XLM on: {text}")
    # Tokenize the input text
    inputs = tokenizer(text, return_tensors="pt", truncation=True, padding=True, max_length=512)

    # Move inputs to the correct device (CPU or GPU)
    inputs = {key: value.to(device) for key, value in inputs.items()}

    # Perform a forward pass to get embeddings
    with torch.no_grad():
        outputs = model(**inputs)

    # Extract the CLS token embedding (represents the entire input sequence)
    cls_embedding = outputs.last_hidden_state[:, 0, :].squeeze().cpu().numpy()

    print("Vectorization with RoBERTa-XLM completed.")
    return cls_embedding.tolist()  # Convert to list for JSON serialization


def vectorize_sources(text):
    """
    Converts a piece of text into a vector using all-mpnet-v2 (optimized for English).
    """
    print(f"Starting vectorization with all-mpnet-v2 on: {text}")
    # Use SentenceTransformers for embedding
    embedding = english_model.encode(text)

    print("Vectorization with all-mpnet-v2 completed.")
    return embedding.tolist()  # Convert to list for JSON serialization
