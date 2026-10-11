import json
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QComboBox, QFileDialog, QGridLayout, QHBoxLayout,
                               QInputDialog, QLabel, QMainWindow, QMessageBox,
                               QPlainTextEdit, QProgressBar, QPushButton,
                               QSlider, QVBoxLayout, QWidget)

from config.settings import (NOME_APP, PASTA_MODELOS, PASTA_VIDEOS, VERSAO_APP,
                             ConfiguracaoProcessamento)
from database.db_manager import DatabaseManager, RegistroSessao
from services.counter import ConfigContagem, ContadorBovinos
from services.detector import DetectorBovinos, modelo_disponivel
from services.processing_worker import ProcessingWorker
from services.tracker import RastreadorBovinos
from services.video_source import (FileVideoSource, RTSPVideoSource,
                                   WebcamVideoSource)
from ui.widgets.cartao_metrica import CartaoMetrica
from ui.widgets.dialogo_historico import DialogoHistorico
from ui.widgets.video_view import VideoView


def detectar_dispositivo() -> str:
    """Informa CPU/GPU disponível."""
    try:
        import torch
        if torch.cuda.is_available():
            return f"GPU ({torch.cuda.get_device_name(0)})"
        return "CPU (GPU CUDA não disponível)"
    except ImportError:
        return "CPU (PyTorch não instalado)"


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{NOME_APP} {VERSAO_APP}")
        self.resize(1340, 820)
        self.config = ConfiguracaoProcessamento()
        self.caminho_video: str | None = None
        self.tipo_fonte: str = "arquivo"  # "arquivo", "webcam", "rtsp"
        self.url_rtsp: str = ""
        self.indice_camera: int = 0
        self.linha_personalizada: tuple[float, float, float, float] = (0.0, 0.75, 1.0, 0.75)

        self.db = DatabaseManager()
        self.worker: ProcessingWorker | None = None
        self._ultimo_resultado = None
        self._metricas_atuais = {}

        self._montar()
        self._estado_inicial()

    # ---------- construção da interface ----------
    def _montar(self):
        raiz = QWidget()
        self.setCentralWidget(raiz)
        col = QVBoxLayout(raiz)

        # Cabeçalho
        cab = QHBoxLayout()
        l1, l2 = QLabel("Bovino"), QLabel("Vision AI")
        l1.setObjectName("logo")
        l2.setObjectName("logoAcento")
        sub = QLabel("🐄  Contagem inteligente de bovinos com drones")
        sub.setObjectName("sub")
        self.selo_disp = QLabel(f"Dispositivo: {detectar_dispositivo()}")
        self.selo_disp.setObjectName("selo")

        self.btn_historico = QPushButton("📋 Histórico e Relatórios")
        self.btn_historico.clicked.connect(self._abrir_historico)

        for w in (l1, l2):
            cab.addWidget(w)
        cab.addSpacing(16)
        cab.addWidget(sub)
        cab.addStretch()
        cab.addWidget(self.btn_historico)
        cab.addSpacing(10)
        cab.addWidget(self.selo_disp)
        col.addLayout(cab)

        # Corpo
        corpo = QHBoxLayout()
        col.addLayout(corpo, 1)

        # Painel Esquerdo (Vídeo e controles principais)
        esq = QVBoxLayout()
        self.video = VideoView()
        self.video.linha_definida.connect(self._linha_desenhada)
        esq.addWidget(self.video, 1)

        # Linha do Tempo / Barra de Busca Interativa
        lay_tempo = QHBoxLayout()
        self.slider_tempo = QSlider(Qt.Horizontal)
        self.slider_tempo.setObjectName("timeline")
        self.slider_tempo.setRange(0, 100)
        self.slider_tempo.setValue(0)
        self.slider_tempo.sliderMoved.connect(self._timeline_movida)
        self.slider_tempo.sliderReleased.connect(self._timeline_solta)
        self._arrastando_tempo = False

        self.lbl_tempo = QLabel("00:00 / 00:00")
        self.lbl_tempo.setObjectName("tempoVideo")
        lay_tempo.addWidget(self.slider_tempo, 1)
        lay_tempo.addWidget(self.lbl_tempo)
        esq.addLayout(lay_tempo)

        botoes = QHBoxLayout()
        self.combo_fonte = QComboBox()
        self.combo_fonte.addItem("Arquivo de Vídeo local", "arquivo")
        self.combo_fonte.addItem("Câmera / Placa HDMI Drone", "webcam")
        self.combo_fonte.addItem("Transmissão RTSP de Rede", "rtsp")
        self.combo_fonte.currentIndexChanged.connect(self._trocou_tipo_fonte)
        botoes.addWidget(self.combo_fonte)

        self.combo_desempenho = QComboBox()
        self.combo_desempenho.addItem("⚡ Equilibrado (Ideal p/ 60 FPS)", 2)
        self.combo_desempenho.addItem("🎯 Máxima Precisão (Todos os quadros)", 1)
        self.combo_desempenho.addItem("🚀 Ultra Rápido (A cada 3 quadros)", 3)
        botoes.addWidget(self.combo_desempenho)

        self.b_sel = QPushButton("Selecionar arquivo")
        self.b_desenhar_linha = QPushButton("✏️ Marcar Linha no Vídeo")
        self.b_ini = QPushButton("Iniciar")
        self.b_ini.setObjectName("primario")
        self.b_pausa = QPushButton("Pausar")
        self.b_fim = QPushButton("Encerrar")
        self.b_fim.setObjectName("perigo")

        for b in (self.b_sel, self.b_desenhar_linha, self.b_ini, self.b_pausa, self.b_fim):
            botoes.addWidget(b)
        esq.addLayout(botoes)
        corpo.addLayout(esq, 3)

        # Painel Direito (Métricas e configurações)
        dir_ = QVBoxLayout()
        grade = QGridLayout()
        self.c_quadro = CartaoMetrica("Detectados no quadro")
        self.c_ids = CartaoMetrica("IDs únicos na sessão")
        self.c_contados = CartaoMetrica("Contados pela regra")
        self.c_estimativa = CartaoMetrica("Estimativa do total")
        self.c_entradas = CartaoMetrica("Entradas (pela linha)")
        self.c_saidas = CartaoMetrica("Saídas (pela linha)")
        self.c_fps = CartaoMetrica("FPS de processamento")
        self.c_conf = CartaoMetrica("Confiança média")
        self.c_tempo = CartaoMetrica("Tempo de sessão")
        self.c_quadros = CartaoMetrica("Quadros processados")

        cartoes = [
            self.c_quadro, self.c_ids,
            self.c_contados, self.c_estimativa,
            self.c_entradas, self.c_saidas,
            self.c_fps, self.c_conf,
            self.c_tempo, self.c_quadros
        ]
        for i, c in enumerate(cartoes):
            grade.addWidget(c, i // 2, i % 2)
        dir_.addLayout(grade)

        # Modelo de IA
        dir_.addWidget(QLabel("Modelo de Inteligência Artificial"))
        self.combo_modelo = QComboBox()
        p_aereo = PASTA_MODELOS / "bovinos_aereo.pt"
        p_gen = PASTA_MODELOS / "bovinos.pt"
        if p_aereo.exists():
            self.combo_modelo.addItem("🛸 Modelo Aéreo Especializado (Drones YOLOv8)", str(p_aereo))
        if p_gen.exists():
            self.combo_modelo.addItem("🐄 Modelo Genérico de Bovinos", str(p_gen))
        self.combo_modelo.currentIndexChanged.connect(self._trocou_modelo)
        dir_.addWidget(self.combo_modelo)

        # Regras de contagem
        dir_.addWidget(QLabel("Regra de contagem"))
        self.combo_regra = QComboBox()
        self.combo_regra.addItem("🛸 Varredura por Drone (Recomendada p/ drone em vôo)", "varredura_drone")
        self.combo_regra.addItem("📏 Linha Virtual Clássica (Recomendada p/ drone parado)", "linha_virtual")
        self.combo_regra.addItem("🔢 IDs Estáveis (Estimativa por persistência)", "ids_estaveis")
        self.combo_regra.addItem("🔲 Área de Interesse (Região central)", "area_interesse")
        self.combo_regra.currentIndexChanged.connect(self._regra_mudou)
        dir_.addWidget(self.combo_regra)

        # Posição / Presets da Linha de Contagem
        self.lbl_posicao_linha = QLabel("Posição da linha de contagem")
        self.combo_preset_linha = QComboBox()
        self.combo_preset_linha.addItem("🛫 Portão Inferior (75% - Drone voando à frente)", (0.0, 0.75, 1.0, 0.75))
        self.combo_preset_linha.addItem("🎯 Portão Central (50% - Meio da tela)", (0.0, 0.50, 1.0, 0.50))
        self.combo_preset_linha.addItem("🛬 Portão Superior (25% - Drone voando em ré)", (0.0, 0.25, 1.0, 0.25))
        self.combo_preset_linha.currentIndexChanged.connect(self._trocou_preset_linha)
        dir_.addWidget(self.lbl_posicao_linha)
        dir_.addWidget(self.combo_preset_linha)

        # Sentido da Linha Virtual
        self.lbl_sentido = QLabel("Sentido contabilizado")
        self.combo_sentido = QComboBox()
        self.combo_sentido.addItem("Apenas Entradas (sentido da seta - Padrão Drone)", "entrada")
        self.combo_sentido.addItem("Contar ambos (Entradas e Saídas)", "ambos")
        self.combo_sentido.addItem("Apenas Saídas (sentido inverso)", "saida")
        dir_.addWidget(self.lbl_sentido)
        dir_.addWidget(self.combo_sentido)

        # Slider de Confiança
        self.lbl_conf = QLabel()
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(5, 95)
        self.slider.setValue(int(self.config.confianca_minima * 100))
        self.slider.valueChanged.connect(self._mudou_confianca)
        self._mudou_confianca(self.slider.value())
        dir_.addWidget(self.lbl_conf)
        dir_.addWidget(self.slider)

        dir_.addWidget(QLabel("Mensagens e avisos"))
        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        dir_.addWidget(self.log, 1)
        corpo.addLayout(dir_, 2)

        # Conexões
        self.b_sel.clicked.connect(self._selecionar)
        self.b_desenhar_linha.clicked.connect(self._ativar_modo_desenhar_linha)
        self.b_ini.clicked.connect(self._iniciar)
        self.b_pausa.clicked.connect(self._alternar_pausa)
        self.b_fim.clicked.connect(self._encerrar)

    # ---------- estado ----------
    def _estado_inicial(self):
        for c in (self.c_quadro, self.c_ids, self.c_fps, self.c_conf, self.c_tempo, self.c_quadros,
                  self.c_contados, self.c_estimativa, self.c_entradas, self.c_saidas):
            c.indisponivel()
        self.slider_tempo.setValue(0)
        self._botoes(sel=True, ini=self._fonte_pronta(), pausa=False, fim=False)
        self.b_pausa.setText("Pausar")
        self.msg("Pronto. Para contar bovinos com o drone sobrevoando a boiada, use 'Varredura por Drone'.")

    def _fonte_pronta(self) -> bool:
        if self.tipo_fonte == "arquivo":
            return self.caminho_video is not None
        if self.tipo_fonte == "rtsp":
            return bool(self.url_rtsp.strip())
        return True  # webcam pronta por padrão

    def _botoes(self, sel, ini, pausa, fim):
        self.b_sel.setEnabled(sel)
        self.b_ini.setEnabled(ini)
        self.b_pausa.setEnabled(pausa)
        self.b_fim.setEnabled(fim)

    def msg(self, texto: str, erro: bool = False):
        self.log.appendPlainText(("❌ " if erro else "ℹ️ ") + texto)

    def _mudou_confianca(self, v: int):
        self.config.confianca_minima = v / 100
        self.lbl_conf.setText(f"Confiança mínima: {v}%")

    def _trocou_modelo(self):
        caminho = self.combo_modelo.currentData()
        if caminho:
            self.config.caminho_modelo = caminho
            self.msg(f"Modelo alterado para: {Path(caminho).name}")

    def _trocou_preset_linha(self):
        dados = self.combo_preset_linha.currentData()
        if dados:
            self.linha_personalizada = dados
            self.msg(f"Portão de contagem reposicionado: y={dados[1]*100:.0f}%.")

    def _regra_mudou(self):
        regra = self.combo_regra.currentData()
        eh_linha = regra in ("linha_virtual", "varredura_drone")
        self.lbl_sentido.setVisible(eh_linha)
        self.combo_sentido.setVisible(eh_linha)
        self.b_desenhar_linha.setVisible(eh_linha)
        self.lbl_posicao_linha.setVisible(eh_linha)
        self.combo_preset_linha.setVisible(eh_linha)

    def _trocou_tipo_fonte(self):
        self.tipo_fonte = self.combo_fonte.currentData()
        if self.tipo_fonte == "arquivo":
            self.b_sel.setText("Selecionar arquivo")
            self.b_sel.setEnabled(True)
        elif self.tipo_fonte == "webcam":
            self.b_sel.setText("Configurar Câmera")
            self.b_sel.setEnabled(True)
        else:
            self.b_sel.setText("Definir URL RTSP")
            self.b_sel.setEnabled(True)
        self._botoes(sel=True, ini=self._fonte_pronta(), pausa=False, fim=False)

    def _ativar_modo_desenhar_linha(self):
        self.video.definir_modo_desenho(True)
        self.msg("Clique e arraste sobre o vídeo para traçar a linha de contagem.")

    def _linha_desenhada(self, xa, ya, xb, yb):
        self.linha_personalizada = (xa, ya, xb, yb)
        self.msg(f"Linha de contagem definida: de ({xa:.2f}, {ya:.2f}) até ({xb:.2f}, {yb:.2f}).")

    def _abrir_historico(self):
        dlg = DialogoHistorico(self.db, self)
        dlg.exec()

    # ---------- ações de execução ----------
    def _selecionar(self):
        if self.tipo_fonte == "arquivo":
            PASTA_VIDEOS.mkdir(parents=True, exist_ok=True)
            caminho, _ = QFileDialog.getOpenFileName(
                self, "Selecionar vídeo de drone", str(PASTA_VIDEOS),
                "Vídeos (*.mp4 *.avi *.mov *.mkv);;Todos os arquivos (*)")
            if caminho:
                self.caminho_video = caminho
                self.msg(f"Vídeo selecionado: {Path(caminho).name}")
                self._botoes(sel=True, ini=True, pausa=False, fim=False)
        elif self.tipo_fonte == "webcam":
            idx, ok = QInputDialog.getInt(self, "Câmera USB / Placa Drone", "Índice do dispositivo (0, 1, 2...):",
                                         self.indice_camera, 0, 10, 1)
            if ok:
                self.indice_camera = idx
                self.msg(f"Dispositivo de câmera configurado: #{self.indice_camera}")
                self._botoes(sel=True, ini=True, pausa=False, fim=False)
        elif self.tipo_fonte == "rtsp":
            url, ok = QInputDialog.getText(self, "Stream RTSP do Drone", "URL RTSP/RTMP da transmissão:",
                                          text=self.url_rtsp or "rtsp://192.168.1.100:554/live")
            if ok and url.strip():
                self.url_rtsp = url.strip()
                self.msg(f"Stream RTSP configurado: {self.url_rtsp}")
                self._botoes(sel=True, ini=True, pausa=False, fim=False)

    def _obter_fonte_video(self):
        if self.tipo_fonte == "arquivo":
            return FileVideoSource(self.caminho_video)
        elif self.tipo_fonte == "webcam":
            return WebcamVideoSource(self.indice_camera)
        else:
            return RTSPVideoSource(self.url_rtsp)

    def _iniciar(self):
        if not self._fonte_pronta():
            return
        ok, texto = modelo_disponivel(self.config.caminho_modelo)
        self.msg(texto, erro=not ok)

        for c in (self.c_quadro, self.c_ids, self.c_conf, self.c_contados,
                  self.c_estimativa, self.c_entradas, self.c_saidas):
            c.indisponivel()

        detector = rastreador = contador = None
        if ok:
            detector = DetectorBovinos(self.config.caminho_modelo, self.config.confianca_minima,
                                       self.config.dispositivo, usar_tiles=self.config.usar_tiles,
                                       tamanho_imagem=self.config.tamanho_imagem)
            try:
                # Buffer de 90 quadros para persistir rastreamento em vídeos de 60 FPS com oclusão
                rastreador = RastreadorBovinos(limiar_confianca=self.config.confianca_minima, buffer_perda=90)
                cfg_contagem = ConfigContagem(
                    estrategia=self.combo_regra.currentData(),
                    linha=self.linha_personalizada,
                    sentido_contado=self.combo_sentido.currentData()
                )
                contador = ContadorBovinos(cfg_contagem)
            except Exception as e:
                self.msg(f"Rastreamento indisponível ({e}). Será exibida apenas a detecção.", erro=True)

        try:
            fonte = self._obter_fonte_video()
        except Exception as e:
            self.msg(f"Erro ao preparar fonte de vídeo: {e}", erro=True)
            return

        passo = self.combo_desempenho.currentData() or 1
        self.worker = ProcessingWorker(fonte, detector, rastreador, contador, passo_processamento=passo)
        self.worker.aviso.connect(self.msg)
        self.worker.quadro_pronto.connect(self.video.mostrar)
        self.worker.metricas.connect(self._metricas)
        self.worker.erro.connect(lambda t: self.msg(t, erro=True))
        self.worker.resultado_final.connect(self._resultado_final)
        self.worker.finalizado.connect(self._terminou)
        self._botoes(sel=False, ini=False, pausa=True, fim=True)
        self.worker.start()

    def _timeline_movida(self, valor: int):
        self._arrastando_tempo = True
        total = self.slider_tempo.maximum() or 1
        fps = 30.0
        if self.worker and hasattr(self.worker, "_fonte") and self.worker._fonte:
            fps = self.worker._fonte.fps or 30.0
        s_atual = int(valor / fps)
        s_total = int(total / fps)
        self.lbl_tempo.setText(f"{s_atual // 60:02d}:{s_atual % 60:02d} / {s_total // 60:02d}:{s_total % 60:02d}")
        if self.worker:
            self.worker.saltar_para_quadro(valor)

    def _timeline_solta(self):
        self._arrastando_tempo = False
        if self.worker:
            self.worker.saltar_para_quadro(self.slider_tempo.value())

    def _alternar_pausa(self):
        if not self.worker:
            return
        if self.b_pausa.text() == "Pausar":
            self.worker.pausar()
            self.b_pausa.setText("Retomar")
        else:
            self.worker.retomar()
            self.b_pausa.setText("Pausar")

    def _encerrar(self):
        if self.worker:
            self.worker.encerrar()

    def _metricas(self, m: dict):
        self._metricas_atuais = m
        self.c_fps.definir(f"{m['fps']:.1f}")
        self.c_quadros.definir(str(m["quadros"]))
        self.c_tempo.definir(f"{m['tempo']:.1f} s")
        if m.get("detectados") is not None:
            self.c_quadro.definir(str(m["detectados"]))
            self.c_conf.definir("—" if m["conf_media"] is None else f"{m['conf_media'] * 100:.0f}%")
        r = m.get("contagem")
        if r is not None:
            self.c_ids.definir(str(r.ids_unicos))
            self.c_contados.definir(str(r.contados))
            self.c_estimativa.definir(r.texto_estimativa)
            self.c_entradas.definir(str(r.entradas))
            self.c_saidas.definir(str(r.saidas))

        total = m.get("total", 0)
        atual = m.get("quadros", 0)
        if total > 0:
            if not self._arrastando_tempo:
                self.slider_tempo.setRange(0, total)
                self.slider_tempo.setValue(atual)
            fps_base = 60.0 if total > 2000 else 30.0
            s_atual = int(atual / fps_base)
            s_total = int(total / fps_base)
            self.lbl_tempo.setText(f"{s_atual // 60:02d}:{s_atual % 60:02d} / {s_total // 60:02d}:{s_total % 60:02d}")

    def _resultado_final(self, r):
        self._ultimo_resultado = r
        if r is None or r.quadros_processados == 0:
            return
        nomes = {"ids_estaveis": "IDs estáveis", "linha_virtual": "linha virtual",
                 "area_interesse": "área de interesse"}
        self.msg(f"RESULTADO: {r.texto_estimativa} animais | regra: {nomes.get(r.estrategia, r.estrategia)} | "
                 f"contados: {r.contados} (entradas={r.entradas}, saídas={r.saidas}, saldo={r.saldo}) | "
                 f"IDs únicos: {r.ids_unicos} | pico simultâneo: {r.pico_simultaneo}")
        for aviso in r.avisos:
            self.msg("⚠ " + aviso)

    def _salvar_sessao_no_banco(self):
        r = self._ultimo_resultado
        m = self._metricas_atuais
        fonte_nome = (Path(self.caminho_video).name if self.tipo_fonte == "arquivo" and self.caminho_video
                      else f"{self.tipo_fonte}")

        registro = RegistroSessao(
            fonte_video=fonte_nome,
            modelo=Path(self.config.caminho_modelo).name,
            estrategia=r.estrategia if r else "nenhuma",
            confianca_minima=self.config.confianca_minima,
            dispositivo=self.config.dispositivo,
            duracao_segundos=m.get("tempo", 0.0),
            quadros_processados=m.get("quadros", 0),
            fps_medio=m.get("fps", 0.0),
            ids_unicos=r.ids_unicos if r else 0,
            contados_regra=r.contados if r else 0,
            entradas=r.entradas if r else 0,
            saidas=r.saidas if r else 0,
            pico_simultaneo=r.pico_simultaneo if r else 0,
            estimativa_texto=r.texto_estimativa if r else "—",
            avisos_json=json.dumps(r.avisos if r else [])
        )
        try:
            sid = self.db.salvar_sessao(registro)
            self.msg(f"Sessão gravada no banco de dados SQLite (Sessão #{sid}).")
        except Exception as e:
            self.msg(f"Erro ao salvar sessão no banco de dados: {e}", erro=True)

    def _terminou(self, motivo: str):
        textos = {"fim": "Processamento concluído com sucesso.",
                  "encerrado": "Sessão encerrada pelo usuário.",
                  "erro": "Sessão interrompida por erro."}
        self.msg(textos.get(motivo, motivo))

        # Grava no banco SQLite se ao menos 1 quadro foi processado
        if self._metricas_atuais.get("quadros", 0) > 0:
            self._salvar_sessao_no_banco()

        if self.worker:
            self.worker.wait()
            self.worker = None
        self.b_pausa.setText("Pausar")
        self._botoes(sel=True, ini=self._fonte_pronta(), pausa=False, fim=False)

    def closeEvent(self, e):
        if self.worker:
            self.worker.encerrar()
            self.worker.wait(3000)
        super().closeEvent(e)
