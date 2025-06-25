"""Обёртка для обратной совместимости.

После рефакторинга вся логика переехала в пакет `ytsummarizer`.
Оставляем этот файл, чтобы старые ярлыки/запуски `python main.py` продолжали работать.
"""

from ytsummarizer.app import main as _main


if __name__ == "__main__":
    _main() 