"""Gerenciador de banco de dados SQLite para sessões do BovinoVision AI.

Armazena histórico de sessões de processamento e permite exportar relatórios em CSV.
"""
import csv
import json
import sqlite3
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

from config.settings import RAIZ_PROJETO

CAMINHO_DB_PADRAO = RAIZ_PROJETO / "data" / "sessions" / "historico_sessoes.db"


@dataclass
class RegistroSessao:
    id: int | None = None
    data_hora: str = ""
    fonte_video: str = ""
    modelo: str = ""
    estrategia: str = ""
    confianca_minima: float = 0.35
    dispositivo: str = "cpu"
    duracao_segundos: float = 0.0
    quadros_processados: int = 0
    fps_medio: float = 0.0
    ids_unicos: int = 0
    contados_regra: int = 0
    entradas: int = 0
    saidas: int = 0
    pico_simultaneo: int = 0
    estimativa_texto: str = ""
    avisos_json: str = "[]"


class DatabaseManager:
    def __init__(self, caminho_db: Path | str | None = None):
        self.caminho_db = Path(caminho_db or CAMINHO_DB_PADRAO)
        self.caminho_db.parent.mkdir(parents=True, exist_ok=True)
        self._inicializar_banco()

    def _conectar(self) -> sqlite3.Connection:
        return sqlite3.connect(str(self.caminho_db))

    def _inicializar_banco(self):
        with self._conectar() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sessoes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    data_hora TEXT NOT NULL,
                    fonte_video TEXT NOT NULL,
                    modelo TEXT,
                    estrategia TEXT,
                    confianca_minima REAL,
                    dispositivo TEXT,
                    duracao_segundos REAL,
                    quadros_processados INTEGER,
                    fps_medio REAL,
                    ids_unicos INTEGER,
                    contados_regra INTEGER,
                    entradas INTEGER,
                    saidas INTEGER,
                    pico_simultaneo INTEGER,
                    estimativa_texto TEXT,
                    avisos_json TEXT
                )
            """)
            conn.commit()

    def salvar_sessao(self, sessao: RegistroSessao) -> int:
        if not sessao.data_hora:
            sessao.data_hora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with self._conectar() as conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO sessoes (
                    data_hora, fonte_video, modelo, estrategia, confianca_minima,
                    dispositivo, duracao_segundos, quadros_processados, fps_medio,
                    ids_unicos, contados_regra, entradas, saidas, pico_simultaneo,
                    estimativa_texto, avisos_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                sessao.data_hora, sessao.fonte_video, sessao.modelo, sessao.estrategia,
                sessao.confianca_minima, sessao.dispositivo, sessao.duracao_segundos,
                sessao.quadros_processados, sessao.fps_medio, sessao.ids_unicos,
                sessao.contados_regra, sessao.entradas, sessao.saidas,
                sessao.pico_simultaneo, sessao.estimativa_texto, sessao.avisos_json
            ))
            conn.commit()
            return cur.lastrowid

    def listar_sessoes(self, limite: int = 100) -> list[RegistroSessao]:
        with self._conectar() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT id, data_hora, fonte_video, modelo, estrategia, confianca_minima,
                       dispositivo, duracao_segundos, quadros_processados, fps_medio,
                       ids_unicos, contados_regra, entradas, saidas, pico_simultaneo,
                       estimativa_texto, avisos_json
                FROM sessoes
                ORDER BY id DESC
                LIMIT ?
            """, (limite,))
            linhas = cur.fetchall()
            return [
                RegistroSessao(
                    id=l[0], data_hora=l[1], fonte_video=l[2], modelo=l[3], estrategia=l[4],
                    confianca_minima=l[5], dispositivo=l[6], duracao_segundos=l[7],
                    quadros_processados=l[8], fps_medio=l[9], ids_unicos=l[10],
                    contados_regra=l[11], entradas=l[12], saidas=l[13], pico_simultaneo=l[14],
                    estimativa_texto=l[15], avisos_json=l[16]
                ) for l in linhas
            ]

    def exportar_csv(self, caminho_csv: Path | str) -> int:
        sessoes = self.listar_sessoes(limite=10000)
        caminho = Path(caminho_csv)
        caminho.parent.mkdir(parents=True, exist_ok=True)
        campos = [
            "id", "data_hora", "fonte_video", "modelo", "estrategia", "confianca_minima",
            "dispositivo", "duracao_segundos", "quadros_processados", "fps_medio",
            "ids_unicos", "contados_regra", "entradas", "saidas", "pico_simultaneo",
            "estimativa_texto", "avisos"
        ]
        with open(caminho, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f, delimiter=";")
            writer.writerow(campos)
            for s in sessoes:
                try:
                    avisos_lista = json.loads(s.avisos_json)
                    avisos_str = " | ".join(avisos_lista)
                except Exception:
                    avisos_str = s.avisos_json
                writer.writerow([
                    s.id, s.data_hora, s.fonte_video, s.modelo, s.estrategia, s.confianca_minima,
                    s.dispositivo, f"{s.duracao_segundos:.1f}", s.quadros_processados, f"{s.fps_medio:.1f}",
                    s.ids_unicos, s.contados_regra, s.entradas, s.saidas, s.pico_simultaneo,
                    s.estimativa_texto, avisos_str
                ])
        return len(sessoes)
