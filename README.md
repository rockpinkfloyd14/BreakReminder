# Break Reminder

A lightweight Windows system-tray app for custom break reminders.

Features
- Multiple concurrent reminders, each with its own interval and message
- System tray menu to add, pause/resume, trigger-now, and terminate reminders
- Mute (DND) toggle in the tray menu
- Optional: Follow Windows Focus Assist (auto-mutes when toasts are disabled)
- Toast banner notifications

Quick start (dev)
1) Create a virtual environment and install deps
   - PowerShell
     - python -m venv .venv
     - .venv\Scripts\Activate.ps1
     - pip install -r requirements.txt
2) Run
   - python main.py

Build a standalone .exe
1) Install PyInstaller
   - pip install pyinstaller
2) Build
   - pyinstaller --noconsole --onefile --name BreakReminder main.py
3) The exe will be at `dist/BreakReminder.exe`

Notes
- The tray icon menu appears in the Windows system tray.
- When "Mute notifications" is enabled, reminders will keep time but will not show toasts until un-muted.
- If "Follow Windows Focus Assist" is enabled, the app will try to detect when Windows toasts are disabled and auto-mute. This may vary by Windows version/config.
- To start multiple reminders, use Tray icon -> Add Reminder... as many times as you like.
- To terminate a reminder, open Tray icon -> Active Reminders -> select the reminder -> Terminate.
