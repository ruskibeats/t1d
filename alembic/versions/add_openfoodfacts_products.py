"""Add compact Open Food Facts product lookup table.

Revision ID: add_openfoodfacts_products
Revises: add_simulator_tables
Create Date: 2026-05-21
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "add_openfoodfacts_products"
down_revision: Union[str, None] = "add_simulator_tables"
branch_labels: Union[Sequence[str], None] = None
depends_on: Union[Sequence[str], None] = None


def upgrade() -> None:
    dialect = op.get_bind().dialect.name
    tag_type = postgresql.ARRAY(sa.Text()) if dialect == "postgresql" else sa.JSON()

    op.create_table(
        "openfoodfacts_products",
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("product_name", sa.Text(), nullable=True),
        sa.Column("brands", sa.Text(), nullable=True),
        sa.Column("categories", sa.Text(), nullable=True),
        sa.Column("categories_tags", tag_type, nullable=True),
        sa.Column("countries_tags", tag_type, nullable=True),
        sa.Column("serving_size", sa.Text(), nullable=True),
        sa.Column("serving_quantity", sa.Float(), nullable=True),
        sa.Column("product_quantity", sa.Float(), nullable=True),
        sa.Column("product_quantity_unit", sa.Text(), nullable=True),
        sa.Column("nutrition_data_per", sa.Text(), nullable=True),
        sa.Column("carbs_100g", sa.Float(), nullable=True),
        sa.Column("sugars_100g", sa.Float(), nullable=True),
        sa.Column("fiber_100g", sa.Float(), nullable=True),
        sa.Column("proteins_100g", sa.Float(), nullable=True),
        sa.Column("fat_100g", sa.Float(), nullable=True),
        sa.Column("saturated_fat_100g", sa.Float(), nullable=True),
        sa.Column("energy_kcal_100g", sa.Float(), nullable=True),
        sa.Column("salt_100g", sa.Float(), nullable=True),
        sa.Column("sodium_100g", sa.Float(), nullable=True),
        sa.Column("nutriscore_grade", sa.Text(), nullable=True),
        sa.Column("nutriscore_score", sa.Integer(), nullable=True),
        sa.Column("nova_group", sa.Integer(), nullable=True),
        sa.Column("data_quality_tags", tag_type, nullable=True),
        sa.Column("source_updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("imported_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("code"),
    )
    op.create_index("ix_off_products_product_name", "openfoodfacts_products", ["product_name"], unique=False)
    op.create_index("ix_off_products_brands", "openfoodfacts_products", ["brands"], unique=False)
    op.create_index("ix_off_products_nutrition_carbs", "openfoodfacts_products", ["carbs_100g"], unique=False)

    if dialect == "postgresql":
        op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
        op.create_index(
            "ix_off_products_product_name_trgm",
            "openfoodfacts_products",
            ["product_name"],
            unique=False,
            postgresql_using="gin",
            postgresql_ops={"product_name": "gin_trgm_ops"},
        )
        op.create_index(
            "ix_off_products_brands_trgm",
            "openfoodfacts_products",
            ["brands"],
            unique=False,
            postgresql_using="gin",
            postgresql_ops={"brands": "gin_trgm_ops"},
        )
        op.create_index(
            "ix_off_products_categories_tags_gin",
            "openfoodfacts_products",
            ["categories_tags"],
            unique=False,
            postgresql_using="gin",
        )


def downgrade() -> None:
    dialect = op.get_bind().dialect.name
    if dialect == "postgresql":
        op.drop_index("ix_off_products_categories_tags_gin", table_name="openfoodfacts_products")
        op.drop_index("ix_off_products_brands_trgm", table_name="openfoodfacts_products")
        op.drop_index("ix_off_products_product_name_trgm", table_name="openfoodfacts_products")
    op.drop_index("ix_off_products_nutrition_carbs", table_name="openfoodfacts_products")
    op.drop_index("ix_off_products_brands", table_name="openfoodfacts_products")
    op.drop_index("ix_off_products_product_name", table_name="openfoodfacts_products")
    op.drop_table("openfoodfacts_products")
