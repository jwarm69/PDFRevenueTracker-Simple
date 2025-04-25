import os
import json
import base64
from openai import OpenAI

# Initialize the OpenAI client
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

def extract_data_from_pdf_text(text):
    """
    Use OpenAI's GPT model to extract structured hourly revenue data from PDF text
    """
    prompt = f"""
    Extract ALL hourly revenue data from the following text that was OCR'd from a PDF.
    
    VERY IMPORTANT: Pay extremely close attention to hours 14 (2 PM) and 15 (3 PM), which may be formatted as:
    - 14 HRS or 15 HRS
    - l4 HRS or l5 HRS (OCR might confuse 1 with l)
    - M HRS (might represent 14 in some cases)
    - 2 PM or 3 PM (in 12-hour format)
    
    The data usually follows this format: "HH HRS [Quantity] $[Amount]" where:
    - HH is the hour (numbers like 09, 10, 11, 12, 13, 14, 15, 16, etc.)
    - [Quantity] is the number of items (sometimes missing)
    - [Amount] is the dollar amount
    
    Return the data as a JSON array with each entry having:
    - "Hour": number (e.g., 9, 10, 11, 14, 15)
    - "Quantity": number or null if missing
    - "Revenue": dollar amount including $ symbol
    
    DO NOT make up or estimate any values. Only extract what is actually present in the text.
    
    Here's the text:
    {text}
    """
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o",  # Using the latest GPT-4o model
            messages=[
                {"role": "system", "content": "You are a precise data extraction system that outputs only JSON."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"}
        )
        
        result = json.loads(response.choices[0].message.content)
        
        # Ensure result contains a data array
        if "data" not in result:
            # If not in "data" property, the model might have just returned an array
            if isinstance(result, list):
                return result
            else:
                # Try to find any array property
                for key, value in result.items():
                    if isinstance(value, list):
                        return value
                # If nothing found, return empty list
                return []
        
        return result["data"]
    except Exception as e:
        raise Exception(f"Error extracting data with OpenAI: {str(e)}")

def analyze_image_for_revenue_data(image_base64):
    """
    Use OpenAI's vision capabilities to analyze an image for revenue data
    """
    prompt = """
    Analyze this image of a revenue log and extract all hourly revenue entries.
    
    VERY IMPORTANT: Look extremely carefully for hours 14 (2 PM) and 15 (3 PM).
    These hours may appear as "14 HRS", "14 HR", "14H", "l4 HRS", "14", or similar patterns.
    
    Each entry should have:
    - Hour (numeric value only, like 9, 10, 11, 14, 15)
    - Quantity (numeric value only, or null if missing)
    - Revenue (dollar amount, including the $ symbol)
    
    For hours around 2 PM and 3 PM, check for entries that might be:
    - 14 HRS or 15 HRS (standard format)
    - l4 HRS or l5 HRS (OCR might confuse 1 with l)
    - M HRS (might represent 14 in some cases)
    - Any entry with timestamps around 2PM or 3PM
    
    Only extract what you can actually see - do not make up or estimate values.
    Format your response as a JSON array of objects.
    """
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_base64}"
                            }
                        }
                    ]
                }
            ]
        )
        
        # Extract JSON from the response
        content = response.choices[0].message.content
        # Look for JSON content within the response
        start_idx = content.find('[')
        end_idx = content.rfind(']') + 1
        
        if start_idx >= 0 and end_idx > start_idx:
            json_str = content[start_idx:end_idx]
            return json.loads(json_str)
        else:
            # If no JSON array found, try to find any JSON object
            start_idx = content.find('{')
            end_idx = content.rfind('}') + 1
            
            if start_idx >= 0 and end_idx > start_idx:
                json_str = content[start_idx:end_idx]
                result = json.loads(json_str)
                
                # Check if result contains a data array
                if "data" in result and isinstance(result["data"], list):
                    return result["data"]
            
        # If all parsing attempts fail
        return []
    except Exception as e:
        raise Exception(f"Error analyzing image with OpenAI: {str(e)}")