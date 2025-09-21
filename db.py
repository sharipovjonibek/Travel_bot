# db.py

import logging
import os
from typing import Any, Dict, Optional, Tuple

from dotenv import load_dotenv

logger = logging.getLogger(__name__)
load_dotenv()

# --- database driver import ---
_DB_DRIVER: Optional[str] = None
_DB_DRIVER_ERR: Optional[str] = None

try:
    import psycopg  # type: ignore
    from psycopg.rows import dict_row  # type: ignore

    _DB_DRIVER = "psycopg"
except Exception as psycopg_exc:
    psycopg = None  # type: ignore
    try:
        import psycopg2  # type: ignore
        from psycopg2.extras import RealDictCursor  # type: ignore

        _DB_DRIVER = "psycopg2"
    except Exception as psycopg2_exc:
        psycopg2 = None  # type: ignore
        RealDictCursor = None  # type: ignore
        _DB_DRIVER_ERR = (
            f"psycopg import failed: {psycopg_exc}; psycopg2 import failed: {psycopg2_exc}"
        )
        logger.warning("%s", _DB_DRIVER_ERR)
else:
    psycopg2 = None  # type: ignore
    RealDictCursor = None  # type: ignore

def _build_db_url() -> Optional[str]:
    """Prefer DATABASE_URL; otherwise compose from PG* parts. Append sslmode=require for non-local hosts."""
    url = os.getenv("DATABASE_URL")
    if not url:
        host = os.getenv("PGHOST")
        port = os.getenv("PGPORT", "5432")
        user = os.getenv("PGUSER")
        pwd  = os.getenv("PGPASSWORD")
        db   = os.getenv("PGDATABASE")
        if all([host, user, pwd, db]):
            url = f"postgresql://{user}:{pwd}@{host}:{port}/{db}"
    if not url:
        return None

    lower = url.lower()
    is_local = ("localhost" in lower) or ("127.0.0.1" in lower)
    if ("sslmode=" not in lower) and (not is_local):
        sep = "&" if "?" in url else "?"
        url = f"{url}{sep}sslmode=require"
    return url

DB_URL = _build_db_url()


def _connect():  # type: ignore[return-value]
    """Return a psycopg(2/3) connection configured to yield dict-like rows."""

    if not DB_URL:
        raise RuntimeError("DB_URL is not configured")
    if _DB_DRIVER == "psycopg":
        return psycopg.connect(DB_URL, row_factory=dict_row)  # type: ignore[call-arg, return-value]
    if _DB_DRIVER == "psycopg2":
        return psycopg2.connect(DB_URL, cursor_factory=RealDictCursor)  # type: ignore[call-arg, return-value]
    raise RuntimeError("No PostgreSQL driver available")

# In-memory fallback store
_IN_MEMORY_MODE: bool = False
_mem_users_by_tg: Dict[int, Dict[str, Any]] = {}
_mem_next_id: int = 1

def _enable_memory_mode(reason: str):
    global _IN_MEMORY_MODE
    if not _IN_MEMORY_MODE:
        logger.error(" Switching to in-memory DB: %s", reason)
    _IN_MEMORY_MODE = True

def init_db():
    """Initialize storage. Use PostgreSQL if possible; otherwise fall back to memory."""
    if not _DB_DRIVER:
        reason = _DB_DRIVER_ERR or "psycopg driver not available"
        _enable_memory_mode(reason)
        return
    if not DB_URL:
        _enable_memory_mode("DATABASE_URL/PG* envs not set")
        return
    con = None
    cur = None
    try:
        con = _connect()
        cur = con.cursor()
        cur.execute(
            """CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                tg_id BIGINT UNIQUE,
                language TEXT,
                first_name TEXT,
                last_name TEXT,
                phone TEXT
            );"""
        )
        con.commit()
        logger.info(" PostgreSQL ready")
    except Exception as e:
        _enable_memory_mode(f"PostgreSQL init failed: {e}")
    finally:
        if cur is not None:
            try:
                cur.close()
            except Exception:
                pass
        if con is not None:
            try:
                con.close()
            except Exception:
                pass

def upsert_user(tg_id: int,
                language: Optional[str] = None,
                first_name: Optional[str] = None,
                last_name: Optional[str] = None,
                phone: Optional[str] = None):
    global _mem_next_id
    if _IN_MEMORY_MODE:
        row = _mem_users_by_tg.get(tg_id)
        if not row:
            row = {"id": _mem_next_id, "tg_id": tg_id,
                   "language": None, "first_name": None, "last_name": None, "phone": None}
            _mem_users_by_tg[tg_id] = row
            _mem_next_id += 1
        if language is not None: row["language"] = language
        if first_name is not None: row["first_name"] = first_name
        if last_name is not None: row["last_name"] = last_name
        if phone is not None: row["phone"] = phone
        return

    try:
        con = None
        cur = None
        con = _connect()
        cur = con.cursor()
        cur.execute(
            """INSERT INTO users (tg_id, language, first_name, last_name, phone)
               VALUES (%s, %s, %s, %s, %s)
               ON CONFLICT (tg_id) DO UPDATE
               SET language = COALESCE(EXCLUDED.language, users.language),
                   first_name = COALESCE(EXCLUDED.first_name, users.first_name),
                   last_name = COALESCE(EXCLUDED.last_name, users.last_name),
                   phone = COALESCE(EXCLUDED.phone, users.phone)""",
            (tg_id, language, first_name, last_name, phone),
        )
        con.commit()
    except Exception as e:
        _enable_memory_mode(f"PostgreSQL upsert failed: {e}")
        # keep the data for this run
        upsert_user(tg_id, language, first_name, last_name, phone)
    finally:
        if cur is not None:
            try:
                cur.close()
            except Exception:
                pass
        if con is not None:
            try:
                con.close()
            except Exception:
                pass

def get_user(tg_id: int) -> Optional[Tuple[int, int, Optional[str], Optional[str], Optional[str], Optional[str]]]:
    if _IN_MEMORY_MODE:
        row = _mem_users_by_tg.get(tg_id)
        if not row: return None
        return (row["id"], row["tg_id"], row.get("language"), row.get("first_name"), row.get("last_name"), row.get("phone"))
    con = None
    cur = None
    row = None
    try:
        con = _connect()
        cur = con.cursor()
        cur.execute("SELECT id, tg_id, language, first_name, last_name, phone FROM users WHERE tg_id=%s", (tg_id,))
        row = cur.fetchone()
    except Exception as e:
        _enable_memory_mode(f"PostgreSQL read failed: {e}")
        return None
    finally:
        if cur is not None:
            try:
                cur.close()
            except Exception:
                pass
        if con is not None:
            try:
                con.close()
            except Exception:
                pass
    if not row:
        return None
    return (row["id"], row["tg_id"], row["language"], row["first_name"], row["last_name"], row["phone"])
