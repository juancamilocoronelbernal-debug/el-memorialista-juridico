"""Correo transaccional explícito; ninguna entrega se simula si falta SMTP.

Las llamadas se realizan sólo tras una petición expresa del propietario o del
destinatario (invitación o código). Un timeout es entrega no confirmada, no éxito.
"""
from __future__ import annotations

import re
import smtplib
import ssl
from email.message import EmailMessage
from email.utils import make_msgid

import anyio
from fastapi import HTTPException

from app.config import get_settings


def valid_email(value: str) -> str:
    value = str(value).strip().lower()
    if (len(value) > 254 or re.search(r"[\x00-\x20\x7f]", value)
            or not re.fullmatch(r"[^@<>;,\"\\]+@[^@<>;,\"\\]+\.[^@<>;,\"\\]+", value)):
        raise HTTPException(422, "Revisa el correo del destinatario.")
    return value


def status() -> dict:
    s = get_settings()
    ready = bool(getattr(s, "SMTP_HOST", "") and getattr(s, "SMTP_FROM_EMAIL", ""))
    if ready:
        try:
            valid_email(getattr(s, "SMTP_FROM_EMAIL", ""))
            ready = (getattr(s, "SMTP_TLS_MODE", "starttls").lower() in {"starttls", "tls"}
                and 1 <= int(getattr(s, "SMTP_PORT", 587)) <= 65535
                and not re.search(r"[\x00-\x20\x7f]", getattr(s, "SMTP_HOST", "")))
        except (HTTPException, TypeError, ValueError):
            ready = False
    return {"configured": ready, "transport": "smtp_tls", "message": (
        "Correo transaccional configurado; cada envío comprueba su disponibilidad."
        if ready else "Configura un remitente y servidor SMTP válidos con TLS para invitaciones y códigos de verificación.")}


def _send(recipient: str, subject: str, body: str) -> dict:
    s = get_settings()
    if not status()["configured"]:
        raise HTTPException(503, "El envío de correo no está configurado. Configura SMTP en el servidor.")
    recipient = valid_email(recipient)
    sender = valid_email(getattr(s, "SMTP_FROM_EMAIL", ""))
    if re.search(r"[\r\n\x00]", subject) or len(subject) > 200 or len(body) > 100_000:
        raise HTTPException(422, "El mensaje supera los límites admitidos.")
    message = EmailMessage()
    message["From"], message["To"], message["Subject"] = sender, recipient, subject
    message["Message-ID"] = make_msgid(domain=sender.rsplit("@", 1)[1])
    message.set_content(body)
    host = getattr(s, "SMTP_HOST", "").strip()
    port = int(getattr(s, "SMTP_PORT", 587))
    mode = getattr(s, "SMTP_TLS_MODE", "starttls").lower()
    if mode not in {"starttls", "tls"}:
        raise HTTPException(503, "SMTP requiere TLS directo o STARTTLS; no se admite correo sin cifrar.")
    context = ssl.create_default_context()
    try:
        if mode == "tls":
            client = smtplib.SMTP_SSL(host, port, timeout=25, context=context)
        else:
            client = smtplib.SMTP(host, port, timeout=25)
        with client:
            client.ehlo()
            if mode == "starttls":
                client.starttls(context=context)
                client.ehlo()
            username = getattr(s, "SMTP_USERNAME", "")
            if username:
                client.login(username, getattr(s, "SMTP_PASSWORD", ""))
            rejected = client.send_message(message)
            if rejected:
                raise HTTPException(502, "El servidor de correo rechazó al destinatario.")
    except HTTPException:
        raise
    except (smtplib.SMTPException, OSError, TimeoutError):
        # No registrar excepciones de SMTP: pueden incluir dirección, usuario,
        # contenido o respuestas sensibles del proveedor.
        raise HTTPException(502, "No se confirmó la entrega del correo. Comprueba el buzón antes de volver a enviarlo.") from None
    return {"accepted_by_smtp": True, "message_id": str(message["Message-ID"]),
            "notice": "El servidor de correo aceptó el mensaje; esto no confirma su llegada al buzón."}


async def send_email(recipient: str, subject: str, body: str) -> dict:
    return await anyio.to_thread.run_sync(_send, recipient, subject, body)
