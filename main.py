import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QLineEdit, QPushButton, QTextEdit, QMessageBox
from PyQt5.QtCore import Qt
import requests
from youtube_transcript_api import YouTubeTranscriptApi
import os

class YouTubeSummarizer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('YouTube Саммари')
        self.setGeometry(100, 100, 900, 700)

        # Создаем центральный виджет и layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(8)

        # Поле для ввода ссылки
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText('Введите ссылку на YouTube видео')
        layout.addWidget(self.url_input)

        # Кнопка для получения саммари
        self.summarize_button = QPushButton('Получить саммари')
        self.summarize_button.clicked.connect(self.process_input)
        layout.addWidget(self.summarize_button)

        # Текстовое поле для вывода результата
        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        self.result_text.setMinimumHeight(400)
        self.result_text.setLineWrapMode(QTextEdit.WidgetWidth)
        layout.addWidget(self.result_text, stretch=1)

        # Растягиваемое окно
        self.setMinimumSize(700, 500)
        self.result_text.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.result_text.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)

    def get_transcript(self, video_id):
        try:
            # Сначала пробуем английский
            try:
                transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=['en'])
                return ' '.join([entry['text'] for entry in transcript])
            except Exception:
                pass
            # Затем пробуем русский
            try:
                transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=['ru'])
                return ' '.join([entry['text'] for entry in transcript])
            except Exception:
                pass
            # Если не удалось — пробуем взять первый доступный
            list_transcripts = YouTubeTranscriptApi.list_transcripts(video_id)
            for transcript in list_transcripts:
                try:
                    t = transcript.fetch()
                    return ' '.join([entry['text'] for entry in t])
                except Exception:
                    continue
            QMessageBox.critical(self, 'Ошибка', 'Не удалось найти доступный транскрипт для этого видео.')
            return None
        except Exception as e:
            QMessageBox.critical(self, 'Ошибка', f'Не удалось получить транскрипт: {e}')
            return None

    def create_summary(self, transcript):
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            QMessageBox.critical(self, 'Ошибка', 'OPENAI_API_KEY не найден в переменных окружения.')
            return None

        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }

        # Используем промпт из файла prompt_summarizer.txt
        try:
            with open('prompt_summarizer.txt', 'r', encoding='utf-8') as f:
                prompt_template = f.read()
        except Exception as e:
            QMessageBox.critical(self, 'Ошибка', f'Не удалось прочитать prompt_summarizer.txt: {e}')
            return None

        prompt = prompt_template.replace('{{CONVERSATION_TEXT}}', transcript)

        data = {
            'model': 'gpt-4o',
            'messages': [
                {'role': 'system', 'content': 'Ты — продвинутый ассистент для саммаризации текстов.'},
                {'role': 'user', 'content': prompt}
            ],
            'max_tokens': 1024,
            'temperature': 0.7
        }

        response = requests.post('https://api.openai.com/v1/chat/completions', headers=headers, json=data)
        if response.status_code == 200:
            return response.json()['choices'][0]['message']['content'].strip()
        else:
            QMessageBox.critical(self, 'Ошибка', f'Ошибка при создании саммари: {response.status_code}\n{response.text}')
            return None

    def process_input(self):
        video_url = self.url_input.text()
        video_id = video_url.split('v=')[1] if 'v=' in video_url else video_url
        transcript = self.get_transcript(video_id)
        if transcript:
            summary = self.create_summary(transcript)
            if summary:
                self.result_text.clear()
                self.result_text.setText(summary)
                self.result_text.moveCursor(0)

def main():
    app = QApplication(sys.argv)
    window = YouTubeSummarizer()
    window.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main() 