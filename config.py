"""Configurações centrais da aplicação.

Este módulo centraliza variáveis de ambiente, seletores e constantes de timing/retry
para facilitar manutenção após mudanças na UI do WhatsApp Web.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Timeouts:
    short: int = int(os.getenv("WA_TIMEOUT_SHORT", "5"))
    medium: int = int(os.getenv("WA_TIMEOUT_MEDIUM", "20"))
    long: int = int(os.getenv("WA_TIMEOUT_LONG", "60"))
    page_load: int = int(os.getenv("WA_PAGELOAD_TIMEOUT", "90"))


@dataclass(frozen=True)
class RetryPolicy:
    attempts: int = int(os.getenv("WA_RETRY_ATTEMPTS", "5"))
    base_delay: float = float(os.getenv("WA_RETRY_BASE_DELAY", "0.8"))
    max_delay: float = float(os.getenv("WA_RETRY_MAX_DELAY", "8.0"))
    backoff_factor: float = float(os.getenv("WA_RETRY_FACTOR", "2.0"))
    jitter: float = float(os.getenv("WA_RETRY_JITTER", "0.25"))


BASE_DIR = Path(os.getenv("WA_BASE_DIR", Path.cwd()))
DATA_DIR = Path(os.getenv("WA_DATA_DIR", BASE_DIR / "data"))
LOG_DIR = Path(os.getenv("WA_LOG_DIR", BASE_DIR / "logs"))
PROFILE_DIR = Path(os.getenv("WA_PROFILE_DIR", BASE_DIR / ".chrome_profile"))

DATA_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)
PROFILE_DIR.mkdir(parents=True, exist_ok=True)

WHATSAPP_WEB_URL = os.getenv("WA_WEB_URL", "https://web.whatsapp.com/")
TARGET_GROUP_NAME = os.getenv("WA_TARGET_GROUP", "")
RUN_HEADLESS = os.getenv("WA_HEADLESS", "false").lower() == "true"
SCROLL_PAUSE_SEC = float(os.getenv("WA_SCROLL_PAUSE_SEC", "0.8"))
NO_PROGRESS_LIMIT = int(os.getenv("WA_NO_PROGRESS_LIMIT", "6"))
CHECKPOINT_EVERY = int(os.getenv("WA_CHECKPOINT_EVERY", "10"))

TIMEOUTS = Timeouts()
RETRY = RetryPolicy()

PHONE_REGEX = r"^\+[1-9]\d{7,14}$"

# Evitar classes ofuscadas. Priorizamos data-* / aria-* / hierarquia semântica.
SELECTORS = {
    "search_box": "div[contenteditable='true'][role='textbox'][data-tab='3']",
    "chat_list_item_by_title": "span[title='{title}']",
    "chat_header": "header",
    "group_info_button": "header [aria-label*='Dados do grupo'], header [title*='Dados do grupo']",
    "participants_panel": "div[role='dialog'], div[aria-label*='Participantes']",
    "participants_rows": "div[role='listitem']",
    "participant_name": "span[dir='auto'][title]",
    "participant_subtitle": "span[dir='ltr'], span[title^='+']",
    "qr_canvas": "canvas[aria-label*='QR'], canvas",
    "offline_banner": "div[role='alert']",
    "banned_message": "div[role='dialog']",
}

CSV_PATH = DATA_DIR / "contacts.csv"
JSONL_PATH = DATA_DIR / "contacts.jsonl"
JSON_EXPORT_PATH = DATA_DIR / "contacts.json"
CHECKPOINT_PATH = DATA_DIR / "checkpoint.json"
LOG_PATH = LOG_DIR / "extractor.log"

ALERT_WEBHOOK = os.getenv("WA_ALERT_WEBHOOK", "").strip()
USER_AGENT = os.getenv(
    "WA_USER_AGENT",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
)
