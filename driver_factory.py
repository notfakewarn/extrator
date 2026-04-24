"""Fábrica de WebDriver com persistência de sessão e logs robustos."""

from __future__ import annotations

import logging
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

from config import PROFILE_DIR, RUN_HEADLESS, TIMEOUTS, USER_AGENT


LOGGER = logging.getLogger(__name__)


def _chrome_profile_args(profile_dir: Path) -> list[str]:
    return [
        f"--user-data-dir={profile_dir}",
        "--profile-directory=Default",
    ]


def build_driver() -> webdriver.Chrome:
    """Inicializa Chrome com webdriver-manager e perfil persistente.

    Retorna:
        webdriver.Chrome pronto para uso em extração.
    """

    options = Options()
    options.add_argument(f"--user-agent={USER_AGENT}")
    options.add_argument("--lang=pt-BR")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1400,1000")
    options.add_argument("--log-level=0")

    for arg in _chrome_profile_args(PROFILE_DIR):
        options.add_argument(arg)

    if RUN_HEADLESS:
        options.add_argument("--headless=new")

    # Logs de performance e browser para troubleshooting de produção.
    options.set_capability("goog:loggingPrefs", {"browser": "ALL", "performance": "ALL"})

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    driver.set_page_load_timeout(TIMEOUTS.page_load)

    LOGGER.info("Chrome iniciado com perfil persistente em %s", PROFILE_DIR)
    return driver
