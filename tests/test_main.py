# tests/test_main.py
import os
import sys
from unittest.mock import MagicMock

os.environ["EINK_SIMULATE"] = "1"

sys.modules['gpiod'] = MagicMock()
sys.modules['gpiod.line'] = MagicMock()


def test_main_module_imports():
    import main  # should not raise ImportError or AttributeError
    assert hasattr(main, "_PAGE_REGISTRY")
    assert "weather" in main._PAGE_REGISTRY
    assert "weather_current" not in main._PAGE_REGISTRY
    assert "weather_forecast" not in main._PAGE_REGISTRY
