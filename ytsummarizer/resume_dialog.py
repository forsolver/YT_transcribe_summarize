"""
Диалог для возобновления пакетной обработки
"""

import logging
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QCheckBox, QGroupBox, QProgressBar
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

from .state_manager import StateManager

logger = logging.getLogger("ytsummarizer.resume_dialog")

class ResumeDialog(QDialog):
    """Диалог для возобновления обработки"""
    
    def __init__(self, parent, source_url: str, state_info: dict):
        """
        Инициализирует диалог с информацией о сохраненном состоянии
        
        Args:
            parent: Родительский виджет
            source_url: URL источника
            state_info: Информация о сохраненном состоянии
        """
        super().__init__(parent)
        self.setWindowTitle("Возобновление пакетной обработки")
        self.setModal(True)
        self.resize(500, 300)
        
        self.source_url = source_url
        self.state_info = state_info
        self.resume_choice = False
        self.remember_choice = False
        
        self.setup_ui()
    
    def setup_ui(self):
        """Настройка пользовательского интерфейса"""
        layout = QVBoxLayout(self)
        
        # Заголовок
        header_label = QLabel("Обнаружен сохраненный прогресс для:")
        header_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(header_label)
        
        # Название источника
        source_name = self.state_info.get("source_name", "Неизвестный источник")
        source_type = self.state_info.get("source_type", "UNKNOWN")
        source_label = QLabel(f"{source_name} ({source_type})")
        source_label.setStyleSheet("font-size: 13px;")
        layout.addWidget(source_label)
        
        # Информация о прогрессе
        progress_group = QGroupBox("Информация о прогрессе")
        progress_layout = QVBoxLayout(progress_group)
        
        # Прогресс-бар
        processed = self.state_info.get("processed_videos", 0)
        total = self.state_info.get("total_videos", 0)
        progress_percent = int((processed / total) * 100) if total > 0 else 0
        
        progress_bar = QProgressBar()
        progress_bar.setValue(progress_percent)
        progress_bar.setTextVisible(True)
        progress_bar.setFormat(f"{processed} из {total} видео ({progress_percent}%)")
        progress_layout.addWidget(progress_bar)
        
        # Информация о последнем видео
        last_video = self.state_info.get("last_processed_video", {})
        if last_video:
            last_video_label = QLabel("Последнее обработанное видео:")
            last_video_label.setStyleSheet("font-weight: bold;")
            progress_layout.addWidget(last_video_label)
            
            title = last_video.get("title", "Неизвестное видео")
            video_title_label = QLabel(f'"{title}"')
            video_title_label.setWordWrap(True)
            progress_layout.addWidget(video_title_label)
        
        # Время сохранения
        timestamp = self.state_info.get("timestamp", "")
        if timestamp:
            time_str = StateManager.format_timestamp(timestamp)
            time_label = QLabel(f"Сохранено: {time_str}")
            progress_layout.addWidget(time_label)
        
        layout.addWidget(progress_group)
        
        # Опция "Запомнить выбор"
        self.remember_checkbox = QCheckBox("Запомнить выбор (не спрашивать в следующий раз)")
        layout.addWidget(self.remember_checkbox)
        
        # Кнопки
        buttons_layout = QHBoxLayout()
        
        self.resume_button = QPushButton("Возобновить")
        self.resume_button.setDefault(True)
        self.resume_button.clicked.connect(self.accept_resume)
        
        self.restart_button = QPushButton("Начать заново")
        self.restart_button.clicked.connect(self.reject_resume)
        
        self.cancel_button = QPushButton("Отмена")
        self.cancel_button.clicked.connect(self.reject)
        
        buttons_layout.addWidget(self.resume_button)
        buttons_layout.addWidget(self.restart_button)
        buttons_layout.addWidget(self.cancel_button)
        
        layout.addLayout(buttons_layout)
    
    def accept_resume(self):
        """Принять возобновление"""
        self.resume_choice = True
        self.remember_choice = self.remember_checkbox.isChecked()
        self.accept()
    
    def reject_resume(self):
        """Отклонить возобновление (начать заново)"""
        self.resume_choice = False
        self.remember_choice = self.remember_checkbox.isChecked()
        self.accept()
    
    def get_resume_choice(self) -> bool:
        """Возвращает выбор пользователя (возобновить или начать заново)"""
        return self.resume_choice
    
    def get_remember_choice(self) -> bool:
        """Возвращает, нужно ли запомнить выбор"""
        return self.remember_choice