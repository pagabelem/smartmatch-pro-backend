"""add imports table

Revision ID: 6ea2f5b5e9ce
Revises: b26b50c71ff7
Create Date: 2026-05-17 06:05:39.103006
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '6ea2f5b5e9ce'
down_revision: Union[str, None] = 'b26b50c71ff7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'imports',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('filename', sa.String(length=255), nullable=False),
        sa.Column('source',
            postgresql.ENUM(
                'csv', 'json', 'scraper_rekrute', 'scraper_emploidiali',
                'scraper_indeed', 'scraper_linkedin', 'manual',
                name='importsource',
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column('import_type', sa.String(length=50), nullable=False),
        sa.Column('status',
            postgresql.ENUM(
                'pending', 'processing', 'done', 'failed',
                name='importstatus',
                create_type=True,
            ),
            nullable=False,
        ),
        sa.Column('total_rows', sa.Integer(), nullable=True),
        sa.Column('imported_rows', sa.Integer(), nullable=True),
        sa.Column('failed_rows', sa.Integer(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_imports_id'), 'imports', ['id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_imports_id'), table_name='imports')
    op.drop_table('imports')
    postgresql.ENUM(name='importstatus').drop(op.get_bind(), checkfirst=True)