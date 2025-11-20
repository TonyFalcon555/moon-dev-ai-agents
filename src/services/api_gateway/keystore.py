import os
import hashlib
import secrets
import time
from typing import Optional, List, Dict, Tuple
from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String, select, update, insert, desc, JSON, DateTime

# Configuration
BASE_DIR = os.path.dirname(__file__)
# Default to SQLite for backward compatibility, but support Postgres via env var
DEFAULT_DB_URL = f"sqlite:///{os.path.join(BASE_DIR, 'keystore.sqlite3')}"
DB_URL = os.getenv("KEYSTORE_DB_URL", DEFAULT_DB_URL)

# SQLAlchemy Setup
engine = create_engine(DB_URL, future=True)
metadata = MetaData()

api_keys = Table(
    "api_keys",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("key_hash", String, unique=True, nullable=False),
    Column("plan", String, nullable=False),
    Column("created_at", Integer, nullable=False),
    Column("revoked_at", Integer, nullable=True),
    Column("rate_limit_override", Integer, nullable=True),
    Column("metadata", String, nullable=True),
)

alerts_table = Table(
    "alerts",
    metadata,
    Column("id", String, primary_key=True),
    Column("owner_hash", String, index=True, nullable=False),
    Column("plan", String, nullable=False),
    Column("config", JSON, nullable=False),
    Column("state", JSON, nullable=True),
    Column("created_at", DateTime, nullable=False),
)

def init_db() -> None:
    metadata.create_all(engine)

def _hash_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()

def generate_key(prefix: str = "md_", hex_bytes: int = 32) -> str:
    return prefix + secrets.token_hex(hex_bytes)

def add_key(plan: str, raw_key: Optional[str] = None, rate_limit_override: Optional[int] = None, metadata: Optional[str] = None) -> str:
    init_db()
    key = raw_key or generate_key()
    kh = _hash_key(key)
    now = int(time.time())
    
    stmt = insert(api_keys).values(
        key_hash=kh,
        plan=plan,
        created_at=now,
        rate_limit_override=rate_limit_override,
        metadata=metadata
    )
    with engine.connect() as conn:
        conn.execute(stmt)
        conn.commit()
    return key

def list_keys() -> List[Dict]:
    init_db()
    stmt = select(api_keys).order_by(desc(api_keys.c.id))
    with engine.connect() as conn:
        result = conn.execute(stmt)
        rows = result.fetchall()
        
    out: List[Dict] = []
    for r in rows:
        # r is a Row object, accessible by index or name
        out.append(
            {
                "key_hash": r.key_hash,
                "plan": r.plan,
                "created_at": r.created_at,
                "revoked_at": r.revoked_at,
                "rate_limit_override": r.rate_limit_override,
                "metadata": r.metadata,
            }
        )
    return out

def revoke_key(raw_key: str) -> bool:
    init_db()
    kh = _hash_key(raw_key)
    now = int(time.time())
    
    stmt = update(api_keys).where(
        api_keys.c.key_hash == kh,
        api_keys.c.revoked_at == None
    ).values(revoked_at=now)
    
    with engine.connect() as conn:
        result = conn.execute(stmt)
        conn.commit()
        return result.rowcount > 0

def rotate_key(raw_key: str) -> Optional[str]:
    init_db()
    kh_old = _hash_key(raw_key)
    
    with engine.connect() as conn:
        stmt = select(api_keys.c.plan, api_keys.c.rate_limit_override, api_keys.c.metadata).where(
            api_keys.c.key_hash == kh_old,
            api_keys.c.revoked_at == None
        )
        row = conn.execute(stmt).fetchone()
        
        if not row:
            return None
            
        plan, rlo, meta = row.plan, row.rate_limit_override, row.metadata
        
        # Revoke old
        revoke_stmt = update(api_keys).where(
            api_keys.c.key_hash == kh_old,
            api_keys.c.revoked_at == None
        ).values(revoked_at=int(time.time()))
        conn.execute(revoke_stmt)
        conn.commit()
        
    # Add new (calls init_db again but that's fine)
    return add_key(plan=plan, rate_limit_override=rlo, metadata=meta)

def get_plan_for_key(raw_key: str) -> Optional[str]:
    init_db()
    kh = _hash_key(raw_key)
    
    stmt = select(api_keys.c.plan, api_keys.c.revoked_at).where(
        api_keys.c.key_hash == kh,
        api_keys.c.revoked_at == None
    )
    
    with engine.connect() as conn:
        row = conn.execute(stmt).fetchone()
        if not row:
            return None
        return row.plan

def get_plan_and_override(raw_key: str) -> Tuple[Optional[str], Optional[int]]:
    """Return (plan, rate_limit_override) for a key, or (None, None) if not found/revoked."""
    init_db()
    kh = _hash_key(raw_key)
    
    stmt = select(api_keys.c.plan, api_keys.c.revoked_at, api_keys.c.rate_limit_override).where(
        api_keys.c.key_hash == kh
    )
    
    with engine.connect() as conn:
        row = conn.execute(stmt).fetchone()
        if not row:
            return None, None
        
        if row.revoked_at is not None:
            return None, None
            
        return row.plan, row.rate_limit_override

def set_plan_for_key(raw_key: str, plan: str) -> bool:
    init_db()
    kh = _hash_key(raw_key)
    
    stmt = update(api_keys).where(api_keys.c.key_hash == kh).values(plan=plan)
    
    with engine.connect() as conn:
        result = conn.execute(stmt)
        conn.commit()
        return result.rowcount > 0

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd")

    p_create = sub.add_parser("create")
    p_create.add_argument("--plan", required=True)

    p_list = sub.add_parser("list")

    p_revoke = sub.add_parser("revoke")
    p_revoke.add_argument("--key", required=True)

    p_rotate = sub.add_parser("rotate")
    p_rotate.add_argument("--key", required=True)

    p_verify = sub.add_parser("verify")
    p_verify.add_argument("--key", required=True)

    args = parser.parse_args()
    if args.cmd == "create":
        k = add_key(plan=args.plan)
        print(k)
    elif args.cmd == "list":
        for row in list_keys():
            print(row)
    elif args.cmd == "revoke":
        print(revoke_key(args.key))
    elif args.cmd == "rotate":
        newk = rotate_key(args.key)
        print(newk or "None")
    elif args.cmd == "verify":
        print(get_plan_for_key(args.key))
    else:
        parser.print_help()
