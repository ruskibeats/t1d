"""Database configuration and session management."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy import pool
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import get_settings


class DatabaseManager:
    """Manages database engine and sessions."""

    def __init__(self):
        self.engine: AsyncEngine = None
        self.async_session_maker: async_sessionmaker = None
        self._initialized = False

    def init_db(self, database_url: str) -> None:
        """Initialize database engine and session factory.
        
        Args:
            database_url: Async PostgreSQL connection URL
        """
        if self._initialized:
            return

        # Create async engine with connection pooling
        self.engine = create_async_engine(
            database_url,
            echo=False,
            poolclass=pool.AsyncAdaptedQueuePool,
            pool_size=10,
            max_overflow=20,
            pool_pre_ping=True,
            pool_recycle=3600,
        )

        # Create async session factory
        self.async_session_maker = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
            autocommit=False,
        )

        self._initialized = True

    async def close(self) -> None:
        """Close database engine."""
        if self.engine:
            await self.engine.dispose()
            self._initialized = False

    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Get database session context manager.
        
        Yields:
            AsyncSession: Database session
            
        Raises:
            RuntimeError: If database not initialized
        """
        if not self._initialized:
            raise RuntimeError("Database not initialized. Call init_db() first.")

        async with self.async_session_maker() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise

    def create_session(self) -> AsyncSession:
        """Create a new standalone database session (for dependency injection).
        
        Returns:
            AsyncSession: New database session
        """
        if not self._initialized:
            raise RuntimeError("Database not initialized. Call init_db() first.")

        return self.async_session_maker()


# Global database manager instance
db_manager = DatabaseManager()


async def init_db() -> None:
    """Initialize database tables and migrations.
    
    This function:
    1. Initializes database engine
    2. Creates tables if they don't exist
    3. Runs any pending migrations via Alembic
    """
    from app.db import models  # noqa: F401 - import models for table creation

    settings = get_settings()

    # Initialize database manager
    db_manager.init_db(settings.database_url)

    # Import Base for table creation

    from app.db.base import Base
    from sqlalchemy import text

    # Create tables if they don't exist
    async with db_manager.engine.begin() as conn:
        # Check if tables exist
        result = await conn.execute(text("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'tbl_users'
            )
        """))
        tables_exist = result.scalar()

        if not tables_exist:
            print("Creating database tables...")
            await conn.run_sync(Base.metadata.create_all)
            print("Database tables created.")
        else:
            print("Database tables already exist.")

    # Check for and run Alembic migrations
    await run_migrations()


async def run_migrations() -> None:
    """Run pending Alembic migrations."""
    try:

        from alembic.config import Config

        from alembic import command

        alembic_cfg = Config("alembic.ini")

        # Get current revision
        from alembic.script import ScriptDirectory
        script = ScriptDirectory.from_config(alembic_cfg)

        # Get database revision
        from sqlalchemy import text
        async with db_manager.engine.begin() as conn:
            result = await conn.execute(text("SELECT version_num FROM alembic_version"))
            db_revision = result.scalar()

        # Get head revision
        head_revision = script.get_current_head()

        if db_revision != head_revision:
            print(f"Migrating from {db_revision} to {head_revision}...")
            command.upgrade(alembic_cfg, "head")
            print("Migrations applied.")
        else:
            print("Database is up to date.")

    except Exception as e:
        print(f"Note: Alembic migrations check skipped: {e}")


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for getting database session.
    
    Yields:
        AsyncSession: Database session
    """
    async with db_manager.get_session() as session:
        try:
            yield session
        finally:
            await session.close()
