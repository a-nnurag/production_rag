# debug_env.py

from app.config import get_settings
import os

print("DIRECT ENV:", os.getenv("GROQ_API_KEY"))

try:
    settings = get_settings()

    print("\nSETTINGS LOADED")
    print("groq_api_key exists:", bool(settings.groq_api_key))
    print("langchain_api_key exists:", bool(settings.langchain_api_key))

except Exception as e:
    print("\nSETTINGS ERROR")
    print(type(e).__name__)
    print(e)