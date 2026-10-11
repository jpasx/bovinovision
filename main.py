import sys

# Pré-carrega torch e torchvision na thread principal para registrar operadores C++ (ex: torchvision::nms)
try:
    import torch
    import torchvision
except ImportError:
    pass

from PySide6.QtWidgets import QApplication

from ui.main_window import MainWindow
from ui.theme import QSS


def main() -> int:
    app = QApplication(sys.argv)
    app.setStyleSheet(QSS)
    janela = MainWindow()
    janela.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
