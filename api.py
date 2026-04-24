"""API e interface web para visualização e exportação de leads."""

from __future__ import annotations

import csv
import io
from dataclasses import asdict
from datetime import datetime, timezone

from fastapi import FastAPI, Query, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from leads_repository import filter_leads, read_leads

app = FastAPI(title="Lead Viewer API", version="1.0.0")
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


@app.get("/", response_class=HTMLResponse)
def index(request: Request) -> HTMLResponse:
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/leads")
def list_leads(
    origem: str | None = Query(default=None),
    start_date: str | None = Query(default=None, description="ISO date/time"),
    end_date: str | None = Query(default=None, description="ISO date/time"),
    status: str | None = Query(default=None),
    tag: str | None = Query(default=None),
    limit: int = Query(default=1000, ge=1, le=5000),
):
    leads = read_leads()
    filtered = filter_leads(
        leads,
        origem=origem,
        start_date=start_date,
        end_date=end_date,
        status=status,
        tag=tag,
    )
    items = [asdict(item) for item in filtered[:limit]]
    return {
        "count": len(items),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "items": items,
    }


@app.get("/export")
def export_csv(
    origem: str | None = Query(default=None),
    start_date: str | None = Query(default=None),
    end_date: str | None = Query(default=None),
    status: str | None = Query(default=None),
    tag: str | None = Query(default=None),
):
    leads = read_leads()
    filtered = filter_leads(
        leads,
        origem=origem,
        start_date=start_date,
        end_date=end_date,
        status=status,
        tag=tag,
    )

    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=["nome", "telefone", "origem", "data", "status", "tag"])
    writer.writeheader()
    for lead in filtered:
        writer.writerow(asdict(lead))

    payload = io.BytesIO(buffer.getvalue().encode("utf-8"))
    filename = f"leads_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

    return StreamingResponse(
        payload,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
