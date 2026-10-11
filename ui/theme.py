"""Tema escuro com identidade agrícola (verde pasto / dourado trigo)."""

VERDE = "#6BBF59"
OURO = "#E3B341"
FUNDO = "#0F1A14"
PAINEL = "#16261D"
BORDA = "#27402F"
TEXTO = "#E6EFE8"
TEXTO_SUAVE = "#8FA89A"
ERRO = "#E5534B"

QSS = f"""
QMainWindow, QWidget {{ background: {FUNDO}; color: {TEXTO}; font-family: 'Segoe UI'; font-size: 13px; }}
QFrame#cartao {{ background: {PAINEL}; border: 1px solid {BORDA}; border-radius: 10px; }}
QLabel#cartaoTitulo {{ color: {TEXTO_SUAVE}; font-size: 11px; }}
QLabel#cartaoValor {{ color: {VERDE}; font-size: 24px; font-weight: 700; }}
QLabel#logo {{ font-size: 22px; font-weight: 800; color: {TEXTO}; }}
QLabel#logoAcento {{ font-size: 22px; font-weight: 800; color: {VERDE}; }}
QLabel#sub {{ color: {TEXTO_SUAVE}; }}
QLabel#selo {{ background: {PAINEL}; border: 1px solid {BORDA}; border-radius: 10px; padding: 3px 10px; color: {OURO}; }}
QPushButton {{ background: {PAINEL}; border: 1px solid {BORDA}; border-radius: 8px; padding: 9px 16px; }}
QPushButton:hover {{ border-color: {VERDE}; }}
QPushButton:disabled {{ color: #4d6356; border-color: #1d3024; }}
QPushButton#primario {{ background: {VERDE}; color: #0B140F; font-weight: 700; border: none; }}
QPushButton#primario:disabled {{ background: #2c4a30; color: #5f7a66; }}
QPushButton#perigo:hover {{ border-color: {ERRO}; color: {ERRO}; }}
QLabel#video {{ background: #08100B; border: 1px solid {BORDA}; border-radius: 10px; color: {TEXTO_SUAVE}; }}
QPlainTextEdit {{ background: {PAINEL}; border: 1px solid {BORDA}; border-radius: 8px; color: {TEXTO}; }}
QProgressBar {{ background: {PAINEL}; border: 1px solid {BORDA}; border-radius: 5px; height: 8px; text-align: center; }}
QProgressBar::chunk {{ background: {VERDE}; border-radius: 4px; }}
QSlider::groove:horizontal {{ background: {BORDA}; height: 4px; border-radius: 2px; }}
QSlider::handle:horizontal {{ background: {VERDE}; width: 14px; margin: -6px 0; border-radius: 7px; }}
QSlider#timeline::groove:horizontal {{ background: #203527; height: 6px; border-radius: 3px; }}
QSlider#timeline::sub-page:horizontal {{ background: {VERDE}; border-radius: 3px; }}
QSlider#timeline::handle:horizontal {{ background: {OURO}; width: 16px; margin: -5px 0; border-radius: 8px; }}
QLabel#tempoVideo {{ color: {OURO}; font-weight: 600; font-size: 12px; }}
"""
