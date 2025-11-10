import os

from dotenv import load_dotenv

load_dotenv()


PG_DSN = os.getenv("PG_DSN", "")
ES_URL = os.getenv("ES_URL", "")
ES_INDEX = os.getenv("ES_INDEX", "")


# Modelo y endpoint: soporta servidores locales compatibles con OpenAI
LLM_MODEL = os.getenv("LLM_MODEL", "")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "")
