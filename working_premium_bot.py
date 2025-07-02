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
else:
    logger.info("⚠️ No Gemini key")

async def get_user_channels(context, user_id):
    """Get channels where user should be subscribed"""
    user_channels = []
    for channel_id, channel_info in bot_channels.items():
        try:
            member = await context.bot.get_chat_member(channel_id, user_id)
            if member.status not in ['member', 'administrator', 'creator']:
                user_channels.append(channel_info)
        except Exception as e:
            logger.error(f"Error checking {channel_id}: {e}")
    return user_channels

async def check_all_subscriptions(context, user_id):
    """Check if user subscribed to all channels"""
    required_channels = await get_user_channels(context, user_id)
    return len(required_channels) == 0

def create_subscription_keyboard(required_channels):
    """Create subscription keyboard"""
    keyboard = []
    for channel in required_channels:
        channel_name = channel.get('title', 'القناة')
        username = channel.get('username', '').replace('@', '')
        if username:
            channel_link = f"https://t.me/{username}"
            keyboard.append([InlineKeyboardButton(f"📺 اشترك في {channel_name}", url=channel_link)])
    
    keyboard.append([InlineKeyboardButton("✅ تحقق من الاشتراك", callback_data="check_subs")])
    return InlineKeyboardMarkup(keyboard)

async def get_gemini_response(text, user_name="المستخدم"):
    """Get direct response from Gemini"""
    if not gemini_model:
        return get_direct_fallback(text)
    
    try:
        # Direct prompt without prefixes
        prompt = f"""
أجب على السؤال التالي باللغة العربية بشكل مباشر ومفيد بدون مقدمات أو عناوين:

السؤال: {text}

قواعد الإجابة:
- أجب مباشرة على السؤال فقط
- لا تبدأ بعبارات مثل "إليك الإجابة" أو "بالطبع يمكنني مساعدتك"
- لا تستخدم رموز تعبيرية أو عناوين 
- فقط أعط الإجابة المطلوبة بشكل واضح ومفيد
- إذا كان السؤال عن الترجمة، أعط الترجمة مباشرة
- إذا كان حساب رياضي، أعط النتيجة مباشرة
- إذا كان سؤال برمجة، أعط الكود أو الشرح مباشرة
"""
        
        response = await asyncio.to_thread(gemini_model.generate_content, prompt)
        return response.text.strip()
        
    except Exception as e:
        logger.error(f"Gemini error: {e}")
        return get_direct_fallback(text)

def get_direct_fallback(text):
    """Direct fallback responses without prefixes"""
    text_lower = text.lower()
    
    # Greetings - keep simple
    if any(word in text_lower for word in ['مرحبا', 'السلام', 'أهلا', 'hello', 'hi']):
        return "أهلاً وسهلاً! كيف يمكنني مساعدتك اليوم؟"
    
    # Translation
    elif any(word in text_lower for word in ['ترجم', 'translate']):
        # Try basic translation
        basic_trans = translate_basic(text)
        if basic_trans:
            return basic_trans
        return "خطأ في الاتصال بـ Gemini للترجمة، حاول مرة أخرى"
    
    # Math
    elif any(word in text_lower for word in ['احسب', 'حل', 'math', '+', '-', '*', '/', '=']):
        # Try basic calculation
        basic_calc = calculate_basic(text)
        if basic_calc:
            return basic_calc
        return "خطأ في الاتصال بـ Gemini للحسابات، حاول مرة أخرى"
    
    # Programming
    elif any(word in text_lower for word in ['برمجة', 'كود', 'python', 'javascript', 'html', 'css']):
        return "خطأ في الاتصال بـ Gemini للمساعدة البرمجية، حاول مرة أخرى"
    
    # General questions
    else:
        return "خطأ في الاتصال بـ Gemini، حاول مرة أخرى"

def translate_basic(text):
    """Basic translation"""
    translations = {
        'hello': 'مرحبا',
        'hi': 'أهلا', 
        'thank you': 'شكراً لك',
        'good morning': 'صباح الخير',
        'good evening': 'مساء الخير',
        'how are you': 'كيف حالك',
        'what is your name': 'ما اسمك',
        'i love you': 'أحبك',
        'goodbye': 'وداعاً',
        'مرحبا': 'Hello',
        'أهلا': 'Hi',
        'شكراً': 'Thank you',
        'صباح الخير': 'Good morning',
        'مساء الخير': 'Good evening',
        'كيف حالك': 'How are you',
        'ما اسمك': 'What is your name',
        'أحبك': 'I love you',
        'وداعاً': 'Goodbye'
    }
    
    text_clean = text.lower().replace('ترجم', '').replace('translate', '').replace(':', '').strip()
    
    for original, translated in translations.items():
        if original in text_clean:
            return translated
    
    return None

def calculate_basic(text):
    """Basic calculation"""
    try:
        # Clean and replace symbols
        text = text.replace('احسب', '').replace('حل', '').replace('×', '*').replace('÷', '/')
        text = text.replace('=', '').replace('؟', '').strip()
        
        # Keep only numbers and operators
        allowed = '0123456789+-*/.() '
        clean_text = ''.join(c for c in text if c in allowed).strip()
        
        if clean_text and any(op in clean_text for op in ['+', '-', '*', '/']):
            try:
                result = eval(clean_text)
                return f"{result}"
            except:
                pass
        
        return None
    except:
        return None

async def analyze_image(image_data, prompt="اشرح ما تراه في هذه الصورة"):
    """Analyze image directly with Gemini Vision"""
    if not gemini_vision:
        return "خطأ في الاتصال بـ Gemini Vision، حاول مرة أخرى"
    
    try:
        vision_prompt = f"""
أجب باللغة العربية مباشرة بدون مقدمات أو عناوين:

المطلوب: {prompt}

قواعد الإجابة:
- اشرح ما تراه في الصورة مباشرة
- لا تبدأ بعبارات مثل "في هذه الصورة" أو "يمكنني أن أرى"
- أعط وصف مباشر وواضح
- لا تستخدم رموز تعبيرية
"""

        response = await asyncio.to_thread(
            gemini_vision.generate_content,
            [vision_prompt, image_data]
        )
        return response.text.strip()
    except Exception as e:
        logger.error(f"Vision error: {e}")
        return f"خطأ في تحليل الصورة: {str(e)}"

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command with full introduction"""
    user = update.effective_user
    chat = update.effective_chat
    
    logger.info(f"📨 /start from {user.first_name}")
    
    if chat.type == ChatType.PRIVATE:
        required_channels = await get_user_channels(context, user.id)
        
        if required_channels:
            text = f"""
🤖 **مرحباً {user.first_name}!**

أهلاً بك في **بوت الذكاء الاصطناعي** المدعوم بـ Google Gemini!

🔮 **قدرات Gemini المتقدمة:**
• إجابة جميع الأسئلة
• ترجمة فورية لجميع اللغات  
• حل المسائل الرياضية المعقدة
• مساعدة شاملة في البرمجة
• تحليل الصور والنصوص
• كتابة وتحرير المحتوى

⚠️ **شرط الاستخدام:**
للاستفادة من البوت، يرجى الاشتراك في القنوات أولاً:
"""
            
            await update.message.reply_text(
                text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=create_subscription_keyboard(required_channels)
            )
        else:
            text = f"""
🎉 **أهلاً وسهلاً {user.first_name}!**

مرحباً بك في بوت الذكاء الاصطناعي المدعوم بـ **Google Gemini**!

🔮 **حالة Gemini:**
• Gemini Pro: {'🟢 نشط' if gemini_model else '🔴 خطأ'}
• Gemini Vision: {'🟢 نشط' if gemini_vision else '🔴 خطأ'}

💬 **كيفية الاستخدام:**
أرسل أي سؤال أو صورة وسأجيب مباشرة!

🎯 **أمثلة:**
• "ما هو الذكاء الاصطناعي؟"
• "ترجم إلى الإنجليزية: مرحبا بك"
• "احسب 25 × 15 + 100"  
• "كيف أتعلم Python؟"
• أرسل صورة مع سؤال

🚀 **ابدأ الآن بسؤالك...**
"""
            
            await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
    
    elif user.id == ADMIN_ID:
        await update.message.reply_text(
            f"""
👑 **مرحباً أيها المدير!**

🤖 **البوت في القناة:** {chat.title}
🔮 **Gemini:** {'🟢 نشط' if gemini_model else '🔴 خطأ'}

✅ **البوت جاهز للعمل كمشرف!**
""",
            parse_mode=ParseMode.MARKDOWN
        )

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle callbacks"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "check_subs":
        user_id = query.from_user.id
        is_subscribed = await check_all_subscriptions(context, user_id)
        
        if is_subscribed:
            await query.edit_message_text(
                f"""
✅ **تم التحقق بنجاح!**

🎉 **مرحباً بك {query.from_user.first_name}!**

🔮 **Gemini جاهز لخدمتك:**
• اسأل أي سؤال
• أرسل صورة للتحليل
• اطلب الترجمة
• احتج لحل مسائل
• اطلب مساعدة برمجية

💬 **ابدأ بسؤالك الآن...**
""",
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            required_channels = await get_user_channels(context, user_id)
            await query.edit_message_text(
                f"❌ **لم تكمل الاشتراك!**\n\nيرجى الاشتراك في جميع القنوات المطلوبة.",
                reply_markup=create_subscription_keyboard(required_channels)
            )

async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text messages - direct answers only"""
    user = update.effective_user
    chat = update.effective_chat
    text = update.message.text
    
    if chat.type != ChatType.PRIVATE:
        return
    
    is_subscribed = await check_all_subscriptions(context, user.id)
    if not is_subscribed:
        required_channels = await get_user_channels(context, user.id)
        await update.message.reply_text(
            "⚠️ **يرجى الاشتراك في القنوات أولاً!**",
            reply_markup=create_subscription_keyboard(required_channels)
        )
        return
    
    logger.info(f"💬 {user.first_name}: {text[:30]}...")
    
    await context.bot.send_chat_action(chat.id, ChatAction.TYPING)
    
    # Get direct response without any prefixes
    response = await get_gemini_response(text, user.first_name)
    
    await update.message.reply_text(response)

async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle photos - direct analysis"""
    user = update.effective_user
    chat = update.effective_chat
    
    if chat.type != ChatType.PRIVATE:
        return
    
    is_subscribed = await check_all_subscriptions(context, user.id)
    if not is_subscribed:
        required_channels = await get_user_channels(context, user.id)
        await update.message.reply_text(
            "⚠️ **يرجى الاشتراك في القنوات أولاً!**",
            reply_markup=create_subscription_keyboard(required_channels)
        )
        return
    
    logger.info(f"📸 Photo from {user.first_name}")
    
    try:
        await context.bot.send_chat_action(chat.id, ChatAction.TYPING)
        
        photo = update.message.photo[-1]
        photo_file = await photo.get_file()
        photo_bytes = await photo_file.download_as_bytearray()
        
        prompt = update.message.caption or "اشرح ما تراه في هذه الصورة بالتفصيل"
        
        # Get direct image analysis
        response = await analyze_image(photo_bytes, prompt)
        
        await update.message.reply_text(response)
        
    except Exception as e:
        logger.error(f"Photo error: {e}")
        await update.message.reply_text("حدث خطأ في تحليل الصورة")

async def my_chat_member_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle bot being added to channels"""
    chat_member = update.my_chat_member
    chat = update.effective_chat
    
    if chat_member.new_chat_member.status in ['administrator', 'member']:
        logger.info(f"🎉 Bot added to {chat.title}")
        
        bot_channels[chat.id] = {
            'id': chat.id,
            'title': chat.title,
            'username': chat.username,
            'type': chat.type
        }
        
        try:
            await context.bot.send_message(
                ADMIN_ID,
                f"""
🎉 **تم إضافة البوت بنجاح!**

📺 **القناة:** {chat.title}
🆔 **ID:** {chat.id}
🔮 **Gemini:** {'🟢 نشط' if gemini_model else '🔴 خطأ'}

✅ **البوت يعمل الآن كمشرف**
المستخدمون يجب الاشتراك لاستخدام البوت

🚀 **جاهز للعمل!**
""",
                parse_mode=ParseMode.MARKDOWN
            )
        except:
            pass
    
    elif chat_member.new_chat_member.status in ['left', 'kicked']:
        logger.info(f"😞 Bot removed from {chat.title}")
        if chat.id in bot_channels:
            del bot_channels[chat.id]

def main():
    """Main function"""
    try:
        logger.info("🚀 Starting Direct Gemini Bot...")
        
        if not BOT_TOKEN:
            logger.error("❌ No bot token!")
            return
        
        app = Application.builder().token(BOT_TOKEN).build()
        
        # Add handlers
        app.add_handler(CommandHandler("start", start_command))
        app.add_handler(CallbackQueryHandler(callback_handler))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))
        app.add_handler(MessageHandler(filters.PHOTO, photo_handler))
        app.add_handler(ChatMemberHandler(my_chat_member_handler, ChatMemberHandler.MY_CHAT_MEMBER))
        
        logger.info("✅ Direct Gemini Bot ready!")
        app.run_polling(drop_pending_updates=True)
        
    except Exception as e:
        logger.error(f"Fatal error: {e}")

if __name__ == "__main__":
    main()
