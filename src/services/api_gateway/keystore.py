import os
import sqlite3
import hashlib
import secrets
import time
from typing import Optional, List, Dict, Tuple

BASE_DIR = os.path.dirname(__file__)
DB_PATH = os.getenv("KEYSTORE_DB_PATH", os.path.join(BASE_DIR, "keystore.sqlite3"))


def _conn():
    return sqlite3.connect(DB_PATH)


def init_db() -> None:
    with _conn() as cx:
        cx.execute(
            """
            CREATE TABLE IF NOT EXISTS api_keys (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              key_hash TEXT UNIQUE NOT NULL,
              plan TEXT NOT NULL,
              created_at INTEGER NOT NULL,
              revoked_at INTEGER,
              rate_limit_override INTEGER,
              metadata TEXT
            )
            """
        )


def _hash_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


def generate_key(prefix: str = "md_", hex_bytes: int = 32) -> str:
    return prefix + secrets.token_hex(hex_bytes)


def add_key(plan: str, raw_key: Optional[str] = None, rate_limit_override: Optional[int] = None, metadata: Optional[str] = None) -> str:
    init_db()
    key = raw_key or generate_key()
    kh = _hash_key(key)
    now = int(time.time())
    with _conn() as cx:
        cx.execute(
            "INSERT INTO api_keys (key_hash, plan, created_at, rate_limit_override, metadata) VALUES (?, ?, ?, ?, ?)",
            (kh, plan, now, rate_limit_override, metadata),
        )
    return key


def list_keys() -> List[Dict]:
    init_db()
    with _conn() as cx:
        rows = cx.execute(
            "SELECT key_hash, plan, created_at, revoked_at, rate_limit_override, metadata FROM api_keys ORDER BY id DESC"
        ).fetchall()
    out: List[Dict] = []
    for r in rows:
        out.append(
            {
                "key_hash": r[0],
                "plan": r[1],
                "created_at": r[2],
                "revoked_at": r[3],
                "rate_limit_override": r[4],
                "metadata": r[5],
            }
        )
    return out


def revoke_key(raw_key: str) -> bool:
    init_db()
    kh = _hash_key(raw_key)
    now = int(time.time())
    with _conn() as cx:
        cur = cx.execute("UPDATE api_keys SET revoked_at=? WHERE key_hash=? AND revoked_at IS NULL", (now, kh))
        return cur.rowcount > 0


def rotate_key(raw_key: str) -> Optional[str]:
    init_db()
    kh_old = _hash_key(raw_key)
    with _conn() as cx:
        row = cx.execute("SELECT plan, rate_limit_override, metadata FROM api_keys WHERE key_hash=? AND revoked_at IS NULL", (kh_old,)).fetchone()
        if not row:
            return None
        plan, rlo, meta = row
    revoke_key(raw_key)
    return add_key(plan=plan, rate_limit_override=rlo, metadata=meta)


def get_plan_for_key(raw_key: str) -> Optional[str]:
    init_db()
    kh = _hash_key(raw_key)
    with _conn() as cx:
        row = cx.execute("SELECT plan, revoked_at FROM api_keys WHERE key_hash=? AND revoked_at IS NULL", (kh,)).fetchone()
        if not row:
            return None
        plan, revoked_at = row
        if revoked_at is not None:
            return None
        return plan


def get_plan_and_override(raw_key: str) -> Tuple[Optional[str], Optional[int]]:
    """Return (plan, rate_limit_override) for a key, or (None, None) if not found/revoked."""
    init_db()
    kh = _hash_key(raw_key)
    with _conn() as cx:
        row = cx.execute(
            "SELECT plan, revoked_at, rate_limit_override FROM api_keys WHERE key_hash=?",
            (kh,),
        ).fetchone()
        if not row:
            return None, None
        plan, revoked_at, rlo = row
        if revoked_at is not None:
            return None, None
        return plan, rlo


def set_plan_for_key(raw_key: str, plan: str) -> bool:
    init_db()
    kh = _hash_key(raw_key)
    with _conn() as cx:
        cur = cx.execute("UPDATE api_keys SET plan=? WHERE key_hash=?", (plan, kh))
        return cur.rowcount > 0


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
