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


import queue
from unittest.mock import patch, MagicMock
from PIL import Image


def _make_cat_image():
    return Image.new("RGB", (800, 480), (255, 0, 0))


def test_cat_mode_displays_cat_and_returns_on_sw2(monkeypatch):
    import main
    import buttons

    q = queue.Queue()
    monkeypatch.setattr(buttons, "_press_queue", q)
    monkeypatch.setattr(main, "display", MagicMock())

    q.put(6)  # SW2 — return immediately after first display

    with patch("main.cat_client.fetch", return_value=_make_cat_image()):
        main.cat_mode()

    main.display.update.assert_called_once()


def test_cat_mode_shows_new_cat_on_sw1(monkeypatch):
    import main
    import buttons

    q = queue.Queue()
    monkeypatch.setattr(buttons, "_press_queue", q)
    monkeypatch.setattr(main, "display", MagicMock())

    q.put(5)  # SW1 — new cat
    q.put(6)  # SW2 — exit

    with patch("main.cat_client.fetch", return_value=_make_cat_image()):
        main.cat_mode()

    assert main.display.update.call_count == 2


def test_cat_mode_shows_error_and_returns_on_fetch_failure(monkeypatch):
    import main
    import buttons

    q = queue.Queue()
    monkeypatch.setattr(buttons, "_press_queue", q)
    mock_display = MagicMock()
    mock_display.new_image.return_value = (MagicMock(), MagicMock())
    monkeypatch.setattr(main, "display", mock_display)
    monkeypatch.setattr(main.time, "sleep", MagicMock())

    with patch("main.cat_client.fetch", side_effect=RuntimeError("no cats")):
        main.cat_mode()

    # _show_no_cats calls display.update once with error screen, then returns
    mock_display.update.assert_called_once()


def test_cat_mode_returns_on_timeout(monkeypatch):
    import main
    import buttons

    q = queue.Queue()
    monkeypatch.setattr(buttons, "_press_queue", q)
    monkeypatch.setattr(main, "display", MagicMock())

    # Empty queue → wait_for_button returns None (timeout) immediately with 0.05s
    with patch("main.buttons.wait_for_button", side_effect=[None]):
        with patch("main.cat_client.fetch", return_value=_make_cat_image()):
            main.cat_mode()

    main.display.update.assert_called_once()
