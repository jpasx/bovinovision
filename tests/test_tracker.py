import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from services.detector import Deteccao  # noqa: E402
from services.tracker import RastreadorBovinos  # noqa: E402


def caixa(cx, cy, lado=30, conf=0.9):
    return Deteccao(cx - lado, cy - lado, cx + lado, cy + lado, conf)


def test_mesmos_animais_mantem_ids_entre_quadros():
    t = RastreadorBovinos(compensar_movimento_camera=False)
    ids_por_quadro = []
    for k in range(20):
        r = t.atualizar([caixa(100 + 2 * k, 100), caixa(400, 300 + k)])
        ids_por_quadro.append({d.id_rastreamento for d in r if d.id_rastreamento is not None})
    ids_finais = ids_por_quadro[-1]
    assert len(ids_finais) == 2
    todos = set().union(*ids_por_quadro)
    assert todos == ids_finais  # nenhum ID extra foi criado ao longo de 20 quadros


def test_sem_deteccoes_nao_quebra_e_nao_inventa():
    t = RastreadorBovinos(compensar_movimento_camera=False)
    assert t.atualizar([]) == []


def test_estado_confirmado_apos_alguns_quadros():
    t = RastreadorBovinos(compensar_movimento_camera=False)
    r = []
    for _ in range(8):
        r = t.atualizar([caixa(200, 200)])
    assert r[0].id_rastreamento is not None and r[0].estado == "confirmado"


def test_reencontro_apos_perda_marca_possivel_perda():
    t = RastreadorBovinos(compensar_movimento_camera=False, buffer_perda=30)
    for _ in range(8):
        t.atualizar([caixa(200, 200)])
    id_original = t.atualizar([caixa(200, 200)])[0].id_rastreamento
    for _ in range(3):  # animal some (oclusão)
        t.atualizar([])
    assert t.ids_perdidos >= 1
    r = t.atualizar([caixa(200, 200)])
    assert r[0].id_rastreamento == id_original and r[0].possivel_perda


def test_funciona_com_compensacao_de_camera_e_imagem():
    t = RastreadorBovinos(compensar_movimento_camera=True)
    rng = np.random.default_rng(0)
    base = rng.integers(0, 255, (480, 640, 3), dtype=np.uint8)
    r = []
    for k in range(6):
        quadro = np.roll(base, k * 3, axis=1)  # câmera "andando"
        r = t.atualizar([caixa(200 + k * 3, 200)], quadro)
    assert r[0].id_rastreamento is not None
