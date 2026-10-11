import numpy as np

from services.detector import gerar_tiles, resolver_dispositivo, modelo_disponivel, DetectorBovinos, ErroModelo
import pytest


def test_tiles_cobrem_imagem_inteira():
    h, w = 3000, 4000
    cobertura = np.zeros((h, w), bool)
    for x, y, x2, y2 in gerar_tiles(h, w, 640, 0.2):
        assert x2 - x <= 640 and y2 - y <= 640
        cobertura[y:y2, x:x2] = True
    assert cobertura.all()


def test_imagem_menor_que_tile():
    assert gerar_tiles(300, 400, 640, 0.2) == [(0, 0, 400, 300)]


def test_modelo_ausente():
    ok, msg = modelo_disponivel("nao_existe.pt")
    assert not ok and "não encontrado" in msg
    with pytest.raises(ErroModelo):
        DetectorBovinos("nao_existe.pt").carregar()


def test_detectar_sem_carregar():
    with pytest.raises(ErroModelo):
        DetectorBovinos("x.pt").detectar(np.zeros((10, 10, 3), np.uint8))


def test_cpu_explicita():
    assert resolver_dispositivo("cpu")[0] == "cpu"
