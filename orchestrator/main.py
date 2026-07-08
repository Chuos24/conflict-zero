#!/usr/bin/env python3
"""
ConflictZero Orchestrator
Corre en background en Mac y coordina todo el sistema automáticamente.
"""

import hashlib
import os
import re
import sys
import time
import logging
import datetime
import subprocess
from pathlib import Path
from zoneinfo import ZoneInfo

import requests
import schedule

# ─── Paths ────────────────────────────────────────────────────────────────────
BASE_DIR    = Path.home() / "ConflictZero"
REPORTES    = BASE_DIR / "reportes"
LOG_FILE    = REPORTES / "orchestrator.log"
UPTIME_LOG  = REPORTES / "uptime.log"

REPOS = [
    BASE_DIR / "app",              # repo principal (conflict-zero)
    BASE_DIR / "landing",          # landing page
    BASE_DIR / "backend",          # backend
]

# ai-inbox — carpeta de intercambio con Kimi (dentro del repo app)
AI_INBOX_DIR    = BASE_DIR / "app" / "ai-inbox"
PARA_CLAUDE_MD  = AI_INBOX_DIR / "para-claude.md"
PARA_KIMI_MD    = AI_INBOX_DIR / "para-kimi.md"
INBOX_SEEN_FILE = REPORTES / "ai-inbox-last-seen.txt"   # hash del último mensaje leído

# ─── Timezone ─────────────────────────────────────────────────────────────────
LIMA = ZoneInfo("America/Lima")

# ─── Env vars ─────────────────────────────────────────────────────────────────
RENDER_API_KEY   = os.environ.get("RENDER_API_KEY", "")
SENDGRID_API_KEY = os.environ.get("SENDGRID_API_KEY", "")
GITHUB_TOKEN     = os.environ.get("GITHUB_TOKEN", "")
NOTION_TOKEN     = os.environ.get("NOTION_TOKEN", "")
NOTION_DB_ID     = os.environ.get("NOTION_DB_ID", "")   # DB de tareas
ALERT_EMAIL_TO   = os.environ.get("ALERT_EMAIL_TO", "")
ALERT_EMAIL_FROM = os.environ.get("ALERT_EMAIL_FROM", "orchestrator@conflictzero.com")
GITHUB_REPO      = os.environ.get("GITHUB_REPO", "Chuos24/conflict-zero")
HEALTH_URL       = "https://conflict-zero-api.onrender.com/api/v1/health"

# ─── Logging ──────────────────────────────────────────────────────────────────
REPORTES.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("orchestrator")

# ─── State ────────────────────────────────────────────────────────────────────
consecutive_health_failures = 0


# ══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def today_report_path() -> Path:
    date_str = datetime.datetime.now(LIMA).strftime("%Y-%m-%d")
    return REPORTES / f"{date_str}.md"


def append_to_report(section: str, content: str):
    path = today_report_path()
    with open(path, "a", encoding="utf-8") as f:
        f.write(f"\n## {section}\n")
        f.write(content.strip())
        f.write("\n")


def send_email(subject: str, body: str):
    if not SENDGRID_API_KEY or not ALERT_EMAIL_TO:
        log.warning("SendGrid no configurado — email no enviado: %s", subject)
        return
    payload = {
        "personalizations": [{"to": [{"email": ALERT_EMAIL_TO}]}],
        "from": {"email": ALERT_EMAIL_FROM},
        "subject": subject,
        "content": [{"type": "text/plain", "value": body}],
    }
    try:
        r = requests.post(
            "https://api.sendgrid.com/v3/mail/send",
            json=payload,
            headers={"Authorization": f"Bearer {SENDGRID_API_KEY}"},
            timeout=15,
        )
        if r.status_code in (200, 202):
            log.info("Email enviado: %s", subject)
        else:
            log.error("Error SendGrid %s: %s", r.status_code, r.text[:200])
    except Exception as e:
        log.error("Excepción enviando email: %s", e)


# ══════════════════════════════════════════════════════════════════════════════
# 1. MORNING BRIEFING — 7am Lima
# ══════════════════════════════════════════════════════════════════════════════

def get_render_status() -> str:
    if not RENDER_API_KEY:
        return "_RENDER_API_KEY no configurado_"
    try:
        r = requests.get(
            "https://api.render.com/v1/services",
            headers={"Authorization": f"Bearer {RENDER_API_KEY}"},
            timeout=15,
        )
        r.raise_for_status()
        services = r.json()
        lines = []
        for svc in services:
            name   = svc.get("service", {}).get("name", "?")
            status = svc.get("service", {}).get("suspended", "unknown")
            lines.append(f"- **{name}**: {'suspendido' if status == 'suspended' else 'activo'}")
        return "\n".join(lines) if lines else "_Sin servicios encontrados_"
    except Exception as e:
        log.error("Render API error: %s", e)
        return f"_Error consultando Render: {e}_"


def get_github_commits() -> str:
    if not GITHUB_TOKEN:
        return "_GITHUB_TOKEN no configurado_"
    since = (datetime.datetime.utcnow() - datetime.timedelta(hours=24)).isoformat() + "Z"
    try:
        r = requests.get(
            f"https://api.github.com/repos/{GITHUB_REPO}/commits",
            params={"since": since, "per_page": 20},
            headers={"Authorization": f"token {GITHUB_TOKEN}"},
            timeout=15,
        )
        r.raise_for_status()
        commits = r.json()
        if not commits:
            return "_Sin commits en las últimas 24h_"
        lines = []
        for c in commits:
            sha    = c["sha"][:7]
            msg    = c["commit"]["message"].split("\n")[0]
            author = c["commit"]["author"]["name"]
            date   = c["commit"]["author"]["date"][:10]
            lines.append(f"- `{sha}` [{date}] **{author}**: {msg}")
        return "\n".join(lines)
    except Exception as e:
        log.error("GitHub API error: %s", e)
        return f"_Error consultando GitHub: {e}_"


def get_notion_tasks() -> str:
    if not NOTION_TOKEN or not NOTION_DB_ID:
        return "_NOTION_TOKEN / NOTION_DB_ID no configurados_"
    today = datetime.datetime.now(LIMA).strftime("%Y-%m-%d")
    payload = {
        "filter": {
            "and": [
                {"property": "Status", "select": {"does_not_equal": "Done"}},
            ]
        },
        "page_size": 20,
    }
    try:
        r = requests.post(
            f"https://api.notion.com/v1/databases/{NOTION_DB_ID}/query",
            json=payload,
            headers={
                "Authorization": f"Bearer {NOTION_TOKEN}",
                "Notion-Version": "2022-06-28",
            },
            timeout=15,
        )
        r.raise_for_status()
        results = r.json().get("results", [])
        if not results:
            return "_Sin tareas pendientes_"
        lines = []
        for page in results:
            props = page.get("properties", {})
            # Intenta leer la propiedad "Name" o "Título"
            name_prop = props.get("Name") or props.get("Título") or props.get("title") or {}
            title_arr = (
                name_prop.get("title")
                or name_prop.get("rich_text")
                or []
            )
            title = "".join(t.get("plain_text", "") for t in title_arr) or "Sin título"
            status = (
                (props.get("Status") or {}).get("select") or {}
            ).get("name", "?")
            lines.append(f"- [{status}] {title}")
        return "\n".join(lines)
    except Exception as e:
        log.error("Notion API error: %s", e)
        return f"_Error consultando Notion: {e}_"


def morning_briefing():
    log.info("=== MORNING BRIEFING ===")
    now = datetime.datetime.now(LIMA).strftime("%Y-%m-%d %H:%M")
    path = today_report_path()

    # Inicializa el reporte del día
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"# Reporte ConflictZero — {now} (Lima)\n")
        f.write(f"\nGenerado automáticamente por el orquestador.\n")

    render_status  = get_render_status()
    github_commits = get_github_commits()
    notion_tasks   = get_notion_tasks()

    append_to_report("Render — Estado de servicios", render_status)
    append_to_report("GitHub — Commits últimas 24h", github_commits)
    append_to_report("Notion — Tareas pendientes", notion_tasks)

    log.info("Morning briefing escrito en %s", path)


# ══════════════════════════════════════════════════════════════════════════════
# 2. MONITOR DE SALUD — cada 30 minutos
# ══════════════════════════════════════════════════════════════════════════════

def health_check():
    global consecutive_health_failures
    now = datetime.datetime.now(LIMA).strftime("%Y-%m-%d %H:%M:%S")
    try:
        r = requests.get(HEALTH_URL, timeout=10)
        ok = r.status_code == 200
    except Exception as e:
        log.warning("Health check excepción: %s", e)
        ok = False

    status = "UP" if ok else "DOWN"
    with open(UPTIME_LOG, "a", encoding="utf-8") as f:
        f.write(f"{now} | {status}\n")

    if ok:
        log.info("Health check: UP")
        consecutive_health_failures = 0
    else:
        consecutive_health_failures += 1
        log.warning("Health check: DOWN (falla #%d)", consecutive_health_failures)
        if consecutive_health_failures >= 2:
            log.error("2 fallos consecutivos — enviando alerta")
            send_email(
                subject="[ConflictZero] ALERTA: API caída",
                body=(
                    f"El endpoint {HEALTH_URL} ha fallado {consecutive_health_failures} "
                    f"veces consecutivas.\n\nÚltima revisión: {now}\n\n"
                    "Revisar Render dashboard."
                ),
            )


# ══════════════════════════════════════════════════════════════════════════════
# 3. SYNC DE CÓDIGO — cada hora
# ══════════════════════════════════════════════════════════════════════════════

def git_pull_repo(repo_path: Path) -> tuple[bool, str]:
    """Hace git pull. Retorna (hubo_cambios, output)."""
    try:
        result = subprocess.run(
            ["git", "pull", "--ff-only"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=60,
        )
        output = result.stdout.strip() + result.stderr.strip()
        hubo_cambios = "Already up to date" not in output and result.returncode == 0
        return hubo_cambios, output
    except subprocess.TimeoutExpired:
        return False, "timeout"
    except Exception as e:
        return False, str(e)


def code_sync():
    log.info("=== CODE SYNC ===")
    cambios_kimi = []

    for repo in REPOS:
        if not repo.exists():
            log.warning("Repo no existe: %s", repo)
            continue
        if not (repo / ".git").exists():
            log.warning("No es un repo git: %s", repo)
            continue
        hubo_cambios, output = git_pull_repo(repo)
        log.info("git pull %s → %s", repo.name, output[:80])

        if hubo_cambios:
            # Detecta commits de Kimi en el output o en git log reciente
            try:
                log_result = subprocess.run(
                    ["git", "log", "--oneline", "-10", "--author=Kimi"],
                    cwd=repo,
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                if log_result.stdout.strip():
                    cambios_kimi.append(f"**{repo.name}**:\n{log_result.stdout.strip()}")
            except Exception:
                pass

        # Después de actualizar el repo principal, revisa ai-inbox/para-claude.md
        if repo == BASE_DIR / "app":
            check_ai_inbox()

    if cambios_kimi:
        seccion = "Commits de Kimi (sync horario)\n" + "\n".join(cambios_kimi)
        append_to_report("Code Sync — Cambios de Kimi", seccion)
        log.info("Registrados cambios de Kimi en el reporte")


# ══════════════════════════════════════════════════════════════════════════════
# 4. REPORTE NOCTURNO — 9pm Lima
# ══════════════════════════════════════════════════════════════════════════════

def calcular_uptime_hoy() -> str:
    today = datetime.datetime.now(LIMA).strftime("%Y-%m-%d")
    if not UPTIME_LOG.exists():
        return "Sin datos de uptime"
    lines = [l for l in UPTIME_LOG.read_text().splitlines() if today in l]
    if not lines:
        return "Sin registros de hoy"
    total  = len(lines)
    ups    = sum(1 for l in lines if "| UP" in l)
    pct    = round(ups / total * 100, 1) if total else 0
    return f"{ups}/{total} checks OK ({pct}%)"


def evening_report():
    log.info("=== REPORTE NOCTURNO ===")
    now    = datetime.datetime.now(LIMA).strftime("%Y-%m-%d %H:%M")
    uptime = calcular_uptime_hoy()

    # Cuenta commits del día
    commits_hoy = get_github_commits()
    n_commits   = commits_hoy.count("\n- ") + (1 if commits_hoy.startswith("- ") else 0)

    # Tareas notion completadas hoy (status=Done)
    tareas_done = "_no disponible_"
    if NOTION_TOKEN and NOTION_DB_ID:
        try:
            payload = {
                "filter": {"property": "Status", "select": {"equals": "Done"}},
                "page_size": 20,
            }
            r = requests.post(
                f"https://api.notion.com/v1/databases/{NOTION_DB_ID}/query",
                json=payload,
                headers={
                    "Authorization": f"Bearer {NOTION_TOKEN}",
                    "Notion-Version": "2022-06-28",
                },
                timeout=15,
            )
            r.raise_for_status()
            count = len(r.json().get("results", []))
            tareas_done = f"{count} tareas marcadas como Done"
        except Exception as e:
            tareas_done = f"Error Notion: {e}"

    resumen = (
        f"REPORTE NOCTURNO — {now} (Lima)\n"
        f"{'='*45}\n\n"
        f"Uptime API:        {uptime}\n"
        f"Commits GitHub:    {n_commits} en las últimas 24h\n"
        f"Tareas Notion:     {tareas_done}\n\n"
        f"Reporte completo: {today_report_path()}\n"
    )

    append_to_report("Resumen Nocturno", resumen)
    log.info("Reporte nocturno completado")

    send_email(
        subject=f"[ConflictZero] Resumen del día {now[:10]}",
        body=resumen,
    )


# ══════════════════════════════════════════════════════════════════════════════
# 5. AI-INBOX — Coordinación con Kimi (cada hora, junto al code sync)
# ══════════════════════════════════════════════════════════════════════════════

def _file_hash(path: Path) -> str:
    """SHA-1 de las primeras 4KB del archivo (suficiente para detectar cambios)."""
    if not path.exists():
        return ""
    return hashlib.sha1(path.read_bytes()[:4096]).hexdigest()


def _last_seen_hash() -> str:
    if not INBOX_SEEN_FILE.exists():
        return ""
    return INBOX_SEEN_FILE.read_text().strip()


def _save_seen_hash(h: str):
    INBOX_SEEN_FILE.write_text(h)


def _next_task_number() -> str:
    """Genera el siguiente número de tarea basándose en para-kimi.md actual."""
    if not PARA_KIMI_MD.exists():
        return "TAREA-002"
    content = PARA_KIMI_MD.read_text()
    nums = re.findall(r"TAREA-(\d+)", content)
    if nums:
        last = max(int(n) for n in nums)
        return f"TAREA-{last + 1:03d}"
    return "TAREA-002"


def _build_next_instructions() -> str:
    """
    Genera las próximas instrucciones para Kimi basándose en el estado del sistema.
    Si la API está caída → pide diagnóstico. Si todo OK → tarea de mantenimiento.
    """
    now = datetime.datetime.now(LIMA).strftime("%Y-%m-%d %H:%M")
    task_num = _next_task_number()

    # Determina prioridad según salud de la API
    if consecutive_health_failures >= 1:
        prioridad = "Alta"
        tarea = (
            f"La API ha fallado {consecutive_health_failures} vez/veces recientemente.\n"
            "Por favor:\n"
            "1. Verifica el estado del servicio en Render\n"
            "2. Revisa los últimos logs de error\n"
            "3. Confirma si el endpoint /api/v1/health responde\n"
            "4. Si detectas el problema, describe la causa raíz"
        )
    else:
        prioridad = "Baja"
        tarea = (
            "Sistema saludable. Tarea de mantenimiento:\n"
            "1. Verifica que /api/v3/network/ sigue respondiendo correctamente\n"
            "2. Revisa si hay errores en los logs de las últimas 2 horas\n"
            "3. Confirma el uso de memoria/CPU del proceso principal"
        )

    return (
        f"# {task_num}\n"
        f"**Fecha:** {now}\n"
        f"**De:** Claude (orquestador automático)\n"
        f"**Para:** Kimi\n"
        f"**Prioridad:** {prioridad}\n\n"
        f"{tarea}\n\n"
        f"Escribe el resultado en para-claude.md\n"
    )


def _git_commit_push_inbox():
    """Commitea y pushea cambios en ai-inbox al repo app."""
    repo = BASE_DIR / "app"
    try:
        subprocess.run(
            ["git", "add", "ai-inbox/"],
            cwd=repo, capture_output=True, timeout=30
        )
        result = subprocess.run(
            ["git", "commit", "-m", "ai: instrucciones para Kimi (orquestador)"],
            cwd=repo, capture_output=True, text=True, timeout=30
        )
        if "nothing to commit" in result.stdout + result.stderr:
            return  # sin cambios, no pushear
        subprocess.run(
            ["git", "push"],
            cwd=repo, capture_output=True, timeout=60
        )
        log.info("ai-inbox: para-kimi.md pusheado a GitHub")
    except Exception as e:
        log.error("Error commiteando ai-inbox: %s", e)


def check_ai_inbox():
    """
    Lee para-claude.md. Si hay un mensaje nuevo de Kimi:
      - Lo registra en el reporte del día
      - Genera y escribe las próximas instrucciones en para-kimi.md
      - Commitea y pushea
    """
    log.info("=== AI-INBOX CHECK ===")

    if not PARA_CLAUDE_MD.exists():
        log.info("ai-inbox: para-claude.md no existe aún")
        return

    current_hash = _file_hash(PARA_CLAUDE_MD)
    if current_hash == _last_seen_hash():
        log.info("ai-inbox: sin mensajes nuevos de Kimi")
        return

    # Mensaje nuevo detectado
    contenido = PARA_CLAUDE_MD.read_text(encoding="utf-8")
    log.info("ai-inbox: mensaje nuevo de Kimi detectado (%d chars)", len(contenido))

    # Registra en el reporte del día
    now = datetime.datetime.now(LIMA).strftime("%H:%M")
    append_to_report(
        f"AI-Inbox — Respuesta de Kimi ({now})",
        contenido,
    )

    # Marca como leído
    _save_seen_hash(current_hash)

    # Genera próximas instrucciones y las escribe
    next_instructions = _build_next_instructions()
    PARA_KIMI_MD.write_text(next_instructions, encoding="utf-8")
    log.info("ai-inbox: nuevas instrucciones escritas en para-kimi.md")

    # Commitea y pushea
    _git_commit_push_inbox()


# ══════════════════════════════════════════════════════════════════════════════
# SCHEDULER
# ══════════════════════════════════════════════════════════════════════════════

def setup_schedule():
    # Morning briefing 7am Lima = 12:00 UTC
    schedule.every().day.at("07:00").do(morning_briefing)

    # Monitor de salud cada 30 minutos
    schedule.every(30).minutes.do(health_check)

    # Sync de código cada hora (incluye check de ai-inbox tras git pull)
    schedule.every().hour.do(code_sync)

    # Reporte nocturno 9pm Lima
    schedule.every().day.at("21:00").do(evening_report)

    log.info("Schedule configurado (timezone Lima):")
    log.info("  Morning briefing: 07:00")
    log.info("  Health check:     cada 30 min")
    log.info("  Code sync + ai-inbox: cada hora")
    log.info("  Evening report:   21:00")


def main():
    log.info("╔══════════════════════════════════════╗")
    log.info("║  ConflictZero Orchestrator  v1.0     ║")
    log.info("╚══════════════════════════════════════╝")
    log.info("PID: %d", os.getpid())
    log.info("Base dir: %s", BASE_DIR)

    # Verifica vars críticas
    missing = []
    for var in ("RENDER_API_KEY", "SENDGRID_API_KEY", "GITHUB_TOKEN", "NOTION_TOKEN"):
        if not os.environ.get(var):
            missing.append(var)
    if missing:
        log.warning("Vars no configuradas (funcionalidad limitada): %s", ", ".join(missing))

    setup_schedule()

    # Ejecuta checks inmediatos al arrancar
    health_check()
    check_ai_inbox()

    log.info("Orquestador corriendo. Ctrl+C para detener.")
    try:
        while True:
            schedule.run_pending()
            time.sleep(60)
    except KeyboardInterrupt:
        log.info("Orquestador detenido por el usuario.")


if __name__ == "__main__":
    main()
