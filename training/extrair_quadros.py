"""Extrai quadros de vídeos de drone para serem anotados.

Uso:
    python training/extrair_quadros.py data/videos/voo1.mp4 --a_cada 30
Os quadros são salvos em data/datasets/bovinos/brutas/<nome_do_video>/.
"""
import argparse
import sys
from pathlib import Path

import cv2

RAIZ = Path(__file__).resolve().parent.parent


def extrair(video: Path, saida: Path, a_cada: int) -> int:
    cap = cv2.VideoCapture(str(video))
    if not cap.isOpened():
        raise SystemExit(f"Não foi possível abrir o vídeo: {video}")
    saida.mkdir(parents=True, exist_ok=True)
    i = salvos = 0
    while True:
        ok, quadro = cap.read()
        if not ok:
            break
        if i % a_cada == 0:
            cv2.imwrite(str(saida / f"{video.stem}_{i:06d}.jpg"), quadro, [cv2.IMWRITE_JPEG_QUALITY, 95])
            salvos += 1
        i += 1
    cap.release()
    return salvos


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("video", type=Path)
    p.add_argument("--a_cada", type=int, default=30, help="salvar 1 quadro a cada N (padrão: 30)")
    p.add_argument("--saida", type=Path, default=None)
    a = p.parse_args()
    saida = a.saida or RAIZ / "data" / "datasets" / "bovinos" / "brutas" / a.video.stem
    n = extrair(a.video, saida, a.a_cada)
    print(f"{n} quadros salvos em {saida}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
