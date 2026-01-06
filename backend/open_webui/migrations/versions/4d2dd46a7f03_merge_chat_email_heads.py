"""merge chat/email heads

Revision ID: 4d2dd46a7f03
Revises: b2c3d4e5f6g7, c440947495f3
Create Date: 2026-01-05 10:23:10.787388

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import open_webui.internal.db


# revision identifiers, used by Alembic.
revision: str = '4d2dd46a7f03'
down_revision: Union[str, None] = ('b2c3d4e5f6g7', 'c440947495f3')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
