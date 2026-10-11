"""Thread de processamento: mantém a interface responsiva."""
import time

import cv2
from PySide6.QtCore import QMutex, QThread, QWaitCondition, Signal
from PySide6.QtGui import QImage

from services.counter import ConfigContagem, ContadorBovinos
from services.detector import DetectorBovinos, ErroModelo
from services.tracker import RastreadorBovinos
from services.video_source import ErroFonteVideo, VideoSource


VERDE = (89, 191, 107)     # BGR: rastreado/confirmado
AMARELO = (51, 179, 227)   # novo ou reencontrado (possível perda)
CINZA = (160, 160, 160)    # detectado, sem ID


def desenhar_regra_contagem(quadro, cfg: ConfigContagem):
    """Desenha a linha virtual com seta direcional ou a área de interesse."""
    h, w = quadro.shape[:2]
    esp = max(2, w // 600)
    if cfg.estrategia in ("linha_virtual", "varredura_drone"):
        xa, ya = int(cfg.linha[0] * w), int(cfg.linha[1] * h)
        xb, yb = int(cfg.linha[2] * w), int(cfg.linha[3] * h)
        cor = (89, 191, 107) if cfg.estrategia == "varredura_drone" else (51, 179, 227)
        cv2.line(quadro, (xa, ya), (xb, yb), cor, esp)
        # Seta indicando direção de "Entrada" (lado positivo da normal)
        mx, my = (xa + xb) // 2, (ya + yb) // 2
        import math
        dx, dy = xb - xa, yb - ya
        comp = math.hypot(dx, dy) or 1.0
        nx, ny = -dy / comp, dx / comp
        tam_seta = int(25 * (esp / 2))
        sx, sy = int(mx + nx * tam_seta), int(my + ny * tam_seta)
        cv2.arrowedLine(quadro, (mx, my), (sx, sy), cor, esp, tipLength=0.35)
        rotulo = ("PORTÃO DE VARREDURA" if cfg.estrategia == "varredura_drone" else "LINHA") + f" ({cfg.sentido_contado.upper()})"
        cv2.putText(quadro, rotulo, (xa + 6, ya - 8 if ya > 20 else ya + 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45 * (esp / 2) + 0.3, cor, max(1, esp // 2), cv2.LINE_AA)
    elif cfg.estrategia == "area_interesse":
        x1, y1, x2, y2 = cfg.area
        cv2.rectangle(quadro, (int(x1 * w), int(y1 * h)), (int(x2 * w), int(y2 * h)), (51, 179, 227), esp)


def desenhar_deteccoes(quadro, deteccoes):
    """Desenha caixas e IDs. Cor: verde=confirmado, amarelo=novo/reencontrado, cinza=sem ID."""
    espessura = max(2, quadro.shape[1] // 600)
    for d in deteccoes:
        cor = CINZA if d.id_rastreamento is None and d.estado == "sem_id" else VERDE
        if d.estado in ("novo", "reencontrado"):
            cor = AMARELO
        p1, p2 = (int(d.x1), int(d.y1)), (int(d.x2), int(d.y2))
        cv2.rectangle(quadro, p1, p2, cor, espessura)
        rotulo = f"{d.confianca:.2f}" if d.id_rastreamento is None else f"#{d.id_rastreamento} {d.confianca:.2f}"
        cv2.putText(quadro, rotulo, (p1[0], max(12, p1[1] - 4)), cv2.FONT_HERSHEY_SIMPLEX,
                    0.5 * espessura / 2 + 0.3, cor, max(1, espessura // 2), cv2.LINE_AA)


class ProcessingWorker(QThread):
    quadro_pronto = Signal(QImage)
    metricas = Signal(dict)       # fps, quadros, tempo, progresso, detectados, conf_media, contagem
    aviso = Signal(str)
    erro = Signal(str)
    finalizado = Signal(str)      # motivo: "fim", "encerrado" ou "erro"
    resultado_final = Signal(object)  # ResultadoContagem (ou None se não houve detecção)

    def __init__(self, fonte: VideoSource, detector: DetectorBovinos | None = None,
                 rastreador: RastreadorBovinos | None = None, contador: ContadorBovinos | None = None,
                 passo_processamento: int = 1):
        super().__init__()
        self._fonte = fonte
        self._detector = detector
        self._rastreador = rastreador
        self._contador = contador
        self.passo_processamento = max(1, passo_processamento)
        self._pausado = False
        self._parar = False
        self._quadro_solicitado: int | None = None
        self._mutex = QMutex()
        self._cond = QWaitCondition()

    def pausar(self):
        self._pausado = True

    def retomar(self):
        self._mutex.lock()
        self._pausado = False
        self._cond.wakeAll()
        self._mutex.unlock()

    def saltar_para_quadro(self, numero_quadro: int):
        """Permite que o usuário avance ou retroceda para qualquer segundo/quadro."""
        self._mutex.lock()
        self._quadro_solicitado = numero_quadro
        self._cond.wakeAll()
        self._mutex.unlock()

    def encerrar(self):
        self._mutex.lock()
        self._parar = True
        self._pausado = False
        self._cond.wakeAll()
        self._mutex.unlock()

    def run(self):
        motivo = "fim"
        try:
            self._fonte.abrir()
            if self._detector is not None:
                try:
                    self._detector.carregar()
                    if self._detector.aviso_dispositivo:
                        self.aviso.emit(self._detector.aviso_dispositivo)
                    self.aviso.emit(f"Detecção ativa em: {self._detector.dispositivo}")
                except ErroModelo as e:
                    self.erro.emit(f"{e} O vídeo será exibido sem detecção.")
                    self._detector = self._rastreador = self._contador = None
            total = self._fonte.total_quadros
            fps_origem = self._fonte.fps or 30.0
            n = 0
            inicio = time.perf_counter()
            ultimo = inicio
            fps_suave = 0.0
            ultimas_deteccoes = None
            ultimo_resultado_contagem = None
            while not self._parar:
                self._mutex.lock()
                while self._pausado and not self._parar and self._quadro_solicitado is None:
                    self._cond.wait(self._mutex)
                    ultimo = time.perf_counter()

                quadro_alvo = self._quadro_solicitado
                self._quadro_solicitado = None
                self._mutex.unlock()

                if self._parar:
                    motivo = "encerrado"
                    break

                if quadro_alvo is not None:
                    self._fonte.posicionar_quadro(quadro_alvo)
                    n = quadro_alvo

                quadro = self._fonte.ler_quadro()
                if quadro is None:
                    break
                n += 1
                agora = time.perf_counter()
                dt = agora - ultimo
                ultimo = agora
                if dt > 0 and n > 1:
                    inst = 1.0 / dt
                    fps_suave = inst if fps_suave == 0 else 0.9 * fps_suave + 0.1 * inst
                deteccoes = None
                resultado_contagem = None
                if self._detector is not None:
                    deve_processar = (n % self.passo_processamento == 0) or (quadro_alvo is not None)
                    if deve_processar:
                        deteccoes = self._detector.detectar(quadro)
                        if self._rastreador is not None:
                            deteccoes = self._rastreador.atualizar(deteccoes, quadro)
                        if self._contador is not None:
                            alt, larg = quadro.shape[:2]
                            self._contador.atualizar(deteccoes, larg, alt)
                            resultado_contagem = self._contador.resultado()
                        ultimas_deteccoes = deteccoes
                        ultimo_resultado_contagem = resultado_contagem
                    else:
                        deteccoes = ultimas_deteccoes
                        resultado_contagem = ultimo_resultado_contagem

                    if self._contador is not None:
                        desenhar_regra_contagem(quadro, self._contador.config)
                    if deteccoes:
                        desenhar_deteccoes(quadro, deteccoes)

                # Otimização de renderização: limita preview a 1280px para máxima fluidez na interface
                h, w = quadro.shape[:2]
                max_larg = 1280
                if w > max_larg:
                    escala = max_larg / w
                    quadro_disp = cv2.resize(quadro, (max_larg, int(h * escala)), interpolation=cv2.INTER_AREA)
                else:
                    quadro_disp = quadro
                rgb = cv2.cvtColor(quadro_disp, cv2.COLOR_BGR2RGB)
                hp, wp, _ = rgb.shape
                img = QImage(rgb.data, wp, hp, 3 * wp, QImage.Format_RGB888).copy()
                self.quadro_pronto.emit(img)

                self.metricas.emit({
                    "fps": fps_suave,
                    "quadros": n,
                    "total": total,
                    "tempo": agora - inicio,
                    # None = sem detecção ativa (indicador indisponível, nunca zero falso)
                    "detectados": None if deteccoes is None else len(deteccoes),
                    "conf_media": (sum(d.confianca for d in deteccoes) / len(deteccoes)
                                   if deteccoes else None),
                    "contagem": resultado_contagem,
                })
                # Em vídeo gravado, respeita o FPS original (reprodução em tempo real).
                if not self._fonte.eh_transmissao_ao_vivo:
                    folga = (1.0 / fps_origem) - (time.perf_counter() - agora)
                    if folga > 0:
                        time.sleep(folga)
            if self._parar:
                motivo = "encerrado"
        except ErroFonteVideo as e:
            motivo = "erro"
            self.erro.emit(str(e))
        except Exception as e:  # interrupção inesperada
            motivo = "erro"
            self.erro.emit(f"Processamento interrompido inesperadamente: {e}")
        finally:
            self._fonte.fechar()
            if self._contador is not None:
                self.resultado_final.emit(self._contador.resultado())
            else:
                self.resultado_final.emit(None)
            self.finalizado.emit(motivo)
