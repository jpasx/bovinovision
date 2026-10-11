"""Rastreamento persistente de bovinos entre quadros (BoT-SORT do Ultralytics).

O BoT-SORT compensa o movimento da câmera (GMC), adequado a drones. A ReID (aparência)
fica desligada por padrão, pois exige modelo e processamento extras.
Detecção e rastreamento são separados: este módulo recebe `Deteccao`s e devolve as mesmas
detecções com `id_rastreamento`, `estado` e `possivel_perda`.
"""
from dataclasses import replace

import numpy as np

from services.detector import Deteccao


class _Deteccoes:
    """Adaptador mínimo no formato esperado pelo rastreador do Ultralytics."""

    def __init__(self, xyxy: np.ndarray, conf: np.ndarray):
        self.xyxy = xyxy.reshape(-1, 4).astype(np.float32)
        self.conf = conf.astype(np.float32)
        self.cls = np.zeros(len(conf), np.float32)
        x1, y1, x2, y2 = self.xyxy.T if len(conf) else (np.zeros(0),) * 4
        self.xywh = np.stack([(x1 + x2) / 2, (y1 + y2) / 2, x2 - x1, y2 - y1], axis=1).astype(np.float32) \
            if len(conf) else np.zeros((0, 4), np.float32)

    def __len__(self):
        return len(self.conf)

    def __getitem__(self, idx):
        novo = _Deteccoes.__new__(_Deteccoes)
        novo.xyxy, novo.conf, novo.cls, novo.xywh = (a[idx] for a in (self.xyxy, self.conf, self.cls, self.xywh))
        return novo


class RastreadorBovinos:
    def __init__(self, limiar_confianca: float = 0.25, buffer_perda: int = 30,
                 compensar_movimento_camera: bool = True):
        from ultralytics.trackers.bot_sort import BOTSORT
        from ultralytics.utils import IterableSimpleNamespace
        cfg = dict(
            tracker_type="botsort", track_high_thresh=max(limiar_confianca, 0.1),
            track_low_thresh=0.1, new_track_thresh=max(limiar_confianca, 0.1),
            track_buffer=buffer_perda, match_thresh=0.8, fuse_score=True,
            gmc_method="sparseOptFlow" if compensar_movimento_camera else "none",
            proximity_thresh=0.5, appearance_thresh=0.8, with_reid=False, model="auto")
        self._trk = BOTSORT(args=IterableSimpleNamespace(**cfg))
        self._perdidos_anterior: set[int] = set()

    @property
    def ids_perdidos(self) -> int:
        """Trilhas atualmente perdidas (animal sumiu; pode voltar com o mesmo ID)."""
        return len(self._trk.lost_stracks)

    def atualizar(self, deteccoes: list[Deteccao], quadro: np.ndarray | None = None) -> list[Deteccao]:
        if deteccoes:
            xyxy = np.array([[d.x1, d.y1, d.x2, d.y2] for d in deteccoes], np.float32)
            conf = np.array([d.confianca for d in deteccoes], np.float32)
        else:
            xyxy, conf = np.zeros((0, 4), np.float32), np.zeros(0, np.float32)

        if quadro is not None and quadro.shape[1] > 640:
            import cv2
            img_gmc = cv2.resize(quadro, (640, int(640 * quadro.shape[0] / quadro.shape[1])), interpolation=cv2.INTER_AREA)
        else:
            img_gmc = quadro
        saida = self._trk.update(_Deteccoes(xyxy, conf), img=img_gmc)

        comprimentos = {t.track_id: t.tracklet_len for t in self._trk.tracked_stracks}
        resultado = [replace(d, id_rastreamento=None, estado="sem_id", possivel_perda=False)
                     for d in deteccoes]
        for linha in saida:
            idx, tid = int(linha[-1]), int(linha[4])
            reencontrado = tid in self._perdidos_anterior
            estado = "reencontrado" if reencontrado else (
                "confirmado" if comprimentos.get(tid, 0) >= 3 else "novo")
            resultado[idx] = replace(resultado[idx], id_rastreamento=tid, estado=estado,
                                     possivel_perda=reencontrado)
        self._perdidos_anterior = {t.track_id for t in self._trk.lost_stracks}
        return resultado
