import os
import shutil
import sys
from pathlib import Path

# Encerra qualquer processo anterior do BovinoVision para liberar arquivos bloqueados
if sys.platform == "win32":
    os.system("taskkill /f /im BovinoVision.exe >nul 2>&1")

import PyInstaller.__main__

print("Iniciando empacotamento do BovinoVision AI em executavel .exe...")

args = [
    "main.py",
    "--name=BovinoVision",
    "--onedir",
    "--windowed",
    "--collect-data=ultralytics",
    "--collect-submodules=ultralytics",
    "--collect-data=torchvision",
    "--collect-binaries=torchvision",
    "--hidden-import=PySide6",
    "--hidden-import=cv2",
    "--hidden-import=torch",
    "--hidden-import=torchvision",
    "--noconfirm",
]

PyInstaller.__main__.run(args)

dist_dir = Path("dist/BovinoVision")
if dist_dir.exists():
    print("Garantindo arquivos de suporte e C++ do torchvision...")
    try:
        import torchvision
        tv_dir = Path(torchvision.__file__).parent
        target_tv = dist_dir / "_internal" / "torchvision"
        target_tv.mkdir(parents=True, exist_ok=True)
        for pattern in ("*.pyd", "*.dll"):
            for f in tv_dir.glob(pattern):
                shutil.copy2(f, target_tv / f.name)
                # Copia também para _internal diretamente por segurança de carregamento do Windows
                shutil.copy2(f, dist_dir / "_internal" / f.name)
        print("Binários do torchvision sincronizados com sucesso!")
    except Exception as e:
        print(f"Aviso ao sincronizar torchvision: {e}")

    print("Copiando pastas de modelos e dados para o pacote executavel...")
    (dist_dir / "models").mkdir(exist_ok=True)
    for modelo in Path("models").glob("*.pt"):
        dest = dist_dir / "models" / modelo.name
        if not dest.exists():
            print(f"Copiando modelo {modelo.name}...")
            shutil.copy2(modelo, dest)

    (dist_dir / "data" / "videos").mkdir(parents=True, exist_ok=True)
    (dist_dir / "data" / "sessions").mkdir(parents=True, exist_ok=True)
    print("PACOTE EXECUTAVEL CONCLUIDO COM SUCESSO EM dist/BovinoVision/")
