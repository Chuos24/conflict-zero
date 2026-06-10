
## ConflictZero Database Migration Script
## Applies production indexes on startup

import asyncio
from sqlalchemy import text, create_engine
from app.db.base import BASE
import os
import logging

logger = logging.getLogger(__name__)

async def apply_migration() -> None:
    """Apply database migration indexes on startup"""
    try:
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            logger.warning("DATABASE_URL not set, skipping migration")
            return

        engine = create_engine(database_url)
        with engine.connect() as conn:
            migration_sql = """
            BEGIN;
            CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
            CREATE INDEX IF NOT EXISTS idx_users_created_at ON users(created_at);
            CREATE INDEX IF NOT EXISTS idx_verifications_ruc ON verifications(ruc);
            CREATE INDEX IF NOT EXISTS idx_verifications_user_id ON verifications(user_id);
            CREATE INDEX IF NOT EXISTS idx_verifications_created_at ON verifications(created_at);
            CREATE INDEX IF NOT EXISTS idx_verifications_user_created ON verifications(user_id, created_at DESC);
            CREATE INDEX IF NOT EXISTS idx_searches_user_id ON search_history(user_id);
            CREATE INDEX IF NOT EXISTS idx_searches_created_at ON search_history(created_at);
            CREATE INDEX IF NOT EXISTS idx_tags_user_id ON tags(user_id);
            CREATE INDEX IF NOT EXISTS idx_ruc_tags_ruc ON ruc_tags(ruc);
            CREATE INDEX IF NOT EXISTS idx_ruc_tags_tag_id ON ruc_tags(tag_id);
            COMMIT;
            """
            conn.execute(text(migration_sql))
            conn.commit()
            logger.info("ºN Database migration indexes created successfully")

    except Exception as e:
        logger.warning(f"Migration skipped (may already exist): {e}")
