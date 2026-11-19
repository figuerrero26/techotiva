"""
Router de administración: estadísticas globales, gestión de usuarios y alertas.
"""

import io
import secrets
import string
from datetime import datetime, timedelta, timezone
from typing import Optional
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel as _BM
from sqlalchemy import case, func
from sqlalchemy.orm import Session
from app.services.email_service import (
    enviar_correo_bienvenida_dispositivo, enviar_correo_recuperacion, generar_token,
    notificar_aprobacion,
)
from app.core.config import settings

from database import get_db
from app.core.security import hash_password
from app.models.models import (
    Usuario, Estados, EstadoRegistro, Dispositivo, Prescriptor, Beneficiario,
    Actividad, Seguimiento, PrimerContacto, Inscripcion,
)
from app.schemas.schemas import (
    AdminStats, UsuarioAdmin, CambiarEstado, AlertaOut,
    AdminDispositivoOut, AdminDispositivoCreate, CambiarRolRequest,
    BeneficiarioResumen,
)
from app.routers._deps import require_role
from app.services.estado_service import EstadoService
from app.services.usuarios_service import borrar_usuario_completo

router = APIRouter(prefix="/admin", tags=["Administración"])
admin_only = require_role("admin")


# ─── Helper interno ──────────────────────────────────────────────────────────
def _build_usuario_admin(u: Usuario) -> UsuarioAdmin:
    """Construye UsuarioAdmin resolviendo el nombre y campos de perfil según el rol."""
    nombre = u.email
    fecha_nacimiento = None
    localidad = None
    telefono = None
    descripcion = None
    genero = None
    prescriptor_nombre = None
    dispositivo_nombre = None
    prescriptor_id_val = None
    dispositivo_id_val = None
    beneficiario_id_val = None

    if u.rol == "dispositivo" and u.dispositivo:
        nombre = u.dispositivo.nombre
        telefono = u.dispositivo.telefono
        descripcion = u.dispositivo.descripcion
        dispositivo_id_val = u.dispositivo.id
        dispositivo_nombre = u.dispositivo.nombre
    elif u.rol == "prescriptor" and u.prescriptor:
        nombre = u.prescriptor.nombre_completo
        telefono = u.prescriptor.telefono
        prescriptor_id_val = u.prescriptor.id
        descripcion = u.prescriptor.perfil_disciplina
        if u.prescriptor.dispositivo_id and u.prescriptor.dispositivo:
            dispositivo_nombre = u.prescriptor.dispositivo.nombre
    elif u.rol == "beneficiario" and u.beneficiario:
        nombre = u.beneficiario.nombre_apodo
        fecha_nacimiento = u.beneficiario.fecha_nacimiento
        localidad = u.beneficiario.localidad
        telefono = u.beneficiario.telefono
        descripcion = u.beneficiario.descripcion
        genero = u.beneficiario.genero
        beneficiario_id_val = u.beneficiario.id
        if u.beneficiario.prescriptor_id and u.beneficiario.prescriptor:
            prescriptor_nombre = u.beneficiario.prescriptor.nombre_completo
        if u.beneficiario.dispositivo_id and u.beneficiario.dispositivo:
            dispositivo_nombre = u.beneficiario.dispositivo.nombre
            dispositivo_id_val = u.beneficiario.dispositivo_id
    elif u.rol == "admin":
        nombre = "Admin"

    proceso_finalizado = (
        u.beneficiario is not None and u.beneficiario.estado == Estados.FINALIZADO
    )

    return UsuarioAdmin(
        id=u.id,
        email=u.email,
        rol=u.rol,
        status=u.estado,
        fecha_registro=u.fecha_registro,
        nombre=nombre,
        fecha_nacimiento=fecha_nacimiento,
        localidad=localidad,
        telefono=telefono,
        descripcion=descripcion,
        genero=genero,
        prescriptor_nombre=prescriptor_nombre,
        dispositivo_nombre=dispositivo_nombre,
        prescriptor_id=prescriptor_id_val,
        dispositivo_id=dispositivo_id_val,
        beneficiario_id=beneficiario_id_val,
        perfil_disciplina=u.prescriptor.perfil_disciplina if u.rol == "prescriptor" and u.prescriptor else None,
        politica_privacidad_at=u.politica_privacidad_at,
        proceso_finalizado=proceso_finalizado,
    )


# ────────────────────────── INDICADORES (panel central) ──────────────────────────
# Valores de "situaciones_presentes" agrupados como en la Hoja de Primer Contacto
_SPA = {
    "Uso de sustancias psicoactivas legales":  "SPA legales",
    "Uso de sustancias psicoactivas ilegales": "SPA ilegales",
    "Uso de sustancias vía intravenosa":       "Vía intravenosa",
}
_CATEGORIAS = {
    "Bienestar emocional y salud": {
        "Crisis psicológica", "Condición psiquiátrica", "Enfermedades", "Discapacidad", "VIH",
        "Embarazo / parto", "Ansiedad / Depresión", "Depresión",
        "Trastorno de estrés postraumático", "Proceso de tratamiento interno",
    },
    "Problemas sociales": {
        "Violencia intrafamiliar", "Violencia comunitaria", "Problemas de convivencia en el entorno",
        "Habita la calle de forma permanente", "Discriminación", "Barrismo social",
        "Problemas con la justicia", "Malos resultados o deserción escolar", "Analfabetismo",
        "Falta de capacitación", "Víctima del conflicto", "Desplazamiento forzado", "Población migrante",
    },
    "Problemas económicos": {
        "Sin empleo u ocupación", "Dificultades económicas", "Pobreza extrema", "Hambre",
        "Escasez de alimentos", "Estrés laboral", "Trabajo sexual",
    },
}
_EMOCIONES = ["Alegría", "Confianza", "Anticipación", "Sorpresa", "Miedo", "Tristeza", "Disgusto", "Ira"]
# Niveles de intensidad de cada emoción (leve → intensa), como en la HPC de malspa
_EMO_NIVELES = {
    "Alegría":      ["Serenidad", "Alegría", "Éxtasis"],
    "Confianza":    ["Aceptación", "Confianza", "Admiración"],
    "Anticipación": ["Interés", "Anticipación", "Vigilancia"],
    "Sorpresa":     ["Distracción", "Sorpresa", "Asombro"],
    "Miedo":        ["Aprensión", "Miedo", "Terror"],
    "Tristeza":     ["Pensativo", "Tristeza", "Pena"],
    "Disgusto":     ["Aburrimiento", "Disgusto", "Aversión"],
    "Ira":          ["Molestia", "Ira", "Furia"],
}
_EMO_POSITIVAS = {"Alegría", "Confianza", "Anticipación"}
_EMO_NEGATIVAS = {"Miedo", "Tristeza", "Disgusto", "Ira"}


def _split(valor):
    return [v.strip() for v in (valor or "").split(" | ") if v.strip()]


def _en_proceso_activo(b: Beneficiario) -> bool:
    """Para priorizar: cuenta activa y proceso sin cerrar."""
    return (b.estado != Estados.FINALIZADO
            and b.usuario is not None and b.usuario.estado == Estados.ACTIVO)


def _benefs_y_ultimo_pc(db: Session, dispositivo_id: Optional[int]):
    """Beneficiarios (filtrados por DBC si se indica) y el último primer contacto de cada uno."""
    q = db.query(Beneficiario)
    if dispositivo_id:
        q = q.filter(Beneficiario.dispositivo_id == dispositivo_id)
    benefs = q.all()
    benef_ids = [b.id for b in benefs]

    ultimo_pc = {}
    if benef_ids:
        pcs = (
            db.query(PrimerContacto)
            .filter(PrimerContacto.beneficiario_id.in_(benef_ids))
            .order_by(PrimerContacto.fecha_contacto, PrimerContacto.id)
            .all()
        )
        for pc in pcs:
            ultimo_pc[pc.beneficiario_id] = pc
    return benefs, ultimo_pc


@router.get("/indicadores/spa")
def admin_indicadores_spa(
    dispositivo_id: Optional[int] = Query(None),
    tipo: Optional[str] = Query(None, description="SPA legales | SPA ilegales | Vía intravenosa"),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(admin_only),
):
    """Personas en proceso activo que, en su último primer contacto, marcaron consumo de SPA."""
    benefs, ultimo_pc = _benefs_y_ultimo_pc(db, dispositivo_id)
    por_id = {b.id: b for b in benefs}
    resultado = []
    for bid, pc in ultimo_pc.items():
        b = por_id[bid]
        if not _en_proceso_activo(b):
            continue
        tipos = [_SPA[s] for s in _split(pc.situaciones_presentes) if s in _SPA]
        if not tipos or (tipo and tipo not in tipos):
            continue
        resultado.append({
            "beneficiario_id": b.id,
            "nombre": b.nombre_apodo,
            "dispositivo": b.dispositivo.nombre if b.dispositivo else "Sin DBC",
            "tipos": tipos,
            "fecha_contacto": pc.fecha_contacto.isoformat() if pc.fecha_contacto else None,
        })
    resultado.sort(key=lambda r: (r["nombre"] or "").lower())
    return resultado


@router.get("/indicadores")
def admin_indicadores(
    dispositivo_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(admin_only),
):
    disps = db.query(Dispositivo).order_by(Dispositivo.nombre).all()
    benefs, ultimo_pc = _benefs_y_ultimo_pc(db, dispositivo_id)

    spa_total = 0
    spa_tipos = {v: 0 for v in _SPA.values()}
    categorias = {c: 0 for c in _CATEGORIAS}
    emociones = {e: 0 for e in _EMOCIONES}
    niveles = {e: {n: 0 for n in _EMO_NIVELES[e]} for e in _EMOCIONES}
    personas_con_emociones = 0
    poblaciones = {}

    activos = {b.id for b in benefs if _en_proceso_activo(b)}
    spa_base = 0   # personas activas con primer contacto (base del porcentaje de SPA)
    for pc in ultimo_pc.values():
        sits = set(_split(pc.situaciones_presentes))
        # SPA cuenta solo a quienes siguen en proceso, para priorizar la atención
        if pc.beneficiario_id in activos:
            spa_base += 1
            tipos = [_SPA[s] for s in sits if s in _SPA]
            if tipos:
                spa_total += 1
                for t in tipos:
                    spa_tipos[t] += 1
        for cat, valores in _CATEGORIAS.items():
            if sits & valores:
                categorias[cat] += 1
        # Formato "Emoción - Nivel" (o solo "Emoción" en registros anteriores)
        emos = []
        for v in _split(pc.emociones):
            base, _, nivel = v.partition(" - ")
            if base in emociones:
                emos.append((base, nivel or base))
        if emos:
            personas_con_emociones += 1
            for base, nivel in emos:
                emociones[base] += 1
                if nivel in niveles[base]:
                    niveles[base][nivel] += 1
        for p in _split(pc.poblaciones_especiales):
            poblaciones[p] = poblaciones.get(p, 0) + 1

    genero = {}
    edades = {"0-17": 0, "18-28": 0, "29-59": 0, "60+": 0, "Sin dato": 0}
    hoy = datetime.now(timezone.utc).date()
    for b in benefs:
        g = b.genero or "Sin dato"
        genero[g] = genero.get(g, 0) + 1
        edad = None
        if b.fecha_nacimiento:
            fn = b.fecha_nacimiento
            edad = hoy.year - fn.year - ((hoy.month, hoy.day) < (fn.month, fn.day))
        elif b.id in ultimo_pc and ultimo_pc[b.id].edad_benef is not None:
            edad = ultimo_pc[b.id].edad_benef
        if edad is None:
            edades["Sin dato"] += 1
        elif edad < 18:
            edades["0-17"] += 1
        elif edad <= 28:
            edades["18-28"] += 1
        elif edad < 60:
            edades["29-59"] += 1
        else:
            edades["60+"] += 1

    # Cobertura: beneficiarios por DBC (siempre de todos, para comparar)
    conteo_disp = dict(
        db.query(Beneficiario.dispositivo_id, func.count(Beneficiario.id))
        .group_by(Beneficiario.dispositivo_id).all()
    )
    cobertura = [
        {"id": d.id, "nombre": d.nombre, "beneficiarios": conteo_disp.get(d.id, 0)}
        for d in disps
    ]
    cobertura.sort(key=lambda x: -x["beneficiarios"])
    if conteo_disp.get(None):
        cobertura.append({"id": None, "nombre": "Sin DBC", "beneficiarios": conteo_disp[None]})

    positivas = sum(emociones[e] for e in _EMO_POSITIVAS)
    negativas = sum(emociones[e] for e in _EMO_NEGATIVAS)

    return {
        "dispositivos": [{"id": d.id, "nombre": d.nombre} for d in disps],
        "total_beneficiarios": len(benefs),
        "con_primer_contacto": len(ultimo_pc),
        "spa": {"total": spa_total, "tipos": spa_tipos, "base": spa_base},
        "cobertura": cobertura,
        "genero": genero,
        "edades": edades,
        "poblaciones": poblaciones,
        "categorias": categorias,
        "emociones": {
            "conteo": emociones,
            "niveles": niveles,
            "personas": personas_con_emociones,
            "positivas": positivas,
            "negativas": negativas,
            "neutras": emociones["Sorpresa"],
        },
    }


# ────────────────────────── SESIONES ACTIVAS ──────────────────────────
@router.get("/sesiones-activas")
def sesiones_activas(
    minutos: int = Query(5, ge=1, le=120),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(admin_only),
):
    """Usuarios con actividad en los últimos `minutos` minutos."""
    ahora = datetime.utcnow()
    usuarios = (
        db.query(Usuario)
        .filter(Usuario.ultima_actividad >= ahora - timedelta(minutes=minutos))
        .order_by(Usuario.ultima_actividad.desc())
        .all()
    )
    resultado = []
    for u in usuarios:
        if u.rol == "dispositivo" and u.dispositivo:
            nombre = u.dispositivo.nombre
        elif u.rol == "prescriptor" and u.prescriptor:
            nombre = u.prescriptor.nombre_completo
        elif u.rol == "beneficiario" and u.beneficiario:
            nombre = u.beneficiario.nombre_apodo
        elif u.rol == "admin":
            nombre = "Administrador"
        else:
            nombre = u.email
        resultado.append({
            "id": u.id,
            "nombre": nombre,
            "email": u.email,
            "rol": u.rol,
            "hace_segundos": int((ahora - u.ultima_actividad).total_seconds()),
        })
    return resultado


# ────────────────────────── STATS GLOBALES ──────────────────────────
@router.get("/stats", response_model=AdminStats)
def admin_stats(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(admin_only),
):
    total_disp = (
        db.query(Dispositivo)
        .join(Usuario, Usuario.id == Dispositivo.usuario_id)
        .join(Usuario.estado_actual)
        .filter(EstadoRegistro.estado == Estados.ACTIVO)
        .count()
    )
    total_users = db.query(Usuario).filter(Usuario.rol != "admin").count()
    total_presc = (
        db.query(Prescriptor)
        .join(Usuario, Usuario.id == Prescriptor.usuario_id)
        .join(Usuario.estado_actual)
        # El admin tiene un perfil interno de prescriptor para firmar sus seguimientos: no cuenta
        .filter(EstadoRegistro.estado == Estados.ACTIVO, Usuario.rol == "prescriptor")
        .count()
    )
    total_benef = (
        db.query(Beneficiario)
        .join(Usuario, Usuario.id == Beneficiario.usuario_id)
        .join(Usuario.estado_actual)
        .filter(EstadoRegistro.estado == Estados.ACTIVO)
        .count()
    )

    umbral = datetime.now(timezone.utc) - timedelta(days=14)
    dispositivos_activos = (
        db.query(Dispositivo)
        .join(Usuario, Usuario.id == Dispositivo.usuario_id)
        .join(Usuario.estado_actual)
        .filter(EstadoRegistro.estado == Estados.ACTIVO)
        .all()
    )
    alertas = 0
    for d in dispositivos_activos:
        presc_ids = [p.id for p in d.prescriptores]
        if not presc_ids:
            alertas += 1
            continue
        ultimo_seg = (
            db.query(Seguimiento)
            .filter(Seguimiento.prescriptor_id.in_(presc_ids), Seguimiento.fecha >= umbral)
            .first()
        )
        if not ultimo_seg:
            alertas += 1

    total_acts = db.query(Actividad).count()

    return AdminStats(
        total_dispositivos=total_disp,
        total_usuarios=total_users,
        total_prescriptores=total_presc,
        total_beneficiarios=total_benef,
        alertas_pendientes=alertas,
        total_actividades=total_acts,
    )


# ────────────────────────── USUARIOS ──────────────────────────
@router.get("/usuarios", response_model=list[UsuarioAdmin])
def listar_usuarios(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(admin_only),
):
    users = (
        db.query(Usuario)
        .outerjoin(EstadoRegistro, Usuario.estado_actual_id == EstadoRegistro.id)
        .filter(Usuario.rol != "admin")
        .order_by(
            case(
                (EstadoRegistro.estado == Estados.PENDIENTE, 0),
                (EstadoRegistro.estado == Estados.ACTIVO,    1),
                (EstadoRegistro.estado == Estados.INACTIVO,  2),
                else_=3,
            ),
            Usuario.fecha_registro.desc(),
        )
        .all()
    )
    return [_build_usuario_admin(u) for u in users]


# ────────────────────────── CAMBIAR ESTADO ──────────────────────────
@router.put("/usuarios/{usuario_id}/estado", response_model=UsuarioAdmin)
def cambiar_estado_usuario(
    usuario_id: int,
    data: CambiarEstado,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(admin_only),
):
    user = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="No puedes cambiar tu propio estado")

    estado_anterior = user.estado
    service = EstadoService(db)
    service.cambiar_estado(entidad_obj=user, nuevo_estado=data.status, admin_id=current_user.id, motivo="Cambio de estado desde panel administrativo")

    if user.dispositivo:
        service.cambiar_estado(entidad_obj=user.dispositivo, nuevo_estado=data.status, admin_id=current_user.id, motivo="Cambio de estado desde panel administrativo")
    elif user.prescriptor:
        service.cambiar_estado(entidad_obj=user.prescriptor, nuevo_estado=data.status, admin_id=current_user.id, motivo="Cambio de estado desde panel administrativo")
    elif user.beneficiario:
        service.cambiar_estado(entidad_obj=user.beneficiario, nuevo_estado=data.status, admin_id=current_user.id, motivo="Cambio de estado desde panel administrativo")

    db.refresh(user)
    if data.status == Estados.ACTIVO:
        notificar_aprobacion(background_tasks, db, user, estado_anterior)
    return _build_usuario_admin(user)


# ────────────────────────── CAMBIAR ROL ──────────────────────────
@router.put("/usuarios/{usuario_id}/rol", response_model=UsuarioAdmin)
def cambiar_rol_usuario(
    usuario_id: int,
    data: CambiarRolRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(admin_only),
):
    user = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="No puedes cambiar tu propio rol")

    rol_anterior = user.rol
    user.rol = data.rol

    # Registrar el cambio en EstadoRegistro con motivo
    service = EstadoService(db)
    service.cambiar_estado(
        entidad_obj=user,
        nuevo_estado=user.estado,
        admin_id=current_user.id,
        motivo=f"Cambio de rol: {rol_anterior} → {data.rol}"
    )

    db.commit()
    db.refresh(user)
    return _build_usuario_admin(user)


# ────────────────────────── ELIMINAR USUARIO ──────────────────────────
@router.delete("/usuarios/{usuario_id}", status_code=204)
def eliminar_usuario(
    usuario_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(admin_only),
):
    user = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="No puedes eliminar tu propia cuenta")

    borrar_usuario_completo(db, user)


# ────────────────────────── RECHAZAR SOLICITUD PENDIENTE ──────────────────────────
@router.post("/usuarios/{usuario_id}/rechazar", status_code=204)
def rechazar_usuario(
    usuario_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(admin_only),
):
    """Rechazar elimina la cuenta para que el correo quede libre. Solo cuentas pendientes."""
    user = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    if user.estado != Estados.PENDIENTE:
        raise HTTPException(status_code=400, detail="Solo se pueden rechazar solicitudes pendientes")
    borrar_usuario_completo(db, user)


# ────────────────────────── RESTABLECER CONTRASEÑA ──────────────────────────
@router.post("/usuarios/{usuario_id}/restablecer-password")
def admin_restablecer_password(
    usuario_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(admin_only),
):
    user = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    if not user.email or user.email.endswith("@sin-cuenta.mascate"):
        raise HTTPException(status_code=400, detail="Este usuario no tiene un correo real registrado")

    token = generar_token()
    user.password_reset_token = token
    user.password_reset_token_expiry = datetime.now(timezone.utc) + timedelta(hours=24)
    db.commit()

    background_tasks.add_task(
        enviar_correo_recuperacion,
        email=user.email,
        token=token,
        base_url=settings.app_base_url,
    )
    return {"message": f"Correo de restablecimiento enviado a {user.email}"}


# ────────────────────────── ALERTAS ──────────────────────────
@router.get("/alertas", response_model=list[AlertaOut])
def alertas_sistema(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(admin_only),
):
    umbral = datetime.now(timezone.utc) - timedelta(days=14)
    dispositivos = (
        db.query(Dispositivo)
        .join(Usuario, Usuario.id == Dispositivo.usuario_id)
        .join(Usuario.estado_actual)
        .filter(EstadoRegistro.estado == Estados.ACTIVO)
        .all()
    )
    alertas = []
    for d in dispositivos:
        tiene_actividad_reciente = False
        presc_ids = [p.id for p in d.prescriptores]
        if presc_ids:
            ultimo_seg = (
                db.query(Seguimiento)
                .filter(Seguimiento.prescriptor_id.in_(presc_ids), Seguimiento.fecha >= umbral)
                .first()
            )
            if ultimo_seg:
                tiene_actividad_reciente = True

        if not tiene_actividad_reciente:
            ultima_fecha = (
                db.query(func.max(Seguimiento.fecha))
                .filter(Seguimiento.prescriptor_id.in_(presc_ids) if presc_ids else False)
                .scalar()
            )
            if ultima_fecha:
                if ultima_fecha.tzinfo is None:
                    ultima_fecha = ultima_fecha.replace(tzinfo=timezone.utc)
                dias = (datetime.now(timezone.utc) - ultima_fecha).days
            else:
                dias = 999

            alertas.append(AlertaOut(
                dispositivo_id=d.id,
                dispositivo=d.nombre,
                mensaje=f"Sin reporte en {dias} días" if dias < 999 else "Sin reportes registrados",
                dias_sin_actividad=dias,
            ))

    return alertas


# ────────────────────────── CREAR DISPOSITIVO (ADMIN) ──────────────────────────
@router.post("/dispositivos", response_model=AdminDispositivoOut, status_code=201)
def admin_crear_dispositivo(
    data: AdminDispositivoCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(admin_only),
):
    if db.query(Usuario).filter(Usuario.email == data.email).first():
        raise HTTPException(status_code=409, detail="Ya existe una cuenta con ese correo")

    # Generar password temporal
    alphabet = string.ascii_letters + string.digits
    password_temporal = ''.join(secrets.choice(alphabet) for _ in range(12))

    user = Usuario(
        email=data.email,
        password_hash=hash_password(password_temporal),
        rol="dispositivo",
        email_verificado=True,
    )
    db.add(user)
    db.flush()

    service_estado = EstadoService(db)
    service_estado.cambiar_estado(entidad_obj=user, nuevo_estado=Estados.ACTIVO, admin_id=current_user.id, motivo="Dispositivo creado directamente por el administrador")

    disp = Dispositivo(
        usuario_id=user.id,
        nombre=data.nombre,
        lugar_actividades=data.lugar_actividades,
        ubicacion=data.ubicacion,
        tipo_servicio=data.tipo_servicio,
        dia_actividad=data.dia_actividad,
        hora_actividad=data.hora_actividad,
        telefono=data.telefono,
        redes_sociales=data.redes_sociales,
    )
    db.add(disp)
    db.flush()

    service_estado.cambiar_estado(entidad_obj=disp, nuevo_estado=Estados.ACTIVO, admin_id=current_user.id, motivo="Dispositivo creado directamente por el administrador")

    db.commit()
    db.refresh(disp)

    background_tasks.add_task(
        enviar_correo_bienvenida_dispositivo,
        email=data.email,
        password=password_temporal,
        base_url=settings.app_base_url,
    )

    return AdminDispositivoOut(
        id=disp.id,
        nombre=disp.nombre,
        tipo_servicio=disp.tipo_servicio,
        num_beneficiarios=0,
        prescriptores=[],
        activo=True,
        email=data.email,
        fecha_registro=user.fecha_registro,
        num_actividades=0,
        asistencia_pct=None,
    )


# ────────────────────────── LISTAR DISPOSITIVOS ──────────────────────────
@router.get("/dispositivos", response_model=list[AdminDispositivoOut])
def admin_listar_dispositivos(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(admin_only),
):
    dispositivos = db.query(Dispositivo).all()
    result = []
    for d in dispositivos:
        benef_ids = set()
        insc = (
            db.query(Inscripcion.beneficiario_id)
            .join(Actividad, Actividad.id == Inscripcion.actividad_id)
            .filter(Actividad.dispositivo_id == d.id)
            .distinct().all()
        )
        benef_ids.update(b[0] for b in insc)
        pc = (
            db.query(PrimerContacto.beneficiario_id)
            .filter(PrimerContacto.dispositivo_id == d.id)
            .distinct().all()
        )
        benef_ids.update(b[0] for b in pc)

        presc_ids = [p.id for p in d.prescriptores]
        if presc_ids:
            seg = (
                db.query(Seguimiento.beneficiario_id)
                .filter(Seguimiento.prescriptor_id.in_(presc_ids))
                .distinct().all()
            )
            benef_ids.update(b[0] for b in seg)

        num_actividades = db.query(Actividad).filter(Actividad.dispositivo_id == d.id).count()
        presc_names = [p.nombre_completo for p in d.prescriptores] if d.prescriptores else []
        presc_activos = [
            p.nombre_completo for p in d.prescriptores
            if p.usuario and p.usuario.rol == "prescriptor" and p.usuario.estado == Estados.ACTIVO
        ]
        email_disp = d.usuario.email if d.usuario else None
        fecha_registro = d.usuario.fecha_registro if d.usuario else None

        result.append(AdminDispositivoOut(
            id=d.id,
            nombre=d.nombre,
            tipo_servicio=d.tipo_servicio,
            num_beneficiarios=len(benef_ids),
            prescriptores=presc_names,
            num_prescriptores=len(presc_activos),
            prescriptores_activos=presc_activos,
            activo=d.usuario.estado == Estados.ACTIVO if d.usuario else False,
            email=email_disp,
            fecha_registro=fecha_registro,
            num_actividades=num_actividades,
            asistencia_pct=None,
            lugar_actividades=d.lugar_actividades,
            ubicacion=d.ubicacion,
            dia_actividad=d.dia_actividad,
            hora_actividad=d.hora_actividad,
            telefono=d.telefono,
            redes_sociales=d.redes_sociales,
        ))

    return result


# ────────────────────────── ELIMINAR DISPOSITIVO ──────────────────────────
@router.delete("/dispositivos/{dispositivo_id}", status_code=204)
def admin_eliminar_dispositivo(
    dispositivo_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(admin_only),
):
    disp = db.query(Dispositivo).filter(Dispositivo.id == dispositivo_id).first()
    if not disp:
        raise HTTPException(status_code=404, detail="Dispositivo no encontrado")

    tiene_actividades = db.query(Actividad).filter(Actividad.dispositivo_id == dispositivo_id).count() > 0
    tiene_prescriptores = len(disp.prescriptores) > 0
    tiene_pc = db.query(PrimerContacto).filter(PrimerContacto.dispositivo_id == dispositivo_id).count() > 0

    if tiene_actividades or tiene_prescriptores or tiene_pc:
        raise HTTPException(status_code=409, detail="No se puede eliminar: el dispositivo tiene datos asociados")

    usuario = db.query(Usuario).filter(Usuario.id == disp.usuario_id).first()
    db.delete(disp)
    db.flush()
    if usuario:
        db.query(EstadoRegistro).filter(
            EstadoRegistro.entidad_tipo == "usuario",
            EstadoRegistro.entidad_id == usuario.id,
        ).delete(synchronize_session="fetch")
        db.flush()
        db.delete(usuario)
    db.commit()


# ────────────────────────── EXPORTAR TODO (Excel) ──────────────────────────
# Columnas que nunca se exportan (credenciales y tokens)
_EXPORT_EXCLUIR = {
    "password_hash", "email_token", "password_reset_token",
    "password_reset_token_expiry", "estado_actual_id",
    "solicitud_dispositivo_id",          # columna sin uso
}


def _valor_excel(v):
    if v is None:
        return ""
    if isinstance(v, bool):
        return "Sí" if v else "No"
    if isinstance(v, datetime):
        return v.strftime("%Y-%m-%d %H:%M")
    if hasattr(v, "isoformat"):          # date / time
        return v.isoformat()
    return getattr(v, "value", v)        # Enum → texto


def _direccion(pc):
    partes = [pc.clase_via, pc.numero_via_principal, pc.letra_via_principal, pc.identificador_sector]
    gen = [pc.numero_via_generadora, pc.letra_via_generadora]
    d = " ".join(p for p in partes if p)
    if any(gen) or pc.numero_predio:
        d += " # " + " ".join(p for p in gen if p)
        if pc.numero_predio:
            d += " - " + pc.numero_predio
    if pc.otras_caracteristicas_dir:
        d += " (" + pc.otras_caracteristicas_dir + ")"
    return d.strip()


# Hoja "Primer contacto": el formulario completo en una fila, en el orden de la HPC.
# Cada entrada: (encabezado, función(pc, beneficiario, usuario) -> valor)
_PC_COLUMNAS = [
    # 1. Datos de registro del contacto
    ("ID registro",                 lambda pc, b, u: pc.id),
    ("Fecha",                       lambda pc, b, u: pc.fecha_contacto),
    ("Hora",                        lambda pc, b, u: pc.hora_contacto),
    ("Caso #",                      lambda pc, b, u: pc.numero_caso),
    ("Forma de contacto",           lambda pc, b, u: pc.forma_contacto),
    ("Tipo de contacto",            lambda pc, b, u: pc.tipo_contacto),
    ("Lugar del contacto",          lambda pc, b, u: pc.lugar_contacto),
    ("Localidad",                   lambda pc, b, u: b.localidad if b else None),
    ("UPZ",                         lambda pc, b, u: pc.upz),
    ("Barrio",                      lambda pc, b, u: pc.barrio),
    ("Convenio",                    lambda pc, b, u: pc.convenio_515),
    ("DBC",                         lambda pc, b, u: pc.dispositivo.nombre if pc.dispositivo else pc.tipo_dbc),
    ("Acepta política de privacidad", lambda pc, b, u: pc.politica_privacidad),
    # 2. Información del beneficiario
    ("Nombre y apellidos",          lambda pc, b, u: b.nombre_apodo if b else None),
    ("Correo electrónico",          lambda pc, b, u: u.email if u and not u.email.endswith("@sin-cuenta.mascate") else None),
    ("¿La información la da el mismo beneficiario?", lambda pc, b, u: pc.info_por_beneficiario),
    ("Fuente: quién es",            lambda pc, b, u: pc.nombre_fuente),
    ("Fuente: teléfono",            lambda pc, b, u: pc.telefono_fuente),
    ("Fuente: identidad de género", lambda pc, b, u: pc.genero_fuente),
    ("Fuente: vínculo con la persona", lambda pc, b, u: pc.vinculo_fuente),
    ("Fecha de nacimiento",         lambda pc, b, u: b.fecha_nacimiento if b else None),
    ("Edad",                        lambda pc, b, u: pc.edad_benef),
    ("Identidad de género",         lambda pc, b, u: b.genero if b else None),
    ("Teléfono",                    lambda pc, b, u: b.telefono if b else None),
    ("Dirección",                   lambda pc, b, u: _direccion(pc)),
    ("Pertenencia a grupo étnico",  lambda pc, b, u: b.pertenencia_etnica if b else None),
    ("Grupo étnico: cuál",          lambda pc, b, u: b.etnia if b else None),
    ("Religión",                    lambda pc, b, u: b.religion if b else None),
    ("Poblaciones de especial interés", lambda pc, b, u: pc.poblaciones_especiales),
    ("N.º procesos de atención previos", lambda pc, b, u: pc.procesos_previos),
    # 3. Entorno familiar y social
    ("Estado civil",                lambda pc, b, u: b.estado_civil if b else None),
    ("N.º hijos(as)",               lambda pc, b, u: b.num_hijos if b else None),
    ("Con quién vive",              lambda pc, b, u: b.con_quien_vive if b else None),
    ("¿Cuántas personas son tan cercanas a ti que puedes contar con ellas?", lambda pc, b, u: pc.apoyo_personas_cercanas),
    ("¿Cuánto interés y preocupación muestra la gente por lo que haces?",    lambda pc, b, u: pc.apoyo_interes_otros),
    ("¿Qué tan fácil es obtener ayuda práctica de los vecinos?",             lambda pc, b, u: pc.apoyo_ayuda_vecinos),
    ("Apoyo de su familia",         lambda pc, b, u: b.apoyo_familiar if b else None),
    ("Apoyo de la comunidad",       lambda pc, b, u: b.apoyo_comunitario if b else None),
    ("Apoyo de institución pública", lambda pc, b, u: b.apoyo_institucional if b else None),
    ("Apoyo de otro actor social",  lambda pc, b, u: b.apoyo_otro_actor if b else None),
    ("Cuál actor social",           lambda pc, b, u: b.cual_actor_social if b else None),
    ("¿Tiene persona de apoyo?",    lambda pc, b, u: b.tiene_persona_apoyo if b else None),
    ("Persona de apoyo: nombre",    lambda pc, b, u: b.nombre_persona_apoyo if b else None),
    ("Persona de apoyo: teléfono",  lambda pc, b, u: b.telefono_persona_apoyo if b else None),
    ("Persona de apoyo: vínculo",   lambda pc, b, u: b.vinculo_persona_apoyo if b else None),
    ("Persona de apoyo: vínculo (código)", lambda pc, b, u: b.tipo_vinculo_codigo if b else None),
    ("Persona de apoyo: género",    lambda pc, b, u: b.genero_apoyo if b else None),
    # 4. Educación y ocupación
    ("Escolaridad",                 lambda pc, b, u: b.escolaridad if b else None),
    ("Ocupación",                   lambda pc, b, u: b.ocupacion if b else None),
    ("Sabe leer y escribir",        lambda pc, b, u: b.sabe_leer_escribir if b else None),
    ("Sabe usar un computador",     lambda pc, b, u: b.sabe_usar_computador if b else None),
    # 5. Bienestar y estilo de vida
    ("Alimentación",                lambda pc, b, u: pc.alimentacion),
    ("Practica deporte / pasatiempo", lambda pc, b, u: b.practica_deporte if b else None),
    ("Tiene tiempo para recreación", lambda pc, b, u: b.tiene_tiempo_recreacion if b else None),
    ("Cuánto tiempo al día",        lambda pc, b, u: b.cuanto_tiempo_recreacion if b else None),
    ("Conoce espacios de participación", lambda pc, b, u: b.conoce_espacios if b else None),
    ("Ha participado en decisiones comunitarias", lambda pc, b, u: b.ha_participado if b else None),
    ("Emociones (rueda de Plutchik)", lambda pc, b, u: pc.emociones),
    # 6–8
    ("Situaciones presentes",       lambda pc, b, u: pc.situaciones_presentes),
    ("Peticiones y necesidades",    lambda pc, b, u: pc.peticiones),
    ("Descripción del caso",        lambda pc, b, u: pc.descripcion_caso),
    # 9. Quien diligencia
    ("Diligenciado por: nombre",    lambda pc, b, u: pc.nombre_registrador),
    ("Diligenciado por: rol",       lambda pc, b, u: pc.rol_registrador),
    ("Diligenciado por: teléfono",  lambda pc, b, u: pc.telefono_registrador),
    # Control
    ("Registrado en plataforma por", lambda pc, b, u: pc.prescriptor.nombre_completo if pc.prescriptor else None),
    ("Fecha de registro en plataforma", lambda pc, b, u: pc.created_at),
    ("Estado actual del beneficiario", lambda pc, b, u: b.estado_actual.estado if b and b.estado_actual else None),
]


@router.get("/exportar-todo")
def exportar_todo(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(admin_only),
):
    """Descarga un Excel con una hoja por tabla de la plataforma."""
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill
    from openpyxl.utils import get_column_letter

    # Nombres legibles para las columnas *_id
    nombres = {
        "usuario_id":      {u.id: u.email for u in db.query(Usuario).all()},
        "dispositivo_id":  {d.id: d.nombre for d in db.query(Dispositivo).all()},
        "prescriptor_id":  {p.id: p.nombre_completo for p in db.query(Prescriptor).all()},
        "beneficiario_id": {b.id: b.nombre_apodo for b in db.query(Beneficiario).all()},
    }

    hojas = [
        ("Dispositivos",        Dispositivo),
        ("Prescriptores",       Prescriptor),
        ("Beneficiarios",       Beneficiario),
        ("Primer contacto",     PrimerContacto),
        ("Seguimientos",        Seguimiento),
        ("Actividades",         Actividad),
    ]

    wb = Workbook()
    resumen = wb.active
    resumen.title = "Resumen"
    resumen.append(["Exportación completa · Cuida Tu Techo"])
    resumen["A1"].font = Font(bold=True, size=13)
    resumen.append(["Fecha", datetime.now().strftime("%Y-%m-%d %H:%M")])
    resumen.append(["Generado por", current_user.email])
    resumen.append([])
    resumen.append(["Hoja", "Registros"])
    for c in resumen[5]:
        c.font = Font(bold=True)

    encabezado = PatternFill("solid", fgColor="E8A800")
    for titulo, modelo in hojas:
        consulta = db.query(modelo)
        if modelo is Prescriptor:
            # Sin el perfil interno del admin
            consulta = consulta.join(Usuario, Usuario.id == Prescriptor.usuario_id).filter(Usuario.rol == "prescriptor")
        filas = consulta.order_by(modelo.id).all()
        ws = wb.create_sheet(titulo)

        if modelo is PrimerContacto:
            # Formulario completo: datos del contacto + datos del beneficiario
            cabecera = [h for h, _ in _PC_COLUMNAS]
            ws.append(cabecera)
            for pc in filas:
                b = pc.beneficiario
                u = b.usuario if b else None
                ws.append([_valor_excel(fn(pc, b, u)) for _, fn in _PC_COLUMNAS])
        else:
            columnas = [c.name for c in modelo.__table__.columns if c.name not in _EXPORT_EXCLUIR]
            tiene_estado = "estado_actual_id" in modelo.__table__.columns

            cabecera = []
            for col in columnas:
                cabecera.append(col)
                if col in nombres:
                    if col == "usuario_id":
                        cabecera.append(col.replace("_id", "") + "_email")
                    else:
                        cabecera.append(col.replace("_id", "") + "_nombre")
            if tiene_estado:
                cabecera.append("estado_actual")
            cabecera = [h.replace("_", " ").capitalize() for h in cabecera]
            ws.append(cabecera)

            for obj in filas:
                fila = []
                for col in columnas:
                    v = getattr(obj, col)
                    fila.append(_valor_excel(v))
                    if col in nombres:
                        fila.append(nombres[col].get(v, "") if v is not None else "")
                if tiene_estado:
                    est = getattr(obj, "estado_actual", None)
                    fila.append(_valor_excel(est.estado) if est else "")
                ws.append(fila)

        for c in ws[1]:
            c.font = Font(bold=True)
            c.fill = encabezado

        ws.freeze_panes = "A2"
        if filas:
            ws.auto_filter.ref = ws.dimensions
        for i, h in enumerate(cabecera, start=1):
            largo = max([len(str(h))] + [len(str(ws.cell(r, i).value or "")) for r in range(2, min(ws.max_row, 200) + 1)])
            ws.column_dimensions[get_column_letter(i)].width = min(max(10, largo + 2), 60)

        resumen.append([titulo, len(filas)])

    resumen.column_dimensions["A"].width = 24
    resumen.column_dimensions["B"].width = 22

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    nombre_archivo = f"cuidatutecho_export_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={nombre_archivo}"},
    )


# ────────────────────────── LISTAR BENEFICIARIOS (para formularios) ──────────
@router.get("/beneficiarios", response_model=list[BeneficiarioResumen])
def admin_listar_beneficiarios(
    admin_actual: Usuario = Depends(admin_only),
    db: Session = Depends(get_db),
):
    benefs = db.query(Beneficiario).all()
    result = []
    for b in benefs:
        email = b.usuario.email if b.usuario else None
        status = b.estado
        result.append(BeneficiarioResumen(
            id=b.id,
            nombre_apodo=b.nombre_apodo,
            email=email,
            genero=b.genero,
            fecha_nacimiento=b.fecha_nacimiento,
            localidad=b.localidad,
            telefono=b.telefono,
            status=status,
        ))
    return result


# ────────────────────────── APROBAR USUARIO ──────────────────────────
@router.post("/usuarios/{usuario_id}/aprobar")
def aprobar_usuario(
    usuario_id: int,
    background_tasks: BackgroundTasks,
    admin_actual: Usuario = Depends(admin_only),
    db: Session = Depends(get_db)
):
    usuario = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    estado_anterior = usuario.estado
    service = EstadoService(db)
    service.cambiar_estado(entidad_obj=usuario, nuevo_estado=Estados.ACTIVO, admin_id=admin_actual.id, motivo="Documentación verificada correctamente")

    if usuario.dispositivo:
        service.cambiar_estado(entidad_obj=usuario.dispositivo, nuevo_estado=Estados.ACTIVO, admin_id=admin_actual.id, motivo="Documentación verificada correctamente")
    elif usuario.prescriptor:
        service.cambiar_estado(entidad_obj=usuario.prescriptor, nuevo_estado=Estados.ACTIVO, admin_id=admin_actual.id, motivo="Documentación verificada correctamente")
    elif usuario.beneficiario:
        service.cambiar_estado(entidad_obj=usuario.beneficiario, nuevo_estado=Estados.ACTIVO, admin_id=admin_actual.id, motivo="Documentación verificada correctamente")

    notificar_aprobacion(background_tasks, db, usuario, estado_anterior)
    return {"msg": "Usuario aprobado"}


# ────────────────────────── ASIGNAR / DESASOCIAR DISPOSITIVO ──────────────────────────
class AsignarDispositivoRequest(_BM):
    dispositivo_id: int | None = None


@router.put("/prescriptores/{prescriptor_id}/dispositivo")
def admin_asignar_dispositivo(
    prescriptor_id: int,
    data: AsignarDispositivoRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(admin_only),
):
    """Asigna o quita el dispositivo de un prescriptor directamente."""
    presc = db.query(Prescriptor).filter(Prescriptor.id == prescriptor_id).first()
    if not presc:
        raise HTTPException(status_code=404, detail="Prescriptor no encontrado")

    if data.dispositivo_id is not None:
        disp = db.query(Dispositivo).filter(Dispositivo.id == data.dispositivo_id).first()
        if not disp:
            raise HTTPException(status_code=404, detail="Dispositivo no encontrado")

    # Si cambia de dispositivo, desasignar todos sus beneficiarios
    if presc.dispositivo_id != data.dispositivo_id:
        db.query(Beneficiario).filter(Beneficiario.prescriptor_id == presc.id).update(
            {Beneficiario.prescriptor_id: None}
        )

    presc.dispositivo_id = data.dispositivo_id
    db.commit()

    if data.dispositivo_id is not None:
        service = EstadoService(db)
        estado_anterior = presc.usuario.estado if presc.usuario else None
        if presc.usuario and presc.usuario.estado != Estados.ACTIVO:
            service.cambiar_estado(entidad_obj=presc.usuario, nuevo_estado=Estados.ACTIVO, admin_id=current_user.id, motivo="Asignado a dispositivo por admin")
        if presc.estado != Estados.ACTIVO:
            service.cambiar_estado(entidad_obj=presc, nuevo_estado=Estados.ACTIVO, admin_id=current_user.id, motivo="Asignado a dispositivo por admin")
        if presc.usuario:
            db.refresh(presc)
            notificar_aprobacion(background_tasks, db, presc.usuario, estado_anterior)

    return {"msg": "Dispositivo actualizado", "dispositivo_nombre": disp.nombre if data.dispositivo_id else None}


@router.put("/beneficiarios/{beneficiario_id}/dispositivo")
def admin_asignar_dispositivo_beneficiario(
    beneficiario_id: int,
    data: AsignarDispositivoRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(admin_only),
):
    benef = db.query(Beneficiario).filter(Beneficiario.id == beneficiario_id).first()
    if not benef:
        raise HTTPException(status_code=404, detail="Beneficiario no encontrado")

    if data.dispositivo_id is not None:
        disp = db.query(Dispositivo).filter(Dispositivo.id == data.dispositivo_id).first()
        if not disp:
            raise HTTPException(status_code=404, detail="Dispositivo no encontrado")

    benef.dispositivo_id = data.dispositivo_id
    if data.dispositivo_id is None:
        benef.prescriptor_id = None
    db.commit()

    return {"msg": "Dispositivo actualizado", "dispositivo_nombre": disp.nombre if data.dispositivo_id else None}
