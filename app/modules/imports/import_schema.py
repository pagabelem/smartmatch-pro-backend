# app/modules/imports/import_schema.py

from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.shared.enums import ImportSource, ImportStatus


# ── Réponse complète ───────────────────────────────────────────────────────────
class ImportResponse(BaseModel):
    id: int
    filename: str
    source: ImportSource
    import_type: str
    status: ImportStatus
    total_rows: int
    imported_rows: int
    failed_rows: int
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── Résumé d'import ────────────────────────────────────────────────────────────
class ImportSummary(BaseModel):
    import_id: int
    filename: str
    import_type: str
    status: str
    total_rows: int
    imported_rows: int
    failed_rows: int
    message: str