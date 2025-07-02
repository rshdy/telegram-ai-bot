import os
import logging
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ChatMember
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler, ChatMemberHandler
from telegram.constants import ParseMode, ChatAction, ChatType
from telegram.error import BadRequest, Forbidden

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Bot Configuration
BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '7500826569:AAHSXBY9elBf89fyAhV_EmGuUGrryGXdVq8')
ADMIN_ID = int(os.getenv('ADMIN_USER_ID', '606898749'))

# AI Configuration
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '').strip()
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', '').strip()

logger.info(f"🤖 Channel Admin Bot starting...")
logger.info(f"👤 Admin ID: {ADMIN_ID}")
logger.info(f"🧠 OpenAI: {len(OPENAI_API_KEY)} chars")
logger.info(f"🔮 Gemini: {len(GEMINI_API_KEY)} chars")

# Bot stats
bot_channels = {}  # Store channels where bot is admin
user_sessions = {}  # Store user sessions

# Initialize AI clients
openai_client = None
gemini_model = None
gemini_vision = None

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

async def get_user_channels(context, user_id):
    """Get channels where user should be subscribed and bot is admin"""
    user_channels = []
    
    # Check all channels where bot is admin
    for channel_id, channel_info in bot_channels.items():
        try:
            # Check if user is member
            member = await context.bot.get_chat_member(channel_id, user_id)
            if member.status not in ['member', 'administrator', 'creator']:
                user_channels.append(channel_info)
        except Exception as e:
            logger.error(f"Error checking membership in {channel_id}: {e}")
    
    return user_channels

async def check_all_subscriptions(context, user_id):
    """Check if user is subscribed to all required channels"""
    required_channels = await get_user_channels(context, user_id)
    return len(required_channels) == 0

def create_subscription_keyboard(required_channels):
    """Create subscription keyboard for required channels"""
    keyboard = []
    
    for channel in required_channels:
        channel_name = channel.get('title', channel.get('username', 'القناة'))
        channel_link = f"https://t.me/{channel.get('username', '').replace('@', '')}"
        keyboard.append([InlineKeyboardButton(f"📺 اشترك في {channel_name}", url=channel_link)])
    
    keyboard.append([InlineKeyboardButton("✅ تحقق من الاشتراك", callback_data="check_all_subs")])
    
    return InlineKeyboardMarkup(keyboard)

async def get_ai_response(text, user_name="المستخدم"):
    """Get AI response from available providers"""
    
    # Try OpenAI first
    if openai_client:
        try:
            response = await openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "أنت مساعد ذكي متطور. أجب باللغة العربية بشكل مفصل ومفيد. يمكنك الترجمة بين اللغات وتحليل النصوص وحل المسائل والمساعدة في البرمجة."},
                    {"role": "user", "content": text}
                ],
                max_tokens=1500,
                temperature=0.7
            )
            return f"🤖 **ChatGPT-3.5:**\n\n{response.choices[0].message.content}"
        except Exception as e:
            logger.error(f"OpenAI error: {e}")
    
    # Try Gemini
    if gemini_model:
        try:
            response = await asyncio.to_thread(
                gemini_model.generate_content, 
                f"أجب باللغة العربية بشكل مفصل ومفيد وشامل: {text}"
            )
            return f"🔮 **Gemini Pro:**\n\n{response.text}"
        except Exception as e:
            logger.error(f"Gemini error: {e}")
    
    # Smart fallback
    return get_smart_response(text, user_name)

def get_smart_response(text, user_name):
    """Smart fallback response with AI capabilities"""
    text_lower = text.lower()
    
    # Translation requests
    if any(word in text_lower for word in ['ترجم', 'translate', 'translation']):
        return f"""
🔤 **خدمة الترجمة الذكية**

📝 **النص:** {text}

🌍 **كشف اللغة:** {'العربية' if any(ord(c) > 1000 for c in text) else 'الإنجليزية'}

🔄 **محاولة ترجمة أساسية:**
{translate_basic(text)}

💡 **للترجمة المتقدمة:**
أضف مفاتيح الذكاء الاصطناعي للحصول على:
• ترجمة دقيقة 100%
• سياق طبيعي
• تصحيح نحوي
• أكثر من 100 لغة
"""
    
    # Math problems
    elif any(word in text_lower for word in ['احسب', 'حل', 'رياضة', 'math', 'calculate', '+', '-', '*', '/', '=', '×', '÷']):
        return f"""
📊 **آلة حاسبة ذكية**

🧮 **العملية:** {text}

💫 **محاولة حل أساسية:**
{calculate_basic(text)}

🚀 **للرياضيات المتقدمة:**
• معادلات تفاضلية
• إحصاء وتحليل البيانات
• هندسة وجبر متقدم
• حسابات علمية معقدة
• شرح خطوة بخطوة

💡 فعّل الذكاء الاصطناعي للحصول على حلول شاملة!
"""
    
    # Programming questions
    elif any(word in text_lower for word in ['برمجة', 'كود', 'python', 'javascript', 'html', 'css', 'java', 'c++', 'php', 'react', 'flutter']):
        return f"""
💻 **مساعد البرمجة المتقدم**

👨‍💻 **سؤالك:** {text}

🚀 **خدمات البرمجة المتاحة:**
• كتابة كود من الصفر
• إصلاح الأخطاء والباغز
• مراجعة وتحسين الكود
• شرح المفاهيم البرمجية
• تصميم قواعد البيانات
• تطوير تطبيقات الويب والموبايل

💡 **لغات البرمجة المدعومة:**
Python, JavaScript, Java, C++, PHP, Swift, Kotlin, React, Flutter, وأكثر

🔧 **للحصول على مساعدة تفصيلية:**
فعّل الذكاء الاصطناعي المتقدم!
"""
    
    # General knowledge questions
    elif any(word in text_lower for word in ['ما هو', 'كيف', 'متى', 'أين', 'لماذا', 'what', 'how', 'why', 'when', 'where']):
        return f"""
🤔 **موسوعة المعرفة الذكية**

❓ **سؤالك:** {text}

📚 **تحليل السؤال:**
• نوع السؤال: معرفي عام
• المجال: {detect_topic(text)}
• صعوبة: متوسطة

💭 **إجابة مبدئية:**
هذا سؤال ممتاز يتطلب بحث وتحليل معمق.

🧠 **مع الذكاء الاصطناعي ستحصل على:**
• إجابات مفصلة ودقيقة
• مصادر وأمثلة حقيقية
• تحليل شامل للموضوع
• معلومات حديثة ومحدثة
• شرح مبسط وواضح

🌟 **الخلاصة:** سؤال رائع يستحق إجابة متطورة!
"""
    
    # Greetings
    elif any(word in text_lower for word in ['مرحبا', 'السلام', 'أهلا', 'hello', 'hi', 'hey']):
        return f"""
🌟 **أهلاً وسهلاً {user_name}!**

مرحباً بك في **بوت الذكاء الاصطناعي المتطور**!

🧠 **قدراتي الذكية:**
• إجابة جميع أنواع الأسئلة
• ترجمة فورية لأكثر من 100 لغة
• حل المسائل الرياضية المعقدة
• مساعدة شاملة في البرمجة
• تحليل وشرح النصوص
• تحليل الصور بالذكاء الاصطناعي
• كتابة وتحرير المحتوى
• استشارات تقنية ومهنية

💬 **كيفية الاستخدام:**
أرسل لي أي سؤال أو طلب وسأساعدك فوراً!

🚀 **جودة الإجابات:**
• أساسية: متاحة الآن
• متقدمة: مع تفعيل مفاتيح الذكاء الاصطناعي

📸 **جديد:** يمكنني تحليل الصور أيضاً!

💡 **ابدأ بسؤالك الآن...**
"""
    
    else:
        return f"""
🧠 **محلل النصوص الذكي**

📝 **نصك:** "{text}"

🔍 **التحليل الذكي:**
• الطول: {len(text)} حرف
• الكلمات: {len(text.split())} كلمة
• اللغة: {'العربية' if any(ord(c) > 1000 for c in text) else 'الإنجليزية'}
• النوع: {detect_text_type(text)}
• المعنى: {analyze_sentiment(text)}

💡 **كيف يمكنني مساعدتك أكثر:**
• اطرح أسئلة محددة
• اطلب الترجمة لأي لغة
• اسأل عن البرمجة والتقنية
• احتج لحل مسائل رياضية
• اطلب تحليل أو شرح النص
• أرسل صورة للتحليل

🚀 **للحصول على تحليل متقدم:**
فعّل الذكاء الاصطناعي للحصول على:
• تحليل عميق للمحتوى
• اقتراحات ذكية
• معلومات إضافية
• سياق أوسع

⚙️ **حالة الأنظمة:**
• OpenAI: {'🟢 نشط' if openai_client else '🔴 يحتاج تفعيل'}
• Gemini: {'🟢 نشط' if gemini_model else '🔴 يحتاج تفعيل'}
• التحليل الأساسي: 🟢 متاح دائماً

🎯 **الخلاصة:** نص مثير للاهتمام، كيف يمكنني مساعدتك أكثر؟
"""

def translate_basic(text):
    """Basic translation attempt"""
    # Simple translation patterns
    translations = {
        'hello': 'مرحبا',
        'hi': 'أهلا',
        'thank you': 'شكراً لك',
        'good morning': 'صباح الخير',
        'good evening': 'مساء الخير',
        'مرحبا': 'Hello',
        'أهلا': 'Hi',
        'شكراً': 'Thank you',
        'صباح الخير': 'Good morning',
        'مساء الخير': 'Good evening'
    }
    
    text_lower = text.lower()
    for ar, en in translations.items():
        if ar in text_lower:
            return f"← {en}"
    
    return "للترجمة الدقيقة، فعّل الذكاء الاصطناعي"

def calculate_basic(text):
    """Basic calculation attempt"""
    try:
        # Replace Arabic/Persian numbers
        text = text.replace('×', '*').replace('÷', '/')
        
        # Simple evaluation (be careful with eval!)
        numbers = '0123456789+-*/.() '
        clean_text = ''.join(c for c in text if c in numbers)
        
        if clean_text:
            result = eval(clean_text)
            return f"≈ {result}"
    except:
        pass
    
    return "للحسابات المعقدة، فعّل الذكاء الاصطناعي"

def detect_topic(text):
    """Detect topic of question"""
    text_lower = text.lower()
    
    if any(word in text_lower for word in ['تاريخ', 'history', 'war', 'ancient']):
        return "التاريخ"
    elif any(word in text_lower for word in ['علم', 'science', 'physics', 'chemistry']):
        return "العلوم"
    elif any(word in text_lower for word in ['تقنية', 'technology', 'computer', 'internet']):
        return "التكنولوجيا"
    elif any(word in text_lower for word in ['صحة', 'health', 'medicine', 'doctor']):
        return "الصحة"
    elif any(word in text_lower for word in ['رياضة', 'sport', 'football', 'basketball']):
        return "الرياضة"
    else:
        return "عام"

def detect_text_type(text):
    """Detect type of text"""
    if '?' in text or any(word in text.lower() for word in ['كيف', 'ما', 'متى', 'what', 'how']):
        return "سؤال"
    elif any(word in text.lower() for word in ['شكرا', 'thank', 'thanks']):
        return "شكر"
    elif len(text.split()) > 20:
        return "نص طويل"
    else:
        return "رسالة قصيرة"

def analyze_sentiment(text):
    """Basic sentiment analysis"""
    positive = ['جيد', 'ممتاز', 'رائع', 'good', 'great', 'awesome', 'love']
    negative = ['سيء', 'سيئ', 'خطأ', 'bad', 'terrible', 'hate', 'wrong']
    
    text_lower = text.lower()
    pos_count = sum(1 for word in positive if word in text_lower)
    neg_count = sum(1 for word in negative if word in text_lower)
    
    if pos_count > neg_count:
        return "إيجابي ✨"
    elif neg_count > pos_count:
        return "يحتاج تحسين 🔧"
    else:
        return "محايد ⚖️"

async def analyze_image(image_data, prompt="اشرح ما تراه في هذه الصورة"):
    """Analyze image using Gemini Vision"""
    if not gemini_vision:
        return """
📸 **تحليل الصور الأساسي**

❗ **تحليل الصور المتقدم غير مفعل حالياً**

🔮 **لتفعيل تحليل الصور بالذكاء الاصطناعي:**
أضف متغير GEMINI_API_KEY في إعدادات Railway

🚀 **مع تحليل الصور المتقدم ستحصل على:**
• وصف تفصيلي للصورة
• تحليل المحتوى والعناصر
• إجابة أسئلة حول الصورة
• تحليل النصوص في الصور
• تعريف الأشياء والأماكن
• تحليل المشاعر والحالة المزاجية

💡 **حاول إضافة مفتاح Gemini API للاستفادة الكاملة!**
"""
    
    try:
        response = await asyncio.to_thread(
            gemini_vision.generate_content,
            [prompt, image_data]
        )
        return f"📸 **تحليل الصورة بالذكاء الاصطناعي:**\n\n{response.text}"
    except Exception as e:
        logger.error(f"Image analysis error: {e}")
        return f"❌ **خطأ في تحليل الصورة:** {str(e)}\n\nحاول مرة أخرى أو تحقق من إعدادات Gemini API."

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command handler"""
    user = update.effective_user
    chat = update.effective_chat
    
    logger.info(f"📨 /start from {user.first_name} in {chat.type}")
    
    # If in private chat
    if chat.type == ChatType.PRIVATE:
        # Check subscriptions to all channels where bot is admin
        required_channels = await get_user_channels(context, user.id)
        
        if required_channels:
            welcome_text = f"""
🤖 **مرحباً {user.first_name}!**

أهلاً بك في **بوت الذكاء الاصطناعي المتطور**!

🧠 **قدراتي المتقدمة:**
• إجابة جميع الأسئلة
• ترجمة فورية لأكثر من 100 لغة
• حل المسائل الرياضية
• مساعدة في البرمجة
• تحليل الصور والنصوص
• كتابة وتحرير المحتوى

⚠️ **شرط الاستخدام:**
للاستفادة من البوت، يرجى الاشتراك في القنوات التالية:

👇 **اشترك في جميع القنوات:**
"""
            
            await update.message.reply_text(
                welcome_text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=create_subscription_keyboard(required_channels)
            )
        else:
            welcome_text = f"""
🎉 **أهلاً وسهلاً {user.first_name}!**

مرحباً بك في بوت الذكاء الاصطناعي المتطور!

🧠 **الأنظمة المتاحة:**
• OpenAI GPT: {'🟢 نشط' if openai_client else '🔴 يحتاج تفعيل'}
• Google Gemini: {'🟢 نشط' if gemini_model else '🔴 يحتاج تفعيل'}
• التحليل الأساسي: 🟢 متاح دائماً

💬 **كيفية الاستخدام:**
• أرسل أي سؤال نصي
• أرسل صورة مع سؤال
• اطلب الترجمة
• اسأل عن البرمجة
• احتج لحل مسائل رياضية

🎯 **أمثلة على الاستخدام:**
• "ما هو الذكاء الاصطناعي؟"
• "ترجم إلى الإنجليزية: مرحبا بك"
• "احسب 25 × 15 + 100"
• "كيف أتعلم Python؟"
• أرسل صورة واسأل عنها

💬 **ابدأ بسؤالك الآن...**
"""
            
            await update.message.reply_text(
                welcome_text,
                parse_mode=ParseMode.MARKDOWN
            )
    
    # If in group/channel
    else:
        if user.id == ADMIN_ID:
            await update.message.reply_text(
                f"""
👑 **مرحباً أيها المدير!**

🤖 **حالة البوت في هذه القناة:**
• الاسم: {chat.title}
• النوع: {chat.type}
• الأعضاء: مجهول

⚙️ **لتفعيل البوت كمشرف:**
1. أضف البوت كمشرف في القناة
2. أعطه صلاحيات قراءة الأعضاء
3. المستخدمون سيحتاجون للاشتراك للاستخدام

✅ **البوت جاهز للعمل!**
""",
                parse_mode=ParseMode.MARKDOWN
            )

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle callback queries"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "check_all_subs":
        user_id = query.from_user.id
        is_subscribed = await check_all_subscriptions(context, user_id)
        
        if is_subscribed:
            await query.edit_message_text(
                f"""
✅ **تم التحقق بنجاح!**

🎉 **مرحباً بك {query.from_user.first_name}!**

🧠 **يمكنك الآن استخدام جميع القدرات:**
• اسأل أي سؤال
• أرسل صورة للتحليل
• اطلب الترجمة
• احتج لحل مسائل
• اطلب المساعدة في البرمجة

💬 **ابدأ بسؤالك الآن...**
""",
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            required_channels = await get_user_channels(context, user_id)
            await query.edit_message_text(
                f"""
❌ **لم تكمل الاشتراك بعد!**

📺 **يرجى الاشتراك في جميع القنوات المطلوبة**

✅ **تأكد من:**
• الاشتراك في كل قناة
• عدم كتم الإشعارات
• انتظار دقيقة واحدة
• ثم اضغط "تحقق" مرة أخرى

👇 **القنوات المطلوبة:**
""",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=create_subscription_keyboard(required_channels)
            )

async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text messages"""
    user = update.effective_user
    chat = update.effective_chat
    text = update.message.text
    
    # Only work in private chats
    if chat.type != ChatType.PRIVATE:
        return
    
    # Check subscriptions
    is_subscribed = await check_all_subscriptions(context, user.id)
    
    if not is_subscribed:
        required_channels = await get_user_channels(context, user.id)
        await update.message.reply_text(
            f"⚠️ **يرجى الاشتراك في جميع القنوات المطلوبة أولاً!**",
            reply_markup=create_subscription_keyboard(required_channels)
        )
        return
    
    logger.info(f"💬 Text from {user.first_name}: {text[:50]}...")
    
    # Show typing
    await context.bot.send_chat_action(chat.id, ChatAction.TYPING)
    
    # Get AI response
    response = await get_ai_response(text, user.first_name)
    
    await update.message.reply_text(
        response,
        parse_mode=ParseMode.MARKDOWN
    )

async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle photo messages"""
    user = update.effective_user
    chat = update.effective_chat
    
    # Only work in private chats
    if chat.type != ChatType.PRIVATE:
        return
    
    # Check subscriptions
    is_subscribed = await check_all_subscriptions(context, user.id)
    
    if not is_subscribed:
        required_channels = await get_user_channels(context, user.id)
        await update.message.reply_text(
            f"⚠️ **يرجى الاشتراك في جميع القنوات المطلوبة أولاً!**",
            reply_markup=create_subscription_keyboard(required_channels)
        )
        return
    
    logger.info(f"📸 Photo from {user.first_name}")
    
    try:
        await context.bot.send_chat_action(chat.id, ChatAction.TYPING)
        
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
            f"❌ **خطأ في تحليل الصورة**\n\nتأكد من إعدادات Gemini API أو حاول مرة أخرى."
        )

async def my_chat_member_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle bot being added/removed from chats"""
    chat_member = update.my_chat_member
    chat = update.effective_chat
    
    if chat_member.new_chat_member.status in ['administrator', 'member']:
        # Bot was added to channel/group
        logger.info(f"🎉 Bot added to {chat.title} ({chat.id})")
        
        # Store channel info
        bot_channels[chat.id] = {
            'id': chat.id,
            'title': chat.title,
            'username': chat.username,
            'type': chat.type
        }
        
        # Send welcome message to admin
        if chat.type in [ChatType.CHANNEL, ChatType.SUPERGROUP]:
            try:
                await context.bot.send_message(
                    ADMIN_ID,
                    f"""
🎉 **تم إضافة البوت بنجاح!**

📺 **القناة:** {chat.title}
🆔 **المعرف:** {chat.id}
👥 **النوع:** {chat.type}

✅ **البوت الآن يعمل كمشرف**
المستخدمون يجب أن يشتركوا في هذه القناة لاستخدام البوت

⚙️ **تأكد من إعطاء البوت صلاحيات:**
• قراءة الرسائل
• إدارة الأعضاء

🚀 **البوت جاهز للعمل!**
""",
                    parse_mode=ParseMode.MARKDOWN
                )
            except:
                pass
    
    elif chat_member.new_chat_member.status in ['left', 'kicked']:
        # Bot was removed
        logger.info(f"😞 Bot removed from {chat.title}")
        
        # Remove from stored channels
        if chat.id in bot_channels:
            del bot_channels[chat.id]

def main():
    """Main function"""
    try:
        logger.info("🚀 Starting Channel Admin Bot...")
        
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
        app.add_handler(ChatMemberHandler(my_chat_member_handler, ChatMemberHandler.MY_CHAT_MEMBER))
        
        logger.info("✅ Channel Admin Bot ready!")
        
        # Run the bot
        app.run_polling(drop_pending_updates=True)
        
    except Exception as e:
        logger.error(f"Fatal error: {e}")

if __name__ == "__main__":
    main()
