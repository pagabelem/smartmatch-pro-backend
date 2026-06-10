# app/modules/imports/import_router.py

from typing import Optional

from fastapi import APIRouter, Depends, File, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ValidationException
from app.core.responses import ok
from app.dependencies import get_db
from app.modules.imports.import_schema import ImportResponse, ImportSummary
from app.modules.imports.import_service import ImportService
from app.shared.pagination import PaginationParams

router = APIRouter(
    prefix="/imports",
    tags=["Imports — Chargement de données en masse"],
)


# ── POST /api/v1/imports/jobs ──────────────────────────────────────────────────
@router.post(
    "/jobs",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Importer des offres d'emploi depuis un fichier CSV",
)
async def import_jobs(
    file: UploadFile = File(
        ...,
        description="Fichier CSV avec colonnes : title, company, description, "
                    "location, url, contract_type, experience_level, work_mode, "
                    "degree_level, required_skills (séparées par |), "
                    "salary_min, salary_max"
    ),
    db: AsyncSession = Depends(get_db),
):
    """
    Importe des offres d'emploi depuis un fichier CSV.
    Les compétences dans la colonne required_skills doivent être séparées par |.
    Exemple : python|fastapi|postgresql
    """
    if not file.filename.endswith(".csv"):
        raise ValidationException("Le fichier doit être au format CSV (.csv)")

    content = await file.read()
    record = await ImportService.import_jobs_csv(db, content, file.filename)

    summary = ImportSummary(
        import_id=record.id,
        filename=record.filename,
        import_type=record.import_type,
        status=record.status,
        total_rows=record.total_rows,
        imported_rows=record.imported_rows,
        failed_rows=record.failed_rows,
        message=(
            f"{record.imported_rows}/{record.total_rows} offres importées "
            f"avec succès. {record.failed_rows} erreurs."
        ),
    )
    return ok(
        data=summary.model_dump(mode="json"),
        message=summary.message,
    )


# ── POST /api/v1/imports/skills ────────────────────────────────────────────────
@router.post(
    "/skills",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Importer des compétences depuis un fichier CSV",
)
async def import_skills(
    file: UploadFile = File(
        ...,
        description="Fichier CSV avec colonnes : name, skill_type, "
                    "category (optionnel), display_name (optionnel)"
    ),
    db: AsyncSession = Depends(get_db),
):
    """
    Importe des compétences depuis un fichier CSV.
    Les doublons sont ignorés automatiquement (pas d'erreur).
    """
    if not file.filename.endswith(".csv"):
        raise ValidationException("Le fichier doit être au format CSV (.csv)")

    content = await file.read()
    record = await ImportService.import_skills_csv(db, content, file.filename)

    summary = ImportSummary(
        import_id=record.id,
        filename=record.filename,
        import_type=record.import_type,
        status=record.status,
        total_rows=record.total_rows,
        imported_rows=record.imported_rows,
        failed_rows=record.failed_rows,
        message=(
            f"{record.imported_rows}/{record.total_rows} compétences importées "
            f"avec succès. {record.failed_rows} ignorées (doublons ou erreurs)."
        ),
    )
    return ok(
        data=summary.model_dump(mode="json"),
        message=summary.message,
    )


# ── GET /api/v1/imports/ ───────────────────────────────────────────────────────
@router.get(
    "/",
    status_code=status.HTTP_200_OK,
    summary="Historique des imports",
)
async def get_import_history(
    import_type: Optional[str] = Query(
        None, description="Filtrer : 'jobs' ou 'skills'"
    ),
    params: PaginationParams = Depends(),
    db: AsyncSession = Depends(get_db),
):
    """Liste paginée de tous les imports effectués."""
    page = await ImportService.get_history(db, params, import_type)
    return ok(
        data=[ImportResponse.model_validate(r).model_dump(mode="json")
              for r in page.items],
        meta=page.to_dict(),
    )


# ── GET /api/v1/imports/{import_id} ───────────────────────────────────────────
@router.get(
    "/{import_id}",
    status_code=status.HTTP_200_OK,
    summary="Détail d'un import",
)
async def get_import(
    import_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Retourne le détail d'un import par son ID."""
    record = await ImportService.get_by_id(db, import_id)
    return ok(data=ImportResponse.model_validate(record).model_dump(mode="json"))