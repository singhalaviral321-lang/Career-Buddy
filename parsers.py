# parsers.py
import pdfplumber
import docx
import os

def extract_text_from_pdf(pdf_path):
    """Extracts text from a PDF file."""
    text = ""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                text += page.extract_text() or ""
        return text
    except Exception as e:
        print(f"PDF parsing error: {e}")
        return "PDF_PARSING_ERROR" # Return a special string to indicate failure

def extract_text_from_docx(docx_path):
    """Extracts text from a DOCX file."""
    doc = docx.Document(docx_path)
    full_text = []
    for para in doc.paragraphs:
        full_text.append(para.text)
    return '\n'.join(full_text)

def get_text_from_file(file_obj):
    """
    Determines file type and extracts text accordingly.
    Handles Gradio's temporary file object.
    """
    if file_obj is None:
        return ""
    
    file_path = file_obj.name
    if file_path.endswith('.pdf'):
        return extract_text_from_pdf(file_path)
    elif file_path.endswith('.docx'):
        return extract_text_from_docx(file_path)
    else:
        # Fallback for plain text files
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
