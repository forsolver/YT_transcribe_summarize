"""
Виджет для выбора папки сохранения файлов
"""

import os
import logging
from PyQt5.QtWidgets import (
    QWidget, QHBoxLayout, QLabel, QPushButton, QFileDialog, QMessageBox
)
from PyQt5.QtCore import pyqtSignal, Qt

from .settings_manager import SettingsManager

logger = logging.getLogger("ytsummarizer.folder_selection_widget")

class FolderSelectionWidget(QWidget):
    """Виджет для выбора и отображения папки сохранения"""
    
    folder_changed = pyqtSignal(str)  # Сигнал при изменении папки
    
    def __init__(self, default_folder: str = None):
        super().__init__()
        
        if default_folder is None:
            default_folder = SettingsManager.DEFAULT_OUTPUT_FOLDER
        
        self.current_folder = default_folder
        self.setup_ui()
        self.load_saved_folder()
    
    def setup_ui(self):
        """Настройка пользовательского интерфейса"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Метка "Папка сохранения:"
        self.label = QLabel("Папка сохранения:")
        layout.addWidget(self.label)
        
        # Поле для отображения текущей папки
        self.folder_display = QLabel()
        self.folder_display.setStyleSheet("""
            QLabel {
                border: 1px solid #ccc;
                padding: 5px;
                background-color: #f9f9f9;
                border-radius: 3px;
            }
        """)
        self.folder_display.setMinimumWidth(300)
        layout.addWidget(self.folder_display, 1)  # Растягиваемый элемент
        
        # Кнопка выбора папки
        self.select_button = QPushButton("Выбрать папку")
        self.select_button.clicked.connect(self.select_folder)
        layout.addWidget(self.select_button)
        
        # Обновляем отображение
        self.update_display()
    
    def load_saved_folder(self):
        """Загружает сохраненную папку из настроек"""
        saved_folder = SettingsManager.load_output_folder()
        if saved_folder != self.current_folder:
            self.set_folder(saved_folder)
    
    def get_selected_folder(self) -> str:
        """Возвращает текущую выбранную папку"""
        return self.current_folder
    
    def set_folder(self, folder_path: str):
        """Устанавливает папку программно"""
        if folder_path and folder_path != self.current_folder:
            # Проверяем доступность папки
            if SettingsManager.validate_folder(folder_path):
                old_folder = self.current_folder
                self.current_folder = folder_path
                self.update_display()
                
                # Сохраняем в настройки
                if SettingsManager.save_output_folder(folder_path):
                    logger.info(f"Папка сохранения изменена: {old_folder} -> {folder_path}")
                    self.folder_changed.emit(folder_path)
                else:
                    logger.error("Не удалось сохранить настройки папки")
            else:
                self.show_folder_error(folder_path, "Папка недоступна для записи")
    
    def select_folder(self):
        """Открывает диалог выбора папки"""
        dialog = QFileDialog()
        dialog.setFileMode(QFileDialog.Directory)
        dialog.setOption(QFileDialog.ShowDirsOnly, True)
        dialog.setWindowTitle("Выберите папку для сохранения трюков")
        
        # Устанавливаем текущую папку как начальную
        if os.path.exists(self.current_folder):
            dialog.setDirectory(self.current_folder)
        
        if dialog.exec_() == QFileDialog.Accepted:
            selected_folders = dialog.selectedFiles()
            if selected_folders:
                selected_folder = selected_folders[0]
                self.set_folder(selected_folder)
    
    def update_display(self):
        """Обновляет отображение текущей папки"""
        display_name = SettingsManager.get_folder_display_name(self.current_folder)
        self.folder_display.setText(display_name)
        
        # Устанавливаем tooltip с полным путем
        self.folder_display.setToolTip(f"Полный путь: {self.current_folder}")
        
        # Меняем цвет в зависимости от доступности папки
        if SettingsManager.validate_folder(self.current_folder):
            self.folder_display.setStyleSheet("""
                QLabel {
                    border: 1px solid #ccc;
                    padding: 5px;
                    background-color: #f9f9f9;
                    border-radius: 3px;
                    color: #000;
                }
            """)
        else:
            self.folder_display.setStyleSheet("""
                QLabel {
                    border: 1px solid #ff6b6b;
                    padding: 5px;
                    background-color: #ffe6e6;
                    border-radius: 3px;
                    color: #d63031;
                }
            """)
    
    def show_folder_error(self, folder_path: str, error_message: str):
        """Показывает ошибку доступа к папке"""
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Warning)
        msg.setWindowTitle("Ошибка доступа к папке")
        msg.setText(f"Не удается использовать папку:\n{folder_path}")
        msg.setInformativeText(f"{error_message}\n\nВыберите другую папку или проверьте права доступа.")
        msg.setStandardButtons(QMessageBox.Ok)
        msg.exec_()
    
    def reset_to_default(self):
        """Сбрасывает папку к значению по умолчанию"""
        self.set_folder(SettingsManager.DEFAULT_OUTPUT_FOLDER)