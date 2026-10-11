import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "training"))
from dividir_dataset import dividir, grupo_do_arquivo  # noqa: E402


def _criar(pasta: Path, voo: str, n: int):
    for i in range(n):
        (pasta / f"{voo}_{i:03d}.jpg").write_bytes(b"x")
        (pasta / f"{voo}_{i:03d}.txt").write_text("0 0.5 0.5 0.1 0.1\n")


def test_grupo():
    assert grupo_do_arquivo("voo1_000120") == "voo1"


def test_divisao_sem_vazamento_entre_voos(tmp_path):
    ent = tmp_path / "ent"
    ent.mkdir()
    for v in ("a", "b", "c", "d", "e", "f"):
        _criar(ent, v, 5)
    saida = tmp_path / "saida"
    c = dividir(ent, saida)
    assert sum(c.values()) == 30
    voos = {p: {f.stem.rsplit("_", 1)[0] for f in (saida / "images" / p).iterdir()} for p in c}
    assert not (voos["train"] & voos["val"]) and not (voos["train"] & voos["test"])
    assert not (voos["val"] & voos["test"])
    assert (saida / "data.yaml").is_file()


def test_sem_anotacoes(tmp_path):
    import pytest
    (tmp_path / "x_001.jpg").write_bytes(b"x")
    with pytest.raises(SystemExit):
        dividir(tmp_path, tmp_path / "s")
