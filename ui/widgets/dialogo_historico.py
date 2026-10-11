"""Diálogo para consulta do histórico de sessões e exportação de relatórios."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QDialog, QFileDialog, QHBoxLayout, QHeaderView,
                               QLabel, QMessageBox, QPushButton, QTableWidget,
                               QTableWidgetItem, QVBoxLayout)

from database.db_manager import DatabaseManager


class DialogoHistorico(QDialog):
    def __init__(self, db: DatabaseManager, parent=None):
        super().__init__(parent)
        self.db = db
        self.setWindowTitle("Histórico de Sessões — BovinoVision AI")
        self.resize(1000, 520)
        self._montar()
        self._carregar_dados()

    def _montar(self):
        lay = QVBoxLayout(self)

        topo = QHBoxLayout()
        tit = QLabel("Sessões Anteriores e Relatórios")
        tit.setStyleSheet("font-size: 16px; font-weight: bold; color: #6BBF59;")
        topo.addWidget(tit)
        topo.addStretch()

        self.btn_exportar = QPushButton("Exportar CSV")
        self.btn_exportar.setObjectName("primario")
        self.btn_exportar.clicked.connect(self._exportar_csv)
        topo.addWidget(self.btn_exportar)

        lay.addLayout(topo)

        self.tabela = QTableWidget()
        colunas = [
            "ID", "Data/Hora", "Fonte do Vídeo", "Regra", "Contados",
            "Entradas", "Saídas", "Estimativa", "Duração (s)", "FPS", "Avisos"
        ]
        self.tabela.setColumnCount(len(colunas))
        self.tabela.setHorizontalHeaderLabels(colunas)
        self.tabela.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.tabela.horizontalHeader().setStretchLastSection(True)
        self.tabela.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tabela.setSelectionBehavior(QTableWidget.SelectRows)
        lay.addWidget(self.tabela)

        botoes = QHBoxLayout()
        botoes.addStretch()
        btn_fechar = QPushButton("Fechar")
        btn_fechar.clicked.connect(self.accept)
        botoes.addWidget(btn_fechar)
        lay.addLayout(botoes)

    def _carregar_dados(self):
        sessoes = self.db.listar_sessoes(limite=500)
        self.tabela.setRowCount(len(sessoes))
        for row, s in enumerate(sessoes):
            self.tabela.setItem(row, 0, QTableWidgetItem(str(s.id)))
            self.tabela.setItem(row, 1, QTableWidgetItem(s.data_hora))
            self.tabela.setItem(row, 2, QTableWidgetItem(s.fonte_video))
            self.tabela.setItem(row, 3, QTableWidgetItem(s.estrategia))
            self.tabela.setItem(row, 4, QTableWidgetItem(str(s.contados_regra)))
            self.tabela.setItem(row, 5, QTableWidgetItem(str(s.entradas)))
            self.tabela.setItem(row, 6, QTableWidgetItem(str(s.saidas)))
            self.tabela.setItem(row, 7, QTableWidgetItem(s.estimativa_texto))
            self.tabela.setItem(row, 8, QTableWidgetItem(f"{s.duracao_segundos:.1f}"))
            self.tabela.setItem(row, 9, QTableWidgetItem(f"{s.fps_medio:.1f}"))
            self.tabela.setItem(row, 10, QTableWidgetItem(s.avisos_json))

    def _exportar_csv(self):
        caminho, _ = QFileDialog.getSaveFileName(
            self, "Salvar Relatório CSV", "relatorio_sessoes.csv", "Arquivos CSV (*.csv)"
        )
        if caminho:
            try:
                qtd = self.db.exportar_csv(caminho)
                QMessageBox.information(
                    self, "Exportação Concluída",
                    f"{qtd} sessão(ões) exportada(s) com sucesso para:\n{caminho}"
                )
            except Exception as e:
                QMessageBox.critical(self, "Erro na Exportação", f"Falha ao salvar CSV: {e}")
