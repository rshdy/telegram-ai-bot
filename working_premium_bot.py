import os
import logging
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from telegram.constants import ParseMode, ChatAction

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Bot Configuration
BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '7500826569:AAHSXBY9elBf89fyAhV_EmGuUGrryGXdVq8')
CHANNEL_USERNAME = os.getenv('CHANNEL_USERNAME', '@your_channel')  # غير هذا لقناتك
CHANNEL_ID = os.getenv('CHANNEL_ID', '-1001234567890')  # غير هذا لـ ID قناتك

# AI Configuration
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '').strip()
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', '').strip()

logger.info(f"🤖 AI Bot starting...")
logger.info(f"📺 Channel: {CHANNEL_USERNAME}")
logger.info(f"🧠 OpenAI: {len(OPENAI_API_KEY)} chars")
logger.info(f"🔮 Gemini: {len(GEMINI_API_KEY)} chars")

# Initialize AI clients
openai_client = None
gemini_model = None

# Try OpenAI
if OPENAI_API_KEY:
    try:
        import openai
        openai_client = openai.AsyncOpenAI(api_key=OPENAI_API_KEY)
        logger.info("✅ OpenAI ready")
    except Exception as e:
        logger.info(f"⚠️ OpenAI not available: {e}")

# Try Gemini
if GEMINI_API_KEY:
    try:
        import google.generativeai as genai
        genai.configure(api_key=GEMINI_API_KEY)
        gemini_model = genai.GenerativeModel('gemini-pro')
        gemini_vision = genai.GenerativeModel('gemini-pro-vision')
        logger.info("✅ Gemini ready")
    except Exception as e:
        logger.info(f"⚠️ Gemini not available: {e}")

async def check_subscription(context, user_id):
    """Check if user is subscribed to channel"""
    try:
        member = await context.bot.get_chat_member(CHANNEL_ID, user_id)
        return member.status in ['member', 'administrator', 'creator']
    except Exception as e:
        logger.error(f"Subscription check error: {e}")
        return False

def create_subscription_keyboard():
    """Create subscription keyboard"""
    keyboard = [
        [InlineKeyboardButton("📺 اشترك في القناة", url=f"https://t.me/{CHANNEL_USERNAME.replace('@', '')}")],
        [InlineKeyboardButton("✅ تحقق من الاشتراك", callback_data="check_sub")]
    ]
    return InlineKeyboardMarkup(keyboard)

async def get_ai_response(text, user_name="المستخدم"):
    """Get AI response from available providers"""
    
    # Try OpenAI first
    if openai_client:
        try:
            response = await openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "أنت مساعد ذكي متطور. أجب باللغة العربية بشكل مفصل ومفيد. يمكنك الترجمة بين اللغات وتحليل النصوص وحل المسائل."},
                    {"role": "user", "content": text}
                ],
                max_tokens=1000,
                temperature=0.7
            )
            return f"🤖 **ChatGPT:**\n\n{response.choices[0].message.content}"
        except Exception as e:
            logger.error(f"OpenAI error: {e}")
    
    # Try Gemini
    if gemini_model:
        try:
            response = await asyncio.to_thread(
                gemini_model.generate_content, 
                f"أجب باللغة العربية بشكل مفصل ومفيد: {text}"
            )
            return f"🔮 **Gemini AI:**\n\n{response.text}"
        except Exception as e:
            logger.error(f"Gemini error: {e}")
    
    # Smart fallback with more capabilities
    return get_smart_response(text, user_name)

def get_smart_response(text, user_name):
    """Smart fallback response with basic AI capabilities"""
    text_lower = text.lower()
    
    # Translation detection
    if any(word in text_lower for word in ['ترجم', 'translate', 'translation']):
        return f"""
🔤 **خدمة الترجمة الذكية**

📝 **النص المطلوب ترجمته:** {text}

🔄 **الترجمة التلقائية:**
للحصول على ترجمة دقيقة ومتطورة، يرجى إضافة مفاتيح الذكاء الاصطناعي:

🤖 **OpenAI GPT** - ترجمة طبيعية ودقيقة
🔮 **Google Gemini** - ترجمة مجانية متقدمة

💡 **حاول كتابة:** "ترجم إلى الإنجليزية: مرحبا بك"
"""
    
    # Math problems
    elif any(word in text_lower for word in ['احسب', 'حل', 'رياضة', 'math', 'calculate']):
        return f"""
📊 **حل المسائل الرياضية**

🧮 **السؤال:** {text}

💡 **للحصول على حلول رياضية متقدمة:**
• معادلات معقدة
• حسابات إحصائية  
• تحليل البيانات
• الهندسة والجبر

🚀 **فعّل الذكاء الاصطناعي للحصول على حلول دقيقة خطوة بخطوة!**
"""
    
    # Programming questions
    elif any(word in text_lower for word in ['برمجة', 'كود', 'python', 'javascript', 'html', 'css']):
        return f"""
💻 **مساعد البرمجة الذكي**

👨‍💻 **سؤالك:** {text}

🚀 **يمكنني مساعدتك في:**
• كتابة الأكواد من الصفر
• إصلاح الأخطاء البرمجية
• شرح المفاهيم البرمجية
• مراجعة وتحسين الكود
• تعلم لغات برمجة جديدة

💡 **لمساعدة برمجية متقدمة، فعّل الذكاء الاصطناعي!**
"""
    
    # General questions
    elif any(word in text_lower for word in ['ما هو', 'كيف', 'متى', 'أين', 'لماذا', 'what', 'how', 'why']):
        return f"""
🤔 **إجابة ذكية على سؤالك**

❓ **سؤالك:** {text}

💭 **تحليل السؤال:**
هذا سؤال يتطلب معرفة وتحليل عميق. 

🧠 **إجابة أساسية:**
للحصول على إجابة شاملة ومفصلة، أنصح بتفعيل الذكاء الاصطناعي المتقدم.

🚀 **مع الذكاء الاصطناعي ستحصل على:**
• إجابات مفصلة ودقيقة
• مصادر وأمثلة
• تحليل شامل للموضوع
• معلومات حديثة ومحدثة
"""
    
    # Greetings
    elif any(word in text_lower for word in ['مرحبا', 'السلام', 'أهلا', 'hello', 'hi']):
        return f"""
🌟 **أهلاً وسهلاً {user_name}!**

مرحباً بك في بوت الذكاء الاصطناعي المتطور!

🧠 **يمكنني مساعدتك في:**
• الإجابة على جميع الأسئلة
• الترجمة بين اللغات
• حل المسائل الرياضية
• المساعدة في البرمجة
• تحليل وشرح النصوص
• تحليل الصور (قريباً)

💬 **اسألني أي شيء تريد معرفته!**
"""
    
    else:
        return f"""
🧠 **الذكاء الاصطناعي يحلل رسالتك...**

📝 **رسالتك:** "{text}"

🔍 **التحليل الذكي:**
• عدد الأحرف: {len(text)}
• عدد الكلمات: {len(text.split())}
• اللغة المكتشفة: {'العربية' if any(ord(c) > 1000 for c in text) else 'الإنجليزية'}

💡 **كيف يمكنني مساعدتك بشكل أفضل:**
• اطرح أسئلة محددة
• اطلب الترجمة
• اسأل عن البرمجة
• احتج لحل مسائل رياضية

🚀 **للحصول على إجابات متطورة، فعّل الذكاء الاصطناعي المتقدم!**

⚙️ **حالة النظام:**
• OpenAI: {'🟢 متاح' if openai_client else '🔴 يحتاج تفعيل'}
• Gemini: {'🟢 متاح' if gemini_model else '🔴 يحتاج تفعيل'}
"""

async def analyze_image(image_data, prompt="اشرح ما تراه في هذه الصورة"):
    """Analyze image using Gemini Vision"""
    if not gemini_model:
        return "📸 **تحليل الصور غير متاح حالياً**\n\nلتفعيل تحليل الصور، أضف مفتاح Gemini API في إعدادات Railway."
    
    try:
        response = await asyncio.to_thread(
            gemini_vision.generate_content,
            [prompt, image_data]
        )
        return f"📸 **تحليل الصورة بالذكاء الاصطناعي:**\n\n{response.text}"
    except Exception as e:
        logger.error(f"Image analysis error: {e}")
        return f"❌ **خطأ في تحليل الصورة:** {str(e)}"

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command handler"""
    user = update.effective_user
    logger.info(f"📨 /start from {user.first_name}")
    
    # Check subscription
    is_subscribed = await check_subscription(context, user.id)
    
    if not is_subscribed:
        welcome_text = f"""
🤖 **مرحباً {user.first_name}!**

أهلاً بك في **بوت الذكاء الاصطناعي المتطور**!

🧠 **يمكنني مساعدتك في:**
• الإجابة على جميع الأسئلة
• الترجمة بين اللغات  
• حل المسائل الرياضية
• المساعدة في البرمجة
• تحليل وشرح النصوص
• تحليل الصور

⚠️ **شرط الاستخدام:**
للاستفادة من البوت، يرجى الاشتراك في قناتنا أولاً:

📺 **القناة:** {CHANNEL_USERNAME}

👇 اضغط الزر أدناه للاشتراك:
"""
        
        await update.message.reply_text(
            welcome_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=create_subscription_keyboard()
        )
    else:
        welcome_text = f"""
🎉 **أهلاً وسهلاً {user.first_name}!**

مرحباً بك في بوت الذكاء الاصطناعي! 

🧠 **الذكاء الاصطناعي المتاح:**
• OpenAI GPT: {'🟢 متاح' if openai_client else '🔴 يحتاج تفعيل'}
• Google Gemini: {'🟢 متاح' if gemini_model else '🔴 يحتاج تفعيل'}

💬 **كيفية الاستخدام:**
أرسل أي سؤال أو نص وسأجيب عليه بذكاء!

📸 **تحليل الصور:**
أرسل صورة مع تعليق وسأحللها لك!

🔤 **الترجمة:**
اكتب "ترجم إلى الإنجليزية: النص هنا"

🧮 **الرياضيات:**
اسأل أي سؤال رياضي وسأحله لك!

💻 **البرمجة:**
اطلب المساعدة في أي لغة برمجة!

💬 **ابدأ بسؤالك الآن...**
"""
        
        await update.message.reply_text(
            welcome_text,
            parse_mode=ParseMode.MARKDOWN
        )

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle callback queries"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "check_sub":
        user_id = query.from_user.id
        is_subscribed = await check_subscription(context, user_id)
        
        if is_subscribed:
            await query.edit_message_text(
                f"""
✅ **تم التحقق بنجاح!**

🎉 مرحباً بك {query.from_user.first_name}!

🧠 **يمكنك الآن استخدام البوت:**
• اسأل أي سؤال
• أرسل صورة للتحليل
• اطلب الترجمة
• احتج لحل مسائل

💬 **ابدأ بسؤالك الآن...**
""",
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            await query.edit_message_text(
                f"""
❌ **لم تشترك بعد!**

يرجى الاشتراك في القناة أولاً: {CHANNEL_USERNAME}

📺 تأكد من:
• الاشتراك في القناة
• عدم كتم الإشعارات
• انتظار دقيقة واحدة ثم المحاولة مرة أخرى

👇 للاشتراك:
""",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=create_subscription_keyboard()
            )

async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text messages"""
    user = update.effective_user
    text = update.message.text
    
    # Check subscription first
    is_subscribed = await check_subscription(context, user.id)
    
    if not is_subscribed:
        await update.message.reply_text(
            f"⚠️ **يرجى الاشتراك في القناة أولاً!**\n\n📺 القناة: {CHANNEL_USERNAME}",
            reply_markup=create_subscription_keyboard()
        )
        return
    
    logger.info(f"💬 Text from {user.first_name}: {text[:50]}...")
    
    # Show typing
    await context.bot.send_chat_action(update.effective_chat.id, ChatAction.TYPING)
    
    # Get AI response
    response = await get_ai_response(text, user.first_name)
    
    await update.message.reply_text(
        response,
        parse_mode=ParseMode.MARKDOWN
    )

async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle photo messages"""
    user = update.effective_user
    
    # Check subscription first
    is_subscribed = await check_subscription(context, user.id)
    
    if not is_subscribed:
        await update.message.reply_text(
            f"⚠️ **يرجى الاشتراك في القناة أولاً!**\n\n📺 القناة: {CHANNEL_USERNAME}",
            reply_markup=create_subscription_keyboard()
        )
        return
    
    logger.info(f"📸 Photo from {user.first_name}")
    
    try:
        await context.bot.send_chat_action(update.effective_chat.id, ChatAction.TYPING)
        
        # Get the largest photo
        photo = update.message.photo[-1]
        photo_file = await photo.get_file()
        
        # Download photo
        photo_bytes = await photo_file.download_as_bytearray()
        
        # Get caption or default prompt
        prompt = update.message.caption or "اشرح ما تراه في هذه الصورة بالتفصيل"
        
        # Analyze image
        response = await analyze_image(photo_bytes, prompt)
        
        await update.message.reply_text(
            response,
            parse_mode=ParseMode.MARKDOWN
        )
        
    except Exception as e:
        logger.error(f"Photo handler error: {e}")
        await update.message.reply_text(
            f"❌ **خطأ في تحليل الصورة**\n\nللحصول على تحليل متقدم للصور، يرجى إضافة مفتاح Gemini API."
        )

def main():
    """Main function"""
    try:
        logger.info("🚀 Starting AI Channel Bot...")
        
        if not BOT_TOKEN:
            logger.error("❌ No bot token!")
            return
        
        # Create application
        app = Application.builder().token(BOT_TOKEN).build()
        
        # Add handlers
        app.add_handler(CommandHandler("start", start_command))
        app.add_handler(CallbackQueryHandler(callback_handler))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))
        app.add_handler(MessageHandler(filters.PHOTO, photo_handler))
        
        logger.info("✅ AI Channel Bot ready!")
        
        # Run the bot
        app.run_polling(drop_pending_updates=True)
        
    except Exception as e:
        logger.error(f"Fatal error: {e}")

if __name__ == "__main__":
    main()
