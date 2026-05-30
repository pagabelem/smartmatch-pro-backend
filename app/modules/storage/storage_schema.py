from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class FileUploadResponse(BaseModel):
    filename: str = Field(..., description="Nom du fichier stocké (sanitizé)")
    url: str = Field(..., description="URL publique pour accéder au fichier")
    relative_path: str = Field(..., description="Chemin relatif (stocké en BDD)")
    size: int = Field(..., description="Taille en octets")
    content_type: str = Field(..., description="MIME type du fichier")
    created_at: datetime = Field(default_factory=datetime.utcnow)


class FileDeleteResponse(BaseModel):
    filename: str
    relative_path: str
    deleted: bool = True
    message: Optional[str] = None