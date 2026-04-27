"""
Configuración global del proyecto MASCATE.
"""

# ── JWT ──
SECRET_KEY = "mascate-secreto-super-seguro-techotiva-2026-cambiame-en-produccion"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 horas

# ── Base de datos ──
DATABASE_URL = "sqlite:///./mascate.db"
