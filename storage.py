"""Persistência incremental e checkpointing resiliente."""

from __future__ import annotations

import csv
import json
import logging
from pathlib import Path
from typing import Any

from config import CHECKPOINT_PATH, CHECKPOINT_EVERY, CSV_PATH, JSON_EXPORT_PATH, JSONL_PATH


LOGGER = logging.getLogger(__name__)


class ExtractionStorage:
    def __init__(self) -> None:
        self.csv_path = Path(CSV_PATH)
        self.jsonl_path = Path(JSONL_PATH)
        self.checkpoint_path = Path(CHECKPOINT_PATH)
        self.json_export_path = Path(JSON_EXPORT_PATH)
        self._counter = 0
        self._seen_keys: set[str] = set()
        self._init_seen_keys()
        self._ensure_csv_header()

    def _init_seen_keys(self) -> None:
        if not self.csv_path.exists():
            return
        with self.csv_path.open("r", newline="", encoding="utf-8") as file:
            reader = csv.DictReader(file)
            for row in reader:
                key = self._contact_key(row.get("name", ""), row.get("phone", ""))
                self._seen_keys.add(key)
        LOGGER.info("Carregados %s registros já existentes (deduplicação).", len(self._seen_keys))

    def _ensure_csv_header(self) -> None:
        if self.csv_path.exists() and self.csv_path.stat().st_size > 0:
            return
        with self.csv_path.open("w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=["name", "phone", "source_group", "extracted_at"])
            writer.writeheader()
            file.flush()

    @staticmethod
    def _contact_key(name: str, phone: str) -> str:
        return f"{name.strip().lower()}::{phone.strip()}"

    def append_contact(self, contact: dict[str, Any], checkpoint_payload: dict[str, Any] | None = None) -> bool:
        key = self._contact_key(str(contact.get("name", "")), str(contact.get("phone", "")))
        if key in self._seen_keys:
            return False

        self._append_csv(contact)
        self._append_jsonl(contact)
        self._seen_keys.add(key)

        self._counter += 1
        if checkpoint_payload and self._counter % CHECKPOINT_EVERY == 0:
            self.save_checkpoint(checkpoint_payload)
        return True

    def _append_csv(self, contact: dict[str, Any]) -> None:
        with self.csv_path.open("a", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=["name", "phone", "source_group", "extracted_at"])
            writer.writerow(contact)
            file.flush()

    def _append_jsonl(self, contact: dict[str, Any]) -> None:
        with self.jsonl_path.open("a", encoding="utf-8") as file:
            file.write(json.dumps(contact, ensure_ascii=False) + "\n")
            file.flush()

    def save_checkpoint(self, payload: dict[str, Any]) -> None:
        tmp_file = self.checkpoint_path.with_suffix(".tmp")
        with tmp_file.open("w", encoding="utf-8") as file:
            json.dump(payload, file, ensure_ascii=False, indent=2)
            file.flush()
        tmp_file.replace(self.checkpoint_path)
        LOGGER.debug("Checkpoint salvo em %s", self.checkpoint_path)

    def load_checkpoint(self) -> dict[str, Any]:
        if not self.checkpoint_path.exists():
            return {"last_scroll_top": 0, "processed": 0, "finished": False}
        with self.checkpoint_path.open("r", encoding="utf-8") as file:
            return json.load(file)

    def finalize_json_export(self) -> None:
        if not self.jsonl_path.exists():
            LOGGER.warning("Nenhum JSONL encontrado para exportação consolidada.")
            return

        records: list[dict[str, Any]] = []
        with self.jsonl_path.open("r", encoding="utf-8") as file:
            for line in file:
                line = line.strip()
                if not line:
                    continue
                records.append(json.loads(line))

        tmp_file = self.json_export_path.with_suffix(".tmp")
        with tmp_file.open("w", encoding="utf-8") as file:
            json.dump(records, file, ensure_ascii=False, indent=2)
            file.flush()
        tmp_file.replace(self.json_export_path)
        LOGGER.info("Exportação consolidada JSON criada em %s", self.json_export_path)
