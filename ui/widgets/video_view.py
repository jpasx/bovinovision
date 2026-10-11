"""Exibe quadros de vídeo e permite desenhar interativamente a linha virtual de contagem."""
from PySide6.QtCore import QPointF, QRectF, QSize, Qt, Signal
from PySide6.QtGui import QColor, QImage, QPainter, QPen, QPixmap
from PySide6.QtWidgets import QLabel, QSizePolicy


class VideoView(QLabel):
    """Exibe quadros mantendo a proporção; redimensiona e permite definir a linha de contagem."""

    linha_definida = Signal(float, float, float, float)  # xA, yA, xB, yB em frações (0..1)

    def __init__(self):
        super().__init__("Nenhum vídeo carregado.\nClique em “Selecionar vídeo”.")
        self.setObjectName("video")
        self.setAlignment(Qt.AlignCenter)
        self.setMinimumSize(QSize(480, 270))
        self.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
        self.setMouseTracking(True)

        self._img: QImage | None = None
        self._modo_desenhar_linha = False
        self._ponto_inicio: QPointF | None = None
        self._ponto_atual: QPointF | None = None
        self._linha_atual: tuple[float, float, float, float] | None = None

    def definir_modo_desenho(self, ativo: bool):
        self._modo_desenhar_linha = ativo
        if ativo:
            self.setCursor(Qt.CrossCursor)
        else:
            self.setCursor(Qt.ArrowCursor)
            self._ponto_inicio = None
            self._ponto_atual = None
            self.update()

    def definir_linha_referencia(self, xA: float, yA: float, xB: float, yB: float):
        self._linha_atual = (xA, yA, xB, yB)
        self.update()

    def mostrar(self, img: QImage):
        self._img = img
        self._atualizar()

    def limpar(self, texto: str = ""):
        self._img = None
        self._linha_atual = None
        self.clear()
        self.setText(texto)

    def _retangulo_imagem(self) -> QRectF:
        """Calcula a área exata onde a imagem está sendo renderizada dentro do QLabel."""
        if self._img is None or self._img.isNull():
            return QRectF(0, 0, self.width(), self.height())
        larg_w, alt_w = self.width(), self.height()
        larg_img, alt_img = self._img.width(), self._img.height()
        escala = min(larg_w / larg_img, alt_w / alt_img)
        w_render = larg_img * escala
        h_render = alt_img * escala
        x_render = (larg_w - w_render) / 2
        y_render = (alt_w - h_render) / 2
        return QRectF(x_render, y_render, w_render, h_render)

    def _widget_para_frac(self, pt: QPointF) -> tuple[float, float]:
        rect = self._retangulo_imagem()
        if rect.width() <= 0 or rect.height() <= 0:
            return 0.0, 0.0
        fx = max(0.0, min(1.0, (pt.x() - rect.x()) / rect.width()))
        fy = max(0.0, min(1.0, (pt.y() - rect.y()) / rect.height()))
        return fx, fy

    def _frac_para_widget(self, fx: float, fy: float) -> QPointF:
        rect = self._retangulo_imagem()
        return QPointF(rect.x() + fx * rect.width(), rect.y() + fy * rect.height())

    def mousePressEvent(self, e):
        if self._modo_desenhar_linha and e.button() == Qt.LeftButton:
            self._ponto_inicio = e.position()
            self._ponto_atual = e.position()
            self.update()
        super().mousePressEvent(e)

    def mouseMoveEvent(self, e):
        if self._modo_desenhar_linha and self._ponto_inicio is not None:
            self._ponto_atual = e.position()
            self.update()
        super().mouseMoveEvent(e)

    def mouseReleaseEvent(self, e):
        if self._modo_desenhar_linha and e.button() == Qt.LeftButton and self._ponto_inicio is not None:
            p_fim = e.position()
            xa, ya = self._widget_para_frac(self._ponto_inicio)
            xb, yb = self._widget_para_frac(p_fim)
            # Evita cliques acidentais pontuais (comprimento mínimo)
            if (xa - xb) ** 2 + (ya - yb) ** 2 > 0.0004:
                self._linha_atual = (xa, ya, xb, yb)
                self.linha_definida.emit(xa, ya, xb, yb)
            self._ponto_inicio = None
            self._ponto_atual = None
            self.definir_modo_desenho(False)
            self.update()
        super().mouseReleaseEvent(e)

    def paintEvent(self, e):
        super().paintEvent(e)
        # Se estiver desenhando a linha temporária no mouse
        if self._ponto_inicio is not None and self._ponto_atual is not None:
            p = QPainter(self)
            pen = QPen(QColor(227, 179, 65), 3, Qt.DashLine)
            p.setPen(pen)
            p.drawLine(self._ponto_inicio, self._ponto_atual)
            p.end()

    def _atualizar(self):
        if self._img is not None:
            self.setPixmap(QPixmap.fromImage(self._img).scaled(
                self.size(), Qt.KeepAspectRatio, Qt.FastTransformation))

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._atualizar()
