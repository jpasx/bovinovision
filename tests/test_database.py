import json
from pathlib import Path

from database.db_manager import DatabaseManager, RegistroSessao


def test_salvar_e_listar_sessoes(tmp_path):
    db_file = tmp_path / "teste.db"
    db = DatabaseManager(db_file)
    s1 = RegistroSessao(
        fonte_video="voo1.mp4", modelo="bovinos.pt", estrategia="linha_virtual",
        confianca_minima=0.35, dispositivo="cuda:0", duracao_segundos=45.2,
        quadros_processados=1350, fps_medio=29.8, ids_unicos=42, contados_regra=38,
        entradas=40, saidas=2, pico_simultaneo=25, estimativa_texto="≈ 38",
        avisos_json=json.dumps(["Câmera em movimento", "Oclusão temporária detectada"])
    )
    novo_id = db.salvar_sessao(s1)
    assert novo_id == 1

    sessoes = db.listar_sessoes()
    assert len(sessoes) == 1
    assert sessoes[0].fonte_video == "voo1.mp4"
    assert sessoes[0].contados_regra == 38
    assert sessoes[0].entradas == 40
    assert sessoes[0].saidas == 2
    avisos_recuperados = json.loads(sessoes[0].avisos_json)
    assert any("movimento" in a for a in avisos_recuperados)


def test_exportar_csv(tmp_path):
    db_file = tmp_path / "teste.db"
    csv_file = tmp_path / "relatorio.csv"
    db = DatabaseManager(db_file)

    for i in range(3):
        db.salvar_sessao(RegistroSessao(
            fonte_video=f"voo_{i}.mp4", contados_regra=10 + i,
            avisos_json=json.dumps([f"Aviso {i}"])
        ))

    qtd = db.exportar_csv(csv_file)
    assert qtd == 3
    assert csv_file.is_file()
    linhas = csv_file.read_text(encoding="utf-8-sig").splitlines()
    assert len(linhas) == 4  # cabeçalho + 3 registros
    assert "voo_2.mp4" in linhas[1] or "voo_0.mp4" in linhas[3]
    assert "Aviso" in linhas[1]
