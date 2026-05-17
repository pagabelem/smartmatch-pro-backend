# app/modules/jobs/job_model.py

from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Enum as SAEnum
from sqlalchemy import Integer, String, Text, Float
from sqlalchemy.dialects.postgresql import JSONB

from app.database import Base
from app.shared.enums import (
    ContractType,
    DegreeLevel,
    ExperienceLevel,
    ImportSource,
    JobStatus,
    WorkMode,
)


class Job(Base):
    """
    Table 'jobs' — Offres d'emploi importées ou saisies manuellement.
    Propriétaire  : Membre 2
    Consommateurs : Matching, Skill Gap, Dashboard, Favorites, IA
    """

    __tablename__ = "jobs"

    # ── Clé primaire ───────────────────────────────────────────────────────────
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    # ── Informations principales ───────────────────────────────────────────────
    title = Column(String(255), nullable=False, index=True,
                   comment="Intitulé du poste")
    company = Column(String(255), nullable=False, index=True,
                     comment="Nom de l'entreprise")
    description = Column(Text, nullable=True,
                         comment="Description complète de l'offre")
    location = Column(String(255), nullable=True, index=True,
                      comment="Ville / pays")
    url = Column(String(500), nullable=True,
                 comment="Lien vers l'offre originale")

    # ── Classification ─────────────────────────────────────────────────────────
    contract_type = Column(
        SAEnum(ContractType, values_callable=lambda e: [i.value for i in e]),
        nullable=False, default=ContractType.OTHER.value,
        comment="CDI, CDD, Stage, Alternance…"
    )
    experience_level = Column(
        SAEnum(ExperienceLevel, values_callable=lambda e: [i.value for i in e]),
        nullable=False, default=ExperienceLevel.ANY.value,
        comment="junior, mid, senior, lead, internship, any"
    )
    work_mode = Column(
        SAEnum(WorkMode, values_callable=lambda e: [i.value for i in e]),
        nullable=False, default=WorkMode.ANY.value,
        comment="on_site, remote, hybrid, any"
    )
    degree_level = Column(
        SAEnum(DegreeLevel, values_callable=lambda e: [i.value for i in e]),
        nullable=True, default=DegreeLevel.ANY.value,
        comment="Bac+2, Bac+3, Bac+5…"
    )

    # ── Compétences requises (JSONB) ───────────────────────────────────────────
    required_skills = Column(
        JSONB, nullable=False, default=list,
        comment="Liste des compétences normalisées : ['python', 'fastapi', 'sql']"
    )

    # ── Salaire ────────────────────────────────────────────────────────────────
    salary_min = Column(Float, nullable=True, comment="Salaire minimum (DH)")
    salary_max = Column(Float, nullable=True, comment="Salaire maximum (DH)")
    salary_currency = Column(String(10), nullable=True, default="DH")

    # ── Statut & Source ────────────────────────────────────────────────────────
    status = Column(
        SAEnum(JobStatus, values_callable=lambda e: [i.value for i in e]),
        nullable=False, default=JobStatus.ACTIVE.value,
        comment="active, expired, suspended, draft"
    )
    source = Column(
        SAEnum(ImportSource, values_callable=lambda e: [i.value for i in e]),
        nullable=False, default=ImportSource.MANUAL.value,
        comment="Origine de l'offre : csv, manual, scraper…"
    )

    # ── Dates ──────────────────────────────────────────────────────────────────
    published_at = Column(DateTime, nullable=True,
                          comment="Date de publication originale")
    expires_at = Column(DateTime, nullable=True,
                        comment="Date d'expiration de l'offre")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow,
                        onupdate=datetime.utcnow, nullable=False)

    def __repr__(self) -> str:
        return (
            f"<Job id={self.id} title='{self.title}' "
            f"company='{self.company}' status='{self.status}'>"
        )