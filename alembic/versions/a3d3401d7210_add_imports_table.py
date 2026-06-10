"""add imports table
Revision ID: a3d3401d7210
Revises: fb810d4cf680
Create Date: 2026-06-10 01:20:04.124279
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = 'a3d3401d7210'
down_revision: Union[str, None] = 'fb810d4cf680'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.create_table('imports',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('filename', sa.String(length=255), nullable=False),
    sa.Column('source', postgresql.ENUM('csv', 'json', 'scraper_rekrute', 'scraper_emploidiali', 'scraper_indeed', 'scraper_linkedin', 'manual', name='importsource', create_type=False), nullable=False),
    sa.Column('import_type', sa.String(length=50), nullable=False),
    sa.Column('status', sa.String(length=20), nullable=False),
    sa.Column('total_rows', sa.Integer(), nullable=True),
    sa.Column('imported_rows', sa.Integer(), nullable=True),
    sa.Column('failed_rows', sa.Integer(), nullable=True),
    sa.Column('error_message', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_imports_id'), 'imports', ['id'], unique=False)

def downgrade() -> None:
    op.drop_index(op.f('ix_imports_id'), table_name='imports')
    op.drop_table('imports')