import sys
from pathlib import Path

import cv2
import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from services.video_source import (ErroFonteVideo, FileVideoSource,
                                   RTSPVideoSource, WebcamVideoSource)


def test_arquivo_inexistente():
    with pytest.raises(ErroFonteVideo):
        FileVideoSource("nao_existe.mp4").abrir()


def test_arquivo_invalido(tmp_path):
    f = tmp_path / "falso.mp4"
    f.write_text("isto não é um vídeo")
    with pytest.raises(ErroFonteVideo):
        FileVideoSource(str(f)).abrir()


def test_le_todos_os_quadros(tmp_path):
    caminho = tmp_path / "t.avi"
    w = cv2.VideoWriter(str(caminho), cv2.VideoWriter_fourcc(*"MJPG"), 10, (64, 48))
    for _ in range(5):
        w.write(np.zeros((48, 64, 3), np.uint8))
    w.release()
    fonte = FileVideoSource(str(caminho))
    fonte.abrir()
    n = 0
    while fonte.ler_quadro() is not None:
        n += 1
    fonte.fechar()
    assert n == 5
    assert not fonte.eh_transmissao_ao_vivo


def test_webcam_invalida():
    # Índice 9999 improvável de existir
    fonte = WebcamVideoSource(indice_dispositivo=9999)
    assert fonte.eh_transmissao_ao_vivo
    with pytest.raises(ErroFonteVideo):
        fonte.abrir()


def test_rtsp_invalido():
    fonte = RTSPVideoSource("rtsp://127.0.0.1:9999/live_stream_inexistente")
    assert fonte.eh_transmissao_ao_vivo
    with pytest.raises(ErroFonteVideo):
        fonte.abrir()
