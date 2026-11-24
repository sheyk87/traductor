"""Tkinter bootstrap helper ensuring runtime libraries are loaded seamlessly."""

import os
import ctypes
import sys
from pathlib import Path


def ensure_tkinter():
    """Initializes and pre-loads Tk/Tcl libraries if not already available in system."""
    try:
        import tkinter
        return True
    except (ImportError, ModuleNotFoundError, OSError):
        pass

    # Resolve local virtualenv directories
    project_root = Path(__file__).parent.parent.resolve()
    venv_dir = project_root / ".venv"
    lib_dir = venv_dir / "lib"
    tk_share = venv_dir / "share" / "tcltk" / "tk8.6"

    if tk_share.exists():
        os.environ["TK_LIBRARY"] = str(tk_share)

    libtk = lib_dir / "libtk8.6.so"
    libblt = lib_dir / "libBLT.2.5.so.8.6"

    try:
        if libtk.exists():
            ctypes.CDLL(str(libtk), mode=ctypes.RTLD_GLOBAL)
        if libblt.exists():
            ctypes.CDLL(str(libblt), mode=ctypes.RTLD_GLOBAL)
    except Exception as exc:
        print(f"[Aviso] No se pudieron precargar bibliotecas compartidas de Tk: {exc}", file=sys.stderr)

    import tkinter
    return True
