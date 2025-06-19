# ocr_utils.py
import pytesseract # <--- THIS LINE IS CRUCIAL AND MUST BE PRESENT
from PIL import Image
import io
from pdf2image import convert_from_bytes # Import only what's needed for pdf2image

def extract_text_from_document(document_bytes: bytes, content_type: str) -> str:
    """
    Extracts text from image or PDF document bytes using Tesseract OCR.

    Args:
        document_bytes: The byte content of the document (image or PDF).
        content_type: The MIME type of the document (e.g., 'image/png', 'application/pdf').

    Returns:
        The extracted text as a string.

    Raises:
        Exception: If Tesseract executable is not found, Poppler is not found (for PDFs),
                   or OCR fails for other reasons, or unsupported file type.
    """
    extracted_text = ""

    # Configure Tesseract command path if necessary.
    # Uncomment and set the path if Tesseract is not in your system's PATH.
    # Example for macOS/Linux:
    # pytesseract.pytesseract.tesseract_cmd = '/usr/local/bin/tesseract'
    # Example for Windows:
    # pytesseract.pytesseract.tesseract_cmd = 'C:\\Program Files\\Tesseract-OCR\\tesseract.exe'

    if content_type.startswith('image/'):
        try:
            image = Image.open(io.BytesIO(document_bytes))
            # Perform OCR on the image. 'lang' specifies the language(s) (e.g., 'eng' for English).
            extracted_text = pytesseract.image_to_string(image, lang='eng')
        except pytesseract.TesseractNotFoundError:
            # Raise an error if Tesseract executable is not found.
            raise Exception("Tesseract OCR engine not found. Please install it from https://tesseract-ocr.github.io/tessdoc/Installation.html and ensure it's in your system's PATH or configured in ocr_utils.py.")
        except Exception as e:
            # Catch other image processing errors.
            raise Exception(f"Error processing image for OCR: {e}. Ensure it's a valid image file.")
    elif content_type == 'application/pdf':
        try:
            # Convert PDF pages to PIL Image objects.
            # If Poppler is not in your system's PATH, you'll need to provide `poppler_path`.
            # Example for macOS Homebrew installation: poppler_path='/opt/homebrew/bin'
            # Example for Windows: poppler_path=r'C:\path\to\poppler\bin'
            images = convert_from_bytes(document_bytes)

            if not images:
                raise Exception("No pages found in the PDF or PDF is empty after conversion.")

            # Iterate through each page image and extract text
            for i, image in enumerate(images):
                page_text = pytesseract.image_to_string(image, lang='eng')
                extracted_text += page_text + "\n" # Add a newline to separate text from different pages
        except pytesseract.TesseractNotFoundError:
            # Raise an error if Tesseract executable is not found.
            raise Exception("Tesseract OCR engine not found. Please install it from https://tesseract-ocr.github.io/tessdoc/Installation.html and ensure it's in your system's PATH or configured in ocr_utils.py.")
        except Exception as e:
            # This broad exception catches issues with Poppler not being found,
            # corrupted PDFs, or other conversion errors.
            error_message = str(e).lower()
            if "poppler" in error_message or "pdfinfo" in error_message or "gs" in error_message:
                raise Exception(f"Poppler (or Ghostscript) is not found or not configured for PDF OCR: {e}. Please install Poppler and ensure it's in your system's PATH, or provide `poppler_path` to `convert_from_bytes` in ocr_utils.py.")
            if "invalid file format" in error_message or "cannot open file" in error_message:
                 raise Exception(f"Error reading PDF: {e}. The file might be corrupted or not a valid PDF.")
            raise Exception(f"An unexpected error occurred during PDF OCR: {e}. Ensure it's a valid PDF file.")
    else:
        # Raise an error for unsupported file types.
        raise Exception(f"Unsupported file type for OCR: {content_type}. Only images (PNG, JPG, etc.) and PDFs are supported.")

    return extracted_text.strip()
