"""add_embedding_columns_to_openfoodfacts

Revision ID: b1557c032d24
Revises: add_openfoodfacts_products
Create Date: 2026-05-25 11:06:28.611756

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b1557c032d24'
down_revision: Union[str, None] = 'add_openfoodfacts_products'
branch_labels: Union[str, None] = None
depends_on: Union[str, None] = None


def upgrade() -> None:
    # Add JSON embedding column (stores 768 floats as JSON string)
    op.add_column('openfoodfacts_products',
        sa.Column('embedding', sa.Text(), nullable=True,
                  comment='JSON array of embedding floats for pgvector search'))

    # Add pgvector column for future native vector search
    # Note: Requires pgvector extension and SQLAlchemy Vector type
    # For now we skip this - the JSON column works with Python similarity
    # To enable pgvector, uncomment below after running: CREATE EXTENSION vector;
    # op.add_column('openfoodfacts_products',
    #     sa.Column('embedding_vec', Vector(768), nullable=True))


def downgrade() -> None:
    op.drop_column('openfoodfacts_products', 'embedding')