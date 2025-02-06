from PyPDF2 import PdfReader

def extract_text_from_pdf_with_pages(file_path):
    """
    Extracts text from a PDF file, returning a dictionary of page numbers and text.
    """
    from PyPDF2 import PdfReader
    reader = PdfReader(file_path)
    page_texts = {}
    for page_number, page in enumerate(reader.pages, start=1):
        page_texts[page_number] = page.extract_text().replace("-\n", "")
    return page_texts