#!/usr/bin/env python3
"""
Быстрый тест транскрипта для конкретного видео
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from ytsummarizer.transcripts import get_transcript
import logging

# Настройка логирования
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

def main():
    if len(sys.argv) < 2:
        print("Использование: python quick_transcript_test.py <URL>")
        print("Пример: python quick_transcript_test.py 'https://www.youtube.com/watch?v=dQw4w9WgXcQ'")
        return
    
    url = sys.argv[1]
    print(f"Тестирование транскрипта для: {url}")
    
    try:
        transcript = get_transcript(url)
        if transcript:
            print(f"✅ Транскрипт получен успешно!")
            print(f"Длина: {len(transcript)} символов")
            print(f"Первые 300 символов:\n{transcript[:300]}...")
        else:
            print("❌ Транскрипт не получен (пустой результат)")
    except Exception as e:
        print(f"❌ Ошибка при получении транскрипта: {e}")

if __name__ == "__main__":
    main()