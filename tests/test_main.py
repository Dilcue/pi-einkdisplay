# tests/test_main.py
import os
import sys
from unittest.mock import MagicMock

os.environ["EINK_SIMULATE"] = "1"

sys.modules['gpiod'] = MagicMock()
sys.modules['gpiod.line'] = MagicMock()


def test_main_module_imports():
    import main  # should not raise ImportError or AttributeError
    assert hasattr(main, "DashboardPage")
    assert callable(main._fingerprint)
