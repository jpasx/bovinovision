"""Treina um modelo YOLO de detecção de bovinos a partir do data.yaml gerado.

Uso:
    python training/treinar.py data/datasets/bovinos/yolo/data.yaml
    python training/treinar.py data/datasets/bovinos/yolo/data.yaml --epocas 100 --tamanho 1280

Ao final, os pesos ficam em runs/ e o melhor é copiado para models/bovinos.pt.
Nenhuma métrica é exibida antes do treino ou inventada: elas vêm da validação real.
"""
import argparse
import shutil
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("dados", type=Path, help="caminho do data.yaml")
    p.add_argument("--base", default="yolov8n.pt", help="modelo inicial (baixado automaticamente)")
    p.add_argument("--epocas", type=int, default=50)
    p.add_argument("--tamanho", type=int, default=960, help="tamanho da imagem (px). Animais pequenos pedem valores maiores")
    p.add_argument("--lote", type=int, default=8, help="reduza se faltar memória da GPU")
    a = p.parse_args()

    if not a.dados.is_file():
        print(f"data.yaml não encontrado: {a.dados}\nRode antes training/dividir_dataset.py")
        return 1
    import torch
    from ultralytics import YOLO

    dispositivo = 0 if torch.cuda.is_available() else "cpu"
    if dispositivo == "cpu":
        print("AVISO: GPU CUDA não disponível. O treino em CPU será muito lento.")
    modelo = YOLO(a.base)
    modelo.train(data=str(a.dados), epochs=a.epocas, imgsz=a.tamanho, batch=a.lote,
                 device=dispositivo, project=str(RAIZ / "runs"), name="bovinos", exist_ok=True)

    print("\nAvaliação no conjunto de TESTE (imagens que não participaram do treino):")
    melhor = Path(modelo.trainer.best)
    metricas = YOLO(str(melhor)).val(data=str(a.dados), split="test", imgsz=a.tamanho, device=dispositivo)
    print(f"mAP50 = {metricas.box.map50:.3f} | mAP50-95 = {metricas.box.map:.3f}")

    destino = RAIZ / "models" / "bovinos.pt"
    destino.parent.mkdir(exist_ok=True)
    shutil.copy2(melhor, destino)
    print(f"Modelo copiado para {destino}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
