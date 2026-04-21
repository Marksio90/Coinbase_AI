import importlib
import sys
from pathlib import Path

import pytest


@pytest.fixture
def config_module():
    pytest.importorskip("pydantic")
    pytest.importorskip("pydantic_settings")
    repo_root = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(repo_root / "shared" / "python"))
    module = importlib.import_module("common.config")
    module.reset_config_singleton()
    yield module
    module.reset_config_singleton()


def test_get_config_is_singleton(config_module, monkeypatch):
    monkeypatch.setenv("ENABLE_AI", "false")
    cfg_1 = config_module.get_config()
    cfg_2 = config_module.get_config()
    assert cfg_1 is cfg_2


def test_live_mode_requires_coinbase_key(config_module, monkeypatch):
    config_module.reset_config_singleton()
    monkeypatch.setenv("ENABLE_AI", "false")
    monkeypatch.setenv("TRADING_MODE", "live")
    monkeypatch.setenv("ENABLE_TRADING", "true")
    monkeypatch.setenv("ENABLE_EXECUTION", "true")
    monkeypatch.delenv("COINBASE_API_KEY", raising=False)

    with pytest.raises(Exception):
        config_module.get_config()


def test_ai_enabled_requires_openai_key(config_module, monkeypatch):
    config_module.reset_config_singleton()
    monkeypatch.setenv("ENABLE_AI", "true")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    with pytest.raises(Exception):
        config_module.get_config()
