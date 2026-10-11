"""Fontes de vídeo e adaptadores para o BovinoVision AI.

Lê quadro a quadro de forma contínua sem carregar o vídeo inteiro na memória.
Suporta arquivos locais, webcam para bancada de testes e streams RTSP/RTMP ao vivo.

Nota sobre drones (DJI Mini 3, Air 2S, etc.):
Drones de consumo não disponibilizam uma porta RTSP aberta diretamente no drone.
Para receber o vídeo ao vivo:
1. Usar aplicativo móvel transmissor de RTMP/RTSP conectado ao rádio-controle.
2. Usar controle com saída HDMI (ex: DJI RC Pro) conectado a uma placa de captura USB (WebcamVideoSource).
3. Usar gateway RTSP ou SDK oficial do fabricante compatível com o modelo.
"""
import time
from abc import ABC, abstractmethod
from pathlib import Path

import cv2
import numpy as np


class ErroFonteVideo(Exception):
    """Falha ao abrir ou ler uma fonte de vídeo."""


class VideoSource(ABC):
    """Interface abstrata base para qualquer fonte de vídeo."""

    @abstractmethod
    def abrir(self) -> None: ...

    @abstractmethod
    def ler_quadro(self) -> np.ndarray | None:
        """Retorna o próximo quadro (BGR) ou None ao fim da fonte."""

    @abstractmethod
    def fechar(self) -> None: ...

    def posicionar_quadro(self, numero_quadro: int) -> None:
        """Pula para um quadro específico (apenas fontes gravadas)."""
        pass

    @property
    def fps(self) -> float:
        return 0.0

    @property
    def total_quadros(self) -> int:
        """0 quando desconhecido (transmissões ao vivo)."""
        return 0

    @property
    def eh_transmissao_ao_vivo(self) -> bool:
        return False

    @property
    def descricao(self) -> str:
        return self.__class__.__name__


class FileVideoSource(VideoSource):
    """Leitor de arquivos de vídeo locais (MP4, AVI, MOV, MKV)."""

    def __init__(self, caminho: str | Path):
        self.caminho = Path(caminho)
        self._cap: cv2.VideoCapture | None = None

    def abrir(self) -> None:
        if not self.caminho.is_file():
            raise ErroFonteVideo(f"Arquivo de vídeo não encontrado: {self.caminho}")
        cap = cv2.VideoCapture(str(self.caminho))
        if not cap.isOpened():
            cap.release()
            raise ErroFonteVideo(
                f"Não foi possível abrir o vídeo (formato inválido ou corrompido): {self.caminho.name}"
            )
        ok, quadro = cap.read()
        if not ok or quadro is None:
            cap.release()
            raise ErroFonteVideo(f"O vídeo não contém quadros legíveis: {self.caminho.name}")
        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
        self._cap = cap

    def ler_quadro(self) -> np.ndarray | None:
        if self._cap is None:
            raise ErroFonteVideo("Fonte de vídeo não foi aberta.")
        ok, quadro = self._cap.read()
        return quadro if ok else None

    def posicionar_quadro(self, numero_quadro: int) -> None:
        if self._cap is not None:
            total = self.total_quadros
            alvo = max(0, min(numero_quadro, total - 1)) if total > 0 else max(0, numero_quadro)
            self._cap.set(cv2.CAP_PROP_POS_FRAMES, alvo)

    def fechar(self) -> None:
        if self._cap is not None:
            self._cap.release()
            self._cap = None

    @property
    def fps(self) -> float:
        return float(self._cap.get(cv2.CAP_PROP_FPS)) if self._cap else 0.0

    @property
    def total_quadros(self) -> int:
        return int(self._cap.get(cv2.CAP_PROP_FRAME_COUNT)) if self._cap else 0

    @property
    def descricao(self) -> str:
        return str(self.caminho.name)


class WebcamVideoSource(VideoSource):
    """Entrada de vídeo de câmera USB ou placa de captura HDMI do drone."""

    def __init__(self, indice_dispositivo: int = 0):
        self.indice = indice_dispositivo
        self._cap: cv2.VideoCapture | None = None

    def abrir(self) -> None:
        # cv2.CAP_DSHOW no Windows para abertura rápida de webcam
        cap = cv2.VideoCapture(self.indice, cv2.CAP_DSHOW)
        if not cap.isOpened():
            cap.release()
            raise ErroFonteVideo(f"Não foi possível abrir o dispositivo de câmera ID #{self.indice}.")
        ok, quadro = cap.read()
        if not ok or quadro is None:
            cap.release()
            raise ErroFonteVideo(f"Câmera #{self.indice} não retornou nenhum quadro legível.")
        self._cap = cap

    def ler_quadro(self) -> np.ndarray | None:
        if self._cap is None:
            raise ErroFonteVideo("Câmera não foi aberta.")
        ok, quadro = self._cap.read()
        return quadro if ok else None

    def fechar(self) -> None:
        if self._cap is not None:
            self._cap.release()
            self._cap = None

    @property
    def fps(self) -> float:
        return float(self._cap.get(cv2.CAP_PROP_FPS)) if self._cap else 30.0

    @property
    def eh_transmissao_ao_vivo(self) -> bool:
        return True

    @property
    def descricao(self) -> str:
        return f"Câmera/Captura #{self.indice}"


class RTSPVideoSource(VideoSource):
    """Fluxo RTSP/RTMP de rede.

    Implementa estratégia configurável para evitar acúmulo de buffer e atraso
    quando o processamento for mais lento que a transmissão ao vivo.
    """

    def __init__(self, url: str, descartar_buffer_acumulado: bool = True):
        self.url = url
        self.descartar_buffer_acumulado = descartar_buffer_acumulado
        self._cap: cv2.VideoCapture | None = None

    def abrir(self) -> None:
        cap = cv2.VideoCapture(self.url)
        if not cap.isOpened():
            cap.release()
            raise ErroFonteVideo(f"Falha ao conectar no stream de rede RTSP: {self.url}")
        if self.descartar_buffer_acumulado:
            # Reduz buffer interno do OpenCV para 1 quadro (evita lag cumulativo)
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        ok, quadro = cap.read()
        if not ok or quadro is None:
            cap.release()
            raise ErroFonteVideo(f"Stream RTSP conectado, mas nenhum quadro foi recebido: {self.url}")
        self._cap = cap

    def ler_quadro(self) -> np.ndarray | None:
        if self._cap is None:
            raise ErroFonteVideo("Stream RTSP não foi aberto.")
        if self.descartar_buffer_acumulado:
            # Em transmissão ao vivo, lê o quadro mais recente descartando buffer antigo
            self._cap.grab()
        ok, quadro = self._cap.read()
        return quadro if ok else None

    def fechar(self) -> None:
        if self._cap is not None:
            self._cap.release()
            self._cap = None

    @property
    def fps(self) -> float:
        return float(self._cap.get(cv2.CAP_PROP_FPS)) if self._cap else 30.0

    @property
    def eh_transmissao_ao_vivo(self) -> bool:
        return True

    @property
    def descricao(self) -> str:
        return f"Stream RTSP ({self.url})"
