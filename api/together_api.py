import os
import time
from dotenv import load_dotenv
from together import Together

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))
api_key = os.getenv('TOGETHER_API_KEY')

client = Together(api_key=api_key)

def get_response(prompt, model_name="mistralai/Mistral-7B-Instruct-v0.2"):
    for _ in range(3):
        try:
            response = client.chat.completions.create(
                model=model_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0
            )
            return response.choices[0].message.content
        except Exception as e:
            print(e)
            time.sleep(20)
            continue  
    return None
    