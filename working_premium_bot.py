import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from telegram.constants import ParseMode

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '7500826569:AAHSXBY9elBf89fyAhV_EmGuUGrryGXdVq8')
ADMIN_ID = int(os.getenv('ADMIN_USER_ID', '606898749'))

logger.info(f"🤖 Bot starting with token: {BOT_TOKEN[:10]}...")
logger.info(f"👤 Admin ID: {ADMIN_ID}")

def create_keyboard():
    keyboard = [
        [InlineKeyboardButton("🧠 الذكاء الاصطناعي", callback_data="ai")],
        [InlineKeyboardButton("📊 الإحصائيات", callback_data="stats")],
        [InlineKeyboardButton("ℹ️ المعلومات", callback_data="info")]
    ]
    return InlineKeyboardMarkup(keyboard)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    logger.info(f"📨 /start from {user.first_name}")
    
    text = f"""🚀 **أهلاً وسهلاً {user.first_name}!**

مرحباً بك في البوت الاحترافي!

🎯 **الميزات المتاحة:**
🧠 الذكاء الاصطناعي
📊 الإحصائيات  
ℹ️ المعلومات

👇 اختر ما تريد:"""
    
    await update.message.reply_text(
        text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=create_keyboard()
    )

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    logger.info(f"🔘 Button: {data}")
    
    if data == "ai":
        text = """🧠 **الذكاء الاصطناعي**

أرسل أي سؤال وسأجيب عليه!

💡 للحصول على إجابات متطورة، أضف مفاتيح API في Railway:
• OPENAI_API_KEY  
• GEMINI_API_KEY"""
        
    elif data == "stats":
        text = """📊 **إحصائيات البوت**

🤖 البوت: 🟢 يعمل بكفاءة
⚡ السرعة: ممتازة
🔧 الحالة: مستقرة

👨‍💻 المطور: @rsdy1"""
        
    elif data == "info":
        text = """ℹ️ **معلومات البوت**

📅 الإصدار: v1.0
🔧 اللغة: Python
📚 المكتبة: python-telegram-bot

👨‍💻 المطور: @rsdy1
🆘 الدعم: متاح 24/7"""
    
    else:
        text = "🔄 قيد التطوير!"
    
    keyboard = [[InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="main")]]
    
    if data == "main":
        text = "🏠 **القائمة الرئيسية**\n\n👇 اختر ما تريد:"
        keyboard = create_keyboard()
    
    await query.edit_message_text(
        text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = update.message.text
    
    if text and not text.startswith('/'):
        response = f"🧠 مرحباً {user.first_name}!\n\nسؤالك: {text}\n\n💡 هذا رد ذكي أساسي. لردود متطورة، أضف مفاتيح API!"
        
        keyboard = [[InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="main")]]
        
        await update.message.reply_text(
            response,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

def main():
    logger.info("🚀 Starting ultra simple bot...")
    
    app = Application.builder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CallbackQueryHandler(callback_handler))
    
    logger.info("✅ Ultra simple bot ready!")
    
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
