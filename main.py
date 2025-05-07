import sys
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QLineEdit, QPushButton, QTextEdit, QMessageBox,
    QTabWidget, QHBoxLayout, QLabel, QSpinBox
)
from PyQt5.QtCore import Qt
import requests
from youtube_transcript_api import YouTubeTranscriptApi
import os
import datetime

class YouTubeSummarizer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('YouTube Саммари')
        self.setGeometry(100, 100, 900, 700)
        self.font_size = 12
        self.transcript_fragments = None

        # QTabWidget
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        # --- Вкладка Саммари ---
        self.summary_tab = QWidget()
        self.tabs.addTab(self.summary_tab, 'Саммари')
        summary_layout = QVBoxLayout(self.summary_tab)
        summary_layout.setContentsMargins(5, 5, 5, 5)
        summary_layout.setSpacing(8)

        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText('Введите ссылку на YouTube видео')
        summary_layout.addWidget(self.url_input)

        self.summarize_button = QPushButton('Получить саммари')
        self.summarize_button.clicked.connect(self.process_input)
        summary_layout.addWidget(self.summarize_button)

        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        self.result_text.setMinimumHeight(400)
        self.result_text.setLineWrapMode(QTextEdit.WidgetWidth)
        summary_layout.addWidget(self.result_text, stretch=1)

        # --- Вкладка Вопросы ---
        self.qa_tab = QWidget()
        self.tabs.addTab(self.qa_tab, 'Вопросы к транскрипту')
        qa_layout = QVBoxLayout(self.qa_tab)
        qa_layout.setContentsMargins(5, 5, 5, 5)
        qa_layout.setSpacing(8)

        self.question_input = QLineEdit()
        self.question_input.setPlaceholderText('Введите вопрос по транскрипту')
        qa_layout.addWidget(self.question_input)

        self.ask_button = QPushButton('Спросить')
        self.ask_button.clicked.connect(self.ask_about_transcript)
        qa_layout.addWidget(self.ask_button)

        self.answer_text = QTextEdit()
        self.answer_text.setReadOnly(True)
        self.answer_text.setMinimumHeight(300)
        self.answer_text.setLineWrapMode(QTextEdit.WidgetWidth)
        qa_layout.addWidget(self.answer_text, stretch=1)

        # --- Управление шрифтом ---
        font_layout = QHBoxLayout()
        font_label = QLabel('Размер шрифта:')
        font_layout.addWidget(font_label)
        self.font_spin = QSpinBox()
        self.font_spin.setMinimum(8)
        self.font_spin.setMaximum(48)
        self.font_spin.setValue(self.font_size)
        self.font_spin.valueChanged.connect(self.set_font_size)
        font_layout.addWidget(self.font_spin)
        font_layout.addStretch(1)
        summary_layout.addLayout(font_layout)
        qa_layout.addLayout(font_layout)
        self.set_font_size(self.font_size)

        self.setMinimumSize(700, 500)
        self.result_text.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.result_text.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.answer_text.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.answer_text.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)

    def set_font_size(self, size):
        self.font_size = size
        font = self.result_text.font()
        font.setPointSize(size)
        self.result_text.setFont(font)
        self.answer_text.setFont(font)

    def seconds_to_timecode(self, seconds):
        return str(datetime.timedelta(seconds=int(seconds))).zfill(8)

    def get_transcript(self, video_id):
        try:
            transcript = None
            # Сначала пробуем английский
            try:
                transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=['en'])
            except Exception:
                pass
            # Затем пробуем русский
            if transcript is None:
                try:
                    transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=['ru'])
                except Exception:
                    pass
            # Если не удалось — пробуем взять первый доступный
            if transcript is None:
                list_transcripts = YouTubeTranscriptApi.list_transcripts(video_id)
                for tr in list_transcripts:
                    try:
                        transcript = tr.fetch()
                        break
                    except Exception:
                        continue
            if not transcript:
                QMessageBox.critical(self, 'Ошибка', 'Не удалось найти доступный транскрипт для этого видео.')
                return None
            # Сохраняем фрагменты с таймкодами
            self.transcript_fragments = [
                {'start': entry['start'], 'text': entry['text']} for entry in transcript
            ]
            # Для summary возвращаем просто текст
            return ' '.join([entry['text'] for entry in transcript])
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
                self.tabs.setCurrentIndex(0)

    def ask_about_transcript(self):
        question = self.question_input.text().strip()
        if not question:
            QMessageBox.warning(self, 'Вопрос', 'Введите вопрос по транскрипту.')
            return
        if not self.transcript_fragments:
            QMessageBox.warning(self, 'Транскрипт', 'Сначала получите саммари, чтобы загрузить транскрипт.')
            return
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            QMessageBox.critical(self, 'Ошибка', 'OPENAI_API_KEY не найден в переменных окружения.')
            return
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }
        # Формируем транскрипт с таймкодами
        transcript_with_timecodes = '\n'.join([
            f"[{self.seconds_to_timecode(f['start'])}] {f['text']}" for f in self.transcript_fragments
        ])
        prompt = (
            f'Вот транскрипт видео с YouTube (каждый фрагмент снабжён таймкодом):\n"""\n{transcript_with_timecodes}\n"""\n\n'
            f'Вопрос: {question}\n\n'
            'Если в ответе ты ссылаешься на конкретную цитату или фрагмент, обязательно указывай таймкод в формате [чч:мм:сс] перед цитатой или после неё. Отвечай максимально подробно и по-русски.'
        )
        data = {
            'model': 'gpt-4o',
            'messages': [
                {'role': 'system', 'content': 'Ты — эксперт по анализу транскриптов видео.'},
                {'role': 'user', 'content': prompt}
            ],
            'max_tokens': 1024,
            'temperature': 0.7
        }
        self.answer_text.clear()
        self.answer_text.setPlainText('Жду ответ от GPT-4o...')
        try:
            response = requests.post('https://api.openai.com/v1/chat/completions', headers=headers, json=data)
            if response.status_code == 200:
                answer = response.json()['choices'][0]['message']['content'].strip()
                self.answer_text.setPlainText(answer)
            else:
                self.answer_text.setPlainText(f'Ошибка: {response.status_code}\n{response.text}')
        except Exception as e:
            self.answer_text.setPlainText(f'Ошибка: {e}')

def main():
    app = QApplication(sys.argv)
    window = YouTubeSummarizer()
    window.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main() 