"""Módulo principal de extração com rolagem inteligente e parsing seguro."""

from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass
from datetime import datetime, timezone

from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement

from config import (
    NO_PROGRESS_LIMIT,
    PHONE_REGEX,
    SCROLL_PAUSE_SEC,
    SELECTORS,
    TARGET_GROUP_NAME,
    TIMEOUTS,
    WHATSAPP_WEB_URL,
)
from storage import ExtractionStorage
from wait_strategies import WaitStrategies


LOGGER = logging.getLogger(__name__)
PHONE_PATTERN = re.compile(PHONE_REGEX)


class UiChangedError(RuntimeError):
    """Erro para cenários de mudança significativa da UI do WhatsApp."""


@dataclass
class ExtractionStats:
    processed_rows: int = 0
    inserted: int = 0
    duplicates: int = 0


class WhatsAppExtractor:
    def __init__(self, driver: WebDriver, storage: ExtractionStorage):
        self.driver = driver
        self.wait = WaitStrategies(driver)
        self.storage = storage
        self.stats = ExtractionStats()

    def _detect_environment_alerts(self) -> None:
        alerts = self.wait.safe_find_elements(SELECTORS["offline_banner"])
        for alert in alerts:
            message = (alert.text or "").lower()
            if "sem conexão" in message or "without internet" in message:
                LOGGER.error("Sem internet detectado no banner do WhatsApp.")
            if "banido" in message or "banned" in message:
                LOGGER.error("Possível conta banida detectada no WhatsApp Web.")

    def bootstrap(self) -> None:
        self.driver.get(WHATSAPP_WEB_URL)
        self._detect_environment_alerts()

        qr_present = self.wait.safe_find_elements(SELECTORS["qr_canvas"])
        if qr_present:
            LOGGER.warning(
                "QR Code detectado. Aguarde login manual (perfil persistente pode não existir ainda)."
            )

        try:
            self.wait.wait_visible(SELECTORS["chat_header"], timeout=TIMEOUTS.long)
        except RuntimeError as exc:
            raise UiChangedError("Não foi possível carregar interface principal do WhatsApp.") from exc

    def open_group(self, group_name: str | None = None) -> str:
        group = group_name or TARGET_GROUP_NAME
        if not group:
            raise ValueError("Informe WA_TARGET_GROUP no .env ou parâmetro em open_group().")

        search_box = self.wait.wait_clickable(SELECTORS["search_box"])
        search_box.click()
        search_box.send_keys(Keys.CONTROL, "a")
        search_box.send_keys(Keys.DELETE)
        search_box.send_keys(group)
        time.sleep(1.2)

        chat_selector = SELECTORS["chat_list_item_by_title"].format(title=group)
        self.wait.wait_clickable(chat_selector).click()
        LOGGER.info("Grupo '%s' aberto com sucesso.", group)
        return group

    def open_participants_panel(self) -> WebElement:
        button = self.wait.wait_clickable(SELECTORS["group_info_button"])
        button.click()
        panel = self.wait.wait_visible(SELECTORS["participants_panel"], timeout=TIMEOUTS.long)
        return panel

    def _extract_phone(self, row: WebElement) -> str | None:
        try:
            subtitle = row.find_element(By.CSS_SELECTOR, SELECTORS["participant_subtitle"]).text.strip()
        except NoSuchElementException:
            subtitle = ""

        if PHONE_PATTERN.match(subtitle):
            return subtitle

        text_fallback = (row.text or "").replace(" ", "")
        for token in text_fallback.split("\n"):
            if PHONE_PATTERN.match(token):
                return token
        return None

    def _parse_contact_row(self, row: WebElement, source_group: str) -> dict | None:
        try:
            name_el = row.find_element(By.CSS_SELECTOR, SELECTORS["participant_name"])
            name = name_el.get_attribute("title") or name_el.text.strip()
        except Exception as exc:  # noqa: BLE001
            LOGGER.debug("Falha ao extrair nome de participante: %s", exc)
            return None

        phone = None
        try:
            phone = self._extract_phone(row)
        except Exception as exc:  # noqa: BLE001
            LOGGER.debug("Falha ao extrair telefone: %s", exc)

        if not phone:
            return None

        return {
            "name": name.strip(),
            "phone": phone,
            "source_group": source_group,
            "extracted_at": datetime.now(timezone.utc).isoformat(),
        }

    def extract_contacts(self, source_group: str) -> ExtractionStats:
        panel = self.open_participants_panel()
        checkpoint = self.storage.load_checkpoint()

        no_progress_rounds = 0
        prev_total = -1

        if checkpoint.get("finished"):
            LOGGER.info("Checkpoint aponta extração concluída anteriormente. Retomada em modo idempotente.")

        while no_progress_rounds < NO_PROGRESS_LIMIT:
            rows = panel.find_elements(By.CSS_SELECTOR, SELECTORS["participants_rows"])
            if not rows:
                LOGGER.warning("Lista de participantes vazia (grupo vazio ou permissão restrita).")
                break

            current_total = len(rows)
            if current_total == prev_total:
                no_progress_rounds += 1
            else:
                no_progress_rounds = 0
                prev_total = current_total

            for row in rows[self.stats.processed_rows :]:
                self.stats.processed_rows += 1
                contact = self._parse_contact_row(row, source_group)
                if not contact:
                    continue

                payload = {
                    "last_scroll_top": self.driver.execute_script("return arguments[0].scrollTop", panel),
                    "processed": self.stats.processed_rows,
                    "finished": False,
                }
                inserted = self.storage.append_contact(contact, checkpoint_payload=payload)
                if inserted:
                    self.stats.inserted += 1
                else:
                    self.stats.duplicates += 1

            # Scroll inteligente: avançar até parar de renderizar novos participantes.
            self.driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", panel)
            time.sleep(SCROLL_PAUSE_SEC)

        self.storage.save_checkpoint(
            {
                "last_scroll_top": self.driver.execute_script("return arguments[0].scrollTop", panel),
                "processed": self.stats.processed_rows,
                "finished": True,
            }
        )
        LOGGER.info(
            "Extração finalizada. processados=%s inseridos=%s duplicados=%s",
            self.stats.processed_rows,
            self.stats.inserted,
            self.stats.duplicates,
        )
        return self.stats
