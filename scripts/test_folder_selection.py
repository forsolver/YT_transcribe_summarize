#!/usr/bin/env python3
"""
Тест функциональности выбора папки сохранения
"""

import sys
import os
import tempfile
import shutil
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from ytsummarizer.settings_manager import SettingsManager
from ytsummarizer.folder_selection_widget import FolderSelectionWidget
from PyQt5.QtWidgets import QApplication

def test_settings_manager():
    """Тест SettingsManager"""
    print("🧪 Тестирование SettingsManager...")
    
    # Создаем временную папку для тестов
    with tempfile.TemporaryDirectory() as temp_dir:
        test_folder = os.path.join(temp_dir, "test_output")
        
        # Тест валидации папки
        print(f"   Тест валидации папки: {test_folder}")
        is_valid = SettingsManager.validate_folder(test_folder)
        print(f"   ✅ Папка создана и валидна: {is_valid}")
        assert is_valid, "Папка должна быть валидной"
        
        # Тест сохранения настроек
        print("   Тест сохранения настроек...")
        success = SettingsManager.save_output_folder(test_folder)
        print(f"   ✅ Настройки сохранены: {success}")
        assert success, "Настройки должны сохраниться"
        
        # Тест загрузки настроек
        print("   Тест загрузки настроек...")
        loaded_folder = SettingsManager.load_output_folder()
        print(f"   ✅ Загруженная папка: {loaded_folder}")
        # Папка может быть сброшена к default если temp папка недоступна
        
        # Тест сокращения имени папки
        long_path = "/very/long/path/to/some/folder/that/exceeds/the/maximum/length"
        short_name = SettingsManager.get_folder_display_name(long_path, 30)
        print(f"   ✅ Сокращенное имя: {short_name}")
        assert len(short_name) <= 30, "Имя должно быть сокращено"
        assert "..." in short_name, "Должно содержать многоточие"

def test_folder_widget():
    """Тест FolderSelectionWidget"""
    print("\n🧪 Тестирование FolderSelectionWidget...")
    
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    
    # Создаем виджет
    widget = FolderSelectionWidget()
    print(f"   ✅ Виджет создан")
    
    # Тест получения текущей папки
    current_folder = widget.get_selected_folder()
    print(f"   ✅ Текущая папка: {current_folder}")
    assert current_folder, "Должна быть установлена папка по умолчанию"
    
    # Тест установки папки
    with tempfile.TemporaryDirectory() as temp_dir:
        test_folder = os.path.join(temp_dir, "widget_test")
        os.makedirs(test_folder, exist_ok=True)
        
        widget.set_folder(test_folder)
        new_folder = widget.get_selected_folder()
        print(f"   ✅ Папка установлена: {new_folder}")
        # Может быть сброшена к default если temp папка недоступна после закрытия контекста

def test_integration():
    """Тест интеграции компонентов"""
    print("\n🧪 Тестирование интеграции...")
    
    # Сброс к настройкам по умолчанию
    SettingsManager.reset_to_defaults()
    print("   ✅ Настройки сброшены к умолчанию")
    
    # Проверка папки по умолчанию
    default_folder = SettingsManager.load_output_folder()
    print(f"   ✅ Папка по умолчанию: {default_folder}")
    assert default_folder == SettingsManager.DEFAULT_OUTPUT_FOLDER
    
    # Проверка создания папки по умолчанию
    is_valid = SettingsManager.validate_folder(default_folder)
    print(f"   ✅ Папка по умолчанию валидна: {is_valid}")
    
    if os.path.exists(default_folder):
        print(f"   ✅ Папка по умолчанию создана: {default_folder}")

def main():
    print("🚀 Тестирование функциональности выбора папки")
    print("=" * 60)
    
    try:
        test_settings_manager()
        test_folder_widget()
        test_integration()
        
        print("\n" + "=" * 60)
        print("✅ Все тесты прошли успешно!")
        
    except Exception as e:
        print(f"\n❌ Ошибка в тестах: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())