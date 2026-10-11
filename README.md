# 🐄 BovinoVision AI — Contagem Inteligente de Gado com Drones

[![Python 3.12](https://img.shields.io/badge/Python-3.12-blue.svg)](https://www.python.org/)
[![PySide6](https://img.shields.io/badge/GUI-PySide6%20(Qt6)-green.svg)](https://doc.qt.io/qtforpython/)
[![YOLOv8](https://img.shields.io/badge/AI-Ultralytics%20YOLO-red.svg)](https://github.com/ultralytics/ultralytics)
[![PyTorch](https://img.shields.io/badge/PyTorch-CUDA%20%7C%20CPU-orange.svg)](https://pytorch.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Aplicação desktop profissional de visão computacional voltada para o agronegócio. Permite **detecção**, **rastreamento persistente (sem repetição de contagem)** e **auditoria de rebanhos bovinos** em filmagens aéreas de drones ou transmissões ao vivo.

---

## 📸 Demonstração e Interface

* **Controle de Reprodução:** Reproduzir, pausar e pular para qualquer segundo do vídeo arrastando a barra de progresso.
* **Linha Virtual Interativa:** Desenhe uma linha com o mouse sobre porteiras, bretes ou corredores. O sistema contabiliza automaticamente as **Entradas**, **Saídas** e o **Saldo**.
* **Zero Repetição:** Algoritmo **BoT-SORT** com compensação do movimento do drone (GMC) para não contar o mesmo animal duas vezes quando a câmera se move.
* **Histórico em SQLite:** Cada sessão é gravada em banco de dados local com resumo e exportação para planilhas `.csv`.

---

## 🚀 Como Executar

Escolha a forma mais conveniente para o seu ambiente:

### 1️⃣ Modo Executável Portátil (`.exe`) — *Recomendado para usuários finais*
Não necessita de Python, terminal nem instalação de dependências.

1. Baixe ou descompacte a pasta **`BovinoVision`** (gerada na pasta `dist/`).
2. Dê **dois cliques** em:
   ```text
   BovinoVision.exe
   ```
3. O aplicativo abrirá imediatamente com aceleração automática (GPU NVIDIA se disponível, ou CPU).

---

### 2️⃣ Modo 1-Clique via Scripts `.bat` (Windows)
Ideal para computadores com Python instalado, sem precisar abrir o terminal.

1. Instale o [Python 3.11 ou 3.12](https://www.python.org/downloads/) marcando a opção **"Add python.exe to PATH"**.
2. Dê dois cliques em **`INSTALAR_DEPENDENCIAS.bat`**  
   *(Detecta sua placa de vídeo, instala PyTorch com suporte a GPU/CPU e baixa o modelo aéreo treinado automaticamente)*.
3. Dê dois cliques em **`INICIAR_APP.bat`** para abrir o sistema.

---

### 3️⃣ Modo Desenvolvedor (Terminal / Git)

```powershell
# 1. Clonar o repositório
git clone https://github.com/jpasx/bovinovision.git
cd bovinovision

# 2. Criar e ativar o ambiente virtual
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 3. Instalar as dependências
pip install -r requirements.txt

# 4. Iniciar a aplicação
python main.py

# 5. Executar a suíte de testes (44 testes automatizados)
pytest tests -v
```

---

## 🕹️ Guia Rápido de Uso

1. **Escolha a Fonte de Vídeo:**
   * **Arquivo de Vídeo:** Selecione vídeos gravados pelo drone (`.mp4`, `.mov`, `.avi`).
   * **Câmera / Placa de Captura:** Para sinal HDMI do rádio controle do drone via USB.
   * **Transmissão RTSP:** Para transmissão via rede em tempo real.
2. **Defina a Linha de Contagem:**
   * Clique no botão **✏️ Marcar Linha no Vídeo**.
   * Clique e arraste com o mouse sobre o vídeo no ponto de passagem (ex: porteira).
   * Uma seta indicará o sentido de fluxo considerado entrada.
3. **Inicie o Processamento:**
   * Clique em **Iniciar**.
   * Você pode navegar no vídeo livremente pela barra inferior ou pausar a qualquer momento.
4. **Relatórios e Histórico:**
   * Ao finalizar, clique em **📋 Histórico e Relatórios** para visualizar os números consolidados ou exportar uma planilha CSV.

---

## 🧠 Arquitetura e Modelos de IA

| Modelo | Arquivo | Finalidade |
| :--- | :--- | :--- |
| **Drone Aéreo (Recomendado)** | `models/bovinos_aereo.pt` | Otimizado para bovinos vistos de cima por drones, tolerante a sombras e pequenos animais. |
| **Bovinos Solo** | `models/bovinos.pt` | Modelo padrão para filmagens laterais ou solo. |

> 💡 Se o arquivo `models/bovinos_aereo.pt` não estiver presente, execute `INSTALAR_DEPENDENCIAS.bat` para fazer o download automático diretamente do repositório oficial.

---

## 📁 Estrutura do Projeto

```text
├── config/             # Configurações globais e resolução de caminhos portáteis
├── data/               # Pastas de dados locais (vídeos, histórico, banco SQLite)
├── database/           # Gerenciador de persistência SQLite
├── models/             # Pesos dos modelos de IA (.pt)
├── services/           # Lógica do pipeline (detector YOLO, tracker BoT-SORT, contador)
│   ├── detector.py     # Inferência com tiling e fallback robusto via OpenCV
│   ├── tracker.py      # Rastreamento persistente de IDs com GMC
│   ├── counter.py      # Cálculo vetorial de passagem por linha
│   └── pipeline.py     # Orquestrador de processamento em tempo real
├── ui/                 # Interface gráfica moderna em PySide6 (Qt)
│   ├── main_window.py  # Janela principal com controles e barra de progresso
│   ├── video_widget.py # Renderizador de vídeo com desenho interativo de linhas
│   └── history_dialog.py # Painel de relatórios e exportação CSV
├── tests/              # Suíte completa de testes automatizados com Pytest
├── build_exe.py        # Script para compilar o executável portátil (.exe)
├── INICIAR_APP.bat     # Inicializador rápido com 1 clique
└── INSTALAR_DEPENDENCIAS.bat # Instalador inteligente de dependências
```

---

## 🧪 Suíte de Testes Automatizados

O projeto conta com mais de 40 testes unitários e de integração cobrindo detecção, rastreamento, contagem direcional, persistência em banco de dados e pipeline:

```powershell
pytest tests -v
```

---

## 📄 Licença

Distribuído sob a licença MIT. Consulte `LICENSE` para mais informações.
