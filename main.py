# ==================================================
# Nuvix Suite Render Edition (Global Launcher)
# Compatible con Python 3.13 y Render
# ==================================================

import os, subprocess, time

print("🚀 Starting Nuvix Suite Render Edition (patched launcher)")

# Lista de bots y sus variables de entorno
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

processes = []

for folder, token_env in BOTS:
    token = os.environ.get(token_env)
    if not token:
        print(f"⚠️ Skipping {folder} — missing token variable ({token_env})")
        continue

    path = os.path.join(os.getcwd(), folder, "bot.py")
    if not os.path.exists(path):
        print(f"❌ Skipping {folder} — bot.py not found at {path}")
        continue

    print(f"✅ Launching {folder} ...")

    # 🪄 Este comando inyecta el fix antes de importar discord
    launch_cmd = [
        "python",
        "-c",
        f"import sys; sys.modules['audioop']=None; exec(open(r'{path}').read())",
    ]

    p = subprocess.Popen(launch_cmd)
    processes.append(p)
    time.sleep(2)

print("✨ All available bots launched successfully.")
print("💡 Press CTRL + C to stop all bots.")

try:
    while True:
        time.sleep(60)
except KeyboardInterrupt:
    print("🛑 Stopping all bots...")
    for p in processes:
        p.terminate()
