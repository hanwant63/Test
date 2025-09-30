# Telegram Media Downloader Bot

## Overview
This is a Telegram bot that downloads media (photos, videos, audio, documents) from Telegram channels and posts. It includes user management, download limits, and premium features.

## Project Structure
- **main.py**: Main bot application with command handlers
- **config.py**: Configuration loader from environment variables
- **database.py**: SQLite database manager for users, usage tracking, and admin functions
- **access_control.py**: Decorators for user authentication and authorization
- **admin_commands.py**: Admin-specific command handlers
- **logger.py**: Logging configuration
- **helpers/**: Utility modules for file handling, messages, and media processing

## Technology Stack
- **Language**: Python 3.11
- **Framework**: Pyrogram (Telegram Bot API)
- **Database**: SQLite
- **Media Processing**: FFmpeg, Pillow
- **Dependencies**: See requirements.txt

## Configuration

### Required Environment Variables (config.env)
The bot requires the following credentials in `config.env`:

1. **API_ID**: Get from https://my.telegram.org
2. **API_HASH**: Get from https://my.telegram.org
3. **BOT_TOKEN**: Get from @BotFather on Telegram
4. **SESSION_STRING**: Generate using @SmartUtilBot (use /pyro command)
5. **OWNER_ID**: Your Telegram user ID (get from @userinfobot)

### Security Note
- **IMPORTANT**: Never commit `config.env` to version control
- All sensitive credentials are stored in Replit Secrets or config.env
- The config.env file is already in .gitignore for security

## Features
- Download media from Telegram posts (photos, videos, audio, documents)
- Media group support
- User management with role-based access (free, premium, admin)
- Download limits for free users (5 per day)
- Batch download for premium users
- Admin commands for user management and broadcasting
- Personal session support for accessing restricted content

## Setup Instructions

1. **Configure Credentials**:
   - Edit `config.env` with your actual Telegram API credentials
   - Make sure all values are properly set

2. **Run the Bot**:
   - The workflow "Telegram Bot" is already configured
   - Click Run to start the bot
   - Check the console for startup logs

3. **Test the Bot**:
   - Find your bot on Telegram using the username you set with @BotFather
   - Send `/start` to begin
   - Send `/help` to see all commands

## Bot Commands

### User Commands
- `/start` - Welcome message and bot introduction
- `/help` - Show all commands and usage examples
- `/dl <url>` - Download media from a Telegram post URL
- `/stats` - View bot statistics and uptime
- `/myinfo` - View your account information
- `/setsession` - Set your personal session string

### Premium Commands
- `/bdl <start_url> <end_url>` - Batch download posts in range

### Admin Commands
- `/logs` - Download bot logs
- `/killall` - Cancel all running download tasks
- `/addadmin <user_id>` - Add a new admin
- `/removeadmin <user_id>` - Remove admin privileges
- `/setpremium <user_id> <days>` - Grant premium access
- `/removepremium <user_id>` - Revoke premium access
- `/ban <user_id>` - Ban a user
- `/unban <user_id>` - Unban a user
- `/broadcast <message>` - Send message to all users
- `/adminstats` - View detailed bot statistics

## Database
- Uses SQLite for local storage
- Database file: `bot_database.db`
- Automatic initialization on first run
- Tables: users, admins, daily_usage, broadcasts

## File Storage
- Downloaded media is temporarily stored in local filesystem
- Thumbnails are generated in the `Assets/` directory
- All temporary files are cleaned up after upload

## Recent Changes
- 2025-09-30: Initial Replit environment setup
  - Installed Python 3.11 and all dependencies
  - Configured FFmpeg for media processing
  - Set up proper .gitignore for security
  - Created config.env template
  - Configured Telegram Bot workflow

## Notes
- This is a backend service (Telegram bot), not a web application
- The bot runs continuously via the configured workflow
- Media processing requires FFmpeg (already installed)
- Free users have a daily download limit of 5 files
- Premium users have unlimited downloads