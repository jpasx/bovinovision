from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout


class CartaoMetrica(QFrame):
    """Cartão de métrica. Mostra '—' enquanto não houver dado real."""

    def __init__(self, titulo: str):
        super().__init__()
        self.setObjectName("cartao")
        lay = QVBoxLayout(self)
        self._titulo = QLabel(titulo)
        self._titulo.setObjectName("cartaoTitulo")
        self._valor = QLabel("—")
        self._valor.setObjectName("cartaoValor")
        lay.addWidget(self._titulo)
        lay.addWidget(self._valor)

    def definir(self, texto: str):
        self._valor.setText(texto)

    def indisponivel(self):
        self._valor.setText("—")
