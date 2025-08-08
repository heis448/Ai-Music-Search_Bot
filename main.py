import os
import logging
import requests
from uuid import uuid4
from telegram import Update, InlineQueryResultArticle, InputTextMessageContent, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    InlineQueryHandler,
    filters,
    CallbackContext,
    CallbackQueryHandler
)
import yt_dlp
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import asyncio
import time
from datetime import datetime, timedelta
import json
from collections import defaultdict
import glob
import sys
import subprocess

# The new GIF URL for the music visualizer
MUSIC_VISUALIZER_GIF = "https://media2.giphy.com/media/v1.Y2lkPTc5MGI3NjExMXhvZ3ppbndrZWRocXNrN3E0OXVyenl2NmtwbWUzYXN2bGF1Z3pqdyZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/cAfaWIcWr7qus/giphy.gif" 
# Track first-time users and store user data
user_data = defaultdict(dict)

# Admin list (add your Telegram user ID here)
ADMINS = [7928993116]  # Replace with your actual Telegram ID

# Banned users list
banned_users = set()

# Bot start time for uptime calculation
bot_start_time = time.time()

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Configuration
TOKEN = "7744151945:AAHNTviI-k8Z2Cp6plRxoc5WZIiFSx4ZOs8"  # Replace with your actual bot token from @Botfathet
SPOTIFY_CLIENT_ID = "539a3af17aa24fbab30bd16b9a6551cd"  # Replace with your actual SPOTIFY_CLIENT_ID
SPOTIFY_CLIENT_SECRET = "c5c1d9354966474eb4a705bf3e2c886b"  # Replace with your actual SPOTIFY_CLIENT_SECRET

# Initialize Spotify client
sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(
    client_id=SPOTIFY_CLIENT_ID,
    client_secret=SPOTIFY_CLIENT_SECRET
))

# Create necessary directories if they don't exist
if not os.path.exists('downloads'):
    os.makedirs('downloads')
if not os.path.exists('bot_data'):
    os.makedirs('bot_data')
if not os.path.exists('audio_downloads'):
    os.makedirs('audio_downloads')

async def save_user_data():
    """Save user data to a JSON file in a non-blocking way."""
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, _save_user_data_sync)

def _save_user_data_sync():
    """Synchronous part of saving user data."""
    with open('bot_data/user_data.json', 'w') as f:
        json.dump(user_data, f, indent=4)

async def load_user_data():
    """Load user data from a JSON file in a non-blocking way."""
    global user_data
    loop = asyncio.get_running_loop()
    try:
        user_data_dict = await loop.run_in_executor(None, _load_user_data_sync)
        user_data = defaultdict(dict, user_data_dict)
    except FileNotFoundError:
        user_data = defaultdict(dict)

def _load_user_data_sync():
    """Synchronous part of loading user data."""
    with open('bot_data/user_data.json', 'r') as f:
        return json.load(f)

async def store_user_info(user):
    """Store or update user information in the in-memory store and save it."""
    user_id = str(user.id)
    if user_id not in user_data:
        # New user, initialize data
        user_data[user_id] = {
            'username': user.username or "No username",
            'first_name': user.first_name or "",
            'last_name': user.last_name or "",
            'language_code': user.language_code or "en",
            'join_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'last_active': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'interaction_count': 1
        }
    else:
        # Existing user, just update activity and interaction count
        user_data[user_id]['last_active'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        user_data[user_id]['interaction_count'] = user_data[user_id].get('interaction_count', 0) + 1
    await save_user_data()

async def send_new_user_notification_to_admin(user, application):
    """Send a simple notification to admin when a new user starts the bot."""
    user_id = str(user.id)
    if user_id not in user_data:
        await store_user_info(user)
        for admin_id in ADMINS:
            try:
                await application.bot.send_message(admin_id, "New user 👤 Online")
            except Exception as e:
                logger.error(f"Couldn't send new user notification to admin {admin_id}: {e}")

async def start(update: Update, context: CallbackContext) -> None:
    """Send welcome message and handle new users."""
    user = update.message.from_user
    user_id = user.id

    if user_id in banned_users:
        await update.message.reply_text("🚫 You are banned from using this bot.")
        return

    await store_user_info(user)

    # Calculate dynamic values for the welcome message
    current_time = time.time()
    uptime_seconds = int(current_time - bot_start_time)
    uptime_str = str(timedelta(seconds=uptime_seconds))
    total_users = len(user_data)
    current_datetime = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # Send a temporary message to measure ping
    start_time = time.time()
    temp_msg = await update.message.reply_text("Calculating ping...")
    end_time = time.time()
    ping_latency = round((end_time - start_time) * 1000, 2)
    
    # Construct the new welcome message with the required format
    welcome_msg_text = (
        f"╭──《 Ai Music Search Bot🌟》──⊰\n"
        f"│\n"
        f"│ ⚡ 𝗨𝗽𝘁𝗶𝗺𝗲: {uptime_str}\n"
        f"│\n"
        f"│ 💫Ping : {ping_latency}ms\n"
        f"│\n"
        f"│ 📊 𝗨𝘀𝗲𝗿𝘀: {total_users}\n"
        f"│\n"
        f"│ 📅 𝗗𝗔𝗧𝗘 : {current_datetime}\n"
        f"│\n"
        f"│ 🧭  Use /menu To explore!\n"
        f"│\n"
        f"│💾 Use: /help to view all commands! \n"
        f"╰─────────────────────⊰\n"
        f"\n"
        f"🌹 Welcome, @{user.username or 'N/A'}!\n"
        f"🆔 Your Telegram ID: {user_id}\n"
        f"👤 Your Username: @{user.username or 'N/A'}\n"
        f"\n"
        f"I can search and play music 🎶 from:\n"
        f"- YouTube\n"
        f"- Spotify\n"
        f"- JioSaavn\n"
        f"- Google Music\n"
        f"\n"
        f"How to use this Ai Music Bot:\n"
        f"1. Send me a song name or URL\n"
        f"2. Use inline mode: @Aimusicsearchbot <song name>\n"
        f"3. Send a voice note with song name\n\n"
        f"Bot developed by Tylor ~ Heis_Tech 💫"
    )

    # Delete the "Calculating ping..." message
    await temp_msg.delete()

    # Combined GIF and welcome message
    await update.message.reply_animation(animation=MUSIC_VISUALIZER_GIF, caption=welcome_msg_text)

    # The startup audio message remains the same
    startup_audio_url = "https://youtube.com/shorts/Mgz24YTx5J8?si=97oeHhHz-L7Yur2z"
    await asyncio.sleep(0.1)
    await download_and_send_audio(context.bot, update.message.chat_id, startup_audio_url, "Welcome to Ai Music Bot Dawg!☺️")

async def update_command(update: Update, context: CallbackContext) -> None:
    """Check for and apply updates from the git repository."""
    await update.effective_message.reply_text("🔄 Checking for updates...")

    try:
        # Run git pull to fetch latest changes
        result = subprocess.run(['git', 'pull'], capture_output=True, text=True, check=True)
        if "Already up to date." in result.stdout:
            await update.effective_message.reply_text("✅ Bot is already up to date.")
        else:
            await update.effective_message.reply_text("✨ New updates found and applied! Restarting the bot to finalize the update...")
            os.execl(sys.executable, sys.executable, *sys.argv)
    except subprocess.CalledProcessError as e:
        await update.effective_message.reply_text(f"❌ Failed to update the bot. Error: {e.stderr}")
    except FileNotFoundError:
        await update.effective_message.reply_text("❌ Git is not installed or not in the system's PATH.")
    except Exception as e:
        logger.error(f"Error during update command: {e}")
        await update.effective_message.reply_text("❌ An unexpected error occurred during the update process.")

async def ping_command(update: Update, context: CallbackContext) -> None:
    """Test bot response speed."""
    start_time = time.time()
    message = await update.message.reply_text("🏓 Pong!")
    end_time = time.time()
    latency = round((end_time - start_time) * 1000, 2)
    await message.edit_text(f"🏓 Pong!\n⏱ Bot latency: {latency}ms")

async def uptime_command(update: Update, context: CallbackContext) -> None:
    """Show bot uptime."""
    current_time = time.time()
    uptime_seconds = current_time - bot_start_time
    uptime = timedelta(seconds=int(uptime_seconds))
    await update.message.reply_text(
        f"⏱ Bot Uptime:\n"
        f"Started at: {datetime.fromtimestamp(bot_start_time).strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"Uptime: {str(uptime)}"
    )

async def menu_command(update: Update, context: CallbackContext) -> None:
    """Show menu with quick options."""
    if update.message.from_user.id in banned_users:
        await update.message.reply_text("🚫 You are banned from using this bot.")
        return

    menu_text = (
        "╭──《 All Bot Commands/ 💫 》──⊰\n"
        "├── \n"
        "│   ├── /start - Show welcome message😊\n"
        "│   ├── /menu - Show quick menu 📃\n"
        "│   ├── /help - Show command help\n"
        "│   ├── /about - About this bot\n"
        "│   ├── /stats - Bot statistics\n"
        "│   ├── /ping - Test bot response speed 🚤\n"
        "│   ├── /uptime - Show bot uptime ⌚\n"
        "│   ├── /update - Check for and apply updates✅\n"
        "│   └── /restart - Restart the bot 💻(admin only)\n"
        "│\n"
        "├── Music Commands/\n"
        "│   ├── /artist <name> - Search for artist tracks🎶\n"
        "│   ├── Send song name - Search for song🎶\n"
        "│   ├── Send artist name - Search for artist 👦\n"
        "│   └── Send YouTube/Spotify URL - Process music link 🔗\n"
        "│\n"
        "└── Admin Commands/\n"
        "    ├── /broadcast <message> - Broadcast to all users👥 \n"
        "    ├── /addadmin <user_id> - Add a new admin🔎\n"
        "    ├── /ban <user_id> - Ban a user⚠️\n"
        "    └── /unban <user_id> - Unban a user😉\n\n"
        "Bot developed by Tylor ~ Heis_Tech 💫"
    )
    # The menu command now sends the GIF with the text as a caption
    await update.message.reply_animation(animation=MUSIC_VISUALIZER_GIF, caption=menu_text)

async def broadcast_command(update: Update, context: CallbackContext) -> None:
    """Broadcast a message to all users (admin only)."""
    user_id = update.message.from_user.id
    if user_id not in ADMINS:
        await update.message.reply_text("🚫 You are not authorized to use this command.")
        return

    if not context.args:
        await update.message.reply_text("Usage: /broadcast <message>")
        return

    message = ' '.join(context.args)
    total_sent = 0
    failed_users = []
    broadcast_msg = await update.message.reply_text("📢 Starting broadcast...")

    for uid in user_data:
        try:
            await context.bot.send_message(uid, f"📢 Broadcast from admin:\n\n{message}")
            total_sent += 1
        except Exception as e:
            failed_users.append(uid)
            logger.error(f"Failed to send to user {uid}: {e}")

    result_text = (
        f"📢 Broadcast completed!\n\n"
        f"Total users: {len(user_data)}\n"
        f"Successfully sent: {total_sent}\n"
        f"Failed: {len(failed_users)}\n"
    )

    if failed_users:
        result_text += f"\nFailed users: {', '.join(failed_users[:10])}"
        if len(failed_users) > 10:
            result_text += f" and {len(failed_users)-10} more..."
    await broadcast_msg.edit_text(result_text)

async def add_admin(update: Update, context: CallbackContext) -> None:
    """Add a new admin to the bot (admin only)."""
    user_id = update.message.from_user.id
    if user_id not in ADMINS:
        await update.message.reply_text("🚫 You are not authorized to use this command.")
        return

    if not context.args:
        await update.message.reply_text("Usage: /addadmin <user_id>")
        return

    try:
        new_admin_id = int(context.args[0])
        if new_admin_id not in ADMINS:
            ADMINS.append(new_admin_id)
            await update.message.reply_text(f"✅ User {new_admin_id} has been added as admin.")
        else:
            await update.message.reply_text(f"User {new_admin_id} is already an admin.")
    except ValueError:
        await update.message.reply_text("Invalid user ID. Please provide a numeric ID.")

async def help_command(update: Update, context: CallbackContext) -> None:
    """Send help message."""
    if update.message.from_user.id in banned_users:
        await update.message.reply_text("🚫 You are banned from using this bot.")
        return

    help_text = (
        "╭──《 All Bot Commands/ 》──⊰\n"
        "├── \n"
        "│   ├── /start - Show welcome message\n"
        "│   ├── /menu - Show quick menu\n"
        "│   ├── /help - Show command help\n"
        "│   ├── /about - About this bot\n"
        "│   ├── /stats - Bot statistics\n"
        "│   ├── /ping - Test bot response speed\n"
        "│   ├── /uptime - Show bot uptime\n"
        "│   ├── /update - Check for and apply updates\n"
        "│   └── /restart - Restart the bot (admin only)\n"
        "│\n"
        "├── Music Commands/\n"
        "│   ├── /artist <name> - Search for artist tracks\n"
        "│   ├── Send song name - Search for song\n"
        "│   ├── Send artist name - Search for artist\n"
        "│   └── Send YouTube/Spotify URL - Process music link\n"
        "│\n"
        "└── Admin Commands/\n"
        "    ├── /broadcast <message> - Broadcast to all users👥 \n"
        "    ├── /addadmin <user_id> - Add a new admin\n"
        "    ├── /ban <user_id> - Ban a user\n"
        "    └── /unban <user_id> - Unban a user\n\n"
        "Bot developed by Tylor ~ Heis_Tech 💫"
    )
    await update.message.reply_text(help_text)

async def about_command(update: Update, context: CallbackContext) -> None:
    """Show about information."""
    if update.message.from_user.id in banned_users:
        await update.message.reply_text("🚫 You are banned from using this bot.")
        return

    await update.message.reply_text(
        "🤖 Ai Music Bot 🤖\n\n"
        "Version: 2.0\n"
        "Developer: Tylor\n"
        "Framework: python-telegram-bot\n"
        "Features:\n"
        "- Search and play music from YouTube, Spotify, JioSaavn, Google Music\n"
        "- Inline mode support\n"
        "- Admin controls\n"
        "- Uptime monitoring\n"
        "- Artist track listing\n\n"
        "Credits to my Developer ➡️ Tylor ~ Heis_Tech,,For Creating Me😊"
    )

async def stats_command(update: Update, context: CallbackContext) -> None:
    """Show bot statistics."""
    if update.message.from_user.id in banned_users:
        await update.message.reply_text("🚫 You are banned from using this bot.")
        return

    stats_text = (
        "📊 Bot Statistics 📊\n\n"
        f"Total users: {len(user_data)}\n"
        f"Total banned users: {len(banned_users)}\n"
        f"Total admins: {len(ADMINS)}\n"
        f"Uptime: {str(timedelta(seconds=int(time.time() - bot_start_time)))}\n"
        "More stats coming soon..."
    )
    await update.message.reply_text(stats_text)

async def ban_user(update: Update, context: CallbackContext) -> None:
    """Ban a user from using the bot (admin only)."""
    user_id = update.message.from_user.id
    if user_id not in ADMINS:
        await update.message.reply_text("🚫 You are not authorized to use this command.")
        return

    if not context.args:
        await update.message.reply_text("Usage: /ban <user_id>")
        return

    try:
        target_id = int(context.args[0])
        banned_users.add(target_id)
        await update.message.reply_text(f"✅ User {target_id} has been banned.")
    except ValueError:
        await update.message.reply_text("Invalid user ID. Please provide a numeric ID.")

async def unban_user(update: Update, context: CallbackContext) -> None:
    """Unban a user (admin only)."""
    user_id = update.message.from_user.id
    if user_id not in ADMINS:
        await update.message.reply_text("🚫 You are not authorized to use this command.")
        return

    if not context.args:
        await update.message.reply_text("Usage: /unban <user_id>")
        return

    try:
        target_id = int(context.args[0])
        if target_id in banned_users:
            banned_users.remove(target_id)
            await update.message.reply_text(f"✅ User {target_id} has been unbanned.")
        else:
            await update.message.reply_text(f"User {target_id} is not banned.")
    except ValueError:
        await update.message.reply_text("Invalid user ID. Please provide a numeric ID.")

async def usr_command(update: Update, context: CallbackContext) -> None:
    """List all users with inline keyboard (admin only)."""
    user_id = update.effective_user.id

    if user_id not in ADMINS:
        await update.effective_message.reply_text("🚫 You are not authorized to use this command.")
        return

    if not user_data:
        await update.effective_message.reply_text("No users have interacted with the bot yet.")
        return

    keyboard = []
    for uid, user_info in user_data.items():
        username = user_info.get('username', f"User {uid}")
        btn_text = f"👤 {username}"
        callback_data = f"user_detail:{uid}"
        keyboard.append([InlineKeyboardButton(btn_text, callback_data=callback_data)])

    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.callback_query:
        try:
            await update.callback_query.edit_message_text(
                "📋 User List - Select a user to view details:",
                reply_markup=reply_markup
            )
        except Exception as e:
            logger.error(f"Error editing message for back to user list: {e}")
    else:
        await update.message.reply_text(
            "📋 User List - Select a user to view details:",
            reply_markup=reply_markup
        )

async def show_user_detail(update: Update, context: CallbackContext, user_id: str):
    """Show detailed information about a specific user (admin only)."""
    query = update.callback_query
    await query.answer()

    user_info = user_data.get(user_id)
    if not user_info:
        await query.edit_message_text("User not found in database.")
        return

    try:
        profile_photos = await context.bot.get_user_profile_photos(user_id)
        has_profile_photo = "✅ Yes" if profile_photos.photos else "❌ No"
    except Exception:
        has_profile_photo = "❌ No"

    user_detail = (
        f"👤 User Details\n\n"
        f"🆔 ID: {user_id}\n"
        f"📛 Name: {user_info.get('first_name', '')} {user_info.get('last_name', '')}\n"
        f"🔗 Username: @{user_info.get('username', 'N/A')}\n"
        f"📱 Phone Number: 🔒 Not Accessible\n"
        f"📝 Bio: 🔒 Not Accessible\n"
        f"🖼️ Profile Picture: {has_profile_photo}\n"
        f"🌐 Language: {user_info.get('language_code', 'N/A')}\n"
        f"📅 Join Date: {user_info.get('join_date', 'N/A')}\n"
        f"🕒 Last Active: {user_info.get('last_active', 'N/A')}\n"
        f"🔢 Interactions: {user_info.get('interaction_count', 0)}"
    )

    keyboard = [
        [InlineKeyboardButton("⬅️ Back to User List", callback_data="back_to_user_list")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    try:
        await query.edit_message_text(
            user_detail,
            reply_markup=reply_markup
        )
    except Exception as e:
        logger.error(f"Error editing message in show_user_detail: {e}")

async def handle_callback_query(update: Update, context: CallbackContext) -> None:
    """Handle callback queries from inline buttons."""
    query = update.callback_query
    await query.answer()

    data = query.data

    try:
        if data.startswith("user_detail:"):
            user_id = data.split(':')[1]
            await show_user_detail(update, context, user_id)
        elif data == "back_to_user_list":
            await usr_command(update, context)
        elif data.startswith("artist_more:"):
            _, artist_id, page = data.split(':')
            page = int(page)
            top_tracks = sp.artist_top_tracks(artist_id)
            artist = sp.artist(artist_id)
            start_idx = page * 5
            end_idx = (page + 1) * 5
            tracks = top_tracks['tracks'][start_idx:end_idx]

            if not tracks:
                await query.edit_message_text("No more tracks to show.")
                return

            message = f"🎤 More tracks for {artist['name']} (Page {page + 1}):\n\n"
            keyboard = []

            for i, track in enumerate(tracks, start_idx + 1):
                keyboard.append([
                    InlineKeyboardButton(
                        f"🎵 {track['name']}",
                        callback_data=f"download_track:{track['name']} {artist['name']}"
                    )
                ])

            pagination_row = []
            if page > 0:
                pagination_row.append(
                    InlineKeyboardButton("⬅️ Previous", callback_data=f"artist_more:{artist_id}:{page - 1}")
                )
            if end_idx < len(top_tracks['tracks']):
                pagination_row.append(
                    InlineKeyboardButton("Next ➡️", callback_data=f"artist_more:{artist_id}:{page + 1}")
                )

            if pagination_row:
                keyboard.append(pagination_row)

            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(message, reply_markup=reply_markup)
        elif data.startswith("download_track:"):
            track_query = data.split(':', 1)[1]
            await query.edit_message_text(f"Your request for '{track_query}' is being processed ☺️. Please wait...")
            fake_update = Update.de_json({'update_id': 0, 'callback_query': query.to_dict()}, context.bot)
            await search_and_send_audio(fake_update, context, track_query)
        elif data.startswith("download_option:"):
            _, option, url = data.split(':', 2)
            if option == "audio":
                await query.edit_message_text("Downloading audio... please wait😊")
                await download_youtube_audio(update, context, url)
            elif option == "video":
                await query.edit_message_text("Downloading video... please wait😊")
                await download_youtube_video(update, context, url)
    except Exception as e:
        logger.error(f"Error handling callback query: {e}")
        try:
            await query.edit_message_text("An error occurred. Please try again.")
        except Exception:
            pass

async def artist_command(update: Update, context: CallbackContext) -> None:
    """Handle artist search command with improved track listing."""
    user_id = update.effective_user.id
    if user_id in banned_users:
        await update.effective_message.reply_text("🚫 You are banned from using this bot.")
        return

    query = ' '.join(context.args)
    if not query:
        await update.effective_message.reply_text("Please provide an artist name after /artist")
        return

    processing_msg = await update.effective_message.reply_text("Thank you 🤝 for your selection, Please wait..")

    try:
        results = sp.search(q=query, type='artist', limit=1)
        if not results['artists']['items']:
            await processing_msg.edit_text("No artist found with that name.")
            return

        artist = results['artists']['items'][0]
        artist_id = artist['id']
        top_tracks = sp.artist_top_tracks(artist_id)

        if not top_tracks['tracks']:
            await processing_msg.edit_text("No tracks found for this artist.")
            return

        message = f"🎤 Top tracks for {artist['name']}:\n\nClick a track to download it:\n"
        keyboard = []

        for i, track in enumerate(top_tracks['tracks'][:5], 1):
            keyboard.append([
                InlineKeyboardButton(
                    f"{i}. {track['name']}",
                    callback_data=f"download_track:{track['name']} {artist['name']}"
                )
            ])

        if len(top_tracks['tracks']) > 5:
            keyboard.append([
                InlineKeyboardButton(
                    "View More Tracks ➡️",
                    callback_data=f"artist_more:{artist_id}:1"
                )
            ])

        reply_markup = InlineKeyboardMarkup(keyboard)
        await processing_msg.edit_text(message, reply_markup=reply_markup)
    except Exception as e:
        logger.error(f"Error in artist_command: {e}")
        await processing_msg.edit_text("Sorry, I couldn't find that artist. Please try another name.")

async def handle_message(update: Update, context: CallbackContext) -> None:
    """Handle all text messages with improved artist detection."""
    user = update.message.from_user
    user_id = user.id

    if user_id in banned_users:
        await update.message.reply_text("🚫 You are banned from using this bot.")
        return

    await store_user_info(user)

    text = update.message.text
    # Updated Spotify URL check to be more generic and reliable
    if "youtube.com" in text or "youtu.be" in text or "spotify.com" in text or "jiosaavn.com" in text:
        await handle_url(update, context, text)
        return
    else:
        processing_msg = await update.message.reply_text("Thank you 🤝 for your selection, Please wait..")
        try:
            # First, try to search on Spotify for the artist
            results = sp.search(q=text, type='artist', limit=1)
            if results and 'artists' in results and results['artists']['items']:
                artist = results['artists']['items'][0]
                if artist['name'].lower() == text.lower():
                    context.args = text.split()
                    await artist_command(update, context)
                    return
        except Exception as e:
            logger.error(f"Error checking artist name: {e}")

        # Fallback to Youtube if it's not a Spotify artist
        try:
            await search_and_send_audio(update, context, text)
        except Exception as e:
            logger.error(f"Error in handle_message: {e}")
            await processing_msg.edit_text("Sorry, I encountered an error processing your request. Please try again.")

async def handle_url(update: Update, context: CallbackContext, url: str) -> None:
    """Handle music URLs from different platforms."""
    if update.message.from_user.id in banned_users:
        await update.message.reply_text("🚫 You are banned from using this bot.")
        return

    chat_id = update.message.chat_id
    processing_msg = None
    try:
        processing_msg = await update.message.reply_text("Processing your request... Please wait...")
        if "spotify.com" in url:
            try:
                track_info = sp.track(url)
                query = f"{track_info['name']} {track_info['artists'][0]['name']}"
                await context.bot.delete_message(chat_id=chat_id, message_id=processing_msg.message_id)
                await search_and_send_audio(update, context, query)
            except Exception as e:
                logger.error(f"Spotify URL processing error: {e}")
                await context.bot.delete_message(chat_id=chat_id, message_id=processing_msg.message_id)
                await update.message.reply_text("Sorry, I couldn't process that Spotify URL.")
        elif "jiosaavn.com" in url:
            await context.bot.delete_message(chat_id=chat_id, message_id=processing_msg.message_id)
            await update.message.reply_text("JioSaavn support coming soon!")
        else:
            keyboard = [
                [
                    InlineKeyboardButton("Download Audio", callback_data=f"download_option:audio:{url}"),
                    InlineKeyboardButton("Download Video", callback_data=f"download_option:video:{url}"),
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await context.bot.delete_message(chat_id=chat_id, message_id=processing_msg.message_id)
            await update.message.reply_text(
                "🎵 YouTube URL detected. Choose download option:",
                reply_markup=reply_markup
            )
    except Exception as e:
        logger.error(f"Error processing URL: {e}")
        try:
            if processing_msg:
                await context.bot.delete_message(chat_id=chat_id, message_id=processing_msg.message_id)
        except Exception:
            pass
        await update.message.reply_text("Sorry, I couldn't process that URL. Please try another one.")

async def download_youtube_audio(update: Update, context: CallbackContext, url: str) -> None:
    """Download audio from YouTube."""
    chat_id = update.effective_chat.id
    audio_file_path = None
    try:
        ydl_opts_mp3 = {
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'outtmpl': 'audio_downloads/%(title)s.%(ext)s',
            'quiet': True,
            'cookiefile': 'cookies.txt'
        }
        with yt_dlp.YoutubeDL(ydl_opts_mp3) as ydl:
            info = ydl.extract_info(url, download=True)
            title = info.get('title', 'Audio')
            temp_filepath = ydl.prepare_filename(info).rsplit('.', 1)[0]
            audio_file_path = glob.glob(f"{temp_filepath}.*")[0]

        with open(audio_file_path, 'rb') as audio:
            await context.bot.send_audio(
                chat_id=chat_id,
                audio=audio,
                title=title,
                performer=info.get('artist', 'YouTube'),
                caption=f"🎵 {title}\n\nBot developed by Tylor ~ Heis_Tech ✅"
            )
    except yt_dlp.utils.DownloadError as e:
        logger.error(f"yt-dlp Download Error: {e}")
        error_msg = f"Failed to download audio. Error: {e}"
        if update.message:
            await update.message.reply_text(error_msg)
        elif update.callback_query:
            await update.callback_query.edit_message_text(error_msg)
    except Exception as e:
        logger.error(f"General YouTube audio download error: {e}")
        error_msg = "An unexpected error occurred while downloading the audio. Please try another link."
        if update.message:
            await update.message.reply_text(error_msg)
        elif update.callback_query:
            await update.callback_query.edit_message_text(error_msg)
    finally:
        if audio_file_path and os.path.exists(audio_file_path):
            os.remove(audio_file_path)

async def download_youtube_video(update: Update, context: CallbackContext, url: str) -> None:
    """Download video from YouTube."""
    chat_id = update.effective_chat.id
    video_file_path = None
    try:
        ydl_opts = {
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            'outtmpl': 'downloads/%(title)s.%(ext)s',
            'quiet': True,
            'cookiefile': 'cookies.txt'
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            video_file_path = ydl.prepare_filename(info)
            title = info.get('title', 'Video')
        with open(video_file_path, 'rb') as video:
            await context.bot.send_video(
                chat_id=chat_id,
                video=video,
                caption=f"🎥 {title}\n\nBot developed by Tylor ~ Heis_Tech ✅"
            )
    except yt_dlp.utils.DownloadError as e:
        logger.error(f"yt-dlp Video Download Error: {e}")
        error_msg = f"Failed to download video. Error: {e}"
        if update.message:
            await update.message.reply_text(error_msg)
        elif update.callback_query:
            await update.callback_query.edit_message_text(error_msg)
    except Exception as e:
        logger.error(f"General YouTube video download error: {e}")
        error_msg = "An unexpected error occurred while downloading the video. Please try another link."
        if update.message:
            await update.message.reply_text(error_msg)
        elif update.callback_query:
            await update.callback_query.edit_message_text(error_msg)
    finally:
        if video_file_path and os.path.exists(video_file_path):
            os.remove(video_file_path)

async def search_and_send_audio(update: Update, context: CallbackContext, query: str) -> None:
    """Search for a song and send audio, with fallback to YouTube Music."""
    user_id = update.effective_user.id
    if user_id in banned_users:
        if update.inline_query:
            await update.inline_query.answer([
                InlineQueryResultArticle(
                    id=str(uuid4()),
                    title="Error: You are banned",
                    input_message_content=InputTextMessageContent("🚫 You are banned from using this bot.")
                )
            ])
        else:
            await update.effective_message.reply_text("🚫 You are banned from using this bot.")
        return

    audio_file_path = None
    try:
        ydl_opts_mp3 = {
            'format': 'bestaudio/best',
            'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '192'}],
            'outtmpl': 'audio_downloads/%(title)s.%(ext)s',
            'quiet': True,
            'cookiefile': 'cookies.txt'
        }
        with yt_dlp.YoutubeDL(ydl_opts_mp3) as ydl:
            info = ydl.extract_info(f"ytsearch:{query}", download=True)
            if not info or not info.get('entries'):
                raise ValueError("No results found on YouTube")
            entry = info['entries'][0]
            temp_filepath = ydl.prepare_filename(entry).rsplit('.', 1)[0]
            audio_file_path = glob.glob(f"{temp_filepath}.*")[0]
            title = entry.get('title', 'Audio Track')

        if update.inline_query:
            await update.inline_query.answer([
                InlineQueryResultArticle(
                    id=str(uuid4()),
                    title=f"🎵 {title}",
                    input_message_content=InputTextMessageContent(f"Please send the song name to the bot for download: {title}")
                )
            ], cache_time=0)
        else:
            chat_id = update.effective_chat.id
            with open(audio_file_path, 'rb') as audio:
                await context.bot.send_audio(
                    chat_id=chat_id,
                    audio=audio,
                    title=title,
                    performer=entry.get('artist', 'YouTube'),
                    caption=f"🎵 {title}\n\nBot developed by Tylor ~ Heis_Tech ✅"
                )
    except Exception as e:
        logger.error(f"Search and download error: {e}")
        error_message = "Sorry, I couldn't find or download that song. Please try another query."
        if update.inline_query:
            await update.inline_query.answer([
                InlineQueryResultArticle(
                    id=str(uuid4()),
                    title="Error: Cannot find song",
                    input_message_content=InputTextMessageContent(error_message)
                )
            ], cache_time=0)
        else:
            await update.effective_message.reply_text(error_message)
    finally:
        if audio_file_path and os.path.exists(audio_file_path):
            os.remove(audio_file_path)

async def inline_query(update: Update, context: CallbackContext) -> None:
    """Handle inline music queries."""
    if not update.inline_query.query:
        return
    query = update.inline_query.query
    user_id = update.inline_query.from_user.id
    if user_id in banned_users:
        await update.inline_query.answer([
            InlineQueryResultArticle(
                id=str(uuid4()),
                title="🚫 You are banned from using this bot.",
                input_message_content=InputTextMessageContent("🚫 You are banned from using this bot.")
            )
        ])
        return
    try:
        ydl_opts_inline = {
            'format': 'bestaudio/best',
            'default_search': 'ytsearch',
            'noplaylist': True,
            'quiet': True,
            'force_generic_extractor': True,
            'cookiefile': 'cookies.txt'
        }
        with yt_dlp.YoutubeDL(ydl_opts_inline) as ydl:
            info = ydl.extract_info(query, download=False)
            if not info or not info.get('entries'):
                raise ValueError("No results found.")
            results = []
            for i, entry in enumerate(info.get('entries', [])[:10]):
                title = entry.get('title', 'Audio Track')
                results.append(
                    InlineQueryResultArticle(
                        id=str(uuid4()),
                        title=f"🎵 {title}",
                        input_message_content=InputTextMessageContent(f"Please send the song name to the bot for download: {title}")
                    )
                )
            await update.inline_query.answer(results, cache_time=5)
    except Exception as e:
        logger.error(f"Inline query error for '{query}': {e}")
        await update.inline_query.answer([
            InlineQueryResultArticle(
                id=str(uuid4()),
                title="Error: No results found",
                input_message_content=InputTextMessageContent("Sorry, I couldn't find that song. Please try a different query.")
            )
        ], cache_time=0)

async def handle_voice(update: Update, context: CallbackContext) -> None:
    """Handle voice messages by converting to text and searching."""
    if update.message.from_user.id in banned_users:
        await update.message.reply_text("🚫 You are banned from using this bot.")
        return
    await update.message.reply_text(
        "🎤 Voice note received!\n\n"
        "Currently, I can't process voice notes directly. Please type the song name you want to search for.\n\n"
        "Coming soon: Automatic voice recognition!"
    )

async def download_and_send_audio(bot, chat_id, url, caption=None):
    """Download and send audio from YouTube URL."""
    audio_file_path = None
    try:
        ydl_opts_mp3 = {
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'outtmpl': 'audio_downloads/%(title)s.%(ext)s',
            'quiet': True,
            'cookiefile': 'cookies.txt'
        }
        with yt_dlp.YoutubeDL(ydl_opts_mp3) as ydl:
            info = ydl.extract_info(url, download=True)
            title = info.get('title', 'Audio')
            temp_filepath = ydl.prepare_filename(info).rsplit('.', 1)[0]
            audio_file_path = glob.glob(f"{temp_filepath}.*")[0]

        final_caption = f"🎵 {title}\n\nBot developed by Tylor ~ Heis_Tech ✅"
        if caption:
            final_caption = f"{caption}\n\nBot developed by Tylor ~ Heis_Tech ✅"

        with open(audio_file_path, 'rb') as audio:
            await bot.send_audio(
                chat_id=chat_id,
                audio=audio,
                title=title,
                performer=info.get('artist', 'YouTube'),
                caption=final_caption
            )
    except Exception as e:
        logger.error(f"Audio download error: {e}")
        await bot.send_message(chat_id=chat_id, text=f"An error occurred while downloading the audio. Error: {e}")
    finally:
        if audio_file_path and os.path.exists(audio_file_path):
            os.remove(audio_file_path)

async def post_init(application: Application) -> None:
    """Function to run after the bot starts."""
    await load_user_data()
    bot = application.bot
    me = await bot.get_me()
    logger.info(f"Bot started as @{me.username}")
    startup_audio_url = "https://youtube.com/shorts/Mgz24YTx5J8?si=97oeHhHz-L7Yur2z"
    for admin_id in ADMINS:
        try:
            await bot.send_message(admin_id, "Yoh Tylor ☺️ 🎵 Music Bot is now online!")
            await download_and_send_audio(bot, admin_id, startup_audio_url, "Music Bot is now online!")
        except Exception as e:
            logger.error(f"Couldn't send startup message to admin {admin_id}: {e}")

def main() -> None:
    """Start the bot."""
    global application
    application = Application.builder().token(TOKEN).post_init(post_init).read_timeout(20).write_timeout(20).pool_timeout(20).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("menu", menu_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("artist", artist_command))
    application.add_handler(CommandHandler("about", about_command))
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(CommandHandler("broadcast", broadcast_command))
    application.add_handler(CommandHandler("addadmin", add_admin))
    application.add_handler(CommandHandler("ban", ban_user))
    application.add_handler(CommandHandler("unban", unban_user))
    application.add_handler(CommandHandler("usr", usr_command))
    application.add_handler(CommandHandler("ping", ping_command))
    application.add_handler(CommandHandler("uptime", uptime_command))
    application.add_handler(CommandHandler("update", update_command)) # Changed to /update
    # The /restart command can still be useful for admins to perform a quick restart without a full git pull.
    # We will leave the /restart command handler but make sure it's for admins only.
    application.add_handler(CommandHandler("restart", lambda update, context: os.execl(sys.executable, sys.executable, *sys.argv) if update.effective_user.id in ADMINS else update.effective_message.reply_text("🚫 You are not authorized to use this command.")))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(MessageHandler(filters.VOICE, handle_voice))
    application.add_handler(InlineQueryHandler(inline_query))
    application.add_handler(CallbackQueryHandler(handle_callback_query))

    application.run_polling(poll_interval=0.1)

if __name__ == "__main__":
    main()
