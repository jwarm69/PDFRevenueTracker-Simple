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
    # Show the extracted text for debugging (in expander)
    with st.expander("🔍 View Extracted Text (OCR)", expanded=False):
        st.text(text)
    
    # NEW APPROACH: Handle actual business format
    # Format 1: '11. HRS 36 $195.88' (with dollar sign)
    # Format 2: '10 HRS 4 47.48' (without dollar sign) 
    
    with st.expander("🔍 View Pattern Matching Analysis", expanded=False):
    
        # Pattern 1: With dollar sign - handles periods after hour numbers
        # Supports full business day range: 07-23 (7 AM to 11 PM)
        # Supports comma-separated amounts: $1,270.17
        pattern_with_dollar = r'(\d{1,2})\.?\s*HRS\s+(\d+)\s+\$(\d{1,4}(?:,\d{3})*\.\d{2})'
        matches_with_dollar = re.findall(pattern_with_dollar, text)
        st.write(f"**💰 With $ sign:** {len(matches_with_dollar)} matches")
        for match in matches_with_dollar:
            hour = int(match[0])
            if 7 <= hour <= 23:  # Valid business hours range
                st.write(f"  Hour {match[0]}: Qty {match[1]}, Amount ${match[2]}")
            else:
                st.warning(f"  ⚠️ Unusual hour {match[0]} found - please verify")
    
        # Pattern 2: Without dollar sign - check line by line to avoid conflicts
        lines = text.split('\n')
        matches_no_dollar = []
        st.write(f"**📋 Without $ sign:** Processing {len(lines)} lines...")
        
        for line in lines:
            # Skip lines that already have $ (already processed above)
            if '$' in line:
                continue
            # Look for lines like '07 HRS 5 32.15' or '08 HRS 12 1,089.40' (no dollar sign)
            match = re.search(r'(\d{1,2})\.?\s*HRS\s+(\d+)\s+(\d{1,4}(?:,\d{3})*\.\d{2})', line)
            if match:
                hour = int(match.group(1))
                if 7 <= hour <= 23:  # Valid business hours range
                    matches_no_dollar.append(match.groups())
                    st.write(f"  Hour {match.group(1)}: Qty {match.group(2)}, Amount ${match.group(3)}")
                else:
                    st.warning(f"  ⚠️ Unusual hour {match.group(1)} found - please verify")
        
        st.write(f"**📊 Total found:** {len(matches_with_dollar) + len(matches_no_dollar)} entries")
    
    # Combine all matches and process
    data = []
    all_matches = matches_with_dollar + matches_no_dollar
    processing_errors = []
    
    for hour_str, qty_str, amount_str in all_matches:
        try:
            hour = int(hour_str)
            quantity = int(qty_str)
            amount = float(amount_str.replace(',', ''))
            
            # Validate hour range (business hours: 7 AM to 11 PM)
            if hour < 7 or hour > 23:
                processing_errors.append(f"⚠️ Skipped unusual hour: {hour} (outside typical business hours 7-23)")
                continue
            
            time_str = f"{hour:02d}:00"
            category = "Before 3:00 PM" if hour < 15 else "After 3:00 PM"
            
            data.append({
                "Hour": hour,
                "Time": time_str,
                "Revenue": amount,
                "Category": category,
                "Quantity": quantity
            })
            
        except Exception as e:
            processing_errors.append(f"❌ Error parsing: Hour {hour_str}, Qty {qty_str}, Amount ${amount_str} - {str(e)}")
    
    # Show processing errors in expander if any
    if processing_errors:
        with st.expander(f"⚠️ Processing Notes ({len(processing_errors)})", expanded=False):
            for error in processing_errors:
                st.write(error)
    
    # Sort by hour
    sorted_data = sorted(data, key=lambda x: x["Hour"])
    
    # Final summary - simplified for cleaner display
    if not sorted_data:
        st.error("❌ No data extracted at all!")
    
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
    
    # Calculate overall total revenue and quantity first
    total_revenue = df['Revenue'].sum()
    total_quantity = df['Quantity'].sum()
    
    # 🎯 PROMINENT SUMMARY AT TOP
    st.markdown("---")
    st.markdown("## 🏆 **Revenue Summary**")
    
    # Show totals in a prominent way at the top
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("💰 Total Revenue", f"${total_revenue:.2f}")
    with col2:
        st.metric("📋 Total Quantity", f"{int(total_quantity)}")
    with col3:
        hours_found = sorted(set(df['Hour'].tolist()))
        st.metric("🕰️ Hours Covered", f"{len(hours_found)}")
    
    # Show before/after 3PM breakdown prominently
    before_3pm = df[df['Category'] == 'Before 3:00 PM']['Revenue'].sum()
    after_3pm = df[df['Category'] == 'After 3:00 PM']['Revenue'].sum()
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric("🌅 Before 3:00 PM", f"${before_3pm:.2f}")
    with col2:
        st.metric("🌆 After 3:00 PM", f"${after_3pm:.2f}")
    
    st.markdown("---")
    
    # Show detailed breakdown in expander
    with st.expander("📊 View Detailed Statistics", expanded=True):
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
    
    # Fill NaN values in Quantity with a numeric value for display purposes
    # We'll format it separately for display
    df_display = formatted_df.copy()
    df_display['Quantity'] = df_display['Quantity'].apply(
        lambda x: "Unknown" if pd.isna(x) else str(int(x))
    )
    
    st.dataframe(df_display)
    
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
                # Extract text from images using OCR
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
