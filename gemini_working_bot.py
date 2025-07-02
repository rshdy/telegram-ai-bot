import os
import logging
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler, ChatMemberHandler
from telegram.constants import ParseMode, ChatAction, ChatType
from telegram.error import BadRequest, Forbidden

# Configure loggingimport os
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

logger.info(f"🤖 Working Gemini Bot starting...")
logger.info(f"🔮 API Key: {GEMINI_API_KEY[:15]}...{GEMINI_API_KEY[-10:]}")

# Bot data
bot_channels = {}

# Initialize Gemini
gemini_model = None
gemini_vision = None
genai = None

# Test and initialize Gemini with correct model names
async def initialize_gemini():
    """Initialize Gemini with proper model names"""
    global gemini_model, gemini_vision, genai
    
    if not GEMINI_API_KEY:
        logger.error("❌ No Gemini API key provided!")
        return False
    
    try:
        import google.generativeai as genai
        logger.info("✅ Gemini library imported")
        
        # Configure API key
        genai.configure(api_key=GEMINI_API_KEY)
        logger.info("✅ API key configured")
        
        # List available models
        logger.info("🔍 Checking available models...")
        
        try:
            # Try different model names
            model_names = [
                'gemini-1.5-flash',
                'gemini-1.5-pro', 
                'gemini-pro',
                'gemini-1.0-pro',
                'models/gemini-1.5-flash',
                'models/gemini-pro'
            ]
            
            for model_name in model_names:
                try:
                    test_model = genai.GenerativeModel(model_name)
                    test_response = await asyncio.to_thread(
                        test_model.generate_content, 
                        "مرحبا"
                    )
                    
                    if test_response and test_response.text:
                        logger.info(f"✅ Working model found: {model_name}")
                        logger.info(f"✅ Test response: {test_response.text[:50]}...")
                        
                        # Initialize working models
                        gemini_model = genai.GenerativeModel(model_name)
                        
                        # Try to initialize vision model
                        try:
                            if 'flash' in model_name or '1.5' in model_name:
                                gemini_vision = genai.GenerativeModel(model_name)  # Same model for vision
                            else:
                                gemini_vision = genai.GenerativeModel('gemini-pro-vision')
                            logger.info(f"✅ Vision model ready")
                        except:
                            logger.warning("⚠️ Vision model not available")
                            gemini_vision = None
                        
                        return True
                        
                except Exception as model_error:
                    logger.debug(f"❌ Model {model_name} failed: {model_error}")
                    continue
            
            logger.error("❌ No working Gemini model found!")
            return False
            
        except Exception as e:
            logger.error(f"❌ Error testing models: {e}")
            return False
            
    except ImportError as e:
        logger.error(f"❌ Failed to import Gemini library: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Gemini initialization failed: {e}")
        return False

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
    """Get response from Gemini with proper error handling"""
    global gemini_model
    
    if not gemini_model:
        logger.error("❌ Gemini model not available")
        return get_smart_fallback(text)
    
    try:
        # Clean and direct prompt
        prompt = f"أجب على هذا السؤال باللغة العربية بشكل مباشر ومفيد:\n\n{text}"
        
        response = await asyncio.wait_for(
            asyncio.to_thread(gemini_model.generate_content, prompt),
            timeout=25.0
        )
        
        if response and response.text:
            result = response.text.strip()
            logger.info(f"✅ Gemini responded: {len(result)} chars")
            return result
        else:
            logger.error("❌ Empty Gemini response")
            return get_smart_fallback(text)
            
    except asyncio.TimeoutError:
        logger.error("❌ Gemini timeout")
        return "الاستجابة تأخذ وقتاً أكثر من المعتاد، حاول مرة أخرى"
        
    except Exception as e:
        logger.error(f"❌ Gemini error: {str(e)}")
        
        # Try to reinitialize
        if "not found" in str(e).lower() or "404" in str(e):
            logger.info("🔄 Reinitializing Gemini...")
            if await initialize_gemini():
                try:
                    response = await asyncio.to_thread(gemini_model.generate_content, prompt)
                    if response and response.text:
                        return response.text.strip()
                except:
                    pass
        
        return get_smart_fallback(text)

def get_smart_fallback(text):
    """Smart fallback responses"""
    text_lower = text.lower()
    
    # Greetings
    if any(word in text_lower for word in ['مرحبا', 'السلام', 'أهلا', 'hello', 'hi', 'صباح', 'مساء']):
        greetings = [
            "أهلاً وسهلاً! كيف يمكنني مساعدتك؟",
            "مرحباً بك! ما الذي تحتاج مساعدة فيه؟",
            "أهلاً! أنا هنا للإجابة على أسئلتك"
        ]
        import random
        return random.choice(greetings)
    
    # Translation requests
    elif any(word in text_lower for word in ['ترجم', 'translate']):
        result = translate_enhanced(text)
        if result:
            return result
        return "أحتاج لإعادة تشغيل خدمة الترجمة. جرب كلمات بسيطة مثل: ترجم Hello"
    
    # Math requests
    elif any(word in text_lower for word in ['احسب', 'حل', 'math', '+', '-', '*', '/', '=', '×', '÷']):
        result = calculate_enhanced(text)
        if result:
            return result
        return "جرب عملية حسابية بسيطة مثل: احسب 10 + 5"
    
    # Programming requests
    elif any(word in text_lower for word in ['برمجة', 'كود', 'python', 'javascript', 'html', 'css', 'java']):
        return "خدمة المساعدة البرمجية متوقفة مؤقتاً. سأعود للعمل قريباً!"
    
    # Questions about AI/technology
    elif any(word in text_lower for word in ['ذكاء اصطناعي', 'تكنولوجيا', 'كمبيوتر', 'هاتف']):
        return "هذا سؤال تقني ممتاز! أحتاج للاتصال بقاعدة المعرفة المتقدمة للإجابة عليه بدقة."
    
    # General questions
    elif '؟' in text or 'what' in text_lower or 'why' in text_lower or 'how' in text_lower:
        return f"سؤال مثير للاهتمام! أحاول إعادة الاتصال بنظام الذكاء الاصطناعي للحصول على إجابة شاملة."
    
    # Default
    else:
        return "أعتذر، أواجه مشكلة تقنية مؤقتة. جرب إعادة صياغة السؤال أو حاول مرة أخرى خلال دقيقة."

def translate_enhanced(text):
    """Enhanced translation with more phrases"""
    translations = {
        # English to Arabic
        'hello': 'مرحبا', 'hi': 'أهلا', 'thank you': 'شكراً لك', 'thanks': 'شكراً',
        'good morning': 'صباح الخير', 'good evening': 'مساء الخير', 
        'good night': 'تصبح على خير', 'how are you': 'كيف حالك',
        'what is your name': 'ما اسمك', 'i love you': 'أحبك',
        'goodbye': 'وداعاً', 'yes': 'نعم', 'no': 'لا',
        'please': 'من فضلك', 'sorry': 'آسف', 'excuse me': 'المعذرة',
        'welcome': 'أهلاً وسهلاً', 'congratulations': 'مبروك',
        'happy birthday': 'عيد ميلاد سعيد', 'see you later': 'أراك لاحقاً',
        
        # Arabic to English
        'مرحبا': 'Hello', 'أهلا': 'Hi', 'شكراً': 'Thank you',
        'صباح الخير': 'Good morning', 'مساء الخير': 'Good evening',
        'تصبح على خير': 'Good night', 'كيف حالك': 'How are you',
        'ما اسمك': 'What is your name', 'أحبك': 'I love you',
        'وداعاً': 'Goodbye', 'نعم': 'Yes', 'لا': 'No',
        'من فضلك': 'Please', 'آسف': 'Sorry', 'المعذرة': 'Excuse me',
        'أهلاً وسهلاً': 'Welcome', 'مبروك': 'Congratulations',
        'عيد ميلاد سعيد': 'Happy Birthday', 'أراك لاحقاً': 'See you later'
    }
    
    # Clean the input
    text_clean = text.lower()
    for word in ['ترجم', 'translate', ':', 'إلى', 'to']:
        text_clean = text_clean.replace(word, ' ')
    text_clean = text_clean.strip()
    
    # Find exact matches
    if text_clean in translations:
        return translations[text_clean]
    
    # Find partial matches
    for original, translated in translations.items():
        if original in text_clean:
            return f"{original} → {translated}"
    
    return None

def calculate_enhanced(text):
    """Enhanced calculation with more operations"""
    try:
        # Clean the text
        clean_text = text.lower()
        for word in ['احسب', 'حل', 'كم', 'ما']:
            clean_text = clean_text.replace(word, '')
        
        # Replace symbols
        replacements = {
            '×': '*', '÷': '/', 'x': '*', '**': '*', 
            '=': '', '؟': '', 'كم': '', 'يساوي': '',
            # Arabic numbers to English
            '٠': '0', '١': '1', '٢': '2', '٣': '3', '٤': '4',
            '٥': '5', '٦': '6', '٧': '7', '٨': '8', '٩': '9'
        }
        
        for ar, en in replacements.items():
            clean_text = clean_text.replace(ar, en)
        
        # Extract only valid characters
        allowed = '0123456789+-*/.() '
        clean_text = ''.join(c for c in clean_text if c in allowed).strip()
        
        # Basic validation
        if not clean_text or not any(op in clean_text for op in ['+', '-', '*', '/']):
            return None
        
        # Safe evaluation
        try:
            # Remove multiple spaces
            clean_text = ' '.join(clean_text.split())
            result = eval(clean_text)
            
            # Format result nicely
            if isinstance(result, float):
                if result.is_integer():
                    result = int(result)
                else:
                    result = round(result, 3)
            
            return f"{clean_text} = {result}"
            
        except ZeroDivisionError:
            return "لا يمكن القسمة على صفر"
        except:
            return None
    
    except:
        return None

async def analyze_image(image_data, prompt="اشرح ما تراه في هذه الصورة"):
    """Analyze image with Gemini Vision"""
    global gemini_vision
    
    if not gemini_vision:
        return "تحليل الصور غير متاح حالياً. جرب مرة أخرى لاحقاً."
    
    try:
        # Create content with image and text
        content = [
            f"اشرح هذه الصورة باللغة العربية: {prompt}",
            image_data
        ]
        
        response = await asyncio.wait_for(
            asyncio.to_thread(gemini_vision.generate_content, content),
            timeout=40.0
        )
        
        if response and response.text:
            return response.text.strip()
        else:
            return "لم أتمكن من تحليل هذه الصورة، جرب صورة أخرى"
            
    except asyncio.TimeoutError:
        return "تحليل الصورة يحتاج وقت أكثر، حاول مرة أخرى"
    except Exception as e:
        logger.error(f"Vision error: {str(e)}")
        return "حدث خطأ في تحليل الصورة، تأكد أن الصورة واضحة وجرب مرة أخرى"

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command"""
    user = update.effective_user
    chat = update.effective_chat
    
    logger.info(f"📨 /start from {user.first_name}")
    
    if chat.type == ChatType.PRIVATE:
        required_channels = await get_user_channels(context, user.id)
        
        if required_channels:
            text = f"""
🤖 **مرحباً {user.first_name}!**

أهلاً بك في **بوت الذكاء الاصطناعي** المدعوم بـ Google Gemini!

🔮 **قدرات متقدمة:**
• إجابة جميع الأسئلة
• ترجمة فورية لجميع اللغات  
• حل المسائل الرياضية
• مساعدة في البرمجة
• تحليل الصور
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
            gemini_status = "🟢 نشط" if gemini_model else "🔴 غير متاح"
            vision_status = "🟢 نشط" if gemini_vision else "🔴 غير متاح"
            
            text = f"""
🎉 **أهلاً وسهلاً {user.first_name}!**

مرحباً بك في بوت الذكاء الاصطناعي!

🔮 **حالة الخدمات:**
• Gemini AI: {gemini_status}
• تحليل الصور: {vision_status}

💬 **استخدم البوت:**
أرسل أي سؤال أو صورة وسأجيب مباشرة!

🎯 **أمثلة:**
• "ما هو الذكاء الاصطناعي؟"
• "ترجم: Hello World"
• "احسب 15 × 8 + 25"  
• "كيف أتعلم البرمجة؟"
• أرسل صورة للتحليل

🚀 **ابدأ الآن...**
"""
            
            await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
    
    elif user.id == ADMIN_ID:
        gemini_status = "🟢 يعمل" if gemini_model else "🔴 متوقف"
        await update.message.reply_text(
            f"""
👑 **أهلاً أيها المدير!**

🤖 **البوت:** {chat.title}
🔮 **Gemini:** {gemini_status}
🔑 **API:** {GEMINI_API_KEY[:12]}...

✅ **البوت جاهز!**
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

🔮 **البوت جاهز لخدمتك:**
• اسأل أي سؤال
• أرسل صورة للتحليل
• اطلب الترجمة
• احت لحل مسائل
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
    """Handle text messages"""
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
    
    # Get response
    response = await get_gemini_response(text, user.first_name)
    
    await update.message.reply_text(response)

async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle photos"""
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
        
        response = await analyze_image(photo_bytes, prompt)
        
        await update.message.reply_text(response)
        
    except Exception as e:
        logger.error(f"Photo error: {e}")
        await update.message.reply_text("حدث خطأ في معالجة الصورة")

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
            gemini_status = "🟢 يعمل" if gemini_model else "🔴 متوقف"
            await context.bot.send_message(
                ADMIN_ID,
                f"""
🎉 **تم إضافة البوت بنجاح!**

📺 **القناة:** {chat.title}
🆔 **ID:** {chat.id}
🔮 **Gemini:** {gemini_status}

✅ **البوت يعمل الآن كمشرف**

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

async def main():
    """Main function"""
    try:
        logger.info("🚀 Starting Working Gemini Bot...")
        
        if not BOT_TOKEN:
            logger.error("❌ No bot token!")
            return
        
        # Initialize Gemini
        logger.info("🔄 Initializing Gemini...")
        gemini_ready = await initialize_gemini()
        
        if gemini_ready:
            logger.info("✅ Gemini ready!")
        else:
            logger.warning("⚠️ Gemini not available, using fallback responses")
        
        app = Application.builder().token(BOT_TOKEN).build()
        
        # Add handlers
        app.add_handler(CommandHandler("start", start_command))
        app.add_handler(CallbackQueryHandler(callback_handler))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))
        app.add_handler(MessageHandler(filters.PHOTO, photo_handler))
        app.add_handler(ChatMemberHandler(my_chat_member_handler, ChatMemberHandler.MY_CHAT_MEMBER))
        
        logger.info("✅ Working Gemini Bot ready!")
        await app.run_polling(drop_pending_updates=True)
        
    except Exception as e:
        logger.error(f"Fatal error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
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
