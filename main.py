# filename: timeout_job_bot.py
import os
import re
import logging
from datetime import timedelta

import discord
from discord.ext import commands

# --- Configuration ---
TOKEN = os.getenv("DISCORD_BOT_TOKEN")  # set this in your env 
TIMEOUT_SECONDS = 60 * 15  
EXEMPT_ROLE_NAMES = {"Discord Mod", "Officers"}  # roles that won't be timed out
LOG_CHANNEL_ID = None  # optional: set to channel ID to log actions (int) or None

# --- Setup logging ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("timeout_bot")

# --- Intents ---
intents = discord.Intents.default()
intents.message_content = True
intents.members = True  # needed to timeout members

bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

# compile regex for whole word "job" (case-insensitive)
JOB_REGEX = re.compile(r"\bjob\b", re.IGNORECASE)

# helper: is member exempt?
def is_exempt(member: discord.Member) -> bool:
    if member.bot:
        return True
    role_names = {r.name for r in member.roles}
    return any(r in role_names for r in EXEMPT_ROLE_NAMES)

async def log_action(guild: discord.Guild, text: str):
    logger.info(text)
    if LOG_CHANNEL_ID:
        ch = guild.get_channel(LOG_CHANNEL_ID)
        if ch:
            try:
                await ch.send(text)
            except Exception:
                logger.exception("Failed to send log message")

@bot.event
async def on_ready():
    logger.info(f"Logged in as {bot.user} (id: {bot.user.id})")
    logger.info("Bot is ready.")

@bot.event
async def on_message(message: discord.Message):
    # ignore messages from the bot itself
    if message.author == bot.user:
        return
    # ignore DMs
    if not message.guild:
        return

    # quick checks
    author = message.author
    if not isinstance(author, discord.Member):
        # resolve member object if needed
        author = await message.guild.fetch_member(message.author.id)

    # check regex for whole-word "job"
    if JOB_REGEX.search(message.content or ""):
        # exempt checks
        if is_exempt(author):
            await log_action(message.guild, f"Exempt member {author} used 'job' in #{message.channel} — no action taken.")
            return

        # attempt to timeout
        try:
            duration = timedelta(seconds=TIMEOUT_SECONDS)
            await author.timeout(duration, reason="Used disallowed word 'job'")
            await log_action(message.guild, f"Timed out {author} for using 'job' in #{message.channel} (message id {message.id})")
            # optionally inform channel (short ephemeral style)
            try:
                await message.channel.send(f"{author.mention} has been timed out for using a disallowed word.", delete_after=8)
            except Exception:
                pass
        except discord.Forbidden:
            await log_action(message.guild, f"Failed to timeout {author}: missing permissions.")
        except discord.HTTPException as e:
            await log_action(message.guild, f"Failed to timeout {author}: {e}")

    # process commands if any
    await bot.process_commands(message)

# run
if __name__ == "__main__":
    if not TOKEN:
        logger.error("Please set DISCORD_BOT_TOKEN environment variable.")
        raise SystemExit("Missing token")
    bot.run(TOKEN)
