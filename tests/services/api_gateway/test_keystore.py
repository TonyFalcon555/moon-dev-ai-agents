import pytest
import os
from sqlalchemy import create_engine
from src.services.api_gateway import keystore

# Use in-memory SQLite for testing
TEST_DB_URL = "sqlite:///:memory:"

@pytest.fixture(autouse=True)
def setup_teardown():
    # Override the engine in keystore with test engine
    keystore.engine = create_engine(TEST_DB_URL, future=True)
    keystore.init_db()
    yield
    # Cleanup is automatic with in-memory DB

def test_add_and_get_key():
    key = keystore.add_key(plan="pro", metadata="test_user")
    assert key.startswith("md_")
    
    plan = keystore.get_plan_for_key(key)
    assert plan == "pro"

def test_list_keys():
    key1 = keystore.add_key(plan="basic")
    key2 = keystore.add_key(plan="pro")
    
    keys = keystore.list_keys()
    assert len(keys) == 2
    assert keys[0]["plan"] == "pro"  # Ordered by ID desc
    assert keys[1]["plan"] == "basic"

def test_revoke_key():
    key = keystore.add_key(plan="enterprise")
    assert keystore.get_plan_for_key(key) == "enterprise"
    
    assert keystore.revoke_key(key) is True
    assert keystore.get_plan_for_key(key) is None
    
    # Revoking again should fail
    assert keystore.revoke_key(key) is False

def test_rotate_key():
    key = keystore.add_key(plan="team", rate_limit_override=100)
    new_key = keystore.rotate_key(key)
    
    assert new_key is not None
    assert new_key != key
    
    # Old key should be revoked
    assert keystore.get_plan_for_key(key) is None
    
    # New key should have same properties
    plan, rlo = keystore.get_plan_and_override(new_key)
    assert plan == "team"
    assert rlo == 100
