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
    
    # Preprocess text to standardize it a bit
    # Replace multiple spaces with a single space
    text = re.sub(r'\s+', ' ', text)
    
    # Find all patterns that look like hour entries with revenue
    # More flexible pattern to catch different variations
    pattern = r'(\d{1,2})\s*(?:HRS|HR5|HRS\'|HRS\"|\bH\b)\s*(\d+)\s*\$(\d+\.\d{2})'
    matches = re.findall(pattern, text)
    
    # Also try to catch entries that might have gotten split differently
    alt_pattern = r'(\d{1,2})\s*(?:HRS|HR5|HRS\'|HRS\"|\bH\b).*?\$(\d+\.\d{2})'
    alt_matches = re.findall(alt_pattern, text)
    
    print(f"Found {len(matches)} entries with quantity and {len(alt_matches)} additional entries without quantity")
    
    data = []
    # Process entries with quantity
    for hour_str, qty_str, amount_str in matches:
        try:
            # Parse the hour (24-hour format)
            hour = int(hour_str)
            
            # Parse the quantity
            quantity = int(qty_str)
            
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
                "Quantity": quantity
            })
            print(f"Added: Hour {hour}, Qty {quantity}, Amount ${amount}")
        except Exception as e:
            print(f"Error parsing entry with quantity 'Hour: {hour_str}, Qty: {qty_str}, Amount: ${amount_str}': {str(e)}")
    
    # Process entries without quantity from alt_pattern
    for hour_str, amount_str in alt_matches:
        # Skip if we already have this hour from the primary pattern
        hour = int(hour_str)
        if any(item["Hour"] == hour for item in data):
            continue
            
        try:
            # Parse the amount
            amount = float(amount_str)
            
            # Create a formatted time string
            time_str = f"{hour:02d}:00"
            
            # Determine if the time is before or after 3PM
            category = "Before 3:00 PM" if hour < 15 else "After 3:00 PM"
            
            # Look through the text to try to find the quantity
            qty_pattern = fr'{hour_str}\s*(?:HRS|HR5|HRS\'|HRS\"|\bH\b)\s*(\d+)'
            qty_match = re.search(qty_pattern, text)
            quantity = int(qty_match.group(1)) if qty_match else None
            
            data.append({
                "Hour": hour,
                "Time": time_str,
                "Revenue": amount,
                "Category": category,
                "Quantity": quantity
            })
            print(f"Added (alt): Hour {hour}, Qty {quantity}, Amount ${amount}")
        except Exception as e:
            print(f"Error parsing entry without quantity 'Hour: {hour_str}, Amount: ${amount_str}': {str(e)}")
    
    # Sort by hour
    sorted_data = sorted(data, key=lambda x: x["Hour"])
    
    return pd.DataFrame(sorted_data)

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