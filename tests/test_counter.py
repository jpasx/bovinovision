import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from services.counter import ConfigContagem, ContadorBovinos  # noqa: E402
from services.detector import Deteccao  # noqa: E402

W, H = 1000, 1000


def det(i, cx=500, cy=500, lado=20, **kw):
    return Deteccao(cx - lado, cy - lado, cx + lado, cy + lado, 0.9, id_rastreamento=i, **kw)


def test_mesmo_id_em_centenas_de_quadros_conta_uma_vez():
    c = ContadorBovinos(ConfigContagem(estrategia="ids_estaveis", min_quadros=5))
    for _ in range(500):
        c.atualizar([det(1)], W, H)
    r = c.resultado()
    assert r.contados == 1
    assert r.ids_unicos == 1
    assert r.detectados_quadro == 1


def test_nao_soma_deteccoes_de_todos_os_quadros():
    c = ContadorBovinos()
    for _ in range(100):
        c.atualizar([det(1), det(2), det(3)], W, H)
    r = c.resultado()
    assert r.contados == 3 and r.ids_unicos == 3 and r.detectados_quadro == 3


def test_id_efemero_nao_e_contado():
    c = ContadorBovinos(ConfigContagem(min_quadros=5))
    for _ in range(3):
        c.atualizar([det(9)], W, H)
    r = c.resultado()
    assert r.ids_unicos == 1 and r.contados == 0


def test_metricas_sao_distintas():
    c = ContadorBovinos(ConfigContagem(min_quadros=5))
    for _ in range(10):
        c.atualizar([det(1), det(2)], W, H)
    c.atualizar([det(3), det(4), det(5)], W, H)  # IDs novos, vistos uma vez
    r = c.resultado()
    assert r.detectados_quadro == 3
    assert r.ids_unicos == 5
    assert r.contados == 2


def linha_h(**kw):
    """Linha horizontal no centro; seta aponta para BAIXO (y crescente). Entrada = descer."""
    return ContadorBovinos(ConfigContagem(estrategia="linha_virtual", linha=(0.0, 0.5, 1.0, 0.5), **kw))


def passar(c, i, ys, cx=500):
    for y in ys:
        c.atualizar([det(i, cx=cx, cy=y)], W, H)


def test_linha_conta_entrada_no_sentido_da_seta():
    c = linha_h()
    passar(c, 1, (300, 350, 400, 450, 600, 650, 700))   # desce: entrada
    r = c.resultado()
    assert (r.entradas, r.saidas, r.contados) == (1, 0, 1)


def test_linha_conta_saida_no_sentido_contrario():
    c = linha_h()
    passar(c, 1, (700, 650, 600, 450, 400, 350, 300))   # sobe: saída
    r = c.resultado()
    assert (r.entradas, r.saidas, r.contados) == (0, 1, 1)


def test_sentido_filtrado_so_conta_entrada():
    c = linha_h(sentido_contado="entrada")
    passar(c, 1, (300, 350, 400, 450, 600, 650, 700))
    passar(c, 2, (700, 650, 600, 450, 400, 350, 300))
    r = c.resultado()
    assert r.contados == 1 and r.entradas == 1 and r.saidas == 1 and r.saldo == 0


def test_vai_e_volta_nao_conta_o_mesmo_animal_duas_vezes_no_total():
    c = linha_h()  # sentido "ambos": cada ID conta uma vez
    passar(c, 1, (300, 350, 400, 600, 650, 700, 600, 400, 350, 300))
    r = c.resultado()
    assert r.contados == 1 and r.entradas == 1 and r.saidas == 1 and r.saldo == 0


def test_tremor_dentro_da_zona_de_tolerancia_nao_conta():
    c = linha_h()  # banda = 1% da diagonal (~14 px)
    passar(c, 1, (300, 350, 400, 450, 495, 505, 495, 505, 495, 505, 450, 400))
    r = c.resultado()
    assert r.contados == 0


def test_nao_conta_quem_nao_cruza():
    c = linha_h()
    for _ in range(50):
        c.atualizar([det(1, cy=200), det(2, cy=800)], W, H)
    assert c.resultado().contados == 0


def test_cruzamento_fora_do_segmento_da_linha_nao_conta():
    # linha só cobre a metade esquerda do quadro (x de 0 a 50%)
    c = ContadorBovinos(ConfigContagem(estrategia="linha_virtual", linha=(0.0, 0.5, 0.5, 0.5)))
    passar(c, 1, (300, 350, 400, 450, 600, 650, 700), cx=800)   # passa pela direita
    passar(c, 2, (300, 350, 400, 450, 600, 650, 700), cx=200)   # passa pela esquerda
    assert c.resultado().contados == 1


def test_trilha_muito_recente_nao_conta_cruzamento():
    c = linha_h(min_quadros_linha=3)
    passar(c, 1, (400, 600))  # só 2 observações
    assert c.resultado().contados == 0


def test_linha_vertical_e_inclinada():
    # vertical: A=(0.5,0) -> B=(0.5,1): normal aponta para a ESQUERDA (x decrescente)
    c = ContadorBovinos(ConfigContagem(estrategia="linha_virtual", linha=(0.5, 0.0, 0.5, 1.0)))
    for x in (700, 650, 600, 450, 400, 350):
        c.atualizar([det(1, cx=x)], W, H)
    r = c.resultado()
    assert r.contados == 1 and r.entradas == 1
    # inclinada (diagonal): cruzando perpendicularmente (ex: de (300, 700) para (700, 300))
    c = ContadorBovinos(ConfigContagem(estrategia="linha_virtual", linha=(0.0, 0.0, 1.0, 1.0)))
    for p in (200, 300, 400, 600, 700, 800):
        c.atualizar([det(1, cx=p, cy=1000 - p)], W, H)
    assert c.resultado().contados == 1


def test_linha_avisa_quando_camera_em_movimento():
    c = linha_h(camera_em_movimento=True)
    c.atualizar([det(1)], W, H)
    assert any("PARADA" in a for a in c.resultado().avisos)


def test_sentido_invalido():
    with pytest.raises(ValueError):
        ContadorBovinos(ConfigContagem(estrategia="linha_virtual", sentido_contado="diagonal"))


def test_area_de_interesse():
    c = ContadorBovinos(ConfigContagem(estrategia="area_interesse", area=(0.4, 0.4, 0.6, 0.6), min_quadros=3))
    for _ in range(5):
        c.atualizar([det(1, 500, 500), det(2, 100, 100)], W, H)
    r = c.resultado()
    assert r.contados == 1 and r.ids_unicos == 2


def test_aviso_de_fragmentacao_de_ids():
    c = ContadorBovinos()
    for k in range(10):
        c.atualizar([det(k + 1)], W, H)  # um animal visível por vez, IDs sempre novos
    assert any("fragmentação" in a for a in c.resultado().avisos)


def test_estimativa_sempre_sinalizada_e_camera_em_movimento_avisa():
    c = ContadorBovinos(ConfigContagem(camera_em_movimento=True))
    c.atualizar([det(1)], W, H)
    avisos = " ".join(c.resultado().avisos)
    assert "estimativa" in avisos and "Câmera em movimento" in avisos


def test_sem_quadros_nao_inventa_numeros():
    r = ContadorBovinos().resultado()
    assert r.texto_estimativa == "—" and r.contados == 0 and r.avisos


def test_deteccao_sem_id_nao_entra_na_contagem():
    c = ContadorBovinos()
    for _ in range(10):
        c.atualizar([Deteccao(0, 0, 10, 10, 0.9)], W, H)
    r = c.resultado()
    assert r.contados == 0 and r.ids_unicos == 0 and r.detectados_quadro == 1
    assert any("sem ID" in a for a in r.avisos)


def test_estrategia_invalida():
    with pytest.raises(ValueError):
        ContadorBovinos(ConfigContagem(estrategia="inventada"))


def test_varredura_drone_anti_repeticao_evita_duplicidade_por_troca_de_id():
    cfg = ConfigContagem(estrategia="varredura_drone", linha=(0.0, 0.5, 1.0, 0.5), sentido_contado="entrada",
                         dedup_espacial=0.10, dedup_tempo_quadros=60)
    c = ContadorBovinos(cfg)
    # Animal com ID 1 cruza descendo na posição x=500
    for y in (400, 450, 480, 520, 560):
        c.atualizar([det(1, cx=500, cy=y)], W, H)
    # Suponha que o ID 1 foi perdido e o tracker criou ID 2 imediatamente na mesma posição x=505 cruzando a linha
    for y in (480, 520, 560):
        c.atualizar([det(2, cx=505, cy=y)], W, H)

    r = c.resultado()
    # O filtro anti-repetição espaço-temporal deve mesclar os eventos e contar apenas 1 bovino!
    assert r.contados == 1
    assert r.entradas == 1
    assert r.ids_unicos == 2  # Houve 2 IDs rastreados, mas apenas 1 bovino real


def test_varredura_drone_dois_animais_distintos_sao_contados():
    cfg = ConfigContagem(estrategia="varredura_drone", linha=(0.0, 0.5, 1.0, 0.5), sentido_contado="entrada",
                         dedup_espacial=0.10, dedup_tempo_quadros=60)
    c = ContadorBovinos(cfg)
    # Animal 1 cruza na esquerda (x=200)
    for y in (400, 450, 480, 520, 560):
        c.atualizar([det(1, cx=200, cy=y)], W, H)
    # Animal 2 cruza na direita (x=800)
    for y in (400, 450, 480, 520, 560):
        c.atualizar([det(2, cx=800, cy=y)], W, H)

    r = c.resultado()
    assert r.contados == 2
    assert r.entradas == 2
