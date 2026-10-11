"""Camada de detecção baseada em Ultralytics YOLO.

Nenhum modelo é fornecido com o projeto. O arquivo de pesos treinado deve
existir em `caminho_modelo`; caso contrário, é levantado `ErroModelo`
e NENHUMA detecção é inventada.
"""
from dataclasses import dataclass
from pathlib import Path

import numpy as np


class ErroModelo(Exception):
    """Modelo ausente, incompatível ou dispositivo indisponível."""


@dataclass
class Deteccao:
    x1: float
    y1: float
    x2: float
    y2: float
    confianca: float
    id_rastreamento: int | None = None
    # "sem_rastreio" | "sem_id" | "novo" | "confirmado" | "reencontrado"
    estado: str = "sem_rastreio"
    possivel_perda: bool = False  # True se o ID havia sido perdido e foi recuperado agora


def modelo_disponivel(caminho: str) -> tuple[bool, str]:
    """Verifica se o arquivo de modelo existe e devolve uma mensagem para o usuário."""
    if Path(caminho).is_file():
        return True, f"Modelo encontrado: {caminho}"
    return False, (
        f"Modelo não encontrado em '{caminho}'. O vídeo será exibido sem detecção. "
        "Coloque um modelo treinado para bovinos aéreos na pasta models/."
    )


def resolver_dispositivo(preferido: str = "auto") -> tuple[str, str | None]:
    """Devolve (dispositivo, aviso). 'auto' usa GPU CUDA se existir, senão CPU."""
    try:
        import torch
    except ImportError:
        return "cpu", "PyTorch não instalado; usando CPU."
    tem_gpu = torch.cuda.is_available()
    if preferido == "cuda" and not tem_gpu:
        return "cpu", "GPU CUDA solicitada, mas não disponível; usando CPU."
    if preferido in ("auto", "cuda") and tem_gpu:
        return "cuda:0", None
    return "cpu", None if preferido == "cpu" else "GPU CUDA não disponível; usando CPU."


def gerar_tiles(altura: int, largura: int, tamanho: int, sobreposicao: float):
    """Lista de (x, y, x2, y2) cobrindo a imagem inteira com sobreposição."""
    passo = max(1, int(tamanho * (1 - sobreposicao)))

    def eixos(total):
        if total <= tamanho:
            return [0]
        pos = list(range(0, total - tamanho, passo))
        pos.append(total - tamanho)
        return pos

    return [(x, y, min(x + tamanho, largura), min(y + tamanho, altura))
            for y in eixos(altura) for x in eixos(largura)]


class DetectorBovinos:
    def __init__(self, caminho_modelo: str, confianca_minima: float = 0.35,
                 dispositivo: str = "auto", usar_tiles: bool = False,
                 tamanho_tile: int = 640, sobreposicao_tile: float = 0.2,
                 tamanho_imagem: int = 640):
        self.caminho_modelo = caminho_modelo
        self.confianca_minima = confianca_minima
        self.usar_tiles = usar_tiles
        self.tamanho_tile = tamanho_tile
        self.sobreposicao_tile = sobreposicao_tile
        self.tamanho_imagem = tamanho_imagem
        self.dispositivo, self.aviso_dispositivo = resolver_dispositivo(dispositivo)
        self._modelo = None

    def carregar(self) -> None:
        if not Path(self.caminho_modelo).is_file():
            raise ErroModelo(f"Modelo não encontrado: {self.caminho_modelo}")
        try:
            from ultralytics import YOLO
        except ImportError as e:
            raise ErroModelo("Biblioteca 'ultralytics' não instalada.") from e
        try:
            self._modelo = YOLO(self.caminho_modelo)
        except Exception as e:
            raise ErroModelo(f"Modelo inválido ou incompatível ({Path(self.caminho_modelo).name}): {e}") from e

    def _inferir(self, imagem: np.ndarray) -> np.ndarray:
        """Retorna array Nx5 [x1,y1,x2,y2,conf] em coordenadas da imagem recebida."""
        r = self._modelo.predict(imagem, conf=self.confianca_minima, device=self.dispositivo,
                                 imgsz=self.tamanho_imagem, verbose=False)[0]
        if r.boxes is None or len(r.boxes) == 0:
            return np.zeros((0, 5), np.float32)
        xyxy = r.boxes.xyxy.cpu().numpy()
        conf = r.boxes.conf.cpu().numpy()[:, None]
        return np.hstack([xyxy, conf]).astype(np.float32)

    def detectar(self, quadro: np.ndarray) -> list[Deteccao]:
        if self._modelo is None:
            raise ErroModelo("Modelo não foi carregado.")
        if not self.usar_tiles:
            caixas = self._inferir(quadro)
        else:
            h, w = quadro.shape[:2]
            todas = []
            for x, y, x2, y2 in gerar_tiles(h, w, self.tamanho_tile, self.sobreposicao_tile):
                c = self._inferir(quadro[y:y2, x:x2])
                if len(c):
                    c[:, [0, 2]] += x
                    c[:, [1, 3]] += y
                    todas.append(c)
            caixas = self._fundir(np.vstack(todas)) if todas else np.zeros((0, 5), np.float32)
        return [Deteccao(*map(float, c)) for c in caixas]

    @staticmethod
    def _fundir(caixas: np.ndarray, iou: float = 0.5) -> np.ndarray:
        """Remove duplicatas na sobreposição entre tiles (NMS)."""
        if len(caixas) == 0:
            return caixas
        try:
            import torch
            from torchvision.ops import nms
            manter = nms(torch.from_numpy(caixas[:, :4]), torch.from_numpy(caixas[:, 4]), iou)
            return caixas[manter.numpy()]
        except Exception:
            boxes = [[float(c[0]), float(c[1]), float(c[2] - c[0]), float(c[3] - c[1])] for c in caixas]
            scores = [float(c[4]) for c in caixas]
            indices = cv2.dnn.NMSBoxes(boxes, scores, score_threshold=0.0, nms_threshold=iou)
            if len(indices) == 0:
                return np.zeros((0, 5), dtype=np.float32)
            indices = np.array(indices).flatten()
            return caixas[indices]

