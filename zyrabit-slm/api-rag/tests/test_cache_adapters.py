import time
from app.infrastructure.adapters.sqlite_cache_adapter import SqliteCacheAdapter
from app.infrastructure.shared.state_tracker import SovereignStateManager

def test_sqlite_cache_adapter_crud(monkeypatch, tmp_path):
    # Set DB_PATH to a temporary location for the test
    db_file = str(tmp_path / "test_cache.db")
    monkeypatch.setattr(SovereignStateManager, "DB_PATH", db_file)
    
    # Initialize DB schema
    SovereignStateManager.init_db()

    adapter = SqliteCacheAdapter()

    # Get non-existent
    assert adapter.get("missing") is None

    # Set and Get
    payload = {"data": "test-data", "status": 200}
    adapter.set("test-key", payload, ttl_seconds=2)
    assert adapter.get("test-key") == payload

    # Delete
    adapter.delete("test-key")
    assert adapter.get("test-key") is None

def test_sqlite_cache_adapter_lazy_expiry(monkeypatch, tmp_path):
    db_file = str(tmp_path / "test_cache_expiry.db")
    monkeypatch.setattr(SovereignStateManager, "DB_PATH", db_file)
    SovereignStateManager.init_db()

    adapter = SqliteCacheAdapter()
    payload = {"expired": "value"}
    
    # Set with 1s TTL
    adapter.set("expire-key", payload, ttl_seconds=1)
    assert adapter.get("expire-key") == payload

    # Wait for TTL to expire
    time.sleep(1.2)
    assert adapter.get("expire-key") is None
