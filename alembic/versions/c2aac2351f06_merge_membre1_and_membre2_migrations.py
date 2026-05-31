"""merge membre1 and membre2 migrations

Revision ID: c2aac2351f06
Revises: 0004, 80beeced3fbe
Create Date: 2026-05-31 13:00:14.265039

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c2aac2351f06'
down_revision: Union[str, None] = ('0004', '80beeced3fbe')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass