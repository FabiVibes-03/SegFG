"""
Arranca el servidor TabletMonitor.
Usar este script en lugar de llamar uvicorn directamente.

Uso:
    python run.py
"""
import sys
import os

# Agregar la carpeta del backend al path de Python
# Esto resuelve todos los imports entre módulos
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        reload_dirs=[os.path.dirname(os.path.abspath(__file__))],
    )