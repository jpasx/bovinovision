"""Divide imagens anotadas (formato YOLO) em treino/validação/teste e gera o data.yaml.

Entrada: uma pasta com pares  imagem.jpg + imagem.txt  (anotação YOLO, classe 0 = bovino).
A divisão é feita por VÍDEO/VOO (prefixo do nome antes do último '_'), para que quadros
quase idênticos do mesmo voo não vazem entre treino e teste, o que inflaria as métricas.

Uso:
    python training/dividir_dataset.py data/datasets/bovinos/anotadas
"""
import argparse
import random
import shutil
import sys
from pathlib import Path

EXT = {".jpg", ".jpeg", ".png"}


def grupo_do_arquivo(nome: str) -> str:
    return nome.rsplit("_", 1)[0] if "_" in nome else nome


def dividir(entrada: Path, saida: Path, prop_val=0.15, prop_teste=0.15, semente=42) -> dict:
    imagens = sorted(p for p in entrada.rglob("*") if p.suffix.lower() in EXT and p.with_suffix(".txt").is_file())
    if not imagens:
        raise SystemExit(f"Nenhum par imagem+anotação (.txt) encontrado em {entrada}")
    grupos: dict[str, list[Path]] = {}
    for img in imagens:
        grupos.setdefault(grupo_do_arquivo(img.stem), []).append(img)

    nomes = sorted(grupos)
    rng = random.Random(semente)
    if len(nomes) >= 3:
        rng.shuffle(nomes)
        n_teste = max(1, round(len(nomes) * prop_teste))
        n_val = max(1, round(len(nomes) * prop_val))
        sel = {"test": nomes[:n_teste], "val": nomes[n_teste:n_teste + n_val],
               "train": nomes[n_teste + n_val:]}
        divisao = {k: [i for g in gs for i in grupos[g]] for k, gs in sel.items()}
    else:
        # Menos de 3 voos: divide por imagem. Quadros vizinhos ficam parecidos, então
        # as métricas de validação/teste serão otimistas (vazamento de dados).
        print("AVISO: menos de 3 vídeos/voos; divisão por imagem torna a validação otimista.")
        todas = list(imagens)
        rng.shuffle(todas)
        n_teste = max(1, round(len(todas) * prop_teste))
        n_val = max(1, round(len(todas) * prop_val))
        divisao = {"test": todas[:n_teste], "val": todas[n_teste:n_teste + n_val],
                   "train": todas[n_teste + n_val:]}

    contagem = {}
    for parte, arquivos in divisao.items():
        (saida / "images" / parte).mkdir(parents=True, exist_ok=True)
        (saida / "labels" / parte).mkdir(parents=True, exist_ok=True)
        for img in arquivos:
            shutil.copy2(img, saida / "images" / parte / img.name)
            shutil.copy2(img.with_suffix(".txt"), saida / "labels" / parte / (img.stem + ".txt"))
        contagem[parte] = len(arquivos)

    yaml = (f"path: {saida.resolve().as_posix()}\ntrain: images/train\nval: images/val\n"
            f"test: images/test\nnames:\n  0: bovino\n")
    (saida / "data.yaml").write_text(yaml, encoding="utf-8")
    return contagem


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("entrada", type=Path)
    p.add_argument("--saida", type=Path, default=None)
    a = p.parse_args()
    saida = a.saida or a.entrada.parent / "yolo"
    c = dividir(a.entrada, saida)
    print(f"Divisão concluída em {saida}: {c}")
    print(f"Configuração: {saida / 'data.yaml'}")
    if c.get("train", 0) < 100:
        print("AVISO: poucas imagens de treino. Resultados podem ser fracos e pouco confiáveis.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
