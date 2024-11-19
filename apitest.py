import os
import json
import requests
import streamlit as st
from dotenv import load_dotenv
from google.oauth2 import service_account
from google.auth.transport.requests import Request
from google.cloud import storage

# Load environment variables from .env file
load_dotenv()

class GeminiApiClient:
    def __init__(self, project_id, location_id, credentials):
        self.project_id = project_id
        self.location_id = location_id
        self.api_endpoint = f"https://{location_id}-aiplatform.googleapis.com"
        self.credentials = credentials

    def generate_content(self, model_id, request_data):
        """Make an authenticated request to the Gemini API"""
        url = f"{self.api_endpoint}/v1/projects/{self.project_id}/locations/{self.location_id}/publishers/google/models/{model_id}:generateContent"

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.credentials.token}"
        }

        response = requests.post(url, headers=headers, json=request_data)
        if response.status_code != 200:
            raise Exception(f"API request failed with status {response.status_code}: {response.text}")

        try:
            response_json = response.json()
            return response_json.get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0].get('text', 'No response generated')
        except Exception as e:
            print(f"Error parsing response: {e}")
            return str(response.text)

def upload_to_bucket(bucket_name, file, file_name):
    """Upload the file to a Google Cloud Storage bucket"""
    try:
        credentials = service_account.Credentials.from_service_account_info(
            json.loads(os.getenv("SERVICE_ACCOUNT_JSON"))
        )
        client = storage.Client(credentials=credentials)
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(file_name)
        blob.upload_from_file(file, content_type=file.type)
        return f"gs://{bucket_name}/{file_name}"
    except Exception as e:
        raise Exception(f"Error uploading to bucket: {str(e)}")

def main():
    st.set_page_config(page_title="Gemini AI Assistant", page_icon="🤖", layout="wide")
    
    # Sidebar for configuration
    with st.sidebar:
        st.header("Configuration")
        project_id = st.text_input("Project ID", "daytona-hehe")
        location_id = st.text_input("Location ID", "us-central1")
        model_id = st.text_input("Model ID", "gemini-1.5-flash-002")
        page = st.radio("Select Mode", ["Basic Tutor", "Quiz Generator", "Image Analysis"])

    # Load credentials from .env
    service_account_json = os.getenv("SERVICE_ACCOUNT_JSON")
    bucket_name = os.getenv("BUCKET_NAME", "your-bucket-name")

    if not service_account_json:
        st.error("Service account credentials not configured. Please set them in the .env file.")
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

        # Basic Tutor
        if page == "Basic Tutor":
            st.title("🎓 AI Tutor Assistant")
            with st.form("tutor_form"):
                query = st.text_area("Ask your question:", height=100)
                submit_button = st.form_submit_button("Get Answer", type="primary")
                if submit_button and query:
                    with st.spinner("Processing request..."):
                        request_data = {"contents": [{"role": "user", "parts": [{"text": query}]}]}
                        response_text = client.generate_content(model_id, request_data)
                        st.markdown("### Answer:")
                        st.write(response_text)

        # Quiz Generator
        elif page == "Quiz Generator":
            st.title("📝 Quiz Generator")
            with st.form("quiz_form"):
                col1, col2, col3 = st.columns(3)
                with col1:
                    subject = st.selectbox("Select Subject", ["Mathematics", "Science", "Social Studies"])
                with col2:
                    topics = {
                        "Mathematics": ["Algebra", "Geometry", "Arithmetic"],
                        "Science": ["Physics", "Chemistry", "Biology"],
                        "Social Studies": ["History", "Geography", "Civics"]
                    }
                    topic = st.selectbox("Select Topic", topics[subject])
                with col3:
                    difficulty = st.selectbox("Select Difficulty", ["Beginner", "Intermediate", "Advanced"])
                
                submit_quiz = st.form_submit_button("Generate Quiz", type="primary")

            if submit_quiz:
                with st.spinner("Generating quiz..."):
                    prompt = f"Generate a quiz with 5 multiple-choice questions on {subject}, focusing on {topic} at {difficulty} level. Include options, the correct answer, and an explanation."
                    
                    request_data = {
                        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
                        "generationConfig": {
                            "temperature": 1,
                            "maxOutputTokens": 8192,
                            "topP": 0.95,
                            "responseMimeType": "application/json",
                            "responseSchema": {
                                "type": "OBJECT",
                                "properties": {
                                    "questions": {
                                        "type": "ARRAY",
                                        "items": {
                                            "type": "OBJECT",
                                            "properties": {
                                                "question": {"type": "STRING"},
                                                "options": {"type": "ARRAY", "items": {"type": "STRING"}},
                                                "correctAnswer": {"type": "STRING"},
                                                "explanation": {"type": "STRING"}
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }

                    quiz_data = client.generate_content(model_id, request_data)

                    # Parse the response
                    try:
                        quiz = json.loads(quiz_data).get("questions", [])
                    except Exception as e:
                        st.error(f"Error parsing quiz data: {str(e)}")
                        quiz = []

                if quiz:
                    st.markdown("### Quiz Questions")
                    user_answers = {}

                    # Display the questions and options
                    with st.form("quiz_submission"):
                        for idx, question_data in enumerate(quiz):
                            question = question_data.get("question", "No question found")
                            options = question_data.get("options", [])
                            user_answers[idx] = st.radio(f"{idx + 1}. {question}", options, key=f"q{idx}")

                        submit_answers = st.form_submit_button("Submit Answers", type="primary")

                    if submit_answers:
                        st.markdown("### Results")
                        for idx, question_data in enumerate(quiz):
                            question = question_data.get("question", "No question found")
                            correct_answer = question_data.get("correctAnswer", "No correct answer provided")
                            explanation = question_data.get("explanation", "No explanation provided")

                            st.markdown(f"**{idx + 1}. {question}**")
                            st.write(f"**Your Answer:** {user_answers.get(idx, 'No answer')}") 
                            st.write(f"**Correct Answer:** {correct_answer}")
                            st.write(f"**Explanation:** {explanation}")
                            st.write("---")
                else:
                    st.error("Failed to generate quiz. Please try again.")

        # Image Analysis
        elif page == "Image Analysis":
            st.title("🖼️ Image Analysis Assistant")
            with st.form("image_analysis_form"):
                query = st.text_area("What would you like to know about the image?", height=100)
                uploaded_image = st.file_uploader("Upload an image for analysis", type=["jpg", "jpeg", "png"])
                submit_analysis = st.form_submit_button("Analyze Image", type="primary")

                if submit_analysis and uploaded_image:
                    file_name = uploaded_image.name
                    with st.spinner("Uploading image to Cloud Storage..."):
                        file_uri = upload_to_bucket(bucket_name, uploaded_image, file_name)

                    with st.spinner("Analyzing image with Gemini API..."):
                        request_data = {
                            "contents": [
                                {
                                    "role": "user",
                                    "parts": [
                                        {"text": query},
                                        {"fileData": {"mimeType": uploaded_image.type, "fileUri": file_uri}}
                                    ]
                                }
                            ]
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
