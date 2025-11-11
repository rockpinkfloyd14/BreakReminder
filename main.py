import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Dict, Optional, Callable, List

import pystray
from pystray import MenuItem as Item, Menu
from PIL import Image, ImageDraw, ImageFont
from winotify import Notification, audio

import tkinter as tk
from tkinter import simpledialog, messagebox
from tkinter import ttk
import sys
import os

try:
    import winreg  # type: ignore
except Exception:  # pragma: no cover
    winreg = None  # Not on Windows?

# Optional: single-instance via Windows named mutex
try:
    import win32event  # type: ignore
    import win32api    # type: ignore
    import winerror    # type: ignore
except Exception:  # pragma: no cover
    win32event = None
    win32api = None
    winerror = None


# ----------------------------- Single-instance -----------------------------
SINGLETON_MUTEX_HANDLE = None


def another_instance_running() -> bool:
    """Returns True if another instance is already running (Windows only)."""
    global SINGLETON_MUTEX_HANDLE
    if win32event is None or win32api is None or winerror is None:
        return False
    try:
        # Use a Global mutex so it works across sessions
        name = "Global\\BreakReminderSingleton"
        handle = win32event.CreateMutex(None, True, name)
        # If already exists, GetLastError will be ERROR_ALREADY_EXISTS
        already = (win32api.GetLastError() == winerror.ERROR_ALREADY_EXISTS)
        if already:
            # Release our handle immediately
            try:
                win32api.CloseHandle(handle)
            except Exception:
                pass
            return True
        # Keep handle open for lifetime of process
        SINGLETON_MUTEX_HANDLE = handle
        return False
    except Exception:
        return False

# ----------------------------- Utilities -----------------------------

def ensure_assets() -> str:
    """Create basic assets (logo.png, logo.ico, header.png) if missing. Returns assets dir."""
    base = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
    os.makedirs(base, exist_ok=True)

    logo_png = os.path.join(base, "logo.png")
    logo_ico = os.path.join(base, "logo.ico")
    header_png = os.path.join(base, "header.png")

    if not os.path.exists(logo_png):
        img = Image.new("RGBA", (256, 256), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        # rounded rectangle background
        bg = (66, 133, 244, 255)
        d.rounded_rectangle([16, 16, 240, 240], radius=48, fill=bg)
        # text "BR"
        try:
            font = ImageFont.truetype("seguiemj.ttf", 120)
        except Exception:
            font = ImageFont.load_default()
        tw, th = d.textsize("BR", font=font)
        d.text(((256 - tw)//2, (256 - th)//2 - 10), "BR", fill=(255, 255, 255, 255), font=font)
        img.save(logo_png)
        # Save ICO at multiple sizes
        img.save(logo_ico, sizes=[(16,16), (32,32), (48,48), (64,64), (128,128), (256,256)])

    if not os.path.exists(header_png):
        w, h = 1000, 120
        hdr = Image.new("RGBA", (w, h), (245, 247, 250, 255))
        d = ImageDraw.Draw(hdr)
        # subtle bottom border
        d.line([(0, h-1), (w, h-1)], fill=(200, 208, 218, 255), width=1)
        # paste logo
        try:
            logo = Image.open(logo_png).convert("RGBA").resize((72, 72), Image.LANCZOS)
            hdr.paste(logo, (24, (h-72)//2), logo)
        except Exception:
            pass
        # title text
        try:
            font = ImageFont.truetype("segoeui.ttf", 28)
        except Exception:
            font = ImageFont.load_default()
        d.text((112, (h-28)//2 - 6), "Break Reminder", fill=(30, 30, 30, 255), font=font)
        d.text((112, (h-28)//2 + 22), "Stay healthy with periodic break reminders", fill=(90, 90, 90, 255))
        hdr.save(header_png)

    return base


def create_tray_image(width: int = 64, height: int = 64) -> Image.Image:
    # Prefer bundled logo
    try:
        assets = ensure_assets()
        p = os.path.join(assets, "logo.png")
        img = Image.open(p).convert("RGBA").resize((width, height), Image.LANCZOS)
        return img
    except Exception:
        # Fallback simple circle icon
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
    """Larger, multi-line input dialog for composing reminder messages."""
    class _TextDialog(simpledialog.Dialog):
        def __init__(self, parent, title: str, prompt: str, initial: str) -> None:
            self._prompt = prompt
            self._initial = initial or ""
            self.result: Optional[str] = None
            super().__init__(parent=parent, title=title)

        def body(self, master):  # type: ignore[override]
            ttk.Label(master, text=self._prompt, anchor="w").grid(row=0, column=0, sticky="w", pady=(0, 6))
            self.text = tk.Text(master, width=60, height=8, wrap="word")
            self.text.grid(row=1, column=0, sticky="nsew")
            self.text.insert("1.0", self._initial)
            master.rowconfigure(1, weight=1)
            master.columnconfigure(0, weight=1)
            return self.text

        def apply(self) -> None:  # type: ignore[override]
            self.result = self.text.get("1.0", "end").strip()

    root = tk.Tk()
    root.withdraw()
    try:
        dlg = _TextDialog(root, "Break Reminder", prompt, initial)
        return dlg.result
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
    snoozed_until: Optional[float] = None
    _stop: threading.Event = field(default_factory=threading.Event, init=False)
    _thread: Optional[threading.Thread] = field(default=None, init=False)

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self._run, name=f"Reminder-{self.id}", daemon=True)
        self._thread.start()

    def _run(self) -> None:
        # Wait for the configured interval; be responsive to edits/stops
        while not self._stop.is_set():
            wait_seconds = max(60, int(self.interval_minutes * 60))
            remaining = wait_seconds
            while remaining > 0 and not self._stop.is_set():
                # sleep in 1s steps so edits and stop apply sooner
                if self._stop.wait(1):
                    return
                remaining -= 1
            if self._stop.is_set():
                break
            now = time.time()
            if self.snoozed_until and now < self.snoozed_until:
                # still snoozed; skip this cycle
                continue
            if not self.paused:
                self.show_toast("Break Reminder", self.message)

    def trigger_now(self) -> None:
        if self.paused:
            return
        if self.snoozed_until and time.time() < self.snoozed_until:
            return
        self.show_toast("Break Reminder", self.message)

    def pause(self) -> None:
        self.paused = True

    def resume(self) -> None:
        self.paused = False

    def snooze(self, minutes: int = 5) -> None:
        self.snoozed_until = time.time() + max(1, int(minutes)) * 60

    def terminate(self) -> None:
        self._stop.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)


class App:
    def __init__(self) -> None:
        # Core state
        # AppUserModelID helps Windows group notifications and show reliably in Action Center
        self.app_id = "BreakReminder.BR"
        try:
            import ctypes  # set process AppUserModelID for toasts
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(self.app_id)
        except Exception:
            pass
        self.reminders: Dict[str, Reminder] = {}
        self.muted: bool = False
        self.follow_focus_assist: bool = False

        # Main window (taskbar-visible)
        self.root = tk.Tk()
        self.root.title("Break Reminder")
        self.root.geometry("900x560")
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.root.bind("<Unmap>", self.on_unmap)

        # Style/theme for a more native Windows look
        try:
            style = ttk.Style(self.root)
            if 'vista' in style.theme_names():
                style.theme_use('vista')
        except Exception:
            pass

        # App assets and icon
        self.assets_dir = ensure_assets()
        try:
            from tkinter import PhotoImage
            self.window_icon = PhotoImage(file=os.path.join(self.assets_dir, 'logo.png'))
            self.root.iconphoto(True, self.window_icon)
        except Exception:
            self.window_icon = None

        # UI variables
        self.muted_var = tk.BooleanVar(value=self.muted)
        self.follow_focus_var = tk.BooleanVar(value=self.follow_focus_assist)

        # Build UI content
        self._tree_items: Dict[str, str] = {}
        self.build_ui()

        # System tray icon (runs detached; we control via menu)
        self.icon = pystray.Icon(
            name="BreakReminder",
            title="Break Reminder",
            icon=create_tray_image(),
            menu=self.build_menu(),
        )

    # --------------- UI (window) ---------------
    def build_ui(self) -> None:
        # Header banner
        header = ttk.Frame(self.root)
        header.grid(row=0, column=0, columnspan=2, sticky="ew")
        try:
            from tkinter import PhotoImage
            self.header_img = PhotoImage(file=os.path.join(self.assets_dir, 'header.png'))
            ttk.Label(header, image=self.header_img).pack(fill="x")
        except Exception:
            ttk.Label(header, text="Break Reminder", font=("Segoe UI", 16, "bold")).pack(side="left", padx=12, pady=8)

        # Tree (reminders list)
        columns = ("message", "interval", "status")
        self.tree = ttk.Treeview(self.root, columns=columns, show="headings", selectmode="browse")
        self.tree.heading("message", text="Message")
        self.tree.heading("interval", text="Interval (min)")
        self.tree.heading("status", text="Status")
        self.tree.column("message", width=380, anchor="w")
        self.tree.column("interval", width=110, anchor="center")
        self.tree.column("status", width=120, anchor="center")

        yscroll = ttk.Scrollbar(self.root, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=yscroll.set)
        self.tree.grid(row=1, column=0, sticky="nsew", padx=(8, 0), pady=8)
        yscroll.grid(row=1, column=1, sticky="ns", pady=8, padx=(0, 8))

        # Buttons / toggles
        btn_frame = ttk.Frame(self.root)
        btn_frame.grid(row=2, column=0, columnspan=2, sticky="ew", padx=8, pady=(0, 8))
        btn_frame.columnconfigure(0, weight=1)
        btn_frame.columnconfigure(1, weight=1)
        btn_frame.columnconfigure(2, weight=1)
        btn_frame.columnconfigure(3, weight=1)
        btn_frame.columnconfigure(4, weight=1)
        btn_frame.columnconfigure(5, weight=1)

        ttk.Button(btn_frame, text="Add Reminder…", command=self.ui_add_reminder).grid(row=0, column=0, padx=4)
        ttk.Button(btn_frame, text="Edit…", command=self.ui_edit_reminder).grid(row=0, column=1, padx=4)
        ttk.Button(btn_frame, text="Trigger now", command=self.ui_trigger_now).grid(row=0, column=2, padx=4)
        ttk.Button(btn_frame, text="Snooze 5 min", command=self.ui_snooze_5).grid(row=0, column=3, padx=4)
        ttk.Button(btn_frame, text="Pause/Resume", command=self.ui_toggle_pause).grid(row=0, column=4, padx=4)
        ttk.Button(btn_frame, text="Terminate", command=self.ui_terminate).grid(row=0, column=5, padx=4)

        chk_frame = ttk.Frame(self.root)
        chk_frame.grid(row=3, column=0, columnspan=2, sticky="ew", padx=8, pady=(0, 8))
        ttk.Checkbutton(chk_frame, text="Mute notifications (DND)", variable=self.muted_var, command=self.ui_toggle_mute).pack(side="left", padx=4)
        ttk.Checkbutton(chk_frame, text="Follow Windows Focus Assist", variable=self.follow_focus_var, command=self.ui_toggle_follow_focus).pack(side="left", padx=12)
        ttk.Button(chk_frame, text="Quit", command=lambda: self.quit(self.icon, None)).pack(side="right", padx=4)

        # Layout behavior
        self.root.rowconfigure(1, weight=1)
        self.root.columnconfigure(0, weight=1)

        # Menu bar (Help)
        try:
            menubar = tk.Menu(self.root)
            helpmenu = tk.Menu(menubar, tearoff=0)
            helpmenu.add_command(label="Help…", command=self.show_help)
            helpmenu.add_command(label="About…", command=self.show_about)
            menubar.add_cascade(label="Help", menu=helpmenu)
            self.root.config(menu=menubar)
        except Exception:
            pass

        # Initial fill
        self.refresh_tree()

    def refresh_tree(self) -> None:
        # Clear and repopulate the tree with current reminders
        for item in self.tree.get_children():
            self.tree.delete(item)
        self._tree_items.clear()
        for rid, r in self.reminders.items():
            if r.paused:
                status = "Paused"
            elif r.snoozed_until and time.time() < r.snoozed_until:
                until = time.strftime('%H:%M', time.localtime(r.snoozed_until))
                status = f"Snoozed until {until}"
            else:
                status = "Running"
            iid = self.tree.insert("", "end", iid=rid, values=(r.message, r.interval_minutes, status))
            self._tree_items[rid] = iid

    def get_selected_rid(self) -> Optional[str]:
        sel = self.tree.selection()
        if not sel:
            return None
        return sel[0]

    def show_window(self, icon: Optional[pystray.Icon] = None, item: Optional[Item] = None) -> None:
        try:
            self.root.deiconify()
            # Open in normal (medium) size
            self.root.state('normal')
            self.root.lift()
            self.root.focus_force()
        except Exception:
            pass

    def on_unmap(self, event=None) -> None:
        # Minimize to tray: when minimized, hide window but keep app running via tray
        try:
            if self.root.state() == 'iconic':
                self.root.withdraw()
        except Exception:
            pass

    def on_close(self) -> None:
        # Close button behaves like minimize to tray (not quitting)
        try:
            self.root.iconify()
        except Exception:
            pass

    # UI action wrappers mapping to menu logic
    def ui_add_reminder(self) -> None:
        self.menu_add_reminder(self.icon, None)  # reuse dialog flow
        self.refresh_tree()

    def ui_edit_reminder(self) -> None:
        rid = self.get_selected_rid()
        if rid:
            self.edit_reminder(rid)

    def ui_trigger_now(self) -> None:
        rid = self.get_selected_rid()
        if not rid:
            if len(self.reminders) == 1:
                rid = next(iter(self.reminders.keys()))
            else:
                messagebox.showinfo("Break Reminder", "Select a reminder first.")
                return
        self.trigger_now(rid)

    def ui_toggle_pause(self) -> None:
        rid = self.get_selected_rid()
        if rid:
            self.toggle_pause(rid)
            self.refresh_tree()

    def ui_snooze_5(self) -> None:
        rid = self.get_selected_rid()
        if not rid:
            if len(self.reminders) == 1:
                rid = next(iter(self.reminders.keys()))
            else:
                messagebox.showinfo("Break Reminder", "Select a reminder first.")
                return
        self.snooze_reminder(rid, minutes=5)

    def ui_terminate(self) -> None:
        rid = self.get_selected_rid()
        if rid:
            self.terminate_reminder(rid)
            self.refresh_tree()

    def ui_toggle_mute(self) -> None:
        self.muted = bool(self.muted_var.get())
        self.refresh_menu()

    def ui_toggle_follow_focus(self) -> None:
        self.follow_focus_assist = bool(self.follow_focus_var.get())
        self.refresh_menu()

    # --------------- Notifications ---------------
    def show_toast(self, title: str, msg: str) -> None:
        if self.muted:
            return
        if self.follow_focus_assist and is_windows_toasts_disabled():
            return
        try:
            toast = Notification(app_id=self.app_id, title=title, msg=msg, duration="short")
            toast.set_audio(audio.Default, loop=False)
            toast.show()
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
        self.refresh_tree()

    def edit_reminder(self, rid: str) -> None:
        r = self.reminders.get(rid)
        if not r:
            return
        new_msg = ask_user_input("Edit reminder message:", initial=r.message)
        if new_msg is None:
            return
        new_interval = ask_user_number("Edit interval (minutes):", initial=r.interval_minutes)
        if not new_interval:
            return
        r.message = new_msg.strip()
        r.interval_minutes = int(new_interval)
        self.refresh_menu()
        self.refresh_tree()

    def terminate_reminder(self, rid: str) -> None:
        r = self.reminders.get(rid)
        if r:
            r.terminate()
            del self.reminders[rid]
            self.refresh_menu()
            self.refresh_tree()

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
                    Item("Edit…", lambda rid=rid: self.edit_reminder(rid)),
                    Item("Trigger now", lambda rid=rid: self.trigger_now(rid)),
                    Item("Snooze 5 min", lambda rid=rid: self.snooze_reminder(rid, 5)),
                    Item("Pause" if not r.paused else "Resume", lambda rid=rid: self.toggle_pause(rid)),
                    Item("Terminate", lambda rid=rid: self.terminate_reminder(rid)),
                )))
            return items

        return Menu(
            Item("Show Window", self.show_window, default=True),
            Item("Add Reminder…", self.menu_add_reminder),
            Item("Active Reminders", Menu(*active_reminders_menu())),
            Item(lambda item: f"Mute notifications: {'On' if self.muted else 'Off'}", self.toggle_mute),
            Item(lambda item: f"Follow Windows Focus Assist: {'On' if self.follow_focus_assist else 'Off'}", self.toggle_follow_focus_assist),
            Item("Quit", self.quit),
            Item("Quit (force)", self.quit_force),
        )

    def refresh_menu(self) -> None:
        self.icon.menu = self.build_menu()
        try:
            self.icon.update_menu()
        except Exception:
            pass

    # --------------- Menu actions ---------------
    def show_help(self) -> None:
        msg = (
            "Break Reminder helps you take periodic breaks.\n\n"
            "- Add reminders with custom messages and intervals.\n"
            "- Snooze a reminder for 5 minutes from the window or tray.\n"
            "- Mute notifications or follow Windows Focus Assist.\n"
            "- Tray menu lets you trigger, pause/resume, edit, or terminate reminders.\n\n"
            "Author: Arjun Sharma\n"
            "Email: arjunsharma9112@gmail.com"
        )
        messagebox.showinfo("Break Reminder - Help", msg)

    def show_about(self) -> None:
        msg = (
            "Break Reminder v1.x\n\n"
            "Author: Arjun Sharma\n"
            "Email: arjunsharma9112@gmail.com\n"
            "License: MIT (proposed)"
        )
        messagebox.showinfo("About Break Reminder", msg)

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
        self.refresh_tree()

    def toggle_follow_focus_assist(self, icon: pystray.Icon, item: Item) -> None:
        self.follow_focus_assist = not self.follow_focus_assist
        self.refresh_menu()
        self.refresh_tree()

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
        self.refresh_tree()

    def snooze_reminder(self, rid: str, minutes: int = 5) -> None:
        r = self.reminders.get(rid)
        if not r:
            return
        r.snooze(minutes)
        self.refresh_tree()

    def quit(self, icon: pystray.Icon, item: Item) -> None:
        # Graceful quit without confirmation to avoid UI blocking issues
        for r in list(self.reminders.values()):
            r.terminate()
        self.reminders.clear()
        try:
            self.icon.visible = False
        except Exception:
            pass
        # Call stop on a background thread to avoid deadlocks from menu callbacks
        threading.Thread(target=self.icon.stop, daemon=True).start()
        try:
            self.root.quit()
            self.root.destroy()
        except Exception:
            pass

    def quit_force(self, icon: pystray.Icon, item: Item) -> None:
        # Force-quit as a last resort
        for r in list(self.reminders.values()):
            r.terminate()
        self.reminders.clear()
        try:
            self.icon.visible = False
        except Exception:
            pass
        import os
        os._exit(0)

    # --------------- Entry point ---------------
    def run(self) -> None:
        # Start tray icon in the background and show main window on taskbar
        try:
            self.icon.run_detached()
        except Exception:
            # Fallback to blocking run if detached not available
            threading.Thread(target=self.icon.run, daemon=True).start()
        self.show_window()
        self.root.mainloop()


def _bring_existing_to_front() -> bool:
    try:
        import ctypes
        user32 = ctypes.windll.user32
        hwnd = user32.FindWindowW(None, "Break Reminder")
        if hwnd:
            SW_RESTORE = 9
            user32.ShowWindow(hwnd, SW_RESTORE)
            user32.SetForegroundWindow(hwnd)
            return True
    except Exception:
        pass
    return False


if __name__ == "__main__":
    # Enforce single instance (Windows)
    if another_instance_running():
        # Try to bring the already-running window to the foreground instead of showing a dialog
        _bring_existing_to_front()
        sys.exit(0)
    App().run()
