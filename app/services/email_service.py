"""
Servicio de correo electrónico para verificación de usuarios.
"""
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
        El enlace expira en 1 hora.
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
      <h2 style="color:#1D9E75">Verifica tu correo en MASCATE</h2>
      <p>Haz clic en el botón para verificar tu correo y continuar con tu solicitud de registro.</p>
      <a href="{link}" style="display:inline-block;padding:12px 24px;background:#1D9E75;color:#fff;border-radius:8px;text-decoration:none;font-weight:bold">
        Verificar correo
      </a>
      <p style="color:#888;font-size:0.85rem;margin-top:1rem">
        Si no solicitaste esto, ignora este mensaje.<br>
        El enlace expira en 24 horas.
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