# Copyright (C) @Wolfy004
# Channel: https://t.me/Wolfy004

import os
import shutil
import psutil
import asyncio
from time import time

from pyleaves import Leaves
from pyrogram.enums import ParseMode
from pyrogram import Client, filters
from pyrogram.errors import PeerIdInvalid, BadRequest
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton

from helpers.utils import (
    processMediaGroup,
    progressArgs,
    send_media
)

from helpers.files import (
    get_download_path,
    fileSizeLimit,
    get_readable_file_size,
    get_readable_time,
    cleanup_download
)

from helpers.msg import (
    getChatMsgID,
    get_file_name,
    get_parsed_msg
)

from config import PyroConf
from logger import LOGGER
from database import db
from phone_auth import PhoneAuthHandler
from access_control import admin_only, paid_or_admin_only, check_download_limit, register_user, check_user_session, get_user_client
from admin_commands import (
    add_admin_command,
    remove_admin_command,
    set_premium_command,
    remove_premium_command,
    ban_user_command,
    unban_user_command,
    broadcast_command,
    admin_stats_command,
    user_info_command,
    broadcast_callback_handler
)

# Initialize the bot client
bot = Client(
    "media_bot",
    api_id=PyroConf.API_ID,
    api_hash=PyroConf.API_HASH,
    bot_token=PyroConf.BOT_TOKEN,
    workers=1000,
    parse_mode=ParseMode.MARKDOWN,
)

# Client for user session
user = Client("user_session", workers=1000, session_string=PyroConf.SESSION_STRING) if PyroConf.SESSION_STRING else None

# Phone authentication handler
phone_auth_handler = PhoneAuthHandler(PyroConf.API_ID, PyroConf.API_HASH)

RUNNING_TASKS = set()

def track_task(coro):
    task = asyncio.create_task(coro)
    RUNNING_TASKS.add(task)
    def _remove(_):
        RUNNING_TASKS.discard(task)
    task.add_done_callback(_remove)
    return task


@bot.on_message(filters.command("start") & filters.private)
@register_user
async def start(_, message: Message):
    welcome_text = (
        "**Welcome to Save Restricted Content Bot!**\n\n"
        "📱 **Get Started:**\n"
        "1. Login with your phone number: `/login +1234567890`\n"
        "2. Enter the OTP code you receive\n"
        "3. Start downloading from your joined channels!\n\n"
        "ℹ️ Use `/help` to view all commands and examples.\n\n"
        "Ready? Login first with `/login <your_phone_number>`"
    )

    markup = InlineKeyboardMarkup(
        [[InlineKeyboardButton("Update Channel", url="https://t.me/Wolfy004")]]
    )
    await message.reply(welcome_text, reply_markup=markup, disable_web_page_preview=True)


@bot.on_message(filters.command("help") & filters.private)
@register_user
async def help_command(_, message: Message):
    help_text = (
        "💡 **Media Downloader Bot Help**\n\n"
        "➤ **Download Media**\n"
        "   – Send `/dl <post_URL>` **or** just paste a Telegram post link to fetch photos, videos, audio, or documents.\n\n"
        "➤ **Batch Download** (Premium Only)\n"
        "   – Send `/bdl start_link end_link` to grab a series of posts in one go.\n"
        "     💡 Example: `/bdl https://t.me/mychannel/100 https://t.me/mychannel/120`\n"
        "**It will download all posts from ID 100 to 120.**\n\n"
        "➤ **Login with Phone Number**\n"
        "   – `/login +1234567890` - Start login process\n"
        "   – `/verify 1 2 3 4 5` - Enter OTP with spaces between digits\n"
        "   – `/password your_2fa_password` - Enter 2FA password (if enabled)\n"
        "   – `/logout` - Logout from your account\n"
        "   – `/cancel` - Cancel pending authentication\n\n"
        "➤ **User Commands**\n"
        "   – `/myinfo` - View your account information\n\n"
        "➤ **Limits**\n"
        "   – Free users: 5 downloads per day\n"
        "   – Premium users: Unlimited downloads\n\n"
        "➤ **If the bot hangs**\n"
        "   – Send `/killall` to cancel any pending downloads (Admin only).\n\n"
        "➤ **Logs**\n"
        "   – Send `/logs` to download the bot’s logs file.\n\n"
        "➤ **Stats**\n"
        "   – Send `/stats` to view current status:\n\n"
        "**Example**:\n"
        "  • `/dl https://t.me/Wolfy004`\n"
        "  • `https://t.me/Wolfy004`"
    )
    
    markup = InlineKeyboardMarkup(
        [[InlineKeyboardButton("Update Channel", url="https://t.me/itsSmartDev")]]
    )
    await message.reply(help_text, reply_markup=markup, disable_web_page_preview=True)


async def handle_download(bot: Client, message: Message, post_url: str, user_client=None, increment_usage=True):
    # Cut off URL at '?' if present
    if "?" in post_url:
        post_url = post_url.split("?", 1)[0]

    try:
        chat_id, message_id = getChatMsgID(post_url)
        
        # Use user's personal session if available, otherwise use bot's session
        client_to_use = user_client if user_client else user
        
        # Ensure the client is started
        if client_to_use and client_to_use == user and user and not user.is_connected:
            await user.start()
        elif not client_to_use or (client_to_use == user and not user):
            await message.reply(
                "❌ **No active session found.**\n\n"
                "Please login with your phone number:\n"
                "`/login +1234567890`"
            )
            return
            
        chat_message = await client_to_use.get_messages(chat_id=chat_id, message_ids=message_id)

        LOGGER(__name__).info(f"Downloading media from URL: {post_url}")

        if chat_message.document or chat_message.video or chat_message.audio:
            file_size = (
                chat_message.document.file_size
                if chat_message.document
                else chat_message.video.file_size
                if chat_message.video
                else chat_message.audio.file_size
            )

            # Check file size limit based on actual client being used
            try:
                is_premium = False
                if client_to_use != user:
                    # User's personal client
                    me = await client_to_use.get_me()
                    is_premium = getattr(me, 'is_premium', False)
                else:
                    # Bot's session
                    if hasattr(user, 'me') and user.me:
                        is_premium = getattr(user.me, 'is_premium', False)
                    else:
                        me = await user.get_me()
                        is_premium = getattr(me, 'is_premium', False)
            except:
                is_premium = False
                
            if not await fileSizeLimit(file_size, message, "download", is_premium):
                return

        parsed_caption = await get_parsed_msg(
            chat_message.caption or "", chat_message.caption_entities
        )
        parsed_text = await get_parsed_msg(
            chat_message.text or "", chat_message.entities
        )

        if chat_message.media_group_id:
            if not await processMediaGroup(chat_message, bot, message):
                await message.reply(
                    "**Could not extract any valid media from the media group.**"
                )
            return

        elif chat_message.media:
            start_time = time()
            progress_message = await message.reply("**📥 Downloading Progress...**")

            filename = get_file_name(message_id, chat_message)
            download_path = get_download_path(message.id, filename)

            media_path = await chat_message.download(
                file_name=download_path,
                progress=Leaves.progress_for_pyrogram,
                progress_args=progressArgs(
                    "📥 Downloading Progress", progress_message, start_time
                ),
            )

            LOGGER(__name__).info(f"Downloaded media: {media_path}")

            media_type = (
                "photo"
                if chat_message.photo
                else "video"
                if chat_message.video
                else "audio"
                if chat_message.audio
                else "document"
            )
            await send_media(
                bot,
                message,
                media_path,
                media_type,
                parsed_caption,
                progress_message,
                start_time,
            )

            cleanup_download(media_path)
            await progress_message.delete()
            
            # Only increment usage after successful download
            if increment_usage:
                db.increment_usage(message.from_user.id)

        elif chat_message.text or chat_message.caption:
            await message.reply(parsed_text or parsed_caption)
        else:
            await message.reply("**No media or text found in the post URL.**")

    except (PeerIdInvalid, BadRequest, KeyError):
        await message.reply("**Make sure the user client is part of the chat.**")
    except Exception as e:
        error_message = f"**❌ {str(e)}**"
        await message.reply(error_message)
        LOGGER(__name__).error(e)
    finally:
        # Clean up user client if it was created
        if user_client and user_client != user:
            try:
                await user_client.stop()
            except:
                pass


@bot.on_message(filters.command("dl") & filters.private)
@check_download_limit
async def download_media(bot: Client, message: Message):
    if len(message.command) < 2:
        await message.reply("**Provide a post URL after the /dl command.**")
        return

    post_url = message.command[1]
    
    # Check if user has personal session
    user_client = await get_user_client(message.from_user.id)
    
    # Don't increment usage here - let handle_download do it after success
    await track_task(handle_download(bot, message, post_url, user_client, True))


@bot.on_message(filters.command("bdl") & filters.private)
@paid_or_admin_only
async def download_range(bot: Client, message: Message):
    args = message.text.split()

    if len(args) != 3 or not all(arg.startswith("https://t.me/") for arg in args[1:]):
        await message.reply(
            "🚀 **Batch Download Process**\n"
            "`/bdl start_link end_link`\n\n"
            "💡 **Example:**\n"
            "`/bdl https://t.me/mychannel/100 https://t.me/mychannel/120`"
        )
        return

    try:
        start_chat, start_id = getChatMsgID(args[1])
        end_chat,   end_id   = getChatMsgID(args[2])
    except Exception as e:
        return await message.reply(f"**❌ Error parsing links:\n{e}**")

    if start_chat != end_chat:
        return await message.reply("**❌ Both links must be from the same channel.**")
    if start_id > end_id:
        return await message.reply("**❌ Invalid range: start ID cannot exceed end ID.**")

    # Check if user has personal session
    user_client = await get_user_client(message.from_user.id)
    client_to_use = user_client if user_client else user
    
    try:
        await client_to_use.get_chat(start_chat)
    except Exception:
        pass

    prefix = args[1].rsplit("/", 1)[0]
    loading = await message.reply(f"📥 **Downloading posts {start_id}–{end_id}…**")

    downloaded = skipped = failed = 0

    for msg_id in range(start_id, end_id + 1):
        url = f"{prefix}/{msg_id}"
        try:
            chat_msg = await client_to_use.get_messages(chat_id=start_chat, message_ids=msg_id)
            if not chat_msg:
                skipped += 1
                continue

            has_media = bool(chat_msg.media_group_id or chat_msg.media)
            has_text  = bool(chat_msg.text or chat_msg.caption)
            if not (has_media or has_text):
                skipped += 1
                continue

            task = track_task(handle_download(bot, message, url, user_client, False))
            try:
                await task
                downloaded += 1
                # Increment usage count for batch downloads after success
                db.increment_usage(message.from_user.id)
            except asyncio.CancelledError:
                await loading.delete()
                return await message.reply(
                    f"**❌ Batch canceled** after downloading `{downloaded}` posts."
                )

        except Exception as e:
            failed += 1
            LOGGER(__name__).error(f"Error at {url}: {e}")

        await asyncio.sleep(3)

    await loading.delete()
    await message.reply(
        "**✅ Batch Process Complete!**\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        f"📥 **Downloaded** : `{downloaded}` post(s)\n"
        f"⏭️ **Skipped**    : `{skipped}` (no content)\n"
        f"❌ **Failed**     : `{failed}` error(s)"
    )


@bot.on_message(filters.private & ~filters.command(["start", "help", "dl", "stats", "logs", "killall", "bdl", "myinfo", "login", "verify", "password", "logout", "cancel", "addadmin", "removeadmin", "setpremium", "removepremium", "ban", "unban", "broadcast", "adminstats", "userinfo"]))
@check_download_limit
async def handle_any_message(bot: Client, message: Message):
    if message.text and not message.text.startswith("/"):
        # Check if user has personal session
        user_client = await get_user_client(message.from_user.id)
        
        # Don't increment usage here - let handle_download do it after success
        await track_task(handle_download(bot, message, message.text, user_client, True))


@bot.on_message(filters.command("stats") & filters.private)
@register_user
async def stats(_, message: Message):
    currentTime = get_readable_time(time() - PyroConf.BOT_START_TIME)
    total, used, free = shutil.disk_usage(".")
    total = get_readable_file_size(total)
    used = get_readable_file_size(used)
    free = get_readable_file_size(free)
    sent = get_readable_file_size(psutil.net_io_counters().bytes_sent)
    recv = get_readable_file_size(psutil.net_io_counters().bytes_recv)
    cpuUsage = psutil.cpu_percent(interval=0.5)
    memory = psutil.virtual_memory().percent
    disk = psutil.disk_usage("/").percent
    process = psutil.Process(os.getpid())

    stats = (
        "**≧◉◡◉≦ Bot is Up and Running successfully.**\n\n"
        f"**➜ Bot Uptime:** `{currentTime}`\n"
        f"**➜ Total Disk Space:** `{total}`\n"
        f"**➜ Used:** `{used}`\n"
        f"**➜ Free:** `{free}`\n"
        f"**➜ Memory Usage:** `{round(process.memory_info()[0] / 1024**2)} MiB`\n\n"
        f"**➜ Upload:** `{sent}`\n"
        f"**➜ Download:** `{recv}`\n\n"
        f"**➜ CPU:** `{cpuUsage}%` | "
        f"**➜ RAM:** `{memory}%` | "
        f"**➜ DISK:** `{disk}%`"
    )
    await message.reply(stats)


@bot.on_message(filters.command("logs") & filters.private)
@admin_only
async def logs(_, message: Message):
    if os.path.exists("logs.txt"):
        await message.reply_document(document="logs.txt", caption="**Logs**")
    else:
        await message.reply("**Not exists**")


@bot.on_message(filters.command("killall") & filters.private)
@admin_only
async def cancel_all_tasks(_, message: Message):
    cancelled = 0
    for task in list(RUNNING_TASKS):
        if not task.done():
            task.cancel()
            cancelled += 1
    await message.reply(f"**Cancelled {cancelled} running task(s).**")


# User Commands
@bot.on_message(filters.command("myinfo") & filters.private)
async def my_info(_, message: Message):
    """Show user information command wrapper"""
    await user_info_command(_, message)


@bot.on_message(filters.command("login") & filters.private)
@register_user
async def login_command(_, message: Message):
    """Phone number login - Step 1: Send OTP"""
    try:
        if len(message.command) < 2:
            await message.reply(
                "📱 **Login with Phone Number**\n\n"
                "To access restricted content from your joined channels, "
                "login with your Telegram phone number.\n\n"
                "**Usage:** `/login +1234567890`\n\n"
                "Make sure to use international format (+ followed by country code and number)\n\n"
                "**Example:**\n"
                "  • `/login +1234567890`\n"
                "  • `/login +919876543210`\n\n"
                "**Note:** When you receive the OTP, enter it with spaces:\n"
                "  • `/verify 1 2 3 4 5`"
            )
            return
        
        phone_number = message.command[1]
        user_id = message.from_user.id
        
        loading_msg = await message.reply("📤 **Sending OTP code...**")
        
        success, msg, _ = await phone_auth_handler.send_otp(user_id, phone_number)
        
        await loading_msg.delete()
        await message.reply(msg)
        
    except Exception as e:
        await message.reply(f"❌ **Error: {str(e)}**")
        LOGGER(__name__).error(f"Error in login_command: {e}")


@bot.on_message(filters.command("verify") & filters.private)
@register_user
async def verify_command(_, message: Message):
    """Phone number login - Step 2: Verify OTP"""
    try:
        if len(message.command) < 2:
            await message.reply(
                "🔐 **Verify OTP Code**\n\n"
                "Enter the OTP code sent to your phone **with spaces between each digit**.\n\n"
                "**Usage:** `/verify 1 2 3 4 5`\n\n"
                "**Example:** If your code is 12345, send:\n"
                "`/verify 1 2 3 4 5`\n\n"
                "If you haven't received a code, start over with `/login <phone_number>`"
            )
            return
        
        # Get all parts after /verify command (handles spaced format like "1 2 3 4 5")
        otp_code = ' '.join(message.command[1:])
        user_id = message.from_user.id
        
        loading_msg = await message.reply("🔄 **Verifying OTP code...**")
        
        result = await phone_auth_handler.verify_otp(user_id, otp_code)
        
        await loading_msg.delete()
        
        if len(result) == 4:
            success, msg, needs_2fa, session_string = result
            if success and session_string:
                db.set_user_session(user_id, session_string)
            await message.reply(msg)
        else:
            success, msg, needs_2fa = result
            await message.reply(msg)
        
    except Exception as e:
        await message.reply(f"❌ **Error: {str(e)}**")
        LOGGER(__name__).error(f"Error in verify_command: {e}")


@bot.on_message(filters.command("password") & filters.private)
@register_user
async def password_command(_, message: Message):
    """Phone number login - Step 3: Verify 2FA password"""
    try:
        if len(message.command) < 2:
            await message.reply(
                "🔐 **Verify 2FA Password**\n\n"
                "Enter your Two-Factor Authentication password.\n\n"
                "**Usage:** `/password <your_2fa_password>`\n\n"
                "⚠️ **Security Note:** Your password will be deleted immediately after verification."
            )
            return
        
        password = message.text.split(maxsplit=1)[1]
        user_id = message.from_user.id
        
        try:
            await message.delete()
        except:
            pass
        
        loading_msg = await message.reply("🔄 **Verifying 2FA password...**")
        
        success, msg, session_string = await phone_auth_handler.verify_2fa_password(user_id, password)
        
        await loading_msg.delete()
        
        if success and session_string:
            db.set_user_session(user_id, session_string)
        
        await message.reply(msg)
        
    except Exception as e:
        await message.reply(f"❌ **Error: {str(e)}**")
        LOGGER(__name__).error(f"Error in password_command: {e}")


@bot.on_message(filters.command("logout") & filters.private)
@register_user
async def logout_command(_, message: Message):
    """Logout from account"""
    user_id = message.from_user.id
    
    if db.set_user_session(user_id, None):
        await message.reply(
            "✅ **Logged out successfully!**\n\n"
            "Your session has been removed. Use `/login <phone_number>` to login again."
        )
    else:
        await message.reply("❌ **Failed to logout. Please try again.**")


@bot.on_message(filters.command("cancel") & filters.private)
@register_user
async def cancel_command(_, message: Message):
    """Cancel pending authentication"""
    user_id = message.from_user.id
    success, msg = await phone_auth_handler.cancel_auth(user_id)
    await message.reply(msg)


# Admin Commands
@bot.on_message(filters.command("addadmin") & filters.private)
async def add_admin(_, message: Message):
    """Add admin command wrapper"""
    await add_admin_command(_, message)


@bot.on_message(filters.command("removeadmin") & filters.private)
async def remove_admin(_, message: Message):
    """Remove admin command wrapper"""
    await remove_admin_command(_, message)


@bot.on_message(filters.command("setpremium") & filters.private)
async def set_premium(_, message: Message):
    """Set premium command wrapper"""
    await set_premium_command(_, message)


@bot.on_message(filters.command("removepremium") & filters.private)
async def remove_premium(_, message: Message):
    """Remove premium command wrapper"""
    await remove_premium_command(_, message)


@bot.on_message(filters.command("ban") & filters.private)
async def ban_user(_, message: Message):
    """Ban user command wrapper"""
    await ban_user_command(_, message)


@bot.on_message(filters.command("unban") & filters.private)
async def unban_user(_, message: Message):
    """Unban user command wrapper"""
    await unban_user_command(_, message)


@bot.on_message(filters.command("broadcast") & filters.private)
async def broadcast(_, message: Message):
    """Broadcast command wrapper"""
    await broadcast_command(_, message)


@bot.on_message(filters.command("adminstats") & filters.private)
async def admin_stats(_, message: Message):
    """Admin stats command wrapper"""
    await admin_stats_command(_, message)


# Callback handler for broadcast confirmation
@bot.on_callback_query()
async def callback_handler(_, callback_query):
    """Handle callback queries"""
    await broadcast_callback_handler(_, callback_query)


if __name__ == "__main__":
    try:
        LOGGER(__name__).info("Bot Started!")
        
        # Initialize database on startup
        LOGGER(__name__).info("Initializing database...")
        db.init_database()
        
        # Add initial admin if specified in config
        if PyroConf.OWNER_ID and PyroConf.OWNER_ID > 0:
            # Add owner to users table first
            db.add_user(PyroConf.OWNER_ID, "Owner", "Bot", "Owner")
            # Then set as admin
            db.add_admin(PyroConf.OWNER_ID, PyroConf.OWNER_ID)
            LOGGER(__name__).info(f"Added owner {PyroConf.OWNER_ID} as admin")
        
        # Start the user client if valid session is provided
        if user and PyroConf.SESSION_STRING and len(PyroConf.SESSION_STRING) > 50 and not PyroConf.SESSION_STRING.startswith("your_"):
            user.start()
            LOGGER(__name__).info("User client started successfully")
        else:
            LOGGER(__name__).warning("No valid SESSION_STRING provided - users must login with phone number")
        bot.run()
    except KeyboardInterrupt:
        pass
    except Exception as err:
        LOGGER(__name__).error(err)
    finally:
        LOGGER(__name__).info("Bot Stopped")
