import time
from typing import List
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from main import Reminder


def test_trigger_now_respects_pause_and_snooze():
    seen: List[str] = []

    def fake_toast(title: str, msg: str) -> None:
        seen.append(f"{title}:{msg}")

    r = Reminder(id="r1", message="msg", interval_minutes=1, show_toast=fake_toast)

    # paused -> no trigger
    r.pause()
    r.trigger_now()
    assert seen == []

    # resume but snoozed -> no trigger
    r.resume()
    r.snooze(minutes=5)
    r.trigger_now()
    assert seen == []

    # clear snooze -> should trigger
    r.snoozed_until = None
    r.trigger_now()
    assert seen == ["Break Reminder:msg"]
