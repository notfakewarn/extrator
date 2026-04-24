"""Camada de acesso a dados de leads (arquivos em data/)."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable

from config import CSV_PATH


@dataclass
class Lead:
    nome: str
    telefone: str
    origem: str
    data: str
    status: str
    tag: str


def _safe_parse_date(value: str) -> datetime | None:
    value = (value or "").strip()
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _infer_origem(raw: str) -> str:
    raw = (raw or "").strip()
    lowered = raw.lower()
    if not lowered:
        return "desconhecida"
    if "whatsapp" in lowered:
        return "WhatsApp"
    if "site" in lowered:
        return "site"
    if "campanha" in lowered:
        return "campanha"
    return raw


def read_leads(data_file: Path | None = None) -> list[Lead]:
    path = data_file or Path(CSV_PATH)
    if not path.exists():
        return []

    leads: list[Lead] = []
    with path.open("r", encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)
        for row in reader:
            origem = _infer_origem(row.get("origem") or row.get("source_group") or "")
            data = row.get("data") or row.get("extracted_at") or ""
            status = row.get("status") or "novo"
            tag = row.get("tag") or "sem-tag"

            leads.append(
                Lead(
                    nome=(row.get("nome") or row.get("name") or "").strip(),
                    telefone=(row.get("telefone") or row.get("phone") or "").strip(),
                    origem=origem,
                    data=data,
                    status=status,
                    tag=tag,
                )
            )
    return leads


def filter_leads(
    leads: Iterable[Lead],
    origem: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    status: str | None = None,
    tag: str | None = None,
) -> list[Lead]:
    start_dt = _safe_parse_date(start_date or "")
    end_dt = _safe_parse_date(end_date or "")

    results: list[Lead] = []
    for lead in leads:
        if origem and lead.origem.lower() != origem.lower():
            continue
        if status and lead.status.lower() != status.lower():
            continue
        if tag and lead.tag.lower() != tag.lower():
            continue

        lead_dt = _safe_parse_date(lead.data)
        if start_dt and lead_dt and lead_dt < start_dt:
            continue
        if end_dt and lead_dt and lead_dt > end_dt:
            continue

        results.append(lead)

    results.sort(key=lambda item: item.data, reverse=True)
    return results
