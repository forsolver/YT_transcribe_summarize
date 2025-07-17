import sys
from PyQt5.QtWidgets import QApplication

from .ui import YouTubeSummarizerUI


def main():
    app = QApplication(sys.argv)
    window = YouTubeSummarizerUI()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main() 