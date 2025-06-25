import sys
import logging
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QLineEdit, QPushButton, QTextEdit,
    QMessageBox, QTabWidget, QHBoxLayout, QLabel, QSpinBox
)
from PyQt5.QtCore import Qt

from . import transcripts as tr
from . import summarizer as sz


class YouTubeSummarizerUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("YouTube Саммари")
        self.setGeometry(100, 100, 900, 700)
        self.font_size = 12
        self.transcript_fragments = None

        # Tabs
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)
        self._init_summary_tab()
        self._init_qa_tab()
        self._init_font_controls()

        self.setMinimumSize(700, 500)
        self.result_text.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.answer_text.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    # ---------- Tabs ----------
    def _init_summary_tab(self):
        self.summary_tab = QWidget()
        self.tabs.addTab(self.summary_tab, "Саммари")
        layout = QVBoxLayout(self.summary_tab)

        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("Введите ссылку на YouTube видео")
        layout.addWidget(self.url_input)

        self.summarize_button = QPushButton("Получить саммари")
        self.summarize_button.clicked.connect(self.process_input)
        layout.addWidget(self.summarize_button)

        self.result_text = QTextEdit(readOnly=True)
        self.result_text.setMinimumHeight(400)
        layout.addWidget(self.result_text, stretch=1)

    def _init_qa_tab(self):
        self.qa_tab = QWidget()
        self.tabs.addTab(self.qa_tab, "Вопросы к транскрипту")
        layout = QVBoxLayout(self.qa_tab)

        self.question_input = QLineEdit()
        self.question_input.setPlaceholderText("Введите вопрос по транскрипту")
        layout.addWidget(self.question_input)

        self.ask_button = QPushButton("Спросить")
        self.ask_button.clicked.connect(self.ask_about_transcript)
        layout.addWidget(self.ask_button)

        self.answer_text = QTextEdit(readOnly=True)
        self.answer_text.setMinimumHeight(300)
        layout.addWidget(self.answer_text, stretch=1)

    def _init_font_controls(self):
        font_layout = QHBoxLayout()
        font_label = QLabel("Размер шрифта:")
        font_layout.addWidget(font_label)
        self.font_spin = QSpinBox(minimum=8, maximum=48, value=self.font_size)
        self.font_spin.valueChanged.connect(self.set_font_size)
        font_layout.addWidget(self.font_spin)
        font_layout.addStretch(1)
        # добавляем в оба таба
        self.summary_tab.layout().addLayout(font_layout)
        self.qa_tab.layout().addLayout(font_layout)

    # ---------- Logic ----------
    def set_font_size(self, size):
        self.font_size = size
        for widget in (self.result_text, self.answer_text):
            f = widget.font(); f.setPointSize(size); widget.setFont(f)

    def process_input(self):
        url = self.url_input.text().strip()
        video_id = tr.extract_video_id(url)
        try:
            transcript_plain, self.transcript_fragments = tr.get_transcript(video_id)
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))
            return
        try:
            summary = sz.create_summary(transcript_plain)
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))
            return
        self.result_text.setPlainText(summary)
        self.tabs.setCurrentIndex(0)

    def seconds_to_timecode(self, seconds):
        import datetime
        return str(datetime.timedelta(seconds=int(seconds))).zfill(8)

    def ask_about_transcript(self):
        question = self.question_input.text().strip()
        if not question:
            QMessageBox.warning(self, "Вопрос", "Введите вопрос по транскрипту.")
            return
        if not self.transcript_fragments:
            QMessageBox.warning(self, "Транскрипт", "Сначала получите саммари, чтобы загрузить транскрипт.")
            return
        # Формируем транскрипт с таймкодами
        transcript_tc = "\n".join(
            f"[{self.seconds_to_timecode(f['start'])}] {f['text']}" for f in self.transcript_fragments
        )
        prompt = (
            "Вот транскрипт видео с YouTube (каждый фрагмент снабжён таймкодом):\n"
            """\n{transcript}\n""".format(transcript=transcript_tc) +
            f"\nВопрос: {question}\n\nЕсли в ответе ты ссылаешься на цитату, указывай таймкод [чч:мм:сс]."
        )
        try:
            answer = sz.create_summary(prompt)  # reuse ChatGPT call for Q&A
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))
            return
        self.answer_text.setPlainText(answer) 