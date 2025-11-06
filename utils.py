import discord
import json
import os
from datetime import datetime

# Añade estas variables si no existen
from pathlib import Path

# ✅ Corrige DATA_DIR para que funcione con /
DATA_DIR = Path(os.getcwd()) / "data"
DATA_DIR.mkdir(exist_ok=True)                 # Ruta donde se guardan backups o logs
OWNER_ROLE_IDS = [1432829605298962534]       # ID del Owner
COOWNER_ROLE_IDS = [1432829606066520144]              # Añade los co-owner si tienes
HIGHSTAFF_ROLE_IDS = [1432829628938059886]                      # Añade los IDs del high staff
STAFF_ROLE_IDS = [1432829631852970095]       # ID del Staff

# ==============================
# 📦 Global Configuration
# ==============================
BANNER_URL = os.getenv("BANNER_URL", "")
FOOTER_TEXT = os.getenv("FOOTER_TEXT", "Nuvix Market • Your wishes, more cheap!")
LOGS_CMD_USE_CHANNEL_ID = os.getenv("LOGS_CMD_USE_CHANNEL_ID")

# ==============================
# 🧠 Permission Helpers
# ==============================
def can_staff(member: discord.Member):
    """Return True if user is staff or higher."""
    allowed_roles = os.getenv("STAFF_ROLE_IDS", "").split(",")
    return any(str(role.id) in allowed_roles for role in member.roles)

def can_highstaff_or_above(member: discord.Member):
    """Return True if user is high staff or higher."""
    allowed_roles = os.getenv("HIGHSTAFF_ROLE_IDS", "").split(",")
    return any(str(role.id) in allowed_roles for role in member.roles)

def can_owner_or_coowner(member: discord.Member):
    """Return True if user is owner or co-owner."""
    allowed_roles = (
        os.getenv("OWNER_ROLE_IDS", "").split(",") +
        os.getenv("COOWNER_ROLE_IDS", "").split(",")
    )
    return any(str(role.id) in allowed_roles for role in member.roles)

# ==============================
# 🧾 Logging Utilities
# ==============================
def log_to_json(filename: str, data: dict):
    """Save logs in JSON format."""
    os.makedirs("logs", exist_ok=True)
    filepath = os.path.join("logs", f"{filename}.json")

    log_entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "data": data
    }

    with open(filepath, "a", encoding="utf-8") as f:
        json.dump(log_entry, f, ensure_ascii=False)
        f.write("\n")

# ==============================
# 🖼 Embed Builder
# ==============================
def default_embed(title: str = "", description: str = "", color=0x5865F2):
    """Create a styled embed with banner and footer."""
    embed = discord.Embed(title=title, description=description, color=color)
    if BANNER_URL:
        embed.set_image(url=BANNER_URL)
    embed.set_footer(text=FOOTER_TEXT)
    return embed

# ==============================
# 🧰 Misc Tools
# ==============================
def format_time(ts: datetime):
    return ts.strftime("%Y-%m-%d %H:%M:%S")

def get_env_value(name: str, default=None):
    """Shortcut to safely load values from environment variables."""
    return os.getenv(name, default)

def log_console(msg: str):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")
