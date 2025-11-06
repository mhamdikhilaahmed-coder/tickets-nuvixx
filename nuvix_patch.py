# nuvix_patch.py
# ✅ Solución definitiva para el error de audioop en Render (Python 3.12+)
# Simula el módulo audioop para que discord.py no falle al importarlo.

import sys, types

if "audioop" not in sys.modules:
    dummy = types.SimpleNamespace(
        add=lambda *a, **kw: None,
        mul=lambda *a, **kw: None,
        bias=lambda *a, **kw: None,
        avg=lambda *a, **kw: 0,
        max=lambda *a, **kw: 0,
        minmax=lambda *a, **kw: (0, 0),
        rms=lambda *a, **kw: 0,
        cross=lambda *a, **kw: 0,
        reverse=lambda *a, **kw: b"",
        tostereo=lambda *a, **kw: b"",
        tomono=lambda *a, **kw: b"",
    )
    sys.modules["audioop"] = dummy
