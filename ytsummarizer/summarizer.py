import os
import requests

PROMPT_FILE = "prompt_summarizer.txt"

SYSTEM_PROMPT = "Ты — продвинутый ассистент для саммаризации текстов."

__all__ = ["create_summary"]

def _load_prompt_template():
    try:
        with open(PROMPT_FILE, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as exc:
        raise RuntimeError(f"Не удалось прочитать {PROMPT_FILE}: {exc}")

def create_summary(transcript: str) -> str:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY не найден в переменных окружения.")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    prompt_template = _load_prompt_template()
    prompt = prompt_template.replace("{{CONVERSATION_TEXT}}", transcript)

    data = {
        "model": "gpt-4-1106-preview",
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        "max_tokens": 4096,
        "temperature": 1.0,
    }

    resp = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=data)
    if resp.status_code == 200:
        return resp.json()["choices"][0]["message"]["content"].strip()
    raise RuntimeError(f"Ошибка при создании саммари: {resp.status_code} {resp.text}") 