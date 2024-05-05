import os
from dotenv import load_dotenv
import time
import pathlib
import textwrap
import google.generativeai as genai

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))
api_key = os.getenv('GOOGLE_API_KEY')

genai.configure(api_key = api_key)

def get_response(prompt, model_name="gemini-1.0-pro"):
    model = genai.GenerativeModel(model_name)
    for _ in range(3):
        try:
            response = model.generate_content(prompt)
            return response.text
        except Exception as e:
            print(e)
            time.sleep(20)
            continue
    return None
"""
Available models as of 2024-05-04:
models/gemini-1.0-pro ** This is the model we will use
models/gemini-1.0-pro-001
models/gemini-1.0-pro-latest
models/gemini-1.0-pro-vision-latest
models/gemini-1.5-pro-latest
models/gemini-pro
models/gemini-pro-vision
"""
