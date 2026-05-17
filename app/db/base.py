"""SQLAlchemy base and shared utilities."""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class for all models."""
    pass


def table_name_generator(name: str) -> str:
    """Generate table name from class name.

    Args:
        name: Model class name

    Returns:
        Table name in snake_case with 'tbl_' prefix
    """
    # Convert CamelCase to snake_case
    import re
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    return f"tbl_{re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()}"


# Set table naming convention
Base.table_name_generator = table_name_generator
