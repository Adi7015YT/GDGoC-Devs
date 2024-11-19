import streamlit as st
import os
import json
import requests
from google.oauth2 import service_account
from google.auth.transport.requests import Request

class GeminiApiClient:
    def __init__(self, project_id, location_id, credentials):
        self.project_id = project_id
        self.location_id = location_id
        self.api_endpoint = f"https://{location_id}-aiplatform.googleapis.com"
        self.credentials = credentials

    def generate_content(self, model_id, request_data):
        """Make an authenticated request to the Gemini API"""
        url = f"{self.api_endpoint}/v1/projects/{self.project_id}/locations/{self.location_id}/publishers/google/models/{model_id}:generateContent"  # Removed stream endpoint

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.credentials.token}"
        }

        response = requests.post(url, headers=headers, json=request_data)
        
        if response.status_code != 200:
            raise Exception(f"API request failed with status {response.status_code}: {response.text}")

        # Return raw text from response
        try:
            response_json = response.json()
            # Print response for debugging
            print("API Response:", response_json)
            return response_json.get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0].get('text', 'No response generated')
        except Exception as e:
            print(f"Error parsing response: {e}")
            return str(response.text)

def main():
    st.set_page_config(page_title="Gemini AI Assistant", page_icon="🤖", layout="wide")
    
    # Sidebar for configuration
    with st.sidebar:
        st.header("Configuration")
        project_id = st.text_input("Project ID", "daytona-hehe")
        location_id = st.text_input("Location ID", "us-central1")
        model_id = st.text_input("Model ID", "gemini-1.5-flash-002")
        
        st.header("Service Account")
        service_account_json = st.text_area(
            "Service Account JSON",
            placeholder="Paste your service account JSON here...",
            height=200
        )

        page = st.radio("Select Mode", ["Basic Tutor", "Quiz Generator", "Image Analysis"])

    if not service_account_json:
        st.error("Please provide service account credentials in the sidebar.")
        return

    try:
        service_account_info = json.loads(service_account_json)
        credentials = service_account.Credentials.from_service_account_info(
            service_account_info,
            scopes=['https://www.googleapis.com/auth/cloud-platform']
        )
        
        if not credentials.valid:
            credentials.refresh(Request())
        
        client = GeminiApiClient(project_id, location_id, credentials)

        if page == "Basic Tutor":
            st.title("🎓 AI Tutor Assistant")
            
            with st.form("tutor_form"):
                query = st.text_area("Ask your question:", height=100)
                submit_button = st.form_submit_button("Get Answer", type="primary")
                
                if submit_button and query:
                    with st.spinner("Processing request..."):
                        request_data = {
                            "contents": [{
                                "role": "user",
                                "parts": [{"text": query}]
                            }]
                        }
                        
                        response_text = client.generate_content(model_id, request_data)
                        st.markdown("### Answer:")
                        st.write(response_text)

        elif page == "Quiz Generator":
            st.title("📝 Quiz Generator")
            
            with st.form("quiz_form"):
                col1, col2, col3 = st.columns(3)
                with col1:
                    subject = st.selectbox("Select Subject", 
                        ["Mathematics", "Science", "Social Studies"])
                
                with col2:
                    topics = {
                        "Mathematics": ["Algebra", "Geometry", "Arithmetic"],
                        "Science": ["Physics", "Chemistry", "Biology"],
                        "Social Studies": ["History", "Geography", "Civics"]
                    }
                    topic = st.selectbox("Select Topic", topics[subject])
                
                with col3:
                    difficulty = st.selectbox("Select Difficulty", 
                        ["Beginner", "Intermediate", "Advanced"])

                submit_quiz = st.form_submit_button("Generate Quiz", type="primary")
                
                if submit_quiz:
                    with st.spinner("Generating quiz..."):
                        prompt = f"""Generate 5 multiple choice questions for {subject} on the topic of {topic} at {difficulty} difficulty level.
                        Format: Question number, followed by question text, then A) B) C) D) options, and finally the correct answer with explanation.
                        """
                        
                        request_data = {
                            "contents": [{
                                "role": "user",
                                "parts": [{"text": prompt}]
                            }]
                        }
                        
                        quiz_text = client.generate_content(model_id, request_data)
                        st.markdown("### Quiz Questions")
                        st.write(quiz_text)

        else:  # Image Analysis
            st.title("🖼️ Image Analysis Assistant")
            
            with st.form("image_analysis_form"):
                query = st.text_area("What would you like to know about the image?", height=100)
                image_url = st.text_input("Image URL:", help="Enter the URL of the image you want to analyze")
                
                if image_url:
                    st.image(image_url, caption="Uploaded Image", use_column_width=True)
                
                submit_analysis = st.form_submit_button("Analyze Image", type="primary")
                
                if submit_analysis and image_url:
                    with st.spinner("Analyzing image..."):
                        request_data = {
                            "contents": [{
                                "role": "user",
                                "parts": [
                                    {"text": query},
                                    {
                                        "fileData": {
                                            "mimeType": "image/jpeg",
                                            "fileUri": image_url
                                        }
                                    }
                                ]
                            }]
                        }
                        
                        analysis_text = client.generate_content(model_id, request_data)
                        st.markdown("### Analysis:")
                        st.write(analysis_text)

    except Exception as e:
        st.error(f"Error: {str(e)}")
        st.error("Full error details for debugging:")
        st.code(str(e))

if __name__ == "__main__":
    main()