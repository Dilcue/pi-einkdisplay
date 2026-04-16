# tests/test_buttons.py
import queue
import sys
from unittest.mock import MagicMock

sys.modules['gpiod'] = MagicMock()
sys.modules['gpiod.line'] = MagicMock()

import buttons


def test_wait_for_button_returns_pin(monkeypatch):
    q = queue.Queue()
    monkeypatch.setattr(buttons, "_press_queue", q)
    q.put(5)
    assert buttons.wait_for_button(1.0) == 5


def test_wait_for_button_returns_none_on_timeout(monkeypatch):
    q = queue.Queue()
    monkeypatch.setattr(buttons, "_press_queue", q)
    assert buttons.wait_for_button(0.05) is None


def test_wait_for_button_returns_correct_pin(monkeypatch):
    q = queue.Queue()
    monkeypatch.setattr(buttons, "_press_queue", q)
    q.put(6)
    assert buttons.wait_for_button(1.0) == 6


