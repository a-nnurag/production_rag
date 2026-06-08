from app.config import get_settings

settings = get_settings()

print("LangSmith Key:", settings.langchain_api_key[:10] + "...")
print("Tracing:", settings.langchain_tracing_v2)
print("Project:", settings.langchain_project)