import pytesseract
from pdf2image import convert_from_bytes
import sys

# Get the PDF file path from command line argument
pdf_path = sys.argv[1]

# Convert PDF to images
print(f"Converting {pdf_path} to images...")
images = convert_from_bytes(open(pdf_path, 'rb').read())
print(f"Number of pages: {len(images)}")

# Extract text from images using OCR
print("Extracting text using OCR...")
for i, img in enumerate(images):
    text = pytesseract.image_to_string(img)
    print(f"\n--- Page {i+1} ---")
    print(text)