"""
Dependencias compartidas: extracción del usuario actual desde el JWT.
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from database import get_db
from app.core.security import decode_access_token
from app.models.models import Usuario, Estados

security_scheme = HTTPBearer()

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme),
    db: Session = Depends(get_db),
) -> Usuario:
    """Extrae y valida el usuario actual a partir del token Bearer."""
    payload = decode_access_token(credentials.credentials)
    if payload is None:
        raise HTTPException(status_code=401, detail="Token inválido o expirado")

    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(status_code=401, detail="Token sin subject")

    user = db.query(Usuario).filter(Usuario.id == int(user_id)).first()
    
    if not user:
        raise HTTPException(status_code=401, detail="Usuario no encontrado")

    # NUEVA LÓGICA DE ESTADOS:
    # Verificamos si tiene un estado y si ese estado es diferente de ACTIVO
    if not user.estado_actual or user.estado_actual.estado != Estados.ACTIVO:
        raise HTTPException(
            status_code=403, 
            detail="Cuenta desactivada o pendiente de aprobación"
        )
        
    return user


def require_role(*roles: str):
    """Genera una dependencia que exige que el usuario tenga uno de los roles dados."""
    def checker(current_user: Usuario = Depends(get_current_user)):
        if current_user.rol not in roles:
            raise HTTPException(
                status_code=403,
                detail=f"Se requiere rol: {', '.join(roles)}"
            )
        return current_user
    return checker