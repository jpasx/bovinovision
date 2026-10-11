"""Teste de integração do pipeline com um DETECTOR FALSO (apenas em teste).

Não valida a qualidade da detecção real (não existe modelo). Valida que vídeo ->
detecção -> rastreamento -> contagem -> worker funcionam juntos e que o mesmo animal
visto em dezenas de quadros é contado uma única vez.
"""
import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import cv2  # noqa: E402
import numpy as np  # noqa: E402
import pytest  # noqa: E402
from PySide6.QtCore import QCoreApplication  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from services.counter import ConfigContagem, ContadorBovinos  # noqa: E402
from services.detector import Deteccao  # noqa: E402
from services.processing_worker import ProcessingWorker  # noqa: E402
from services.tracker import RastreadorBovinos  # noqa: E402
from services.video_source import FileVideoSource  # noqa: E402


class DetectorFalso:
    aviso_dispositivo = None
    dispositivo = "cpu"

    def __init__(self):
        self.k = 0

    def carregar(self):
        pass

    def detectar(self, quadro):
        k = self.k
        self.k += 1
        return [Deteccao(50 + 3 * k, 50, 90 + 3 * k, 90, 0.9),
                Deteccao(200, 100 + 2 * k, 240, 140 + 2 * k, 0.8),
                Deteccao(300, 200, 340, 240, 0.7)]


@pytest.fixture(scope="module")
def app():
    return QCoreApplication.instance() or QCoreApplication([])


@pytest.fixture
def video(tmp_path):
    caminho = tmp_path / "v.avi"
    w = cv2.VideoWriter(str(caminho), cv2.VideoWriter_fourcc(*"MJPG"), 1000, (400, 300))
    for _ in range(40):
        w.write(np.zeros((300, 400, 3), np.uint8))
    w.release()
    return str(caminho)


def test_pipeline_completo_conta_tres_animais_uma_vez_cada(app, video):
    worker = ProcessingWorker(
        FileVideoSource(video), DetectorFalso(),
        RastreadorBovinos(compensar_movimento_camera=False),
        ContadorBovinos(ConfigContagem(estrategia="ids_estaveis", min_quadros=5)))
    metricas, finais, motivos, erros = [], [], [], []
    worker.metricas.connect(metricas.append)
    worker.resultado_final.connect(finais.append)
    worker.finalizado.connect(motivos.append)
    worker.erro.connect(erros.append)
    worker.run()  # executa de forma síncrona no teste

    assert not erros and motivos == ["fim"]
    assert len(metricas) == 40
    r = finais[0]
    assert r.quadros_processados == 40
    assert r.detectados_quadro == 3
    assert r.ids_unicos == 3          # 120 detecções no total, mas só 3 animais
    assert r.contados == 3
    assert r.avisos                   # sempre há ressalvas de estimativa


def test_sem_modelo_nao_inventa_contagem(app, video):
    worker = ProcessingWorker(FileVideoSource(video))
    metricas, finais = [], []
    worker.metricas.connect(metricas.append)
    worker.resultado_final.connect(finais.append)
    worker.run()
    assert all(m["detectados"] is None and m["contagem"] is None for m in metricas)
    assert finais == [None]
