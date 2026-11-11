"""THE LAST SIGNAL - launcher. Run:  python main.py"""
import sys
from PyQt6.QtWidgets import QApplication
from tls.engine import GameWindow


def main():
    app = QApplication(sys.argv)
    win = GameWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
