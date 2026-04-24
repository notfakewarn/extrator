"""Estratégias de espera explícita com retry e exponential backoff."""

from __future__ import annotations

import logging
import random
import time
from typing import Any, Callable

from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from config import RETRY, TIMEOUTS


LOGGER = logging.getLogger(__name__)


class WaitStrategies:
    def __init__(self, driver: WebDriver | None):
        self.driver = driver

    def retry_with_backoff(self, operation: Callable[[], Any], context: str) -> Any:
        """Executa operação com exponential backoff + jitter."""
        delay = RETRY.base_delay
        last_error: Exception | None = None

        for attempt in range(1, RETRY.attempts + 1):
            try:
                return operation()
            except Exception as exc:  # noqa: BLE001 - centralização de robustez
                last_error = exc
                if attempt >= RETRY.attempts:
                    break
                sleep_time = min(delay, RETRY.max_delay) + random.uniform(0, RETRY.jitter)
                LOGGER.warning(
                    "Falha em '%s' (tentativa %s/%s): %s. Repetindo em %.2fs",
                    context,
                    attempt,
                    RETRY.attempts,
                    exc,
                    sleep_time,
                )
                time.sleep(sleep_time)
                delay *= RETRY.backoff_factor

        raise RuntimeError(f"Operação falhou após retries: {context}") from last_error

    def wait_visible(self, css_selector: str, timeout: int = TIMEOUTS.medium) -> WebElement:
        def _op() -> WebElement:
            if self.driver is None:
                raise RuntimeError("Driver não inicializado para wait_visible")
            wait = WebDriverWait(self.driver, timeout)
            return wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, css_selector)))

        return self.retry_with_backoff(_op, f"wait_visible({css_selector})")

    def wait_clickable(self, css_selector: str, timeout: int = TIMEOUTS.medium) -> WebElement:
        def _op() -> WebElement:
            if self.driver is None:
                raise RuntimeError("Driver não inicializado para wait_clickable")
            wait = WebDriverWait(self.driver, timeout)
            return wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, css_selector)))

        return self.retry_with_backoff(_op, f"wait_clickable({css_selector})")

    def safe_find_elements(self, css_selector: str) -> list[WebElement]:
        """Busca segura, retornando lista vazia em Timeout."""
        try:
            if self.driver is None:
                return []
            self.wait_visible(css_selector, timeout=TIMEOUTS.short)
            return self.driver.find_elements(By.CSS_SELECTOR, css_selector)
        except (TimeoutException, RuntimeError):
            return []
