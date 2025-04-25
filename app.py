import streamlit as st
import pandas as pd
import re
import io
import tempfile
import os
from datetime import datetime
from pdf2image import convert_from_path, convert_from_bytes
import pytesseract
from PIL import Image

# Set page configuration
st.set_page_config(
    page_title="Revenue Log Analyzer",
    page_icon="📊",
    layout="wide"
)

# Title and description
st.title("PDF Revenue Log Analyzer")
st.markdown("""
This application processes PDF revenue logs, extracts time and amount data using OCR, 
and provides before/after 3PM revenue analytics.
""")

# Function to convert PDF to images
def convert_pdf_to_images(pdf_file):
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_pdf:
            temp_pdf.write(pdf_file.read())
            temp_pdf_path = temp_pdf.name
        
        # Convert PDF to images
        images = convert_from_bytes(open(temp_pdf_path, 'rb').read())
        os.unlink(temp_pdf_path)  # Delete the temporary file
        
        return images
    except Exception as e:
        st.error(f"Error converting PDF to images: {str(e)}")
        return None

# Function to extract text from images using OCR
def extract_text_from_images(images):
    all_text = []
    progress_bar = st.progress(0)
    
    for i, img in enumerate(images):
        # Extract text from image using pytesseract
        text = pytesseract.image_to_string(img)
        all_text.append(text)
        progress_bar.progress((i + 1) / len(images))
    
    return "\n".join(all_text)

# Function to parse the extracted text
def parse_revenue_data(text):
    # Preprocess text to standardize it a bit
    # Replace multiple spaces with a single space
    text = re.sub(r'\s+', ' ', text)
    
    # Show the extracted text for debugging
    st.write("### Extracted Text (OCR)")
    st.text(text)
    
    # Find all patterns that look like hour entries with revenue
    # More flexible pattern to catch different variations
    pattern = r'(\d{1,2})\s*(?:HRS|HR5|HRS\'|HRS\"|\bH\b)\s*(\d+)\s*\$(\d+\.\d{2})'
    matches = re.findall(pattern, text)
    
    # Also try to catch entries that might have gotten split differently
    alt_pattern = r'(\d{1,2})\s*(?:HRS|HR5|HRS\'|HRS\"|\bH\b).*?\$(\d+\.\d{2})'
    alt_matches = re.findall(alt_pattern, text)
    
    st.write(f"Found {len(matches)} entries with quantity and {len(alt_matches)} additional entries without quantity")
    
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
        except Exception as e:
            st.warning(f"Error parsing entry with quantity 'Hour: {hour_str}, Qty: {qty_str}, Amount: ${amount_str}': {str(e)}")
    
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
        except Exception as e:
            st.warning(f"Error parsing entry without quantity 'Hour: {hour_str}, Amount: ${amount_str}': {str(e)}")
    
    # Sort by hour
    sorted_data = sorted(data, key=lambda x: x["Hour"])
    
    return pd.DataFrame(sorted_data)

# Function to analyze the revenue data
def analyze_revenue_data(df):
    if df.empty:
        return pd.DataFrame()
    
    # Group by category and calculate statistics
    stats = df.groupby('Category').agg(
        Total_Revenue=('Revenue', 'sum'),
        Entry_Count=('Revenue', 'count'),
        Average_Revenue=('Revenue', 'mean'),
        Total_Quantity=('Quantity', 'sum')
    ).reset_index()
    
    # Replace NaN values in Total_Quantity with 0
    stats['Total_Quantity'] = stats['Total_Quantity'].fillna(0).astype(int)
    
    return stats

# Function to display the revenue data and analytics
def display_revenue_data(df, stats):
    if df.empty:
        st.warning("No revenue data was extracted from the PDF.")
        return
    
    st.subheader("Revenue Data Analysis")
    
    # Display the analytics
    st.markdown("### Summary Statistics")
    
    # Format the statistics dataframe for display
    formatted_stats = stats.copy()
    formatted_stats['Total_Revenue'] = formatted_stats['Total_Revenue'].apply(lambda x: f"${x:.2f}")
    formatted_stats['Average_Revenue'] = formatted_stats['Average_Revenue'].apply(lambda x: f"${x:.2f}")
    formatted_stats = formatted_stats.rename(columns={
        'Category': 'Time Period',
        'Total_Revenue': 'Total Revenue',
        'Entry_Count': 'Number of Entries',
        'Average_Revenue': 'Average Revenue',
        'Total_Quantity': 'Total Quantity'
    })
    
    st.table(formatted_stats)
    
    # Display all entries in a table
    st.markdown("### All Revenue Entries")
    
    # Format the dataframe for display
    formatted_df = df.copy()
    formatted_df['Revenue'] = formatted_df['Revenue'].apply(lambda x: f"${x:.2f}")
    
    # Fill NaN values in Quantity with "N/A"
    formatted_df['Quantity'] = formatted_df['Quantity'].fillna("Unknown")
    
    st.dataframe(formatted_df)
    
    # Provide CSV download option
    csv = df.to_csv(index=False)
    st.download_button(
        label="Download as CSV",
        data=csv,
        file_name="revenue_data.csv",
        mime="text/csv"
    )

# Main function
def main():
    # File uploader
    uploaded_file = st.file_uploader("Upload a PDF file containing revenue logs", type=["pdf"])
    
    if uploaded_file is not None:
        with st.spinner("Processing PDF file..."):
            # Convert PDF to images
            images = convert_pdf_to_images(uploaded_file)
            
            if images:
                # Extract text from images
                with st.spinner("Extracting text using OCR..."):
                    extracted_text = extract_text_from_images(images)
                
                # Parse the extracted text
                with st.spinner("Parsing revenue data..."):
                    df = parse_revenue_data(extracted_text)
                
                # Analyze the revenue data
                stats = analyze_revenue_data(df)
                
                # Display the revenue data and analytics
                display_revenue_data(df, stats)
            else:
                st.error("Failed to process the PDF file.")

if __name__ == "__main__":
    main()
