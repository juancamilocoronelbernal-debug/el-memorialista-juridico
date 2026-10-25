"""Control de permisos, roles y acreditación jurídica para el Centro de Calidad Jurídica Continua y Conector Oficial.

Diferencia de manera estricta entre:
1. Administrador técnico: Gestión operativa, sincronización, programación de agenda, reintentos, piloto, retiros técnicos preventivos.
2. Auditor documental: Validación de integridad, coherencia de metadatos, supervisión de fragmentos, bandeja de triage y auditoría.
3. Profesional jurídico autorizado / Revisor jurídico humano: Revisión jurídica de fondo, certificación vinculante de providencias,
   restauración de documentos por subsanación jurídica, resolución de incidencias jurídicas y confirmación de evolución jurisprudencial.

REGLAS DE SEGURIDAD (REMEDIACIÓN EM-02):
- Toda facultad o acreditación se obtiene EXCLUSIVAMENTE desde `app_metadata` controlado por el servidor.
- Se ignora por completo `user_metadata` para roles, permisos o acreditaciones jurídicas.
- La simple presencia de `tarjeta_profesional` (cadena de texto) NO otorga `is_legal_professional`.
- El rol de administrador técnico (`admin`, `superadmin`, `administrador_tecnico`) NO equivale a una acreditación jurídica profesional,
  salvo que el servidor haya registrado explícitamente `app_metadata.acreditacion_juridica_verificada = True`.
- Si existe conflicto o contradicción de roles en la cuenta, ésta queda en estado `pendiente_revision` sin privilegios elevados.
"""
from typing import Any, Dict, Optional, Tuple
from fastapi import HTTPException


LEGAL_PROFESSIONAL_ROLES = frozenset({
    "abogado",
    "abogado_acreditado",
    "relator",
    "magistrado",
    "auditor_juridico",
    "profesional_juridico",
    "revisor_juridico_humana",
})

TECHNICAL_ADMIN_ROLES = frozenset({
    "admin",
    "superadmin",
    "administrador_tecnico",
    "developer",
})

DOCUMENT_AUDITOR_ONLY_ROLES = frozenset({
    "auditor_documental",
    "auditor_calidad",
    "gestor_corpus",
})

DOCUMENT_AUDITOR_ROLES = (
    DOCUMENT_AUDITOR_ONLY_ROLES
    | TECHNICAL_ADMIN_ROLES
    | LEGAL_PROFESSIONAL_ROLES
)

UNPRIVILEGED_ROLES = frozenset({
    "usuario",
    "lector",
    "invitado",
    "ciudadano",
    "asistente",
    "asistente_general",
    "authenticated",
    "anon",
})

PRIVILEGED_ROLES = DOCUMENT_AUDITOR_ROLES


def _detect_role_conflict(user: Dict[str, Any], app_meta: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """Detecta conflictos o contradicciones de roles en los metadatos del servidor (`app_metadata`)."""
    if app_meta.get("role_conflict") is True or app_meta.get("estado_rol") == "pendiente_revision":
        return True, "Cuenta marcada explícitamente con conflicto de rol o pendiente de revisión"

    role_en = str(app_meta.get("role") or "").lower().strip()
    role_es = str(app_meta.get("rol") or "").lower().strip()

    if role_en == "pendiente_revision" or role_es == "pendiente_revision":
        return True, "Rol en estado pendiente_revision"

    if role_en and role_es and role_en != role_es:
        return True, f"Contradicción en app_metadata entre role='{role_en}' y rol='{role_es}'"

    primary_role = role_en or role_es

    raw_roles_list = app_meta.get("roles")
    if isinstance(raw_roles_list, (list, tuple, set)):
        normalized_roles = {str(r).lower().strip() for r in raw_roles_list if str(r).strip()}
        if primary_role:
            normalized_roles.add(primary_role)

        has_unprivileged = bool(normalized_roles & (UNPRIVILEGED_ROLES | {"suspendido", "pendiente_revision"}))
        has_privileged = bool(normalized_roles & PRIVILEGED_ROLES)
        if has_unprivileged and has_privileged:
            return True, "Contradicción entre rol no privilegiado/restringido y rol privilegiado en app_metadata"

        has_tech = bool(normalized_roles & TECHNICAL_ADMIN_ROLES)
        has_legal = bool(normalized_roles & LEGAL_PROFESSIONAL_ROLES)
        if has_tech and has_legal and app_meta.get("acreditacion_juridica_verificada") is not True:
            return True, "Conflicto entre rol técnico y rol jurídico sin acreditación jurídica verificada por el servidor"

    if primary_role in LEGAL_PROFESSIONAL_ROLES and app_meta.get("acreditacion_juridica_verificada") is False:
        return True, "Contradicción entre rol jurídico asignado y acreditacion_juridica_verificada=False"

    if primary_role in TECHNICAL_ADMIN_ROLES and app_meta.get("is_technical_admin") is False:
        return True, "Contradicción entre rol de administrador técnico e is_technical_admin=False"

    perfil_rol = str(user.get("perfil_rol") or "").lower().strip()
    if perfil_rol:
        if perfil_rol in {"suspendido", "pendiente_revision"}:
            return True, f"Perfil en estado '{perfil_rol}'"
        if primary_role in PRIVILEGED_ROLES and perfil_rol in {"lector", "invitado", "ciudadano", "usuario"}:
            return True, f"Contradicción entre rol de servidor '{primary_role}' y perfil '{perfil_rol}'"

    return False, None


def extract_user_identity(user: Dict[str, Any]) -> Dict[str, Any]:
    """Extrae y normaliza la identidad y permisos exclusivamente desde `app_metadata` controlado por el servidor."""
    if not isinstance(user, dict):
        user = {}

    user_id = str(user.get("id") or "anon")
    email = str(user.get("email") or "")
    meta = user.get("user_metadata") if isinstance(user.get("user_metadata"), dict) else {}
    app_meta = user.get("app_metadata") if isinstance(user.get("app_metadata"), dict) else {}

    # Nombre solo para visualización en auditoría (nunca otorga permisos)
    full_name = (
        str(user.get("name") or "")
        or str(meta.get("full_name") or "")
        or str(meta.get("nombre_completo") or "")
        or str(meta.get("nombre") or "")
        or str(meta.get("name") or "")
        or (email.split("@")[0] if email else "Usuario")
    ).strip()

    has_conflict, conflict_reason = _detect_role_conflict(user, app_meta)
    if has_conflict:
        return {
            "id": user_id,
            "email": email,
            "name": full_name,
            "role": "pendiente_revision",
            "role_status": "pendiente_revision",
            "has_role_conflict": True,
            "role_conflict_reason": conflict_reason,
            "is_legal_professional": False,
            "is_document_auditor": False,
            "is_technical_admin": False,
        }

    # SEGURIDAD (EM-02): Rol extraído EXCLUSIVAMENTE de app_metadata controlado por el servidor.
    # Se ignora por completo user_metadata y el campo raíz 'role' ('authenticated') de Supabase Auth.
    raw_role = str(
        app_meta.get("role")
        or app_meta.get("rol")
        or "usuario"
    ).lower().strip()

    if not raw_role or raw_role in {"authenticated", "anon"}:
        raw_role = "usuario"

    # Acreditación jurídica verificada por el servidor (nunca por cadena tarjeta_profesional ni user_metadata)
    explicit_server_legal_accreditation = app_meta.get("acreditacion_juridica_verificada") is True
    is_tech_admin = raw_role in TECHNICAL_ADMIN_ROLES
    is_legal = (raw_role in LEGAL_PROFESSIONAL_ROLES) or explicit_server_legal_accreditation
    is_doc_auditor = (raw_role in DOCUMENT_AUDITOR_ROLES) or is_tech_admin or is_legal

    return {
        "id": user_id,
        "email": email,
        "name": full_name,
        "role": raw_role,
        "role_status": "activo",
        "has_role_conflict": False,
        "role_conflict_reason": None,
        "is_legal_professional": is_legal,
        "is_document_auditor": is_doc_auditor,
        "is_technical_admin": is_tech_admin,
    }


def _ensure_authenticated_and_no_conflict(user: Dict[str, Any], identity: Dict[str, Any], action_description: str) -> None:
    if not user or not user.get("id") or identity["id"] == "anon":
        raise HTTPException(status_code=401, detail="No autenticado.")
    if identity.get("has_role_conflict"):
        raise HTTPException(
            status_code=403,
            detail=(
                f"Acceso denegado para {action_description}: la cuenta se encuentra en estado "
                f"'pendiente_revision' sin privilegios elevados ({identity.get('role_conflict_reason')})."
            ),
        )


def require_legal_professional(user: Dict[str, Any], action_description: str = "esta acción jurídica") -> Dict[str, Any]:
    """Exige rol de profesional jurídico acreditado en `app_metadata`. Rechaza con HTTP 403 si no lo posee."""
    identity = extract_user_identity(user)
    _ensure_authenticated_and_no_conflict(user, identity, action_description)
    if not identity["is_legal_professional"]:
        raise HTTPException(
            status_code=403,
            detail=(
                f"Acceso denegado: Se requiere acreditación jurídica profesional verificada "
                f"(rol 'abogado', 'relator' o 'auditor_juridico') para {action_description}. "
                f"El rol '{identity['role']}' no cuenta con atribuciones jurídicas acreditadas."
            ),
        )
    return identity


def require_document_auditor(user: Dict[str, Any], action_description: str = "esta auditoría documental") -> Dict[str, Any]:
    """Exige rol de auditor documental, administrador técnico o profesional jurídico acreditado."""
    identity = extract_user_identity(user)
    _ensure_authenticated_and_no_conflict(user, identity, action_description)
    if not identity["is_document_auditor"]:
        raise HTTPException(
            status_code=403,
            detail=(
                f"Acceso denegado: Se requiere rol de auditor documental o jurídico "
                f"para {action_description}. El rol actual es '{identity['role']}'."
            ),
        )
    return identity


def require_technical_admin(user: Dict[str, Any], action_description: str = "esta gestión técnica") -> Dict[str, Any]:
    """Exige rol de administrador técnico en `app_metadata`. Rechaza con HTTP 403 si no lo posee."""
    identity = extract_user_identity(user)
    _ensure_authenticated_and_no_conflict(user, identity, action_description)
    if not identity["is_technical_admin"]:
        raise HTTPException(
            status_code=403,
            detail=(
                f"Acceso denegado: Se requiere rol de administrador técnico "
                f"para {action_description}. El rol actual es '{identity['role']}'."
            ),
        )
    return identity

