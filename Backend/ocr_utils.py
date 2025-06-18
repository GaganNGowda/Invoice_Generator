# ocr_utils.py

from PIL import Image
import pytesseract
import io

def extract_text_from_image(file: bytes) -> str:
    """Extracts text from an image file (bytes) using Tesseract OCR."""
    try:
        image = Image.open(io.BytesIO(file))
        text = pytesseract.image_to_string(image)
        return text.strip()
    except Exception as e:
        return f"Error reading image: {e}"
