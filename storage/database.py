"""Database connection and session management for Black Box (P3 Chirag).

Connects to Supabase PostgreSQL using SQLAlchemy and psycopg.
Provides graceful local SQLite fallback when SUPABASE_DB_URL is not configured
or temporarily unreachable (ensuring demo/offline resilience per spec section 20).
"""
from __future__ import annotations

import logging
import os
from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker, Session

import config

logger = logging.getLogger("blackbox.storage.database")

Base = declarative_base()


def get_database_url() -> str:
    """Normalize and return the database URL from config.
    
    Handles postgres:// -> postgresql+psycopg:// conversion for SQLAlchemy 2.0.
    Falls back to local SQLite if unconfigured or contains placeholder values.
    """
    raw_url = getattr(config, "DB_URL", "") or os.getenv("SUPABASE_DB_URL", "")
    if not raw_url or "YourPasswordHere" in raw_url or "<" in raw_url:
        if os.getenv("RAILWAY_ENVIRONMENT"):
            raise RuntimeError("SUPABASE_DB_URL is not set")
        return "sqlite:///./blackbox_local.db"

    url = raw_url.strip()
    if url.startswith("postgres://"):
        url = "postgresql+psycopg://" + url[len("postgres://"):]
    elif url.startswith("postgresql://") and not url.startswith("postgresql+"):
        url = "postgresql+psycopg://" + url[len("postgresql://"):]

    return url


def create_db_engine(db_url: str | None = None):
    """Create a configured SQLAlchemy engine."""
    url = db_url or get_database_url()
    is_sqlite = url.startswith("sqlite")
    
    connect_args = {"check_same_thread": False} if is_sqlite else {}
    pool_kwargs = {} if is_sqlite else {"pool_pre_ping": True, "pool_recycle": 300}

    return create_engine(url, connect_args=connect_args, **pool_kwargs)


# Global singleton engine and sessionmaker
engine = create_db_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
_DB_INITIALIZED = False


def ensure_tables(target_engine=None) -> None:
    global _DB_INITIALIZED
    if not _DB_INITIALIZED:
        init_db(target_engine or engine)
        _DB_INITIALIZED = True


def get_session() -> Session:
    """Return a new SQLAlchemy Session."""
    ensure_tables()
    return SessionLocal()


@contextmanager
def get_db() -> Generator[Session, None, None]:
    """Context manager for transactional database access with auto-rollback on error."""
    ensure_tables()
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def init_db(target_engine=None) -> None:
    """Initialize all tables defined in models.py with automatic SQLite fallback."""
    global engine, SessionLocal
    active_engine = target_engine or engine
    
    from . import models  # noqa: F401

    try:
        if active_engine.dialect.name == "postgresql":
            try:
                with active_engine.connect() as conn:
                    conn.execute(text('create extension if not exists "uuid-ossp";'))
                    conn.commit()
            except Exception as e:
                logger.debug(f"uuid-ossp extension check: {e}")

        Base.metadata.create_all(bind=active_engine)
        logger.info(f"Database schema initialized successfully using {active_engine.dialect.name}.")
    except Exception as e:
        if active_engine.dialect.name == "postgresql":
            logger.warning(
                f"⚠️ PostgreSQL connection failed: {e}. Falling back gracefully to local SQLite database."
            )
            fallback_engine = create_db_engine("sqlite:///./blackbox_local.db")
            engine = fallback_engine
            SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=fallback_engine)
            Base.metadata.create_all(bind=fallback_engine)
            logger.info("Local SQLite database schema initialized as fallback.")
        else:
            raise
