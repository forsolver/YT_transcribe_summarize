import sys
import os
import logging
from threading import Event
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QLineEdit, QPushButton, QTextEdit,
    QMessageBox, QTabWidget, QHBoxLayout, QLabel, QSpinBox, QProgressBar, QDialog,
    QCheckBox, QGroupBox, QFormLayout, QDialogButtonBox, QScrollArea
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer

# Создаем логгер для UI
logger = logging.getLogger("ytsummarizer.ui")

from . import transcripts as tr
from . import summarizer as sz
from . import video_processor as vp
from .url_detector import URLDetector, URLType
from .batch_processor import BatchProcessor, BatchOptions, BatchResult
from .folder_selection_widget import FolderSelectionWidget
from .settings_manager import SettingsManager


class YouTubeSummarizerUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("YouTube Инструменты")
        self.setGeometry(100, 100, 900, 700)
        self.font_size = 12
        self.processed_transcript_fragments = None
        self.video_info = None
        
        # Batch processing state
        self.batch_thread = None
        self.cancel_token = Event()
        self.url_detector = URLDetector()

        # Основная вкладка
        self.main_tab = QWidget()
        self.setCentralWidget(self.main_tab)

        layout = QVBoxLayout(self.main_tab)

        # URL input with enhanced placeholder
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("Введите ссылку на YouTube видео, канал или плейлист")
        layout.addWidget(self.url_input)

        # Горизонтальный layout для кнопок
        buttons_layout = QHBoxLayout()
        self.summarize_button = QPushButton("Получить саммари")
        self.summarize_button.clicked.connect(self.run_summarize)
        buttons_layout.addWidget(self.summarize_button)

        # Кнопка для проверки отдельного видео (только анализ, без скачивания)
        self.check_video_button = QPushButton("Проверить видео")
        self.check_video_button.clicked.connect(self.run_check_video)
        buttons_layout.addWidget(self.check_video_button)

        # Объединенная кнопка для извлечения и скачивания трюков
        self.extract_and_download_button = QPushButton("Извлечь и скачать трюки")
        self.extract_and_download_button.clicked.connect(self.run_extract_and_download_tricks)
        buttons_layout.addWidget(self.extract_and_download_button)

        # Batch settings button
        self.batch_settings_button = QPushButton("Настройки пакетной обработки")
        self.batch_settings_button.clicked.connect(self.show_batch_settings)
        buttons_layout.addWidget(self.batch_settings_button)

        layout.addLayout(buttons_layout)

        # Folder selection widget
        self.folder_selection_widget = FolderSelectionWidget()
        self.folder_selection_widget.folder_changed.connect(self.on_folder_changed)
        layout.addWidget(self.folder_selection_widget)

        # Progress indicators (initially hidden)
        self.progress_widget = self.create_progress_widget()
        layout.addWidget(self.progress_widget)
        self.progress_widget.hide()

        # Cancel button (initially hidden)
        self.cancel_button = QPushButton("Отменить обработку")
        self.cancel_button.clicked.connect(self.cancel_processing)
        layout.addWidget(self.cancel_button)
        self.cancel_button.hide()

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
    
    def get_output_folder(self) -> str:
        """Возвращает выбранную папку для сохранения файлов"""
        return self.folder_selection_widget.get_selected_folder()
    
    def on_folder_changed(self, new_folder: str):
        """Обработчик изменения папки сохранения"""
        logger.info(f"Папка сохранения изменена на: {new_folder}")
        self.output_text_area.append(f"📁 Папка сохранения изменена на: {new_folder}")

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
            
            # Предлагаем ручной ввод транскрипта
            reply = QMessageBox.question(
                self, 
                "Ошибка при получении транскрипта",
                f"Не удалось автоматически получить транскрипт:\n{str(e)}\n\n"
                "Хотите ввести транскрипт вручную?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes
            )
            
            if reply == QMessageBox.Yes:
                return self._get_manual_transcript(video_id_or_url)
            
            return False
    
    def _get_manual_transcript(self, video_url: str) -> bool:
        """
        Получить транскрипт вручную через диалог.
        Возвращает True в случае успеха, False если пользователь отменил.
        """
        dialog = ManualTranscriptDialog(self, video_url)
        if dialog.exec_() == QDialog.Accepted:
            try:
                fragments, video_info = dialog.get_transcript_data()
                if fragments:
                    self.processed_transcript_fragments = fragments
                    self.video_info = video_info
                    
                    # Показываем информацию о загруженном транскрипте
                    self.output_text_area.setPlainText(
                        f"✅ Транскрипт загружен вручную!\n\n"
                        f"📹 Видео: {video_info.get('title', 'Без названия')}\n"
                        f"📝 Фрагментов: {len(fragments)}\n"
                        f"⏱️ Примерная длительность: {self.seconds_to_timecode(video_info.get('duration', 0))}\n\n"
                        f"Теперь вы можете использовать любую функцию для анализа."
                    )
                    
                    return True
                else:
                    QMessageBox.warning(self, "Предупреждение", "Не удалось обработать введенный транскрипт.")
                    return False
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Ошибка при обработке ручного транскрипта: {str(e)}")
                return False
        
        return False

    def run_summarize(self):
        url = self.url_input.text().strip()
        if not self._fetch_transcript_data(url):
            return

        if not self.processed_transcript_fragments:
            # Предлагаем ручной ввод если данных все еще нет
            reply = QMessageBox.question(
                self, 
                "Нет данных транскрипта",
                "Нет данных транскрипта для саммаризации.\n\n"
                "Хотите ввести транскрипт вручную?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes
            )
            
            if reply == QMessageBox.Yes:
                if not self._get_manual_transcript(url):
                    return
            else:
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

    def run_extract_and_download_tricks(self):
        """Enhanced trick extraction and download that supports both single videos and batch processing."""
        url = self.url_input.text().strip()
        if not url:
            QMessageBox.warning(self, "Предупреждение", "Пожалуйста, введите URL.")
            return
        
        # Detect URL type
        logger.info(f"Processing URL: {url}")
        url_type = self.url_detector.detect_url_type(url)
        logger.info(f"Detected URL type: {url_type}")
        
        if url_type == URLType.SINGLE_VIDEO:
            logger.info("Using single video processing with download")
            # Use single video processing that downloads tricks
            self.run_download_tricks()
        elif url_type in [URLType.CHANNEL, URLType.PLAYLIST]:
            logger.info("Using batch processing with download")
            # Use batch processing (already downloads tricks)
            self.run_batch_processing(url)
        else:
            logger.error(f"Unsupported URL type: {url_type}")
            QMessageBox.critical(self, "Ошибка", "Неподдерживаемый тип URL.")
    
    def run_check_video(self):
        """Check a single video for transcript and tricks (analysis only, no download)."""
        url = self.url_input.text().strip()
        if not url:
            QMessageBox.warning(self, "Предупреждение", "Пожалуйста, введите URL.")
            return
        
        # Detect URL type
        logger.info(f"Checking video: {url}")
        url_type = self.url_detector.detect_url_type(url)
        logger.info(f"Detected URL type: {url_type}")
        
        if url_type != URLType.SINGLE_VIDEO:
            QMessageBox.warning(
                self, 
                "Предупреждение", 
                "Функция 'Проверить видео' работает только с отдельными видео.\n"
                "Для плейлистов и каналов используйте 'Извлечь и скачать трюки'."
            )
            return
        
        logger.info("Starting single video check (analysis only)")
        
        # Get transcript data
        if not self._fetch_transcript_data(url):
            return

        if not self.processed_transcript_fragments:
            # Предлагаем ручной ввод если данных все еще нет
            reply = QMessageBox.question(
                self, 
                "Нет данных транскрипта",
                "Нет данных транскрипта для анализа.\n\n"
                "Хотите ввести транскрипт вручную?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes
            )
            
            if reply == QMessageBox.Yes:
                if not self._get_manual_transcript(url):
                    return
            else:
                return
        
        if not self.processed_transcript_fragments:
            QMessageBox.critical(self, "Ошибка", "Нет данных транскрипта для анализа.")
            return

        try:
            # Analyze transcript and find tricks
            trick_segments = vp.extract_trick_segments(self.processed_transcript_fragments)
            
            # Prepare detailed report
            video_title = self.video_info.get('title', 'Без названия')
            video_duration = self.video_info.get('duration', 'Неизвестно')
            
            result_lines = [
                f"📹 АНАЛИЗ ВИДЕО: {video_title}",
                f"⏱️ Длительность: {video_duration} сек" if isinstance(video_duration, (int, float)) else f"⏱️ Длительность: {video_duration}",
                f"📝 Фрагментов транскрипта: {len(self.processed_transcript_fragments)}",
                "",
                f"🎯 НАЙДЕНО ТРЮКОВ: {len(trick_segments)}",
                ""
            ]

            if trick_segments:
                result_lines.append("📋 ДЕТАЛИ ТРЮКОВ:")
                total_tricks_duration = 0
                
                for i, seg in enumerate(trick_segments, 1):
                    start_td = self.seconds_to_timecode(seg['start'])
                    end_td = self.seconds_to_timecode(seg['end'])
                    duration_td = self.seconds_to_timecode(seg['duration'])
                    total_tricks_duration += seg['duration']
                    
                    result_lines.append(f"  {i}. Трюк {start_td} - {end_td} (Длительность: {duration_td})")
                
                result_lines.extend([
                    "",
                    f"⏱️ ОБЩАЯ ДЛИТЕЛЬНОСТЬ ТРЮКОВ: {self.seconds_to_timecode(total_tricks_duration)}",
                    f"📊 ПРОЦЕНТ ОТ ВИДЕО: {(total_tricks_duration / video_duration * 100):.1f}%" if isinstance(video_duration, (int, float)) and video_duration > 0 else "📊 ПРОЦЕНТ ОТ ВИДЕО: Неизвестно",
                    "",
                    "💡 Для скачивания видео файлов используйте кнопку 'Извлечь и скачать трюки'"
                ])
            else:
                result_lines.extend([
                    "❌ Трюки не найдены в этом видео.",
                    "",
                    "🔍 ВОЗМОЖНЫЕ ПРИЧИНЫ:",
                    "  • Видео содержит непрерывную речь/комментарии",
                    "  • Нет достаточно длинных 'тихих' сегментов (минимум 10 сек)",
                    "  • Транскрипт содержит много текста даже в моменты трюков",
                    "",
                    "💡 РЕКОМЕНДАЦИИ:",
                    "  • Попробуйте другое видео с меньшим количеством комментариев",
                    "  • Проверьте, есть ли в видео сегменты только с музыкой"
                ])

            self.output_text_area.setPlainText("\n".join(result_lines))
            logger.info(f"Video check completed: {len(trick_segments)} tricks found")

        except Exception as e:
            error_msg = f"Ошибка при анализе видео: {str(e)}"
            logger.error(error_msg)
            QMessageBox.critical(self, "Ошибка при анализе видео", error_msg)

    def run_download_tricks(self):
        url = self.url_input.text().strip()
        if not self._fetch_transcript_data(url):
            return

        if not self.processed_transcript_fragments:
            # Предлагаем ручной ввод если данных все еще нет
            reply = QMessageBox.question(
                self, 
                "Нет данных транскрипта",
                "Нет данных транскрипта для извлечения трюков.\n\n"
                "Хотите ввести транскрипт вручную?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes
            )
            
            if reply == QMessageBox.Yes:
                if not self._get_manual_transcript(url):
                    return
            else:
                return
        
        if not self.processed_transcript_fragments:
            QMessageBox.critical(self, "Ошибка", "Нет данных транскрипта для извлечения трюков.")
            return
        
        # Проверяем доступность папки сохранения
        output_folder = self.get_output_folder()
        if not SettingsManager.validate_folder(output_folder):
            reply = QMessageBox.question(
                self, 
                "Папка недоступна", 
                f"Папка сохранения '{output_folder}' недоступна для записи.\n\nВыбрать другую папку?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                self.folder_selection_widget.select_folder()
                # Проверяем еще раз после выбора
                if not SettingsManager.validate_folder(self.get_output_folder()):
                    return
            else:
                return

        try:
            # Извлекаем сегменты трюков
            trick_segments = vp.extract_trick_segments(self.processed_transcript_fragments)

            if not trick_segments:
                self.output_text_area.setPlainText(f"Трюки не найдены в видео \"{self.video_info.get('title', 'Без названия')}\".")
                return

            # Получаем video_id
            video_id = tr.extract_video_id(url)
            
            # Показываем сообщение о начале загрузки
            self.output_text_area.setPlainText(f"Начинаю скачивание {len(trick_segments)} трюковых сегментов...\nЭто может занять некоторое время.")
            
            # Принудительно обновляем UI
            QApplication.processEvents()
            
            # Скачиваем видео сегменты, передаем информацию о видео для создания подпапки
            downloaded_files = vp.extract_video_segments(
                video_id, 
                trick_segments, 
                output_dir=self.get_output_folder(),
                video_info=self.video_info
            )
            
            if downloaded_files:
                result_lines = [f"Успешно скачано {len(downloaded_files)} видео трюков из видео \"{self.video_info.get('title', 'Без названия')}\":\n"]
                for i, file_path in enumerate(downloaded_files):
                    seg = trick_segments[i]
                    start_td = self.seconds_to_timecode(seg['start'])
                    end_td = self.seconds_to_timecode(seg['end'])
                    duration_td = self.seconds_to_timecode(seg['duration'])
                    result_lines.append(f"- {file_path}")
                    result_lines.append(f"  Время: {start_td} - {end_td} (Длительность: {duration_td})")
                
                # Получаем имя подпапки из первого пути к файлу
                if downloaded_files and len(downloaded_files) > 0:
                    subfolder_path = os.path.dirname(downloaded_files[0])
                    subfolder_name = os.path.basename(subfolder_path)
                    result_lines.append(f"\nВсе файлы сохранены в папке 'tricks/{subfolder_name}'")
                else:
                    result_lines.append(f"\nВсе файлы сохранены в папке 'tricks'")
                self.output_text_area.setPlainText("\n".join(result_lines))
            else:
                self.output_text_area.setPlainText("Не удалось скачать видео сегменты.")

        except Exception as e:
            QMessageBox.critical(self, "Ошибка при скачивании трюков", str(e))
            logging.error(f"Ошибка при скачивании трюков: {e}", exc_info=True)

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

    def create_progress_widget(self):
        """Create progress indicators widget."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Overall progress
        self.overall_progress_label = QLabel("Общий прогресс:")
        layout.addWidget(self.overall_progress_label)
        
        self.overall_progress_bar = QProgressBar()
        layout.addWidget(self.overall_progress_bar)
        
        # Current video progress
        self.current_video_label = QLabel("Текущее видео:")
        layout.addWidget(self.current_video_label)
        
        # Status label
        self.status_label = QLabel("Готов к работе")
        layout.addWidget(self.status_label)
        
        return widget
    
    def show_batch_settings(self):
        """Show batch processing settings dialog."""
        dialog = BatchSettingsDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            # Settings are stored in the dialog and will be used when processing
            pass
    
    def cancel_processing(self):
        """Cancel current batch processing operation."""
        if self.cancel_token:
            self.cancel_token.set()
            self.status_label.setText("Отмена обработки...")
    
    def update_progress(self, current, total, message):
        """Update progress indicators."""
        if total > 0:
            progress = int((current / total) * 100)
            self.overall_progress_bar.setValue(progress)
            self.overall_progress_label.setText(f"Общий прогресс: {current}/{total}")
        
        self.status_label.setText(message)
        QApplication.processEvents()
    

    def run_batch_processing(self, source_url):
        """Run batch processing for channels and playlists."""
        logger.info(f"Starting batch processing for URL: {source_url}")
        
        # Проверяем доступность папки сохранения
        output_folder = self.get_output_folder()
        if not SettingsManager.validate_folder(output_folder):
            reply = QMessageBox.question(
                self, 
                "Папка недоступна", 
                f"Папка сохранения '{output_folder}' недоступна для записи.\n\nВыбрать другую папку?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                self.folder_selection_widget.select_folder()
                # Проверяем еще раз после выбора
                if not SettingsManager.validate_folder(self.get_output_folder()):
                    return
            else:
                return
        
        # Show progress widgets
        logger.debug("Showing progress widgets")
        self.progress_widget.show()
        self.cancel_button.show()
        
        # Disable buttons during processing
        self.set_buttons_enabled(False)
        
        # Reset cancel token
        self.cancel_token.clear()
        
        # Get batch options (for now use defaults, later from settings dialog)
        options = BatchOptions(max_videos=50, output_dir=self.get_output_folder())
        logger.info(f"Batch options: max_videos={options.max_videos}")
        
        # Start batch processing in a separate thread
        logger.debug("Creating BatchProcessingThread")
        self.batch_thread = BatchProcessingThread(source_url, options, self.cancel_token)
        self.batch_thread.progress_update.connect(self.update_progress)
        self.batch_thread.finished_signal.connect(self.on_batch_finished)
        self.batch_thread.error_signal.connect(self.on_batch_error)
        
        logger.debug("Starting batch processing thread")
        self.batch_thread.start()
        logger.info("Batch processing thread started successfully")
    
    def on_batch_finished(self, result):
        """Handle batch processing completion."""
        # Hide progress widgets
        self.progress_widget.hide()
        self.cancel_button.hide()
        
        # Re-enable buttons
        self.set_buttons_enabled(True)
        
        # Show results
        self.show_batch_results(result)
    
    def on_batch_error(self, error_message):
        """Handle batch processing error."""
        # Hide progress widgets
        self.progress_widget.hide()
        self.cancel_button.hide()
        
        # Re-enable buttons
        self.set_buttons_enabled(True)
        
        # Show error
        QMessageBox.critical(self, "Ошибка пакетной обработки", error_message)
    
    def show_batch_results(self, result):
        """Display batch processing results."""
        if result.cancelled:
            summary = f"Обработка отменена.\n"
            summary += f"Обработано видео: {result.processed_videos}/{result.total_videos}\n"
        else:
            summary = f"Пакетная обработка завершена!\n\n"
            summary += f"Источник: {result.source_info.name}\n"
            summary += f"Всего видео: {result.total_videos}\n"
            summary += f"Обработано: {result.processed_videos}\n"
            summary += f"Успешно: {result.successful_extractions}\n"
            summary += f"Найдено трюков: {result.total_tricks}\n"
            summary += f"Создано сегментов: {result.total_segments}\n"
            summary += f"Время обработки: {result.processing_time:.1f} сек\n"
        
        if result.errors:
            summary += f"\nОшибки ({len(result.errors)}):\n"
            for error in result.errors[:5]:  # Show first 5 errors
                summary += f"- {error.video_title}: {error.error_message}\n"
            if len(result.errors) > 5:
                summary += f"... и еще {len(result.errors) - 5} ошибок\n"
        
        self.output_text_area.setPlainText(summary)
    
    def set_buttons_enabled(self, enabled):
        """Enable or disable all buttons."""
        self.summarize_button.setEnabled(enabled)
        self.check_video_button.setEnabled(enabled)
        self.extract_and_download_button.setEnabled(enabled)
        self.batch_settings_button.setEnabled(enabled)


class BatchProcessingThread(QThread):
    """Thread for running batch processing operations."""
    
    progress_update = pyqtSignal(int, int, str)
    finished_signal = pyqtSignal(object)
    error_signal = pyqtSignal(str)
    
    def __init__(self, source_url, options, cancel_token):
        super().__init__()
        self.source_url = source_url
        self.options = options
        self.cancel_token = cancel_token
    
    def run(self):
        """Run the batch processing operation."""
        logger.info(f"BatchProcessingThread.run() started for URL: {self.source_url}")
        try:
            logger.debug("Creating BatchProcessor instance")
            processor = BatchProcessor(
                progress_callback=self.emit_progress,
                cancel_token=self.cancel_token
            )
            logger.debug("Calling processor.process_source()")
            result = processor.process_source(self.source_url, self.options)
            logger.info(f"BatchProcessor completed successfully, emitting result")
            self.finished_signal.emit(result)
        except Exception as e:
            logger.exception(f"BatchProcessingThread error: {e}")
            self.error_signal.emit(str(e))
    
    def emit_progress(self, current, total, message):
        """Emit progress update signal."""
        self.progress_update.emit(current, total, message)


class ManualTranscriptDialog(QDialog):
    """Dialog for manual transcript input when automatic extraction fails."""
    
    def __init__(self, parent=None, video_url=""):
        super().__init__(parent)
        self.setWindowTitle("Ручной ввод транскрипта")
        self.setModal(True)
        self.resize(600, 500)
        
        layout = QVBoxLayout(self)
        
        # Info label
        info_label = QLabel(
            "Не удалось автоматически получить транскрипт для видео.\n"
            "Вы можете вручную скопировать и вставить текст транскрипта для анализа.\n\n"
            "Инструкция:\n"
            "1. Откройте видео на YouTube\n"
            "2. Нажмите на кнопку '...' под видео\n"
            "3. Выберите 'Показать расшифровку'\n"
            "4. Скопируйте весь текст и вставьте его ниже"
        )
        info_label.setWordWrap(True)
        layout.addWidget(info_label)
        
        # Video URL display
        if video_url:
            url_label = QLabel(f"URL видео: {video_url}")
            url_label.setWordWrap(True)
            url_label.setStyleSheet("font-weight: bold; color: blue;")
            layout.addWidget(url_label)
        
        # Transcript input area
        transcript_label = QLabel("Вставьте текст транскрипта:")
        layout.addWidget(transcript_label)
        
        self.transcript_text = QTextEdit()
        self.transcript_text.setPlaceholderText(
            "Вставьте сюда текст транскрипта...\n\n"
            "Пример:\n"
            "0:00\n"
            "привет всем сегодня я покажу вам новый трюк\n"
            "0:15\n"
            "сначала нужно взять доску и поставить ее вот так\n"
            "..."
        )
        self.transcript_text.setMinimumHeight(250)
        layout.addWidget(self.transcript_text)
        
        # Video title input
        title_label = QLabel("Название видео (опционально):")
        layout.addWidget(title_label)
        
        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText("Введите название видео для лучшей организации файлов")
        layout.addWidget(self.title_input)
        
        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
        # Enable OK button only when transcript is not empty
        self.ok_button = buttons.button(QDialogButtonBox.Ok)
        self.ok_button.setEnabled(False)
        self.transcript_text.textChanged.connect(self.check_input)
    
    def check_input(self):
        """Enable OK button only when transcript text is provided."""
        has_text = bool(self.transcript_text.toPlainText().strip())
        self.ok_button.setEnabled(has_text)
    
    def get_transcript_data(self):
        """Get the manually entered transcript data."""
        transcript_text = self.transcript_text.toPlainText().strip()
        video_title = self.title_input.text().strip() or "Ручной транскрипт"
        
        # Parse the transcript text into fragments
        fragments = self.parse_manual_transcript(transcript_text)
        
        # Create video info
        video_info = {
            'title': video_title,
            'duration': self.estimate_duration_from_fragments(fragments) if fragments else 0
        }
        
        return fragments, video_info
    
    def parse_manual_transcript(self, text):
        """Parse manually entered transcript text into fragments."""
        fragments = []
        lines = text.split('\n')
        current_time = 0
        current_text = ""
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Check if line looks like a timestamp (e.g., "0:00", "1:23", "12:34")
            if ':' in line and len(line.split(':')) == 2:
                try:
                    time_parts = line.split(':')
                    minutes = int(time_parts[0])
                    seconds = int(time_parts[1])
                    timestamp = minutes * 60 + seconds
                    
                    # Save previous fragment if exists
                    if current_text:
                        fragments.append({
                            'start': current_time,
                            'text': current_text.strip()
                        })
                    
                    # Start new fragment
                    current_time = timestamp
                    current_text = ""
                    continue
                except ValueError:
                    pass
            
            # Add line to current text
            if current_text:
                current_text += " " + line
            else:
                current_text = line
        
        # Add final fragment
        if current_text:
            fragments.append({
                'start': current_time,
                'text': current_text.strip()
            })
        
        # If no timestamps were found, treat entire text as one fragment
        if not fragments and text:
            fragments.append({
                'start': 0,
                'text': text
            })
        
        # Calculate duration for each fragment
        self._calculate_fragment_durations(fragments)
        
        return fragments
    
    def _calculate_fragment_durations(self, fragments):
        """Calculate duration for each fragment based on timestamps and text length."""
        for i, fragment in enumerate(fragments):
            if i < len(fragments) - 1:
                # Duration is the time until the next fragment starts
                next_start = fragments[i + 1]['start']
                fragment['duration'] = next_start - fragment['start']
            else:
                # For the last fragment, estimate duration based on text length
                text = fragment.get('text', '')
                estimated_duration = len(text.split()) * 0.5  # ~0.5 seconds per word
                # Minimum duration of 1 second, maximum of 30 seconds for estimation
                fragment['duration'] = max(1.0, min(30.0, estimated_duration))
    
    def estimate_duration_from_fragments(self, fragments):
        """Estimate video duration from transcript fragments."""
        if not fragments:
            return 0
        
        # Find the last timestamp and add estimated duration for last fragment
        last_fragment = fragments[-1]
        last_start = last_fragment.get('start', 0)
        
        # Estimate duration based on text length (rough approximation)
        last_text = last_fragment.get('text', '')
        estimated_last_duration = len(last_text.split()) * 0.5  # ~0.5 seconds per word
        
        return last_start + estimated_last_duration


class BatchSettingsDialog(QDialog):
    """Dialog for configuring batch processing settings."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_ui = parent
        self.setWindowTitle("Настройки пакетной обработки")
        self.setModal(True)
        self.resize(400, 300)
        
        layout = QVBoxLayout(self)
        
        # Settings group
        settings_group = QGroupBox("Параметры обработки")
        settings_layout = QFormLayout(settings_group)
        
        # Max videos
        self.max_videos_spin = QSpinBox()
        self.max_videos_spin.setRange(1, 1000)
        self.max_videos_spin.setValue(50)
        settings_layout.addRow("Максимум видео:", self.max_videos_spin)
        
        # Skip existing
        self.skip_existing_check = QCheckBox("Пропускать уже обработанные")
        settings_layout.addRow(self.skip_existing_check)
        
        layout.addWidget(settings_group)
        
        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
    
    def get_options(self):
        """Get batch processing options from the dialog."""
        output_dir = self.parent_ui.get_output_folder() if self.parent_ui else "tricks"
        return BatchOptions(
            max_videos=self.max_videos_spin.value(),
            skip_existing=self.skip_existing_check.isChecked(),
            output_dir=output_dir
        )