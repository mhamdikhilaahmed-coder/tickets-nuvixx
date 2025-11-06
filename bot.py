import os
import json
import asyncio
import datetime as dt
from typing import Optional, Dict, Any, List

import discord_no_audio_patch  # disables audioop requirement
import discord
from discord import app_commands
from discord.ext import commands, tasks

# =============================
# Read environment (Render-only)
# =============================
TOKEN = os.getenv("TOKEN")
GUILD_ID = int(os.getenv("GUILD_ID", "0"))
TICKET_CATEGORY_ID = int(os.getenv("TICKET_CATEGORY_ID", "0"))

LOGS_CHANNEL_ID = int(os.getenv("LOGS_CHANNEL_ID", "0"))
CMD_LOGS_CHANNEL_ID = int(os.getenv("CMD_LOGS_CHANNEL_ID", "0"))
TRANSCRIPTS_CHANNEL_ID = int(os.getenv("TRANSCRIPTS_CHANNEL_ID", "0"))
REVIEWS_CHANNEL_ID = int(os.getenv("REVIEWS_CHANNEL_ID", "0"))

TRIAL_SUPPORT_ROLE_ID = int(os.getenv("TRIAL_SUPPORT_ROLE_ID", "0"))
SUPPORT_ROLE_ID       = int(os.getenv("SUPPORT_ROLE_ID", "0"))
STAFF_ROLE_ID         = int(os.getenv("STAFF_ROLE_ID", "0"))
HIGH_STAFF_ROLE_ID    = int(os.getenv("HIGH_STAFF_ROLE_ID", "0"))
ADMIN_ROLE_ID         = int(os.getenv("ADMIN_ROLE_ID", "0"))
OWNER_ROLE_ID         = int(os.getenv("OWNER_ROLE_ID", "0"))

BOT_NAME = "Nuvix Tickets"

# =============================
# Storage
# =============================
DATA_DIR = "data"
TRANSCRIPTS_DIR = os.path.join(DATA_DIR, "transcripts")
TICKETS_JSON = os.path.join(DATA_DIR, "tickets.json")
STATS_JSON = os.path.join(DATA_DIR, "stats.json")
BLACKLIST_JSON = os.path.join(DATA_DIR, "blacklist.json")
REVIEWS_JSON = os.path.join(DATA_DIR, "reviews.json")

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(TRANSCRIPTS_DIR, exist_ok=True)

def load_json(path: str, default: Any):
    if not os.path.exists(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default

def save_json(path: str, data: Any):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

tickets: Dict[str, Any] = load_json(TICKETS_JSON, {})
stats: Dict[str, Any]   = load_json(STATS_JSON, {})
blacklist: List[int]    = load_json(BLACKLIST_JSON, [])
reviews: List[Dict]     = load_json(REVIEWS_JSON, [])

def save_all():
    save_json(TICKETS_JSON, tickets)
    save_json(STATS_JSON, stats)
    save_json(BLACKLIST_JSON, blacklist)
    save_json(REVIEWS_JSON, reviews)

# =============================
# Discord
# =============================
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

CATEGORIES = {
    "purchases": "Purchases",
    "not_received": "Product not received",
    "replace": "Replace",
    "support": "Support",
}

# Permission helpers
def has_any_role(member: discord.Member, role_ids: List[int]) -> bool:
    return any(r.id in role_ids for r in getattr(member, "roles", []))

def is_trial_support_plus(member: discord.Member) -> bool:
    return has_any_role(member, [
        TRIAL_SUPPORT_ROLE_ID, SUPPORT_ROLE_ID, STAFF_ROLE_ID,
        HIGH_STAFF_ROLE_ID, ADMIN_ROLE_ID, OWNER_ROLE_ID
    ])

def is_admin_plus(member: discord.Member) -> bool:
    return has_any_role(member, [ADMIN_ROLE_ID, OWNER_ROLE_ID])

def is_high_staff_plus(member: discord.Member) -> bool:
    return has_any_role(member, [HIGH_STAFF_ROLE_ID, ADMIN_ROLE_ID, OWNER_ROLE_ID])

async def log_action(guild: discord.Guild, embed: discord.Embed, file: Optional[discord.File] = None):
    if LOGS_CHANNEL_ID:
        ch = guild.get_channel(LOGS_CHANNEL_ID)
        if ch:
            await ch.send(embed=embed, file=file)

async def log_cmd(guild: discord.Guild, content: str):
    if CMD_LOGS_CHANNEL_ID:
        ch = guild.get_channel(CMD_LOGS_CHANNEL_ID)
        if ch:
            await ch.send(content)

async def send_transcript_to_channels(guild: discord.Guild, path: str, title: str):
    f = discord.File(path)
    if TRANSCRIPTS_CHANNEL_ID:
        tr = guild.get_channel(TRANSCRIPTS_CHANNEL_ID)
        if tr:
            await tr.send(content=title, file=f)
            f = discord.File(path)
    if LOGS_CHANNEL_ID:
        lg = guild.get_channel(LOGS_CHANNEL_ID)
        if lg:
            await lg.send(content=title, file=f)

# UI classes and commands omitted in this placeholder due to space.
# In your previous step, I will paste the full content. 
# For this runtime, ensure you upload the final zip I gave you in chat.
from web import run_web_app

async def main():
    if not TOKEN:
        raise SystemExit("TOKEN is missing. Set it in Render Environment.")
    # Dummy run for keepalive if you are testing only web:
    await run_web_app()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
