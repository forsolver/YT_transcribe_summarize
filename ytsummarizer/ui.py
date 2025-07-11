import sys
import logging
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QLineEdit, QPushButton, QTextEdit,
    QMessageBox, QTabWidget, QHBoxLayout, QLabel, QSpinBox
)
from PyQt5.QtCore import Qt

from . import transcripts as tr
from . import summarizer as sz
from . import video_processor as vp # Импортируем новый модуль


class YouTubeSummarizerUI(QMainWindow): # Переименуем позже, если будет иметь смысл
    def __init__(self):
        super().__init__()
        self.setWindowTitle("YouTube Инструменты") # Обновим заголовок
        self.setGeometry(100, 100, 900, 700)
        self.font_size = 12
        self.processed_transcript_fragments = None # Для хранения фрагментов с duration
        self.video_info = None # Для хранения общей информации о видео

        # Основная вкладка (пока одна)
        self.main_tab = QWidget()
        self.setCentralWidget(self.main_tab) # Устанавливаем как центральный виджет

        layout = QVBoxLayout(self.main_tab)

        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("Введите ссылку на YouTube видео или ID")
        layout.addWidget(self.url_input)

        # Горизонтальный layout для кнопок
        buttons_layout = QHBoxLayout()
        self.summarize_button = QPushButton("Получить саммари")
        self.summarize_button.clicked.connect(self.run_summarize)
        buttons_layout.addWidget(self.summarize_button)

        self.extract_tricks_button = QPushButton("Извлечь трюки")
        self.extract_tricks_button.clicked.connect(self.run_extract_tricks)
        buttons_layout.addWidget(self.extract_tricks_button)

        layout.addLayout(buttons_layout)

        self.output_text_area = QTextEdit(readOnly=True) # Общее текстовое поле для вывода
        self.output_text_area.setMinimumHeight(400)
        layout.addWidget(self.output_text_area, stretch=1)

        # Элементы управления шрифтом (добавляем прямо в основной layout)
        font_layout = QHBoxLayout()
        font_label = QLabel("Размер шрифта:")
        font_layout.addWidget(font_label)
        self.font_spin = QSpinBox(minimum=8, maximum=48, value=self.font_size)
        self.font_spin.valueChanged.connect(self.set_font_size_for_output)
        font_layout.addWidget(self.font_spin)
        font_layout.addStretch(1)
        layout.addLayout(font_layout)

        self.setMinimumSize(700, 500)
        self.output_text_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    def set_font_size_for_output(self, size):
        self.font_size = size
        font = self.output_text_area.font()
        font.setPointSize(size)
        self.output_text_area.setFont(font)

    def _fetch_transcript_data(self, video_id_or_url: str) -> bool:
        """
        Вспомогательный метод для получения и сохранения транскрипта и информации о видео.
        Возвращает True в случае успеха, False в случае ошибки.
        """
        self.output_text_area.clear() # Очищаем предыдущий вывод
        video_id = tr.extract_video_id(video_id_or_url)
        if not video_id:
            QMessageBox.critical(self, "Ошибка", "Не удалось извлечь ID видео из ссылки.")
            return False
        try:
            # get_transcript теперь возвращает (plain_text, processed_fragments, video_info)
            plain_transcript, fragments, info = tr.get_transcript(video_id)
            self.processed_transcript_fragments = fragments
            self.video_info = info
            # self.plain_transcript_text = plain_transcript # Сохраняем, если понадобится для Q&A или прямого отображения
            return True
        except Exception as e:
            self.processed_transcript_fragments = None
            self.video_info = None
            QMessageBox.critical(self, "Ошибка при получении транскрипта", str(e))
            return False

    def run_summarize(self):
        url = self.url_input.text().strip()
        if not self._fetch_transcript_data(url):
            return

        if not self.processed_transcript_fragments:
             QMessageBox.critical(self, "Ошибка", "Нет данных транскрипта для саммаризации.")
             return

        # Собираем plain_text из обработанных фрагментов для саммаризации
        plain_text_for_summary = " ".join(f["text"] for f in self.processed_transcript_fragments)

        try:
            summary = sz.create_summary(plain_text_for_summary)
            self.output_text_area.setPlainText(f"Саммари для видео \"{self.video_info.get('title', 'Без названия')}\":\n\n{summary}")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка при создании саммари", str(e))

    def run_extract_tricks(self):
        url = self.url_input.text().strip()
        if not self._fetch_transcript_data(url):
            return

        if not self.processed_transcript_fragments:
            QMessageBox.critical(self, "Ошибка", "Нет данных транскрипта для извлечения трюков.")
            return

        try:
            # Используем параметры по умолчанию для extract_trick_segments
            # Их можно будет вынести в UI, если потребуется настройка
            trick_segments = vp.extract_trick_segments(self.processed_transcript_fragments)

            if not trick_segments:
                self.output_text_area.setPlainText(f"Трюки не найдены в видео \"{self.video_info.get('title', 'Без названия')}\".")
                return

            result_lines = [f"Найденные трюковые сегменты для видео \"{self.video_info.get('title', 'Без названия')}\":\n"]
            for seg in trick_segments:
                start_td = self.seconds_to_timecode(seg['start'])
                end_td = self.seconds_to_timecode(seg['end'])
                duration_td = self.seconds_to_timecode(seg['duration'])
                result_lines.append(f"- Начало: {start_td}, Конец: {end_td} (Длительность: {duration_td})")

            self.output_text_area.setPlainText("\n".join(result_lines))

        except Exception as e:
            QMessageBox.critical(self, "Ошибка при извлечении трюков", str(e))
            logging.error(f"Ошибка при извлечении трюков: {e}", exc_info=True)

    def seconds_to_timecode(self, seconds):
        import datetime
        # Убедимся, что seconds это float или int
        if not isinstance(seconds, (int, float)):
            try:
                seconds = float(seconds)
            except (ValueError, TypeError):
                return "00:00:00" # Возвращаем дефолтное значение при ошибке
        ts = str(datetime.timedelta(seconds=int(round(seconds)))).split('.')[0]
        if len(ts) == 7: # H:MM:SS
            return "0" + ts
        return ts # HH:MM:SS

    # Функциональность Q&A пока не интегрируем с новой структурой,
    # чтобы сфокусироваться на основной задаче. Можно будет добавить позже.
    # def ask_about_transcript(self):
    #     ... (старый код Q&A, требующий адаптации)