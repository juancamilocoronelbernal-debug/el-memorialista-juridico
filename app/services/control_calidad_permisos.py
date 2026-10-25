"""Control de permisos, roles y acreditación jurídica para el Centro de Calidad Jurídica Continua (Fase 2.3).

Diferencia de manera estricta entre:
1. Administrador técnico: Gestión operativa, sincronización, auditorías automáticas, retiros técnicos preventivos.
2. Auditor documental: Validación de integridad, coherencia de metadatos, supervisión de fragmentos y hashes.
3. Profesional jurídico autorizado / Revisor jurídico humano: Revisión jurídica de fondo, certificación vinculante de providencias,
   resolución de discrepancias sustantivas y confirmación de evolución jurisprudencial.

REGLA DE SEGURIDAD:
El rol de administrador técnico NO equivale automáticamente a una acreditación jurídica profesional.
Toda identidad se extrae criptográficamente del token JWT autenticado por el servidor en Supabase Auth.
"""
from typing import Any, Dict, Optional
from fastapi import HTTPException


LEGAL_PROFESSIONAL_ROLES = frozenset({
    "abogado",
    "relator",
    "magistrado",
    "auditor_juridico",
    "profesional_juridico",
    "revisor_juridico_humana",
    "superadmin",
})

DOCUMENT_AUDITOR_ROLES = frozenset({
    "auditor_documental",
    "relator",
    "abogado",
    "auditor_juridico",
    "admin",
    "superadmin",
})

TECHNICAL_ADMIN_ROLES = frozenset({
    "admin",
    "superadmin",
    "administrador_tecnico",
    "developer",
})


def extract_user_identity(user: Dict[str, Any]) -> Dict[str, Any]:
    """Extrae y normaliza la identidad del usuario desde el payload verificado de Supabase."""
    user_id = str(user.get("id") or "anon")
    email = str(user.get("email") or "")
    meta = user.get("user_metadata") or {}
    app_meta = user.get("app_metadata") or {}

    # Rol extraído de app_metadata (más prioritario) o user_metadata
    raw_role = (
        app_meta.get("role")
        or meta.get("role")
        or user.get("role")
        or "usuario"
    ).lower().strip()

    full_name = (
        meta.get("full_name")
        or meta.get("nombre_completo")
        or meta.get("name")
        or (email.split("@")[0] if email else "Usuario")
    ).strip()

    is_legal = raw_role in LEGAL_PROFESSIONAL_ROLES or bool(meta.get("tarjeta_profesional"))
    is_doc_auditor = raw_role in DOCUMENT_AUDITOR_ROLES
    is_tech_admin = raw_role in TECHNICAL_ADMIN_ROLES

    return {
        "id": user_id,
        "email": email,
        "name": full_name,
        "role": raw_role,
        "is_legal_professional": is_legal,
        "is_document_auditor": is_doc_auditor,
        "is_technical_admin": is_tech_admin,
    }


def require_legal_professional(user: Dict[str, Any], action_description: str = "esta acción jurídica") -> Dict[str, Any]:
    """Exige rol de profesional jurídico acreditado. Rechaza con HTTP 403 Forbidden si no lo posee."""
    identity = extract_user_identity(user)
    if not identity["is_legal_professional"]:
        raise HTTPException(
            status_code=403,
            detail=(
                f"Acceso denegado: Se requiere acreditación jurídica profesional (rol 'abogado', 'relator' o 'auditor_juridico') "
                f"para {action_description}. El rol actual es '{identity['role']}'."
            )
        )
    return identity


def require_document_auditor(user: Dict[str, Any], action_description: str = "esta auditoría documental") -> Dict[str, Any]:
    """Exige rol de auditor documental o jurídico."""
    identity = extract_user_identity(user)
    if not (identity["is_document_auditor"] or identity["is_legal_professional"]):
        raise HTTPException(
            status_code=403,
            detail=(
                f"Acceso denegado: Se requiere rol de auditor documental o jurídico "
                f"para {action_description}. El rol actual es '{identity['role']}'."
            )
        )
    return identity


def require_technical_admin(user: Dict[str, Any], action_description: str = "esta gestión técnica") -> Dict[str, Any]:
    """Exige rol de administrador técnico o superadmin."""
    identity = extract_user_identity(user)
    if not identity["is_technical_admin"]:
        raise HTTPException(
            status_code=403,
            detail=(
                f"Acceso denegado: Se requiere rol de administrador técnico "
                f"para {action_description}. El rol actual es '{identity['role']}'."
            )
        )
    return identity
