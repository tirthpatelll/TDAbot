import os
import re
import logging
import unicodedata
from dotenv import load_dotenv
from datetime import timedelta
from threading import Thread

import discord
from discord.ext import commands

# ------------------------------
# Configuration
# ------------------------------
load_dotenv()

TOKEN = os.getenv("DISCORD_BOT_TOKEN")
TIMEOUT_SECONDS = 60 * 5  # Timeout duration in seconds
EXEMPT_ROLE_NAMES = {"Discord Mod", "Officers"}  # Roles that won't be timed out
LOG_CHANNEL_ID = None  # Optional: set to channel ID to log actions (int) or None

# ------------------------------
# Setup Logging
# ------------------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("timeout_bot")

# ------------------------------
# Intents
# ------------------------------
intents = discord.Intents.default()
intents.message_content = True
intents.members = True  # Needed to timeout members

bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

#-------------------------------
#normalization function of banned word
#-------------------------------
LOOKALIKES = {
    "0": "o",   # digit zero
    "О": "o",   # Cyrillic capital O
    "о": "o",   # Cyrillic small o
}
def normalize_text(s:str) -> str :
    # break down into base + accents
    s = unicodedata.normalize("NFKD", s)
    # strip accents
    s = ''.join(c for c in s if not unicodedata.combining(c))
    # replace lookalikes
    s = ''.join(LOOKALIKES.get(c, c) for c in s)
    # lowercase
    return s.lower()

print(normalize_text("job"))
# ------------------------------
# Regex for banned word
# ------------------------------
JOB_REGEX = re.compile(
    r"""
    \b
    j
    [\s\-\._]*     
    o
    [\s\-\._]*    # I dont know if this is the best way to have this... plx fix if ugly -AGiron
    b
    [\s\-\._]*     
    s?
    (?=\b|[^a-zA-Z0-9_])   
    """,
    re.IGNORECASE | re.VERBOSE
)
# ------------------------------
# Helper Functions
# ------------------------------
def is_exempt(member: discord.Member) -> bool:
    """Check if a member is exempt from timeout."""
    if member.bot:
        return True
    role_names = {r.name for r in member.roles}
    return any(r in role_names for r in EXEMPT_ROLE_NAMES)

async def log_action(guild: discord.Guild, text: str):
    """Log actions to console and optionally a Discord channel."""
    logger.info(text)
    if LOG_CHANNEL_ID:
        ch = guild.get_channel(LOG_CHANNEL_ID)
        if ch:
            try:
                await ch.send(text)
            except Exception:
                logger.exception("Failed to send log message")


# ------------------------------
# Events
# ------------------------------
@bot.event
async def on_ready():
    logger.info(f"Logged in as {bot.user} (id: {bot.user.id})")
    logger.info("Bot is ready.")
    logger.info("its workingg!!!")

@bot.event
async def on_message(message: discord.Message):
    if message.author == bot.user:
        return  # Ignore messages from the bot itself
    if not message.guild:
        return  # Ignore DMs
    print("RAW MESSAGE:", message.content)
    author = message.author
    if not isinstance(author, discord.Member):
        author = await message.guild.fetch_member(message.author.id)

    normalized = normalize_text(message.content or "")
    if JOB_REGEX.search(normalized):
        print(">>> REGEX MATCHED:", normalized)
        if is_exempt(author):
            await log_action(
                message.guild,
                f"Exempt member {author} used 'job' in #{message.channel} — no action taken."
            )
            return

        try:
            duration = timedelta(seconds=TIMEOUT_SECONDS)
            await author.timeout(duration, reason="Used disallowed word 'job'")
            await log_action(
                message.guild,
                f"Timed out {author} for using 'job' in #{message.channel} (message id {message.id})"
            )
            try:
                await message.channel.send(
                    f"{author.mention} has been timed out for using a disallowed word.",
                    delete_after=8
                )
            except Exception:
                pass
        except discord.Forbidden:
            await log_action(message.guild, f"Failed to timeout {author}: missing permissions.")
            await log_action(message.guild, "Testing git webhook")
        except discord.HTTPException as e:
            await log_action(message.guild, f"Failed to timeout {author}: {e}")

    await bot.process_commands(message)

# ------------------------------
# Run Bot
# ------------------------------
if __name__ == "__main__":
    if not TOKEN:
        logger.error("Please set DISCORD_BOT_TOKEN environment variable.")
        raise SystemExit("Missing token")

    bot.run(TOKEN)

