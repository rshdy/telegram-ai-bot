import os
import logging
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler, ChatMemberHandler
from telegram.constants import ParseMode, ChatAction, ChatType
from telegram.error import BadRequest, Forbidden

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Reduce httpx logging
httpx_logger = logging.getLogger("httpx")
httpx_logger.setLevel(logging.WARNING)

# Bot Configuration
BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '7500826569:AAHSXBY9elBf89fyAhV_EmGuUGrryGXdVq8')
ADMIN_ID = int(os.getenv('ADMIN_USER_ID', '606898749'))
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', 'AIzaSyC-xuAc1Ong6_HI3lCA4V1ybLyo5I0PPJQ').strip()

logger.info(f"🤖 Direct Gemini Bot starting...")
logger.info(f"🔮 Gemini: {len(GEMINI_API_KEY)} chars")

# Bot data
bot_channels = {}

# Initialize Gemini
gemini_model = None
gemini_vision = None

if GEMINI_API_KEY:
    try:
        import google.generativeai as genai
        genai.configure(api_key=GEMINI_API_KEY)
        gemini_model = genai.GenerativeModel('gemini-pro')
        gemini_vision = genai.GenerativeModel('gemini-pro-vision')
        logger.info("✅ Gemini Pro & Vision ready")
    except Exception as e:
        logger.error(f"❌ Gemini error: {e}")
        gemini_model = None
        gemini_vision = None
