# app/modules/imports/import_service.py

import io
from typing import Optional

import pandas as pd
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundException, ValidationException
from app.modules.imports.import_model import Import
from app.modules.jobs.job_schema import JobCreate
from app.modules.jobs.job_service import JobService
from app.modules.skills.skill_schema import SkillCreate
from app.modules.skills.skill_service import SkillService
from app.shared.enums import (
    ContractType,
    DegreeLevel,
    ExperienceLevel,
    ImportSource,
    ImportStatus,
    JobStatus,
    SkillType,
    WorkMode,
)
from app.shared.pagination import PaginationParams, paginate_query
from app.shared.utils import normalize_skill


class ImportService:
    """
    Service d'import de données en masse depuis des fichiers CSV.
    Supporte : offres d'emploi (jobs) et compétences (skills).
    """

    # ── Colonnes attendues dans les CSV ────────────────────────────────────────
    JOBS_REQUIRED_COLS = {"title", "company"}
    SKILLS_REQUIRED_COLS = {"name", "skill_type"}

    # ── IMPORT JOBS CSV ────────────────────────────────────────────────────────
    @staticmethod
    def import_jobs_csv(
        db: Session,
        file_content: bytes,
        filename: str,
    ) -> Import:
        """
        Lit un fichier CSV de jobs, valide et insère les offres en base.

        Colonnes requises  : title, company
        Colonnes optionnelles : description, location, url, contract_type,
                                experience_level, work_mode, degree_level,
                                required_skills (séparées par |), salary_min,
                                salary_max
        """
        record = Import(
            filename=filename,
            source=ImportSource.CSV.value,
            import_type="jobs",
            status=ImportStatus.PROCESSING.value,
        )
        db.add(record)
        db.commit()
        db.refresh(record)

        try:
            df = pd.read_csv(io.BytesIO(file_content), encoding="utf-8")
            df.columns = [c.strip().lower() for c in df.columns]

            # Vérifier les colonnes obligatoires
            missing = ImportService.JOBS_REQUIRED_COLS - set(df.columns)
            if missing:
                raise ValidationException(
                    f"Colonnes manquantes dans le CSV : {', '.join(missing)}"
                )

            df = df.where(pd.notna(df), None)
            total = len(df)
            imported = 0
            failed = 0

            jobs_to_create = []
            for _, row in df.iterrows():
                try:
                    # Compétences : séparées par | dans le CSV
                    raw_skills = row.get("required_skills", "") or ""
                    skills = [
                        normalize_skill(s)
                        for s in str(raw_skills).split("|")
                        if s.strip()
                    ]

                    job_data = JobCreate(
                        title=str(row["title"]),
                        company=str(row["company"]),
                        description=str(row["description"]) if row.get("description") else None,
                        location=str(row["location"]) if row.get("location") else None,
                        url=str(row["url"]) if row.get("url") else None,
                        contract_type=_safe_enum(ContractType, row.get("contract_type"), ContractType.OTHER),
                        experience_level=_safe_enum(ExperienceLevel, row.get("experience_level"), ExperienceLevel.ANY),
                        work_mode=_safe_enum(WorkMode, row.get("work_mode"), WorkMode.ANY),
                        degree_level=_safe_enum(DegreeLevel, row.get("degree_level"), DegreeLevel.ANY),
                        required_skills=skills,
                        salary_min=float(row["salary_min"]) if row.get("salary_min") else None,
                        salary_max=float(row["salary_max"]) if row.get("salary_max") else None,
                        status=JobStatus.ACTIVE,
                        source=ImportSource.CSV,
                    )
                    jobs_to_create.append(job_data)
                    imported += 1
                except Exception:
                    failed += 1

            if jobs_to_create:
                JobService.bulk_create(db, jobs_to_create)

            # Mettre à jour le record d'import
            record.status = ImportStatus.DONE.value
            record.total_rows = total
            record.imported_rows = imported
            record.failed_rows = failed

        except ValidationException as e:
            record.status = ImportStatus.FAILED.value
            record.error_message = str(e.message)
        except Exception as e:
            record.status = ImportStatus.FAILED.value
            record.error_message = str(e)

        db.commit()
        db.refresh(record)
        return record

    # ── IMPORT SKILLS CSV ──────────────────────────────────────────────────────
    @staticmethod
    def import_skills_csv(
        db: Session,
        file_content: bytes,
        filename: str,
    ) -> Import:
        """
        Lit un fichier CSV de compétences et les insère dans le référentiel.

        Colonnes requises   : name, skill_type (hard|soft)
        Colonnes optionnelles : sub_category, description
        """
        record = Import(
            filename=filename,
            source=ImportSource.CSV.value,
            import_type="skills",
            status=ImportStatus.PROCESSING.value,
        )
        db.add(record)
        db.commit()
        db.refresh(record)

        try:
            df = pd.read_csv(io.BytesIO(file_content), encoding="utf-8")
            df.columns = [c.strip().lower() for c in df.columns]

            missing = ImportService.SKILLS_REQUIRED_COLS - set(df.columns)
            if missing:
                raise ValidationException(
                    f"Colonnes manquantes dans le CSV : {', '.join(missing)}"
                )

            df = df.where(pd.notna(df), None)
            total = len(df)
            imported = 0
            failed = 0

            for _, row in df.iterrows():
                try:
                    skill_data = SkillCreate(
                        name=str(row["name"]),
                        skill_type=_safe_enum(SkillType, row.get("skill_type"), SkillType.HARD),
                        description=str(row["description"]) if row.get("description") else None,
                    )
                    SkillService.create(db, skill_data)
                    imported += 1
                except Exception:
                    failed += 1

            record.status = ImportStatus.DONE.value
            record.total_rows = total
            record.imported_rows = imported
            record.failed_rows = failed

        except ValidationException as e:
            record.status = ImportStatus.FAILED.value
            record.error_message = str(e.message)
        except Exception as e:
            record.status = ImportStatus.FAILED.value
            record.error_message = str(e)

        db.commit()
        db.refresh(record)
        return record

    # ── HISTORIQUE ─────────────────────────────────────────────────────────────
    @staticmethod
    def get_history(
        db: Session,
        params: PaginationParams,
        import_type: Optional[str] = None,
    ):
        """Liste paginée de l'historique des imports."""
        query = db.query(Import)
        if import_type:
            query = query.filter(Import.import_type == import_type)
        query = query.order_by(Import.created_at.desc())
        return paginate_query(query, params)

    # ── GET BY ID ──────────────────────────────────────────────────────────────
    @staticmethod
    def get_by_id(db: Session, import_id: int) -> Import:
        record = db.query(Import).filter(Import.id == import_id).first()
        if not record:
            raise NotFoundException("Import", import_id)
        return record


# ── Helper privé ───────────────────────────────────────────────────────────────
def _safe_enum(enum_class, value, default):
    """
    Convertit une valeur string en enum de manière sécurisée.
    Retourne default si la valeur est None ou invalide.
    """
    if not value:
        return default
    try:
        return enum_class(str(value).strip())
    except ValueError:
        return default