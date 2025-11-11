# BreakReminder v1.0.0

Highlights
- Native Windows toasts (winotify + AppUserModelID)
- Snooze 5 min per reminder (window + tray)
- Edit reminder (message + interval) while running
- Default tray double-click shows the window; window opens maximized
- Bring-to-front when launching a second instance
- Larger multi-line message dialog
- More responsive timer (applies interval edits without restart)

Install
- Download BreakReminder.exe from the Assets below (or the ZIP)
- Windows SmartScreen may warn because the app is unsigned
  - Click "More info" → "Run anyway"

Notes
- You can pin the tray icon: click the ^ overflow, drag the icon into the visible area
- Optional: Follow Windows Focus Assist to auto-mute during Focus Assist

Changelog
- Switch to winotify, add AppUserModelID
- Add Snooze 5 min (UI + tray), show "Snoozed until HH:MM" in the table
- Add Edit… for reminders (UI + tray)
- Make tray default action Show Window; maximize on show
- Implement bring-to-front on second launch
- Improve Trigger Now behavior when only one reminder exists
- Replace message input with multi-line dialog
- Make scheduler responsive to interval changes
