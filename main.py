# ==========================================================
# NUVIX SUITE RENDER EDITION - MAIN LAUNCHER
# ----------------------------------------------------------
# ✅ Runs ALL Nuvix bots from one window / Render service
# ✅ Reads ONLY Render environment variables (NOT .env)
# ✅ Requires: python 3.11+ and all bot folders with bot.py
# ==========================================================
import sys
sys.modules['audioop'] = None
import os
import subprocess
import time

# List of all Nuvix bots and their expected environment variables (Render-side)
BOTS = [
    ("nuvix_ai", "NUVIX_AI_TOKEN"),
    ("nuvix_apps", "NUVIX_APPS_TOKEN"),
    ("nuvix_backup", "NUVIX_BACKUP_TOKEN"),
    ("nuvix_information", "NUVIX_INFORMATION_TOKEN"),
    ("nuvix_invoices", "NUVIX_INVOICES_TOKEN"),
    ("nuvix_machine", "NUVIX_MACHINE_TOKEN"),
    ("nuvix_management", "NUVIX_MANAGEMENT_TOKEN"),
    ("nuvix_sanctions", "NUVIX_SANCTIONS_TOKEN"),
    ("nuvix_system", "NUVIX_SYSTEM_TOKEN"),
    ("nuvix_tickets", "NUVIX_TICKETS_TOKEN"),
]

print("🚀 Starting Nuvix Suite Render Edition (single launcher)\n")
processes = []

for folder, token_env in BOTS:
    token = os.environ.get(token_env)
    if not token:
        print(f"⚠️ Skipping {folder} — missing Render environment variable: {token_env}")
        continue

    path = os.path.join(os.getcwd(), "bots", folder, "bot.py")
    if not os.path.exists(path):
        # fallback if bots are in root folders
        path = os.path.join(os.getcwd(), folder, "bot.py")

    print(f"✅ Launching {folder} ...")
    process = subprocess.Popen(["python", path])
    processes.append(process)
    time.sleep(1.5)

print("\n✨ All available bots launched successfully.")
print("💡 Press CTRL + C to stop all bots.\n")

try:
    for process in processes:
        process.wait()
except KeyboardInterrupt:
    print("\n🛑 Stopping all bots...")
    for process in processes:
        process.terminate()
    print("✅ All bots stopped cleanly.")

