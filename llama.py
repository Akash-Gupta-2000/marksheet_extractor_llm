import streamlit as st
import base64
import os
import json
import re
from groq import Groq
import pandas as pd

# Constants
GROQ_API_KEY = "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"  # Replace with your API key
GROQ_MODEL = "llama-3.2-90b-vision-preview"

# Set up the Groq client
os.environ["GROQ_API_KEY"] = GROQ_API_KEY
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# Function to encode image to base64
def encode_image(image_file):
    return base64.b64encode(image_file.read()).decode("utf-8")

# Function to extract JSON from response using regex
def parse_json_response(response_text):
    try:
        match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if match:
            json_text = match.group(0)
            return json.loads(json_text)
        else:
            return {"Error": "No valid JSON found in response"}
    except json.JSONDecodeError:
        return {"Error": "Invalid JSON format"}

# Function to send image to Groq API and extract marksheet data
def extract_marksheet_data(image_data):
    prompt_text = """
        Extract details from the provided mark sheet with 100% accuracy. 
        Do not assume or hallucinate any data. Maintain structured output as follows:

    **Student Information:**  
    - Candidate Name:  
    - Roll No.:  
    - Examination Year:  
                   
    **Final Status:**  
    - Result: [Pass/Fail]  

    Extract only the exact details as they appear on the document.
    Output the response strictly in JSON format:
    {"Name": "value", "Roll No.": "value", "Examination Year": "value", "Result": "value"}
    """

    payload = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": prompt_text},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_data}"}}
            ]
        }
    ]

    try:
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=payload,
            temperature=0,
            max_tokens=1024
        )
        raw_response = response.choices[0].message.content if response.choices else ""
        if not raw_response.strip():
            return {"Error": "Empty response from API"}
        extracted_data = parse_json_response(raw_response)
        return extracted_data
    except Exception as e:
        return {"Error": str(e)}

# --- Custom CSS for Full-Width Button and Table ---
st.markdown(
    """
    <style>
    .submit-button-container {
        display: flex;
        justify-content: center;
        margin-top: 20px;
        width: 100%;
    }
    .stButton button {
        width: 100%;
        max-width: 400px;
    }
    .stDataFrame {
        width: 100% !important;
    }
    </style>
    """,
    unsafe_allow_html=True
)

st.title("📜 Marksheet Data Extractor & Validator")
st.write("Enter the details manually and compare with the marksheet extraction.")

# --- Manual Entry Form ---
col1, col2 = st.columns(2)

with col1:
    st.subheader("Manual Entry")
    with st.form("manual_input_form"):
        manual_name = st.text_input("Name")
        manual_roll = st.text_input("Roll No.")
        manual_exam_year = st.text_input("Examination Year")
        manual_result = st.selectbox("Result", ["", "Pass", "Fail"])
        
        # Centering the Submit Button
        with st.container():
            submit_manual = st.form_submit_button("Submit Manual Details")

# --- File Uploader in Sidebar ---
uploaded_file = st.sidebar.file_uploader("Upload Marksheet Image", type=["jpg", "jpeg", "png"])

# --- Image Preview in Right Column ---
with col2:
    st.subheader("Image Preview")
    if uploaded_file:
        st.image(uploaded_file, caption="Uploaded Marksheet", use_container_width=True)
    else:
        st.info("No image uploaded.")

# --- Process Extraction & Comparison ---
if submit_manual and uploaded_file:
    with st.spinner("Extracting details from image..."):
        image_data = encode_image(uploaded_file)
        extracted_info = extract_marksheet_data(image_data)
    
    if "Error" in extracted_info:
        st.error(f"Error: {extracted_info['Error']}")
    else:
        st.subheader("Comparison Summary")
        fields = ["Name", "Roll No.", "Examination Year", "Result"]
        manual_values = {
            "Name": manual_name.strip(),
            "Roll No.": manual_roll.strip(),
            "Examination Year": manual_exam_year.strip(),
            "Result": manual_result.strip()
        }
        extracted_values = {
            "Name": extracted_info.get("Name", "N/A").strip(),
            "Roll No.": extracted_info.get("Roll No.", "N/A").strip(),
            "Examination Year": extracted_info.get("Examination Year", "N/A").strip(),
            "Result": extracted_info.get("Result", "N/A").strip()
        }
        
        # Create Comparison Table
        comparison = []
        for field in fields:
            m_val = manual_values[field]
            e_val = extracted_values[field]
            match = "Yes" if m_val and e_val and m_val.lower() == e_val.lower() else "No"
            comparison.append({
                "Field": field,
                "Manual Input": m_val if m_val else "Not Provided",
                "Extracted Value": e_val if e_val else "Not Provided",
                "Match": match
            })
        
        # Convert list to DataFrame
        comparison_df = pd.DataFrame(comparison)

        # Display table with full width
        st.dataframe(comparison_df, hide_index=True, use_container_width=True)
