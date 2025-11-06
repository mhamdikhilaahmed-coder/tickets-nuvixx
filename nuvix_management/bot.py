import nuvix_patch
import os, time, asyncio
from aiohttp import web
import discord
from discord import app_commands
from discord.ext import commands

BOT_NAME = "Nuvix Management"
TOKEN = os.getenv("NUVIX_MANAGEMENT_TOKEN")
OWNER_ROLE_ID = int(os.getenv("OWNER_ROLE_ID", "0"))
EMBED_COLOR = int(os.getenv("EMBED_COLOR_HEX", "0xE91E63"), 16)  # default Nuvix pink

UPTIME = time.time()

intents = discord.Intents.none()
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

async def health_handler(request):
    alive = int(time.time() - UPTIME)
    return web.Response(text=f"Nuvix Management connected | alive {alive}s")

async def run_web():
    app = web.Application()
    app.router.add_get("/", health_handler)
    app.router.add_get("/health", health_handler)
    port = int(os.getenv("PORT", "10000"))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    while True:
        await asyncio.sleep(3600)

def owner_only(interaction: discord.Interaction) -> bool:
    if interaction.user is None or not interaction.guild:
        return False
    if OWNER_ROLE_ID and any(r.id == OWNER_ROLE_ID for r in interaction.user.roles):
        return True
    # also allow guild owner and admins
    if interaction.user.id == interaction.guild.owner_id:
        return True
    perms = interaction.user.guild_permissions
    return perms.administrator

@tree.command(name="status", description="Show connection status and uptime (owner only).")
@app_commands.check(lambda i: owner_only(i))
async def status(interaction: discord.Interaction):
    uptime_sec = int(time.time() - UPTIME)
    mins, secs = divmod(uptime_sec, 60)
    hours, mins = divmod(mins, 60)
    days, hours = divmod(hours, 24)
    human = (f"{days}d " if days else "") + (f"{hours}h " if hours else "") + (f"{mins}m {secs}s")
    embed = discord.Embed(title="✅ Connected", description=f"🟢 **Alive since:** {human}", color=EMBED_COLOR)
    embed.set_footer(text="Nuvix System • Connected")
    try:
        await interaction.response.send_message(embed=embed, ephemeral=True)
    except discord.InteractionResponded:
        await interaction.followup.send(embed=embed, ephemeral=True)

@status.error
async def status_error(interaction: discord.Interaction, error):
    if isinstance(error, app_commands.CheckFailure):
        await interaction.response.send_message("You don't have permission to use this command.", ephemeral=True)
    else:
        await interaction.response.send_message("Unexpected error.", ephemeral=True)

@bot.event
async def on_ready():
    try:
        await tree.sync()
    except Exception:
        pass
    print(f"🌐 {BOT_NAME} connected as {bot.user}")

async def main():
    if not TOKEN:
        raise RuntimeError(f"Missing token env: NUVIX_MANAGEMENT_TOKEN")
    web_task = asyncio.create_task(run_web())
    bot_task = asyncio.create_task(bot.start(TOKEN))
    await asyncio.wait([web_task, bot_task], return_when=asyncio.FIRST_COMPLETED)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
