import pytesseract
from pdf2image import convert_from_bytes
import pandas as pd
import re
import sys

def convert_pdf_to_images(pdf_path):
    print(f"Converting {pdf_path} to images...")
    images = convert_from_bytes(open(pdf_path, 'rb').read())
    print(f"Number of pages: {len(images)}")
    return images

def extract_text_from_images(images):
    print("Extracting text using OCR...")
    all_text = []
    for i, img in enumerate(images):
        text = pytesseract.image_to_string(img)
        all_text.append(text)
    return "\n".join(all_text)

def parse_revenue_data(text):
    print("Parsing revenue data...")
    # Print text for debugging
    print("Extracted text:")
    print(text)
    
    # Regex pattern to match time and amount pattern like "11 HRS    $122.57"
    pattern = r'(\d{1,2})\s+HRS\s+\d+\s+\$(\d+\.\d{2})'
    matches = re.findall(pattern, text)
    
    print(f"Found {len(matches)} revenue entries")
    
    data = []
    for hour_str, amount_str in matches:
        # Parse the hour (24-hour format)
        hour = int(hour_str)
        
        # Parse the amount
        amount = float(amount_str)
        
        # Create a formatted time string
        time_str = f"{hour:02d}:00"
        
        # Determine if the time is before or after 3PM
        category = "Before 3:00 PM" if hour < 15 else "After 3:00 PM"
        
        data.append({
            "Hour": hour,
            "Time": time_str,
            "Revenue": amount,
            "Category": category,
            "Quantity": None  # We'll try to extract this in a separate pass
        })
    
    # Try to extract quantities separately
    quantity_pattern = r'(\d{1,2})\s+HRS\s+(\d+)\s+\$'
    quantity_matches = re.findall(quantity_pattern, text)
    
    # Create a dictionary to map hours to quantities
    hour_to_quantity = {}
    for hour_str, qty_str in quantity_matches:
        try:
            hour = int(hour_str)
            quantity = int(qty_str)
            hour_to_quantity[hour] = quantity
            print(f"Hour {hour}: Quantity {quantity}")
        except Exception as e:
            print(f"Error parsing quantity: {e}")
    
    # Update quantities in the data
    for item in data:
        hour = item["Hour"]
        if hour in hour_to_quantity:
            item["Quantity"] = hour_to_quantity[hour]
    
    return pd.DataFrame(data)

def main():
    if len(sys.argv) != 2:
        print("Usage: python test_sample.py <pdf_file>")
        return
        
    pdf_path = sys.argv[1]
    images = convert_pdf_to_images(pdf_path)
    text = extract_text_from_images(images)
    df = parse_revenue_data(text)
    
    print("\nExtracted Data:")
    print(df)
    
    # Analyze data
    before_3pm = df[df['Category'] == "Before 3:00 PM"]
    after_3pm = df[df['Category'] == "After 3:00 PM"]
    
    print("\nBefore 3:00 PM:")
    print(f"Total Revenue: ${before_3pm['Revenue'].sum():.2f}")
    print(f"Entry Count: {len(before_3pm)}")
    print(f"Average Revenue: ${before_3pm['Revenue'].mean():.2f}")
    print(f"Total Quantity: {before_3pm['Quantity'].sum()}")
    
    print("\nAfter 3:00 PM:")
    print(f"Total Revenue: ${after_3pm['Revenue'].sum():.2f}")
    print(f"Entry Count: {len(after_3pm)}")
    print(f"Average Revenue: ${after_3pm['Revenue'].mean():.2f}")
    print(f"Total Quantity: {after_3pm['Quantity'].sum()}")

if __name__ == "__main__":
    main()