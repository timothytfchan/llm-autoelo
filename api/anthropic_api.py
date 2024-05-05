import os
from dotenv import load_dotenv
import anthropic
import time

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))
api_key = os.getenv('ANTHROPIC_API_KEY')

client = anthropic.Anthropic(
    api_key=api_key,
)

def get_response(prompt, model_name="claude-instant-1.2"):
    for _ in range(3):
        try:
            message = client.messages.create(
                model= model_name,
                max_tokens=1000,
                temperature=0.0,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            return message.content[0].text
        except Exception as e:
            print(e)
            time.sleep(20)
            continue
    return None