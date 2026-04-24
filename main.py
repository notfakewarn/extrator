"""Orquestração da extração de contatos do WhatsApp Web."""

from __future__ import annotations

import json
import logging
import logging.handlers
import sys
from datetime import datetime, timezone

import requests

from config import ALERT_WEBHOOK, LOG_PATH
from driver_factory import build_driver
from extractor import UiChangedError, WhatsAppExtractor
from storage import ExtractionStorage
from wait_strategies import WaitStrategies


def setup_logging() -> None:
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s", "%Y-%m-%d %H:%M:%S"
    )

    root = logging.getLogger()
    root.setLevel(logging.INFO)

    file_handler = logging.handlers.RotatingFileHandler(
        LOG_PATH, maxBytes=5_000_000, backupCount=5, encoding="utf-8"
    )
    file_handler.setFormatter(formatter)

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(formatter)

    root.handlers.clear()
    root.addHandler(file_handler)
    root.addHandler(stream_handler)


def send_alert(payload: dict) -> None:
    if not ALERT_WEBHOOK:
        logging.info("Webhook de alerta não configurado. Payload: %s", payload)
        return

    # Reuso da estratégia de retry/backoff para rede.
    def _send() -> requests.Response:
        resp = requests.post(ALERT_WEBHOOK, json=payload, timeout=15)
        resp.raise_for_status()
        return resp

    wait = WaitStrategies(driver=None)  # type: ignore[arg-type]
    wait.retry_with_backoff(_send, "send_alert")


def main() -> int:
    setup_logging()
    logger = logging.getLogger("main")
    storage = ExtractionStorage()

    driver = None
    try:
        driver = build_driver()
        extractor = WhatsAppExtractor(driver, storage)

        extractor.bootstrap()
        group = extractor.open_group()
        stats = extractor.extract_contacts(group)
        storage.finalize_json_export()

        alert_payload = {
            "status": "success",
            "group": group,
            "stats": stats.__dict__,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        send_alert(alert_payload)
        logger.info("Concluído com sucesso: %s", json.dumps(alert_payload, ensure_ascii=False))
        return 0

    except UiChangedError as exc:
        logger.exception("UI do WhatsApp mudou e requer ajuste de seletores: %s", exc)
        send_alert(
            {
                "status": "failure",
                "error_type": "ui_changed",
                "message": str(exc),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )
        return 2

    except Exception as exc:  # noqa: BLE001
        logger.exception("Falha global não tratada: %s", exc)
        send_alert(
            {
                "status": "failure",
                "error_type": type(exc).__name__,
                "message": str(exc),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )
        return 1

    finally:
        if driver is not None:
            driver.quit()


if __name__ == "__main__":
    raise SystemExit(main())
