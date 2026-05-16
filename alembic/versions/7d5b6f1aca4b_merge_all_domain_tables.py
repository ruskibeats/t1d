"""merge all domain tables

Revision ID: 7d5b6f1aca4b
Revises: add_sleep_tables, add_fasting_mood_water_tables
Create Date: 2026-05-16 18:43:14.632062

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7d5b6f1aca4b'
down_revision: Union[str, None] = ('add_sleep_tables', 'add_fasting_mood_water_tables')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
