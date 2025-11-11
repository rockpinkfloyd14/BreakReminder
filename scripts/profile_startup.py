import os
import time

# Ensure profiling is on
os.environ["BR_PROFILE_STARTUP"] = os.environ.get("BR_PROFILE_STARTUP", "1")

import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import main  # noqa: E402

# Remove existing profile log to avoid confusion
try:
    if os.path.exists(main.PROFILE_PATH):
        os.remove(main.PROFILE_PATH)
except Exception:
    pass

# Construct the app to exercise __init__ and UI build, then exit quickly
app = main.App()
# Give Tk a moment to settle and then destroy
app.root.update_idletasks()
print("Profile: constructed App; now destroying window")
app.root.destroy()
print("Profile log written to:", main.PROFILE_PATH)
