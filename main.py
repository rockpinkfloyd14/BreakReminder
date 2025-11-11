import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Dict, Optional, Callable, List

import pystray
from pystray import MenuItem as Item, Menu
from PIL import Image, ImageDraw
from win10toast import ToastNotifier

import tkinter as tk
from tkinter import simpledialog, messagebox

try:
    import winreg  # type: ignore
except Exception:  # pragma: no cover
    winreg = None  # Not on Windows?


# ----------------------------- Utilities -----------------------------

def create_tray_image(width: int = 64, height: int = 64) -> Image.Image:
    # Simple circle icon
    img = Image.new('RGBA', (width, height), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    r = min(width, height) // 2 - 6
    center = (width // 2, height // 2)
    d.ellipse(
        [center[0]-r, center[1]-r, center[0]+r, center[1]+r],
        fill=(66, 133, 244, 255),
        outline=(25, 103, 210, 255),
        width=3,
    )
    d.text((width//2 - 10, height//2 - 9), "BR", fill=(255, 255, 255, 255))
    return img


def ask_user_input(prompt: str, initial: str = "") -> Optional[str]:
    root = tk.Tk()
    root.withdraw()
    try:
        return simpledialog.askstring("Break Reminder", prompt, initialvalue=initial, parent=root)
    finally:
        root.destroy()


def ask_user_number(prompt: str, initial: int = 30) -> Optional[int]:
    root = tk.Tk()
    root.withdraw()
    try:
        value = simpledialog.askinteger("Break Reminder", prompt, initialvalue=initial, minvalue=1, maxvalue=7*24*60, parent=root)
        return value
    finally:
        root.destroy()


def confirm(prompt: str) -> bool:
    root = tk.Tk()
    root.withdraw()
    try:
        return messagebox.askyesno("Break Reminder", prompt, parent=root)
    finally:
        root.destroy()


def is_windows_toasts_disabled() -> bool:
    # Best-effort check: if toasts are disabled (Focus Assist), many systems set this REG_DWORD to 0
    try:
        if winreg is None:
            return False
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Notifications\\Settings")
        val, _ = winreg.QueryValueEx(key, "NOC_GLOBAL_SETTING_TOASTS_ENABLED")
        winreg.CloseKey(key)
        # 1 -> toasts enabled, 0 -> disabled
        return val == 0
    except Exception:
        return False


# ----------------------------- Core logic -----------------------------

@dataclass
class Reminder:
    id: str
    message: str
    interval_minutes: int
    show_toast: Callable[[str, str], None]

    paused: bool = False
    _stop: threading.Event = field(default_factory=threading.Event, init=False)
    _thread: Optional[threading.Thread] = field(default=None, init=False)

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self._run, name=f"Reminder-{self.id}", daemon=True)
        self._thread.start()

    def _run(self) -> None:
        # Initial delay equals the interval so it reminds after the configured time
        wait_seconds = max(60, int(self.interval_minutes * 60))
        while not self._stop.wait(wait_seconds):
            if not self.paused:
                self.show_toast("Break Reminder", self.message)

    def trigger_now(self) -> None:
        if not self.paused:
            self.show_toast("Break Reminder", self.message)

    def pause(self) -> None:
        self.paused = True

    def resume(self) -> None:
        self.paused = False

    def terminate(self) -> None:
        self._stop.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)


class App:
    def __init__(self) -> None:
        self.notifier = ToastNotifier()
        self.reminders: Dict[str, Reminder] = {}
        self.muted: bool = False
        self.follow_focus_assist: bool = False

        self.icon = pystray.Icon(
            name="BreakReminder",
            title="Break Reminder",
            icon=create_tray_image(),
            menu=self.build_menu(),
        )

    # --------------- Notifications ---------------
    def show_toast(self, title: str, msg: str) -> None:
        if self.muted:
            return
        if self.follow_focus_assist and is_windows_toasts_disabled():
            return
        try:
            # Shows a banner-style toast in Windows action center area
            self.notifier.show_toast(title, msg, duration=5, threaded=True)
        except Exception:
            # Avoid crashing if notifications fail
            pass

    # --------------- Reminders management ---------------
    def add_reminder(self, message: str, interval_minutes: int) -> None:
        rid = str(uuid.uuid4())[:8]
        reminder = Reminder(
            id=rid,
            message=message,
            interval_minutes=interval_minutes,
            show_toast=self.show_toast,
        )
        reminder.start()
        self.reminders[rid] = reminder
        self.refresh_menu()

    def terminate_reminder(self, rid: str) -> None:
        r = self.reminders.get(rid)
        if r:
            r.terminate()
            del self.reminders[rid]
            self.refresh_menu()

    # --------------- Menu building ---------------
    def build_menu(self) -> Menu:
        def active_reminders_menu() -> List[Item]:
            items: List[Item] = []
            if not self.reminders:
                items.append(Item("(none)", lambda: None, enabled=False))
                return items
            for rid, r in list(self.reminders.items()):
                label = f"{r.message[:20]}… ({r.interval_minutes}m)" if len(r.message) > 20 else f"{r.message} ({r.interval_minutes}m)"
                items.append(Item(label, Menu(
                    Item("Trigger now", lambda rid=rid: self.trigger_now(rid)),
                    Item("Pause" if not r.paused else "Resume", lambda rid=rid: self.toggle_pause(rid)),
                    Item("Terminate", lambda rid=rid: self.terminate_reminder(rid)),
                )))
            return items

        return Menu(
            Item("Add Reminder…", self.menu_add_reminder),
            Item("Active Reminders", Menu(*active_reminders_menu())),
            Item(lambda item: f"Mute notifications: {'On' if self.muted else 'Off'}", self.toggle_mute),
            Item(lambda item: f"Follow Windows Focus Assist: {'On' if self.follow_focus_assist else 'Off'}", self.toggle_follow_focus_assist),
            Item("Quit", self.quit),
        )

    def refresh_menu(self) -> None:
        self.icon.menu = self.build_menu()
        try:
            self.icon.update_menu()
        except Exception:
            pass

    # --------------- Menu actions ---------------
    def menu_add_reminder(self, icon: pystray.Icon, item: Item) -> None:
        message = ask_user_input("Reminder message:", initial="Don't forget to take a break")
        if not message:
            return
        interval = ask_user_number("Interval (minutes):", initial=30)
        if not interval:
            return
        self.add_reminder(message, int(interval))

    def toggle_mute(self, icon: pystray.Icon, item: Item) -> None:
        self.muted = not self.muted
        self.refresh_menu()

    def toggle_follow_focus_assist(self, icon: pystray.Icon, item: Item) -> None:
        self.follow_focus_assist = not self.follow_focus_assist
        self.refresh_menu()

    def trigger_now(self, rid: str) -> None:
        r = self.reminders.get(rid)
        if r:
            r.trigger_now()

    def toggle_pause(self, rid: str) -> None:
        r = self.reminders.get(rid)
        if not r:
            return
        if r.paused:
            r.resume()
        else:
            r.pause()
        self.refresh_menu()

    def quit(self, icon: pystray.Icon, item: Item) -> None:
        # Confirm quit
        if not confirm("Quit Break Reminder and stop all reminders?"):
            return
        for r in list(self.reminders.values()):
            r.terminate()
        self.reminders.clear()
        self.icon.stop()

    # --------------- Entry point ---------------
    def run(self) -> None:
        self.icon.run()


if __name__ == "__main__":
    App().run()
