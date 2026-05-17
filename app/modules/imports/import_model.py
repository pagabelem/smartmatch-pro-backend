# app/modules/imports/import_model.py

from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import ENUM as PgEnum

from app.database import Base


class Import(Base):
    __tablename__ = "imports"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    filename = Column(String(255), nullable=False)
    source = Column(
        PgEnum('csv', 'json', 'scraper_rekrute', 'scraper_emploidiali',
               'scraper_indeed', 'scraper_linkedin', 'manual',
               name='importsource', create_type=False),
        nullable=False, default='csv',
    )
    import_type = Column(String(50), nullable=False)
    status = Column(
        PgEnum('pending', 'processing', 'done', 'failed',
               name='importstatus', create_type=True),
        nullable=False, default='pending',
    )
    total_rows    = Column(Integer, default=0)
    imported_rows = Column(Integer, default=0)
    failed_rows   = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)
    created_at    = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at    = Column(DateTime, default=datetime.utcnow,
                           onupdate=datetime.utcnow, nullable=False)

    def __repr__(self) -> str:
        return f"<Import id={self.id} file='{self.filename}' status='{self.status}'>"