import os
from dotenv import load_dotenv
import openai
from openai import OpenAI
import time

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))
api_key = os.getenv('OPENAI_API_KEY')


client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'), organization=os.getenv('OPENAI_ORGANIZATION'))

def get_response(prompt, model_name="gpt-3.5-turbo-1106"):
    for _ in range(3):
        try:
            completion = client.chat.completions.create(model=model_name, messages=[{'role': 'user', 'content': prompt}], temperature=0.0)
            return completion.choices[0].message.content
        except Exception as e:
            print(e)
            time.sleep(20)
            continue
    return None