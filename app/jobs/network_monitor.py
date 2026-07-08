"""
network_monitor.py — Cron job diario de Mi Red (Conflict Zero)

Recorre todos los RUCs en network_watchlist, los re-verifica,
detecta cambios de score/estado, crea registros en network_alerts
y envía un email de resumen al usuario propietario.

Uso:
    python -m app.jobs.network_monitor

Cron (Render / Railway / servidor propio):
    0 6 * * * cd /app && python -m app.jobs.network_monitor >> /var/log/network_monitor.log 2>&1
"""
import logging
import sys
from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Any

from app.core.database import SessionLocal
from app.models import User, NetworkWatchlist, NetworkAlert
from app.services.verification import verification_service
from app.services.email_service import email_service, UHNW_COLORS

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [network_monitor] %(levelname)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)


# ─── Email ────────────────────────────────────────────────────────────────────

def _build_alert_email(user: User, changes: List[Dict[str, Any]]) -> str:
    """Genera el HTML del resumen de cambios para un usuario."""

    rows_html = ""
    for c in changes:
        if c["alert_type"] == "score_change":
            label = "Score"
            old_val = f"{c['old']} pts" if c["old"] else "—"
            new_val = f"{c['new']} pts"
            # Rojo si bajó, dorado si subió
            try:
                color = "#8B0000" if int(c["new"]) < int(c["old"] or 0) else UHNW_COLORS["gold"]
            except (ValueError, TypeError):
                color = UHNW_COLORS["gold"]
        else:
            label = "Estado"
            old_val = c["old"] or "—"
            new_val = c["new"] or "—"
            color = "#B87333" if new_val in ("INHABILITADO", "SUSPENDIDO", "BAJA") else UHNW_COLORS["gold"]

        rows_html += f"""
        <div class="info-box" style="margin-bottom:10px;">
            <div class="info-label">{c['alias']} — RUC {c['ruc']} — {label}</div>
            <div class="info-value">
                <span style="color:{UHNW_COLORS['light_gray']};text-decoration:line-through;">{old_val}</span>
                &nbsp;→&nbsp;
                <span style="color:{color};font-weight:600;">{new_val}</span>
            </div>
        </div>
        """

    content = f"""
    <div class="title">Cambios en Tu Red de Proveedores</div>

    <div class="text">
        Estimado/a <strong>{user.full_name}</strong>,<br><br>
        Durante la verificación diaria de tu red detectamos
        <strong>{len(changes)} cambio(s)</strong> en tus proveedores monitoreados.
    </div>

    <div class="divider"></div>

    {rows_html}

    <div class="divider"></div>

    <div class="text">
        Revisa el detalle completo en tu dashboard:
    </div>

    <a href="https://czperu.com/red.html" class="cta-button">Ver Mi Red</a>

    <div class="text" style="margin-top:24px;font-size:12px;color:{UHNW_COLORS['light_gray']};">
        Este email fue generado automáticamente el {datetime.utcnow().strftime('%d/%m/%Y')} a las
        {datetime.utcnow().strftime('%H:%M')} UTC.
        Si no deseas recibir estas alertas, desactiva el monitoreo desde tu dashboard.
    </div>
    """

    return email_service._get_base_template(content, "Alertas de Tu Red — Conflict Zero")


def _send_alert_email(user: User, changes: List[Dict[str, Any]]) -> bool:
    html = _build_alert_email(user, changes)
    result = email_service._send_email(
        to_email=user.email,
        subject=f"⚠ {len(changes)} cambio(s) en tu red de proveedores — Conflict Zero",
        html_content=html,
    )
    return result.get("success", False)


# ─── Core ─────────────────────────────────────────────────────────────────────

def run() -> Dict[str, Any]:
    """
    Punto de entrada del cron job.
    Devuelve un dict con el resumen de ejecución.
    """
    db = SessionLocal()
    stats = {
        "started_at": datetime.utcnow().isoformat(),
        "total_entries": 0,
        "total_users": 0,
        "alerts_created": 0,
        "emails_sent": 0,
        "errors": [],
    }

    try:
        # Usamos el usuario admin para las verificaciones (no consume cuota de usuarios)
        admin_user = db.query(User).filter(User.is_admin == True).first()  # noqa: E712
        if not admin_user:
            log.error("No se encontró usuario admin. Abortando.")
            stats["errors"].append("admin_user_not_found")
            return stats

        entries = db.query(NetworkWatchlist).all()
        stats["total_entries"] = len(entries)
        log.info(f"Procesando {len(entries)} entradas en watchlist...")

        # Agrupar cambios por usuario para enviar un solo email por usuario
        changes_by_user: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        user_cache: Dict[str, User] = {}

        for entry in entries:
            try:
                result = verification_service.verify_ruc(
                    ruc=entry.ruc,
                    user=admin_user,
                    db=db,
                )
            except Exception as exc:
                log.warning(f"Error verificando RUC {entry.ruc}: {exc}")
                stats["errors"].append({"ruc": entry.ruc, "error": str(exc)})
                continue

            new_score = result.get("score")
            new_status = result.get("sunat_data", {}).get("estado")

            changed = False

            # — Cambio de score —
            if new_score is not None and new_score != entry.last_score:
                alert = NetworkAlert(
                    user_id=entry.user_id,
                    ruc=entry.ruc,
                    alert_type="score_change",
                    old_status=str(entry.last_score) if entry.last_score is not None else None,
                    new_status=str(new_score),
                )
                db.add(alert)
                stats["alerts_created"] += 1
                changes_by_user[entry.user_id].append({
                    "alert_type": "score_change",
                    "ruc": entry.ruc,
                    "alias": entry.alias,
                    "old": str(entry.last_score) if entry.last_score is not None else None,
                    "new": str(new_score),
                })
                changed = True
                log.info(f"Score cambiado — {entry.alias} ({entry.ruc}): {entry.last_score} → {new_score}")

            # — Cambio de estado —
            if new_status and new_status != entry.last_status:
                alert = NetworkAlert(
                    user_id=entry.user_id,
                    ruc=entry.ruc,
                    alert_type="status_change",
                    old_status=entry.last_status,
                    new_status=new_status,
                )
                db.add(alert)
                stats["alerts_created"] += 1
                changes_by_user[entry.user_id].append({
                    "alert_type": "status_change",
                    "ruc": entry.ruc,
                    "alias": entry.alias,
                    "old": entry.last_status,
                    "new": new_status,
                })
                changed = True
                log.info(f"Estado cambiado — {entry.alias} ({entry.ruc}): {entry.last_status} → {new_status}")

            # Actualizar snapshot en watchlist
            if changed or entry.last_score is None:
                entry.last_score = new_score
                entry.last_status = new_status

            # Cachear usuario para no hacer N queries
            if entry.user_id not in user_cache:
                owner = db.query(User).filter(User.id == entry.user_id).first()
                if owner:
                    user_cache[entry.user_id] = owner

        db.commit()

        # — Enviar emails de resumen, uno por usuario —
        stats["total_users"] = len(changes_by_user)
        for user_id, changes in changes_by_user.items():
            owner = user_cache.get(user_id)
            if not owner:
                log.warning(f"Usuario {user_id} no encontrado para enviar email.")
                continue
            try:
                sent = _send_alert_email(owner, changes)
                if sent:
                    stats["emails_sent"] += 1
                    log.info(f"Email enviado a {owner.email} ({len(changes)} cambios)")
                else:
                    log.warning(f"Falló el envío de email a {owner.email}")
            except Exception as exc:
                log.error(f"Error enviando email a {owner.email}: {exc}")
                stats["errors"].append({"user_email": owner.email, "error": str(exc)})

    finally:
        db.close()

    stats["finished_at"] = datetime.utcnow().isoformat()
    log.info(
        f"Finalizado — entradas: {stats['total_entries']}, "
        f"alertas: {stats['alerts_created']}, "
        f"emails: {stats['emails_sent']}, "
        f"errores: {len(stats['errors'])}"
    )
    return stats


if __name__ == "__main__":
    result = run()
    if result["errors"]:
        sys.exit(1)
    sys.exit(0)
