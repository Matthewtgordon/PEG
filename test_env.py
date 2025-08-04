from dotenv import load_dotenv
import os

load_dotenv()

openai_key = os.getenv("OPENAI_API_KEY")
gemini_key = os.getenv("GEMINI_API_KEY")
github_token = os.getenv("GITHUB_PAT")

print("✅ OpenAI Key:", repr(openai_key))
print("✅ Gemini Key:", repr(gemini_key))
print("✅ GitHub Token:", repr(github_token))

