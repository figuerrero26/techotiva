"""
Servicio de correo electrónico para verificación de usuarios.
"""
import html as html_lib
import secrets
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig, MessageType
from app.core.config import settings

conf = ConnectionConfig(
    MAIL_USERNAME=settings.mail_username,
    MAIL_PASSWORD=settings.mail_password,
    MAIL_FROM=settings.mail_from,
    MAIL_PORT=587,
    MAIL_SERVER="smtp.gmail.com",
    MAIL_STARTTLS=True,
    MAIL_SSL_TLS=False,
    USE_CREDENTIALS=True,
)


def generar_token() -> str:
    return secrets.token_urlsafe(32)


async def enviar_correo_recuperacion(email: str, token: str, base_url: str):
    link = f"{base_url}/login?reset_token={token}"
    html = f"""
    <div style="font-family:sans-serif;max-width:480px;margin:auto">
      <h2 style="color:#1D9E75">Recupera tu contraseña en MASCATE</h2>
      <p>Recibimos una solicitud para restablecer tu contraseña. Haz clic en el botón para crear una nueva:</p>
      <a href="{link}" style="display:inline-block;padding:12px 24px;background:#1D9E75;color:#fff;border-radius:8px;text-decoration:none;font-weight:bold">
        Cambiar contraseña
      </a>
      <p style="color:#888;font-size:0.85rem;margin-top:1rem">
        Si no solicitaste esto, ignora este mensaje. Tu contraseña no cambiará.<br>
        El enlace expira en 10 minutos.
      </p>
    </div>
    """
    message = MessageSchema(
        subject="Recupera tu contraseña - MASCATE",
        recipients=[email],
        body=html,
        subtype=MessageType.html,
    )
    fm = FastMail(conf)
    await fm.send_message(message)


async def enviar_correo_aprobacion(email: str, rol: str, nombre: str, dispositivo: str,
                                   token_verificacion: str, base_url: str):
    nombre = html_lib.escape(nombre or "")
    dispositivo = html_lib.escape(dispositivo or "")
    if rol == "prescriptor":
        cuerpo = (f"Tu cuenta de <strong>prescriptxr</strong> fue aprobada"
                  + (f" y quedaste asociadx al dispositivo <strong>{dispositivo}</strong>." if dispositivo else "."))
    else:
        cuerpo = f"Tu dispositivo <strong>{dispositivo or nombre}</strong> fue aprobado en la plataforma."
    if token_verificacion:
        # Aún no ha verificado su correo: el botón lo verifica y lo lleva al login
        enlace = f"{base_url}/auth/verificar-email?token={token_verificacion}"
        texto = "Para activar tu cuenta, confirma tu correo con el botón de abajo y luego ingresa con tu correo y contraseña."
        boton = "Verificar correo e ingresar"
    else:
        enlace, boton = f"{base_url}/login", "Ingresar"
        texto = "Ya puedes ingresar a Cuida Tu Techo con tu correo y contraseña."
    html = f"""
    <div style="font-family:sans-serif;max-width:480px;margin:auto">
      <h2 style="color:#1D9E75">✅ ¡Tu cuenta fue aprobada!</h2>
      <p>Hola {nombre},</p>
      <p>{cuerpo}</p>
      <p>{texto}</p>
      <a href="{enlace}" style="display:inline-block;padding:12px 24px;background:#1D9E75;color:#fff;border-radius:8px;text-decoration:none;font-weight:bold">
        {boton}
      </a>
    </div>
    """
    message = MessageSchema(
        subject="✅ Tu cuenta fue aprobada - Cuida Tu Techo",
        recipients=[email],
        body=html,
        subtype=MessageType.html,
    )
    fm = FastMail(conf)
    await fm.send_message(message)


def notificar_aprobacion(background_tasks, db, usuario, estado_anterior: str) -> None:
    """
    Programa el correo de "cuenta aprobada" si la cuenta pasó de pendiente a activa.
    Si la persona aún no verificó su correo, el mismo correo trae el enlace para hacerlo.
    No se envía al reactivar una cuenta que estaba desactivada.
    """
    if estado_anterior != "pendiente" or usuario.rol not in ("prescriptor", "dispositivo"):
        return
    if usuario.rol == "prescriptor" and usuario.prescriptor:
        p = usuario.prescriptor
        nombre, disp = p.nombre_completo, (p.dispositivo.nombre if p.dispositivo else "")
    elif usuario.rol == "dispositivo" and usuario.dispositivo:
        nombre = disp = usuario.dispositivo.nombre
    else:
        nombre, disp = usuario.email, ""
    token = None
    if not usuario.email_verificado:
        token = generar_token()
        usuario.email_token = token
        db.commit()
    background_tasks.add_task(
        enviar_correo_aprobacion,
        email=usuario.email, rol=usuario.rol, nombre=nombre, dispositivo=disp,
        token_verificacion=token, base_url=settings.app_base_url,
    )


async def enviar_codigo_2fa(email: str, codigo: str, minutos: int):
    html = f"""
    <div style="font-family:sans-serif;max-width:480px;margin:auto">
      <h2 style="color:#1D9E75">Código de acceso — Cuida Tu Techo</h2>
      <p>Usa este código para terminar de iniciar sesión como administrador:</p>
      <p style="font-size:2rem;font-weight:bold;letter-spacing:0.4rem;margin:1rem 0">{codigo}</p>
      <p style="color:#888;font-size:0.85rem">
        El código vence en {minutos} minutos y solo sirve una vez.<br>
        Si no intentaste iniciar sesión, alguien conoce tu contraseña: cámbiala de inmediato.
      </p>
    </div>
    """
    message = MessageSchema(
        subject=f"Código de acceso: {codigo} - Cuida Tu Techo",
        recipients=[email],
        body=html,
        subtype=MessageType.html,
    )
    fm = FastMail(conf)
    await fm.send_message(message)


async def enviar_correo_bienvenida_dispositivo(email: str, password: str, base_url: str):
    html = f"""
    <div style="font-family:sans-serif;max-width:480px;margin:auto">
      <h2 style="color:#1D9E75">¡Bienvenido a MASCATE!</h2>
      <p>Tu cuenta de Dispositivo CBC ha sido creada por el administrador.</p>
      <p>Tus credenciales de acceso son:</p>
      <div style="background:#f4f4f4;padding:1rem;border-radius:8px;margin:1rem 0">
        <strong>Correo:</strong> {email}<br>
        <strong>Contraseña temporal:</strong> <code style="font-size:1.1rem">{password}</code>
      </div>
      <a href="{base_url}/login" style="display:inline-block;padding:12px 24px;background:#1D9E75;color:#fff;border-radius:8px;text-decoration:none;font-weight:bold">
        Ingresar al sistema
      </a>
      <p style="color:#888;font-size:0.85rem;margin-top:1rem">
        Por seguridad, cambia tu contraseña en Configuración después de ingresar.
      </p>
    </div>
    """
    message = MessageSchema(
        subject="Bienvenido a MASCATE — Tus credenciales de acceso",
        recipients=[email],
        body=html,
        subtype=MessageType.html,
    )
    fm = FastMail(conf)
    await fm.send_message(message)


async def enviar_correo_bienvenida_beneficiario(email: str, token: str, base_url: str):
    link = f"{base_url}/login?reset_token={token}"
    html = f"""
    <div style="font-family:sans-serif;max-width:480px;margin:auto">
      <h2 style="color:#1D9E75">¡Te registraron en Cuida Tu Techo!</h2>
      <p>Se ha creado un perfil para ti en la plataforma. Para acceder, configura tu contraseña haciendo clic en el botón:</p>
      <a href="{link}" style="display:inline-block;padding:12px 24px;background:#1D9E75;color:#fff;border-radius:8px;text-decoration:none;font-weight:bold">
        Configurar contraseña
      </a>
      <p style="color:#888;font-size:0.85rem;margin-top:1rem">
        Este enlace expira en 24 horas. Si no solicitaste esto, ignora este mensaje.
      </p>
    </div>
    """
    message = MessageSchema(
        subject="Configura tu contraseña — Cuida Tu Techo",
        recipients=[email],
        body=html,
        subtype=MessageType.html,
    )
    fm = FastMail(conf)
    await fm.send_message(message)


async def enviar_correo_verificacion(email: str, token: str, base_url: str):
    link = f"{base_url}/auth/verificar-email?token={token}"
    html = f"""
    <div style="font-family:sans-serif;max-width:480px;margin:auto">
      <h2 style="color:#1D9E75">Verifica tu correo en Cuida Tu Techo</h2>
      <p>Recibimos tu registro. Verifica tu correo con el botón de abajo y luego podrás ingresar a la plataforma.</p>
      <a href="{link}" style="display:inline-block;padding:12px 24px;background:#1D9E75;color:#fff;border-radius:8px;text-decoration:none;font-weight:bold">
        Verificar correo
      </a>
      <p style="color:#888;font-size:0.85rem;margin-top:1rem">
        Si no te registraste, ignora este mensaje.
      </p>
    </div>
    """
    message = MessageSchema(
        subject="Verifica tu correo - MASCATE",
        recipients=[email],
        body=html,
        subtype=MessageType.html,
    )
    fm = FastMail(conf)
    await fm.send_message(message)