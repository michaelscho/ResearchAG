def chunk_text_with_page_numbers(page_texts, max_length=500):
    """
    Splits text from a dictionary of page numbers and texts into chunks of a specified maximum length.
    
    Args:
        page_texts (dict): A dictionary where keys are page numbers and values are page texts.
        max_length (int): Maximum length of each chunk (in words).

    Returns:
        list: A list of tuples containing the chunk text and the page number it came from.
    """
    print("Starting chunking process")
    chunks_with_metadata = []

    for page_number, page_text in page_texts.items():
        words = page_text.split()
        current_chunk = []

        for word in words:
            current_chunk.append(word)
            if len(current_chunk) >= max_length:
                chunks_with_metadata.append((" ".join(current_chunk), page_number))
                current_chunk = []

        if current_chunk:
            chunks_with_metadata.append((" ".join(current_chunk), page_number))
    print("Finishing chunking process")

    return chunks_with_metadata
