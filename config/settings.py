import sys
from dataclasses import dataclass
from pathlib import Path

if getattr(sys, "frozen", False):
    RAIZ_PROJETO = Path(sys.executable).resolve().parent
else:
    RAIZ_PROJETO = Path(__file__).resolve().parent.parent
PASTA_MODELOS = RAIZ_PROJETO / "models"
PASTA_VIDEOS = RAIZ_PROJETO / "data" / "videos"
PASTA_SESSOES = RAIZ_PROJETO / "data" / "sessions"

NOME_APP = "BovinoVision AI"
VERSAO_APP = "0.1.0"


@dataclass
class ConfiguracaoProcessamento:
    """Parâmetros ajustáveis de uma sessão."""
    caminho_modelo: str = str(PASTA_MODELOS / "bovinos_aereo.pt" if (PASTA_MODELOS / "bovinos_aereo.pt").exists() else PASTA_MODELOS / "bovinos.pt")
    confianca_minima: float = 0.20
    dispositivo: str = "auto"  # "auto", "cpu" ou "cuda"
    usar_tiles: bool = False   # detecção em recortes (mais lenta, melhor p/ animais pequenos)
    tamanho_imagem: int = 1088 # Resolução otimizada para detecção aérea com drones em GPU
