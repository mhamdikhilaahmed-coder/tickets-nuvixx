
import os
import json
import asyncio
import datetime as dt
from typing import Optional, Dict, Any, List

import discord
from discord import app_commands
from discord.ext import commands, tasks
from dotenv import load_dotenv

# ──────────────────────────────────────────────────────────────────────────────
# Load environment
# ──────────────────────────────────────────────────────────────────────────────
load_dotenv()
TOKEN = os.getenv("TOKEN")  # IMPORTANT: never hardcode your token
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

# ──────────────────────────────────────────────────────────────────────────────
# Paths & storage
# ──────────────────────────────────────────────────────────────────────────────
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

tickets: Dict[str, Any] = load_json(TICKETS_JSON, {})     # channel_id -> info
stats: Dict[str, Any]   = load_json(STATS_JSON, {})       # staff_id  -> {"claims": int, "closed": int, "messages_by_ticket": {channel_id: count}}
blacklist: List[int]    = load_json(BLACKLIST_JSON, [])
reviews: List[Dict]     = load_json(REVIEWS_JSON, [])

def save_all():
    save_json(TICKETS_JSON, tickets)
    save_json(STATS_JSON, stats)
    save_json(BLACKLIST_JSON, blacklist)
    save_json(REVIEWS_JSON, reviews)

# ──────────────────────────────────────────────────────────────────────────────
# Bot setup
# ──────────────────────────────────────────────────────────────────────────────
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Ticket categories
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
    # send to transcripts channel
    if TRANSCRIPTS_CHANNEL_ID:
        tr = guild.get_channel(TRANSCRIPTS_CHANNEL_ID)
        if tr:
            await tr.send(content=title, file=f)
            f = discord.File(path)  # recreate to send again
    # also to logs
    if LOGS_CHANNEL_ID:
        lg = guild.get_channel(LOGS_CHANNEL_ID)
        if lg:
            await lg.send(content=title, file=f)

# ──────────────────────────────────────────────────────────────────────────────
# UI: Panel view & ticket buttons
# ──────────────────────────────────────────────────────────────────────────────
class TicketButtons(discord.ui.View):
    def __init__(self, opener_id: int):
        super().__init__(timeout=None)
        self.opener_id = opener_id

    @discord.ui.button(label="Assign me", style=discord.ButtonStyle.success, custom_id="ticket_assign")
    async def assign(self, interaction: discord.Interaction, _: discord.ui.Button):
        if not isinstance(interaction.user, discord.Member) or not is_trial_support_plus(interaction.user):
            return await interaction.response.send_message("❌ You must be **Trial Support or higher** to assign tickets.", ephemeral=True)
        ch = interaction.channel
        t = tickets.get(str(getattr(ch, "id", 0)))
        if not t:
            return await interaction.response.send_message("This is not a registered ticket channel.", ephemeral=True)
        t["assigned_to"] = interaction.user.id
        t["updated_at"] = dt.datetime.utcnow().isoformat()
        tickets[str(ch.id)] = t
        s = stats.get(str(interaction.user.id), {"claims": 0, "closed": 0, "messages_by_ticket": {}})
        s["claims"] = s.get("claims", 0) + 1
        stats[str(interaction.user.id)] = s
        save_all()
        await interaction.response.send_message(f"✅ Assigned to {interaction.user.mention}.", ephemeral=True)

    @discord.ui.button(label="Unclaim", style=discord.ButtonStyle.secondary, custom_id="ticket_unclaim")
    async def unclaim(self, interaction: discord.Interaction, _: discord.ui.Button):
        if not isinstance(interaction.user, discord.Member) or not is_trial_support_plus(interaction.user):
            return await interaction.response.send_message("❌ You must be **Trial Support or higher**.", ephemeral=True)
        ch = interaction.channel
        t = tickets.get(str(getattr(ch, "id", 0)))
        if not t:
            return await interaction.response.send_message("This is not a registered ticket channel.", ephemeral=True)
        if t.get("assigned_to") not in (None, interaction.user.id) and not is_admin_plus(interaction.user):
            return await interaction.response.send_message("❌ Only the current assignee or Admin+ can unclaim.", ephemeral=True)
        t["assigned_to"] = None
        t["updated_at"] = dt.datetime.utcnow().isoformat()
        tickets[str(ch.id)] = t
        save_all()
        await interaction.response.send_message("🔓 Ticket unclaimed.", ephemeral=True)

    @discord.ui.button(label="Close", style=discord.ButtonStyle.danger, custom_id="ticket_close")
    async def close(self, interaction: discord.Interaction, _: discord.ui.Button):
        if not isinstance(interaction.user, discord.Member) or not is_trial_support_plus(interaction.user):
            return await interaction.response.send_message("❌ Only **Trial Support+** can close tickets.", ephemeral=True)
        ch = interaction.channel
        if isinstance(ch, discord.TextChannel):
            await close_ticket(ch, interaction.user)
            await interaction.response.send_message("⏹️ Ticket closed.", ephemeral=True)

class CategorySelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label=CATEGORIES["purchases"], value="purchases", emoji="🛒"),
            discord.SelectOption(label=CATEGORIES["not_received"], value="not_received", emoji="📦"),
            discord.SelectOption(label=CATEGORIES["replace"], value="replace", emoji="🔁"),
            discord.SelectOption(label=CATEGORIES["support"], value="support", emoji="💬"),
        ]
        super().__init__(placeholder="Select a ticket category…", min_values=1, max_values=1, options=options, custom_id="ticket_category_select")

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id in blacklist:
            return await interaction.response.send_message("🚫 You are blacklisted from opening tickets.", ephemeral=True)
        await interaction.response.send_modal(TicketModal(self.values[0]))

class PanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(CategorySelect())

class TicketModal(discord.ui.Modal, title="Support"):
    def __init__(self, category: str):
        super().__init__(timeout=None)
        self.category = category

        if category == "purchases":
            self.q1 = discord.ui.TextInput(label="What do you want to buy?", required=True, max_length=200)
            self.q2 = discord.ui.TextInput(label="Amount for buy?", required=True, max_length=100)
            self.q3 = discord.ui.TextInput(label="Payment Method?", required=True, max_length=100)
            self.add_item(self.q1); self.add_item(self.q2); self.add_item(self.q3)
        elif category == "not_received":
            self.q1 = discord.ui.TextInput(label="Invoice ID", required=True, max_length=120)
            self.q2 = discord.ui.TextInput(label="What payment method did you use?", required=True, max_length=120)
            self.q3 = discord.ui.TextInput(label="When did you pay? (date)", required=True, max_length=120)
            self.add_item(self.q1); self.add_item(self.q2); self.add_item(self.q3)
        elif category == "replace":
            self.q1 = discord.ui.TextInput(label="Is this a store purchase or a replacement?", required=True, max_length=200)
            self.q2 = discord.ui.TextInput(label="Invoice ID or Order ID", required=True, max_length=120)
            self.q3 = discord.ui.TextInput(label="Describe the issue", required=True, style=discord.TextStyle.long, max_length=2000)
            self.add_item(self.q1); self.add_item(self.q2); self.add_item(self.q3)
        else:  # support
            self.q1 = discord.ui.TextInput(label="How can we help you?", required=True, style=discord.TextStyle.long, max_length=2000)
            self.add_item(self.q1)

    async def on_submit(self, interaction: discord.Interaction):
        guild = interaction.guild
        if not guild:
            return

        category_channel = guild.get_channel(TICKET_CATEGORY_ID)
        if not isinstance(category_channel, discord.CategoryChannel):
            return await interaction.response.send_message("❌ Ticket category is not configured correctly.", ephemeral=True)

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True, attach_files=True)
        }
        # Trial Support+ allowed to see tickets
        for role_id in [TRIAL_SUPPORT_ROLE_ID, SUPPORT_ROLE_ID, STAFF_ROLE_ID, HIGH_STAFF_ROLE_ID, ADMIN_ROLE_ID, OWNER_ROLE_ID]:
            r = guild.get_role(role_id)
            if r:
                overwrites[r] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True, attach_files=True, manage_messages=True)

        chan_name = f"{interaction.user.name[:20]}-{self.category}"
        channel = await guild.create_text_channel(name=chan_name, category=category_channel, overwrites=overwrites, reason="New ticket")

        # build ticket info
        now = dt.datetime.utcnow().isoformat()
        ticket_info = {
            "channel_id": channel.id,
            "opener_id": interaction.user.id,
            "category": self.category,
            "created_at": now,
            "updated_at": now,
            "assigned_to": None,
            "warned_inactive_at": None
        }
        tickets[str(channel.id)] = ticket_info
        save_all()

        embed = discord.Embed(
            title="Support Ticket",
            description="Please wait until one of our support team members can help you.\n**Response time may vary**; please be patient.",
            color=discord.Color.fuchsia()
        )
        embed.add_field(name="Category", value=CATEGORIES.get(self.category, self.category), inline=True)
        embed.add_field(name="User", value=interaction.user.mention, inline=True)

        if self.category == "purchases":
            details = f"**What buy:** {self.q1.value}\n**Amount:** {self.q2.value}\n**Payment:** {self.q3.value}"
        elif self.category == "not_received":
            details = f"**Invoice ID:** {self.q1.value}\n**Payment:** {self.q2.value}\n**Paid at:** {self.q3.value}"
        elif self.category == "replace":
            details = f"**Type:** {self.q1.value}\n**Invoice/Order:** {self.q2.value}\n**Issue:** {self.q3.value}"
        else:
            details = f"**Message:** {self.q1.value}"
        embed.add_field(name="Details", value=details, inline=False)

        view = TicketButtons(opener_id=interaction.user.id)
        await channel.send(embed=embed, view=view)

        le = discord.Embed(title="🆕 Ticket opened", color=discord.Color.green())
        le.add_field(name="User", value=f"{interaction.user} ({interaction.user.id})", inline=False)
        le.add_field(name="Channel", value=channel.mention, inline=False)
        le.add_field(name="Category", value=CATEGORIES.get(self.category, self.category), inline=False)
        await log_action(guild, le)

        await interaction.response.send_message(f"✅ Ticket created: {channel.mention}", ephemeral=True)

# Transcript builder
async def make_transcript(channel: discord.TextChannel) -> Optional[str]:
    ts = dt.datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    filename = f"transcript_{channel.id}_{ts}.txt"
    path = os.path.join(TRANSCRIPTS_DIR, filename)

    lines = [f"Ticket transcript for #{channel.name} ({channel.id})"]
    async for msg in channel.history(limit=None, oldest_first=True):
        created = msg.created_at.strftime("%Y-%m-%d %H:%M:%S")
        author = f"{msg.author} ({msg.author.id})"
        content = msg.content or ""
        lines.append(f"[{created}] {author}: {content}")
        for a in msg.attachments:
            lines.append(f"[{created}] Attachment: {a.filename} ({a.url})")

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    return path

# Close helper
async def close_ticket(channel: discord.TextChannel, closed_by: discord.abc.User, deleted: bool = False):
    guild = channel.guild
    t = tickets.pop(str(channel.id), None)
    save_all()

    transcript_path = await make_transcript(channel)
    title = f"Ticket transcript • #{channel.name} • closed by {closed_by} ({closed_by.id})"
    await send_transcript_to_channels(guild, transcript_path, title)

    # DM user + review
    opener_id = t.get("opener_id") if t else None
    if opener_id:
        try:
            user = guild.get_member(opener_id) or await guild.fetch_member(opener_id)
            if user:
                dm = await user.create_dm()
                await dm.send(embed=discord.Embed(
                    title="Your ticket has been closed",
                    description="Thanks for contacting support! You can leave a review below.",
                    color=discord.Color.blurple())
                )
                # Send review UI
                await dm.send(view=ReviewView(opener_id, channel.id))
        except Exception:
            pass

    # Logs
    le = discord.Embed(title="⏹️ Ticket closed" if not deleted else "🗑️ Ticket deleted", color=(discord.Color.red() if not deleted else discord.Color.dark_red()))
    le.add_field(name="Channel", value=f"#{channel.name}", inline=False)
    le.add_field(name="Closed by", value=f"{closed_by} ({closed_by.id})", inline=False)
    if t and t.get("assigned_to"):
        le.add_field(name="Assigned to", value=f"<@{t['assigned_to']}>", inline=False)
        # increment closer stats
        s = stats.get(str(t["assigned_to"]), {"claims": 0, "closed": 0, "messages_by_ticket": {}})
        s["closed"] = s.get("closed", 0) + 1
        stats[str(t["assigned_to"])] = s
        save_all()
    await log_action(guild, le)

    # rename and delete
    try:
        await channel.edit(name=f"closed-{channel.name}")
    except Exception:
        pass
    try:
        await channel.delete(reason="Ticket closed")
    except Exception:
        pass

# Review UI
class ReviewModal(discord.ui.Modal, title="Leave a review"):
    def __init__(self, opener_id: int, channel_id: int, stars: int):
        super().__init__(timeout=None)
        self.opener_id = opener_id
        self.channel_id = channel_id
        self.stars = stars
        self.comment = discord.ui.TextInput(label="Comment (optional)", required=False, style=discord.TextStyle.long, max_length=1000)
        self.add_item(self.comment)

    async def on_submit(self, interaction: discord.Interaction):
        now = dt.datetime.utcnow().isoformat()
        review_obj = {
            "user_id": self.opener_id,
            "channel_id": self.channel_id,
            "stars": self.stars,
            "comment": str(self.comment.value or "").strip(),
            "created_at": now
        }
        reviews.append(review_obj)
        save_json(REVIEWS_JSON, reviews)

        # forward to reviews channel
        guild = interaction.client.get_guild(GUILD_ID)
        if guild and REVIEWS_CHANNEL_ID:
            ch = guild.get_channel(REVIEWS_CHANNEL_ID)
            if ch:
                emb = discord.Embed(title="📝 New Ticket Review", color=discord.Color.gold())
                emb.add_field(name="Stars", value=f"{self.stars}⭐", inline=True)
                emb.add_field(name="User ID", value=str(self.opener_id), inline=True)
                emb.add_field(name="Ticket Channel ID", value=str(self.channel_id), inline=True)
                if review_obj["comment"]:
                    emb.add_field(name="Comment", value=review_obj["comment"], inline=False)
                await ch.send(embed=emb)

        await interaction.response.send_message("✅ Thanks! Your review has been submitted.", ephemeral=True)

class ReviewView(discord.ui.View):
    def __init__(self, opener_id: int, channel_id: int):
        super().__init__(timeout=300)  # 5 minutes
        self.opener_id = opener_id
        self.channel_id = channel_id

    @discord.ui.select(
        placeholder="Rate your support (1–5 stars)",
        min_values=1,
        max_values=1,
        options=[
            discord.SelectOption(label="1", value="1"),
            discord.SelectOption(label="2", value="2"),
            discord.SelectOption(label="3", value="3"),
            discord.SelectOption(label="4", value="4"),
            discord.SelectOption(label="5", value="5"),
        ]
    )
    async def select_rating(self, interaction: discord.Interaction, select: discord.ui.Select):
        if interaction.user.id != self.opener_id:
            return await interaction.response.send_message("This review is not for you.", ephemeral=True)
        stars = int(select.values[0])
        await interaction.response.send_modal(ReviewModal(self.opener_id, self.channel_id, stars))

# ──────────────────────────────────────────────────────────────────────────────
# Background: inactivity checker
# ──────────────────────────────────────────────────────────────────────────────
@tasks.loop(minutes=60)
async def inactivity_check():
    await bot.wait_until_ready()
    guild = bot.get_guild(GUILD_ID)
    if not guild:
        return
    for key, t in list(tickets.items()):
        ch = guild.get_channel(int(key))
        if not isinstance(ch, discord.TextChannel):
            continue
        try:
            last = None
            async for m in ch.history(limit=1):
                last = m.created_at
            if not last:
                continue
            now = dt.datetime.utcnow().replace(tzinfo=dt.timezone.utc)
            if (now - last).total_seconds() >= 24*3600:
                warned_at = t.get("warned_inactive_at")
                if not warned_at:
                    warn = discord.Embed(
                        title="⏰ Ticket inactivity warning",
                        description="There has been no activity in this ticket for **24 hours**. Please reply if you still need help. Otherwise, staff may close this ticket.",
                        color=discord.Color.orange()
                    )
                    await ch.send(embed=warn)
                    t["warned_inactive_at"] = dt.datetime.utcnow().isoformat()
                    tickets[key] = t
                    save_all()
        except Exception:
            continue

# ──────────────────────────────────────────────────────────────────────────────
# Message tracking for /activity (≥5 messages in a ticket)
# ──────────────────────────────────────────────────────────────────────────────
@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return
    # Track only inside ticket channels
    if str(message.channel.id) in tickets:
        if isinstance(message.author, discord.Member) and is_trial_support_plus(message.author):
            s = stats.get(str(message.author.id), {"claims": 0, "closed": 0, "messages_by_ticket": {}})
            mbt = s.get("messages_by_ticket", {})
            mbt[str(message.channel.id)] = mbt.get(str(message.channel.id), 0) + 1
            s["messages_by_ticket"] = mbt
            stats[str(message.author.id)] = s
            save_all()
    await bot.process_commands(message)

# ──────────────────────────────────────────────────────────────────────────────
# Slash commands
# ──────────────────────────────────────────────────────────────────────────────
@bot.event
async def on_ready():
    try:
        guild = bot.get_guild(GUILD_ID)
        if guild:
            bot.tree.copy_global_to(guild=guild)
            await bot.tree.sync(guild=guild)
        else:
            await bot.tree.sync()
    except Exception as e:
        print("Sync error:", e)
    inactivity_check.start()
    print(f"✅ Logged in as {bot.user}")

# /panel (Admin+)
@bot.tree.command(name="panel", description="Send the ticket panel")
async def panel(interaction: discord.Interaction):
    if not isinstance(interaction.user, discord.Member) or not is_admin_plus(interaction.user):
        return await interaction.response.send_message("❌ You don’t have permission (Admin+ only).", ephemeral=True)
    embed = discord.Embed(
        title="Nuvix Tickets",
        description="Select a category below to open a ticket. **Response time may vary.**",
        color=discord.Color.fuchsia(),
    )
    await interaction.response.send_message(embed=embed, view=PanelView())
    await log_cmd(interaction.guild, f"🧩 /panel used by {interaction.user}")

# /transcript (Trial Support+)
@bot.tree.command(name="transcript", description="Generate a transcript of this ticket")
async def transcript(interaction: discord.Interaction):
    if not isinstance(interaction.user, discord.Member) or not is_trial_support_plus(interaction.user):
        return await interaction.response.send_message("❌ You don’t have permission (Trial Support+).", ephemeral=True)
    ch = interaction.channel
    if not isinstance(ch, discord.TextChannel):
        return await interaction.response.send_message("Use this inside a ticket channel.", ephemeral=True)
    if str(ch.id) not in tickets and not ch.name.startswith("closed-"):
        return await interaction.response.send_message("This does not look like a ticket channel.", ephemeral=True)
    path = await make_transcript(ch)
    if not path:
        return await interaction.response.send_message("Could not create transcript.", ephemeral=True)
    await interaction.response.send_message(file=discord.File(path), ephemeral=True)
    await send_transcript_to_channels(interaction.guild, path, f"Manual transcript • #{ch.name}")
    await log_cmd(interaction.guild, f"🧾 /transcript by {interaction.user} in #{ch.name}")

# /close (Trial Support+)
@bot.tree.command(name="close", description="Close this ticket")
async def close(interaction: discord.Interaction):
    if not isinstance(interaction.user, discord.Member) or not is_trial_support_plus(interaction.user):
        return await interaction.response.send_message("❌ You don’t have permission (Trial Support+).", ephemeral=True)
    ch = interaction.channel
    if not isinstance(ch, discord.TextChannel):
        return await interaction.response.send_message("Use this inside a ticket channel.", ephemeral=True)
    await close_ticket(ch, interaction.user)
    await interaction.response.send_message("Ticket closed.", ephemeral=True)
    await log_cmd(interaction.guild, f"⏹️ /close by {interaction.user} in #{ch.name}")

# /delete (Admin+, instant no-permission reply if not Admin+)
@bot.tree.command(name="delete", description="Force delete this ticket (Admin+)")
async def delete(interaction: discord.Interaction):
    if not isinstance(interaction.user, discord.Member) or not is_admin_plus(interaction.user):
        return await interaction.response.send_message("❌ You don’t have permission (Admin+ only).", ephemeral=True)
    ch = interaction.channel
    if not isinstance(ch, discord.TextChannel):
        return await interaction.response.send_message("Use this inside a ticket channel.", ephemeral=True)
    # Send transcript before deletion
    path = await make_transcript(ch)
    await send_transcript_to_channels(interaction.guild, path, f"Deleted ticket transcript • #{ch.name}")
    await log_cmd(interaction.guild, f"🗑️ /delete by {interaction.user} in #{ch.name}")
    # Close helper with deleted=True (to log properly)
    await close_ticket(ch, interaction.user, deleted=True)

# /add, /remove (Trial Support+)
@bot.tree.command(name="add", description="Add a user to this ticket")
@app_commands.describe(user="User to add")
async def add_user(interaction: discord.Interaction, user: discord.Member):
    if not isinstance(interaction.user, discord.Member) or not is_trial_support_plus(interaction.user):
        return await interaction.response.send_message("❌ You don’t have permission (Trial Support+).", ephemeral=True)
    ch = interaction.channel
    if not isinstance(ch, discord.TextChannel):
        return await interaction.response.send_message("Use this inside a ticket channel.", ephemeral=True)
    await ch.set_permissions(user, view_channel=True, send_messages=True, read_message_history=True, attach_files=True)
    await interaction.response.send_message(f"✅ {user.mention} added to the ticket.", ephemeral=True)
    await log_cmd(interaction.guild, f"➕ /add {user} by {interaction.user} in #{ch.name}")

@bot.tree.command(name="remove", description="Remove a user from this ticket")
@app_commands.describe(user="User to remove")
async def remove_user(interaction: discord.Interaction, user: discord.Member):
    if not isinstance(interaction.user, discord.Member) or not is_trial_support_plus(interaction.user):
        return await interaction.response.send_message("❌ You don’t have permission (Trial Support+).", ephemeral=True)
    ch = interaction.channel
    if not isinstance(ch, discord.TextChannel):
        return await interaction.response.send_message("Use this inside a ticket channel.", ephemeral=True)
    await ch.set_permissions(user, overwrite=None)
    await interaction.response.send_message(f"✅ {user.mention} removed from the ticket.", ephemeral=True)
    await log_cmd(interaction.guild, f"➖ /remove {user} by {interaction.user} in #{ch.name}")

# Blacklist (Admin+ for add/remove; list for Trial Support+)
@bot.tree.command(name="blacklist_add", description="Blacklist a user (Admin+)")
@app_commands.describe(user="User to blacklist")
async def blacklist_add(interaction: discord.Interaction, user: discord.Member):
    if not isinstance(interaction.user, discord.Member) or not is_admin_plus(interaction.user):
        return await interaction.response.send_message("❌ You don’t have permission (Admin+ only).", ephemeral=True)
    if user.id not in blacklist:
        blacklist.append(user.id)
        save_all()
    await interaction.response.send_message(f"🚫 {user} has been blacklisted.", ephemeral=True)
    await log_cmd(interaction.guild, f"🚫 /blacklist_add {user} by {interaction.user}")

@bot.tree.command(name="blacklist_remove", description="Remove a user from blacklist (Admin+)")
@app_commands.describe(user="User to unblacklist")
async def blacklist_remove(interaction: discord.Interaction, user: discord.Member):
    if not isinstance(interaction.user, discord.Member) or not is_admin_plus(interaction.user):
        return await interaction.response.send_message("❌ You don’t have permission (Admin+ only).", ephemeral=True)
    if user.id in blacklist:
        blacklist.remove(user.id)
        save_all()
    await interaction.response.send_message(f"✅ {user} removed from blacklist.", ephemeral=True)
    await log_cmd(interaction.guild, f"✅ /blacklist_remove {user} by {interaction.user}")

@bot.tree.command(name="blacklist_list", description="Show blacklist (Trial Support+)")
async def blacklist_list(interaction: discord.Interaction):
    if not isinstance(interaction.user, discord.Member) or not is_trial_support_plus(interaction.user):
        return await interaction.response.send_message("❌ You don’t have permission (Trial Support+).", ephemeral=True)
    if not blacklist:
        msg = "Blacklist is empty."
    else:
        msg = "\n".join(str(uid) for uid in blacklist)
    await interaction.response.send_message(f"**Blacklisted IDs:**\n{msg}", ephemeral=True)

# Staff stats
@bot.tree.command(name="staffstats_me", description="Your staff stats (Trial Support+)")
async def staffstats_me(interaction: discord.Interaction):
    if not isinstance(interaction.user, discord.Member) or not is_trial_support_plus(interaction.user):
        return await interaction.response.send_message("❌ You don’t have permission (Trial Support+).", ephemeral=True)
    s = stats.get(str(interaction.user.id), {"claims": 0, "closed": 0, "messages_by_ticket": {}})
    emb = discord.Embed(title="📊 Your Staff Stats", color=discord.Color.green())
    emb.add_field(name="Claims", value=str(s.get("claims", 0)), inline=True)
    emb.add_field(name="Closed", value=str(s.get("closed", 0)), inline=True)
    active_tickets = sum(1 for _, c in s.get("messages_by_ticket", {}).items() if c >= 5)
    emb.add_field(name="Active tickets (≥5 msgs)", value=str(active_tickets), inline=True)
    await interaction.response.send_message(embed=emb, ephemeral=True)

@bot.tree.command(name="staffstats_leaderboard", description="Staff leaderboard (High Staff+)")
async def staffstats_leaderboard(interaction: discord.Interaction):
    if not isinstance(interaction.user, discord.Member) or not is_high_staff_plus(interaction.user):
        return await interaction.response.send_message("❌ You don’t have permission (High Staff+).", ephemeral=True)
    # Rank by closed then claims
    rows = []
    for uid, s in stats.items():
        rows.append((int(uid), s.get("closed", 0), s.get("claims", 0)))
    rows.sort(key=lambda x: (x[1], x[2]), reverse=True)
    lines = []
    for i, (uid, closed, claims) in enumerate(rows[:10], 1):
        lines.append(f"**#{i}** <@{uid}> — Closed: {closed} • Claims: {claims}")
    desc = "\n".join(lines) if lines else "No data yet."
    emb = discord.Embed(title="🏆 Staff Leaderboard", description=desc, color=discord.Color.gold())
    await interaction.response.send_message(embed=emb, ephemeral=True)

# Activity (≥5 distinct messages per ticket)
@bot.tree.command(name="activity_me", description="Your activity: tickets with ≥5 messages (Trial Support+)")
async def activity_me(interaction: discord.Interaction):
    if not isinstance(interaction.user, discord.Member) or not is_trial_support_plus(interaction.user):
        return await interaction.response.send_message("❌ You don’t have permission (Trial Support+).", ephemeral=True)
    s = stats.get(str(interaction.user.id), {"messages_by_ticket": {}})
    count = sum(1 for _, c in s.get("messages_by_ticket", {}).items() if c >= 5)
    await interaction.response.send_message(f"✅ You have been active (≥5 msgs) in **{count}** tickets.", ephemeral=True)

@bot.tree.command(name="activity_user", description="Show a user's activity (High Staff+)")
@app_commands.describe(user="Staff member to check")
async def activity_user(interaction: discord.Interaction, user: discord.Member):
    if not isinstance(interaction.user, discord.Member) or not is_high_staff_plus(interaction.user):
        return await interaction.response.send_message("❌ You don’t have permission (High Staff+).", ephemeral=True)
    s = stats.get(str(user.id), {"messages_by_ticket": {}})
    count = sum(1 for _, c in s.get("messages_by_ticket", {}).items() if c >= 5)
    await interaction.response.send_message(f"✅ {user.mention} has been active (≥5 msgs) in **{count}** tickets.", ephemeral=True)

# Utility
@bot.tree.command(name="ping", description="Ping")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message("Pong!", ephemeral=True)

# ──────────────────────────────────────────────────────────────────────────────
# Run
# ──────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    if not TOKEN:
        raise SystemExit("TOKEN is missing. Put it in your .env or Render env variables.")
    bot.run(TOKEN)
