#!/usr/bin/env python3
import os
import logging
import asyncio
import sys
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler, ChatMemberHandler
from telegram.constants import ParseMode, ChatAction, ChatType
from telegram.error import BadRequest, Forbidden, NetworkError, TimedOut

# Configure logging with more details
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Reduce noisy logs
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("telegram").setLevel(logging.INFO)

# Bot Configuration
BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '7500826569:AAHSXBY9elBf89fyAhV_EmGuUGrryGXdVq8')
ADMIN_ID = int(os.getenv('ADMIN_USER_ID', '606898749'))
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', 'AIzaSyC-xuAc1Ong6_HI3lCA4V1ybLyo5I0PPJQ')

print(f"🚀 Bot starting...")
print(f"🤖 Bot Token: {BOT_TOKEN[:25]}...")
print(f"👤 Admin ID: {ADMIN_ID}")
print(f"🔑 Gemini Key: {GEMINI_API_KEY[:20]}..." if GEMINI_API_KEY else "❌ No Gemini Key")

# Bot data
bot_channels = {}
gemini_model = None
gemini_vision = None

# Initialize Gemini if key is available
async def init_gemini():
    """Initialize Gemini safely"""
    global gemini_model, gemini_vision
    
    if not GEMINI_API_KEY:
        logger.warning("⚠️ No Gemini API key")
        return False
    
    try:
        import google.generativeai as genai
        genai.configure(api_key=GEMINI_API_KEY)
        
        # Try different models
        models_to_try = ['gemini-1.5-flash', 'gemini-1.5-pro', 'gemini-pro']
        
        for model in models_to_try:
            try:
                test_model = genai.GenerativeModel(model)
                response = await asyncio.to_thread(test_model.generate_content, "Test")
                
                if response and response.text:
                    gemini_model = test_model
                    gemini_vision = test_model  # Same model for vision
                    logger.info(f"✅ Gemini ready with {model}")
                    return True
            except Exception as e:
                logger.debug(f"Model {model} failed: {e}")
                continue
        
        logger.error("❌ No working Gemini model found")
        return False
        
    except Exception as e:
        logger.error(f"❌ Gemini init failed: {e}")
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
            logger.error(f"Error checking channel {channel_id}: {e}")
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

async def get_ai_response(text):
    """Get AI response with fallback"""
    global gemini_model
    
    if gemini_model:
        try:
            prompt = f"أجب على هذا السؤال باللغة العربية بشكل مباشر:\n{text}"
            response = await asyncio.wait_for(
                asyncio.to_thread(gemini_model.generate_content, prompt),
                timeout=20.0
            )
            
            if response and response.text:
                return response.text.strip()
                
        except Exception as e:
            logger.error(f"Gemini error: {e}")
    
    # Fallback responses
    return get_smart_response(text)

def get_smart_response(text):
    """Smart fallback responses"""
    text_lower = text.lower()
    
    # Greetings
    if any(word in text_lower for word in ['مرحبا', 'السلام', 'أهلا', 'hello', 'hi']):
        return "مرحباً بك! أنا بوت ذكي جاهز لمساعدتك في أي شيء تحتاجه."
    
    # Questions about the bot
    elif any(word in text_lower for word in ['من أنت', 'ما اسمك', 'what are you']):
        return "أنا بوت ذكي مدعوم بالذكاء الاصطناعي، أستطيع مساعدتك في الإجابة على الأسئلة والترجمة والحسابات."
    
    # Translation
    elif any(word in text_lower for word in ['ترجم', 'translate']):
        result = basic_translate(text)
        if result:
            return result
        return "أرسل النص الذي تريد ترجمته مع كلمة 'ترجم' قبله"
    
    # Math
    elif any(word in text_lower for word in ['احسب', 'حل', '+', '-', '*', '/']):
        result = basic_calculate(text)
        if result:
            return result
        return "أرسل العملية الحسابية بوضوح، مثل: احسب 5 + 3"
    
    # General questions
    elif '؟' in text or 'ما' in text_lower or 'كيف' in text_lower:
        return "سؤال جيد! أحاول إعادة الاتصال بنظام الذكاء الاصطناعي المتقدم للحصول على إجابة شاملة."
    
    else:
        return "يمكنني مساعدتك في الإجابة على الأسئلة، الترجمة، والحسابات. ما الذي تحتاج مساعدة فيه؟"

def basic_translate(text):
    """Basic translation"""
    translations = {
        'hello': 'مرحبا', 'hi': 'أهلا', 'thank you': 'شكراً',
        'good morning': 'صباح الخير', 'good night': 'تصبح على خير',
        'how are you': 'كيف حالك', 'what is your name': 'ما اسمك',
        'مرحبا': 'Hello', 'أهلا': 'Hi', 'شكراً': 'Thank you',
        'صباح الخير': 'Good morning', 'كيف حالك': 'How are you'
    }
    
    text_clean = text.lower().replace('ترجم', '').replace('translate', '').strip()
    
    for word, translation in translations.items():
        if word in text_clean:
            return f"{word} → {translation}"
    
    return None

def basic_calculate(text):
    """Basic calculation"""
    try:
        # Clean text
        clean_text = text.replace('احسب', '').replace('حل', '').replace('×', '*').replace('÷', '/')
        clean_text = clean_text.replace('=', '').replace('؟', '').strip()
        
        # Keep only valid characters
        allowed = '0123456789+-*/.() '
        clean_text = ''.join(c for c in clean_text if c in allowed).strip()
        
        if clean_text and any(op in clean_text for op in ['+', '-', '*', '/']):
            result = eval(clean_text)
            return f"{clean_text} = {result}"
    except:
        pass
    
    return None

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command with detailed logging"""
    try:
        user = update.effective_user
        chat = update.effective_chat
        
        logger.info(f"📨 /start from {user.first_name} (ID: {user.id}) in chat {chat.id}")
        
        if chat.type == ChatType.PRIVATE:
            required_channels = await get_user_channels(context, user.id)
            
            if required_channels:
                logger.info(f"👤 User needs to subscribe to {len(required_channels)} channels")
                
                text = f"""
🤖 **مرحباً {user.first_name}!**

أهلاً بك في **بوت الذكاء الاصطناعي**!

🔮 **قدراتي:**
• إجابة جميع الأسئلة
• ترجمة فورية  
• حل المسائل الرياضية
• مساعدة في البرمجة
• تحليل الصور

⚠️ **للاستخدام:**
يرجى الاشتراك في القنوات أولاً:
"""
                
                await update.message.reply_text(
                    text,
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=create_subscription_keyboard(required_channels)
                )
                
            else:
                logger.info("✅ User has access to bot")
                
                gemini_status = "🟢 نشط" if gemini_model else "🔴 غير متاح"
                
                text = f"""
🎉 **أهلاً وسهلاً {user.first_name}!**

مرحباً بك في بوت الذكاء الاصطناعي!

🔮 **حالة الخدمات:**
• الذكاء الاصطناعي: {gemini_status}
• الترجمة: 🟢 نشط
• الحسابات: 🟢 نشط

💬 **كيفية الاستخدام:**
أرسل أي سؤال وسأجيب عليه!

🎯 **أمثلة:**
• اسأل أي سؤال
• ترجم: Hello
• احسب 5 + 3
• أرسل صورة للتحليل

🚀 **ابدأ الآن...**
"""
                
                await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
                logger.info("✅ Welcome message sent")
        
        else:
            # Group/Channel
            logger.info(f"👥 Bot added to group: {chat.title}")
            await update.message.reply_text(
                f"👋 مرحباً! تم إضافة البوت إلى {chat.title}\n"
                f"استخدم /start في الرسائل الخاصة للتفاعل معي."
            )
    
    except Exception as e:
        logger.error(f"❌ Error in start command: {e}")
        try:
            await update.message.reply_text(
                "حدث خطأ في تشغيل البوت. يرجى المحاولة مرة أخرى."
            )
        except:
            logger.error("❌ Failed to send error message")

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle callback queries"""
    try:
        query = update.callback_query
        await query.answer()
        
        logger.info(f"🔘 Callback: {query.data} from {query.from_user.first_name}")
        
        if query.data == "check_subs":
            user_id = query.from_user.id
            is_subscribed = await check_all_subscriptions(context, user_id)
            
            if is_subscribed:
                logger.info(f"✅ User {user_id} passed subscription check")
                
                await query.edit_message_text(
                    f"""
✅ **تم التحقق بنجاح!**

🎉 **مرحباً بك {query.from_user.first_name}!**

🔮 **البوت جاهز الآن:**
• اسأل أي سؤال
• أرسل صورة للتحليل
• اطلب الترجمة
• احتج لحل مسائل

💬 **ابدأ بسؤالك...**
""",
                    parse_mode=ParseMode.MARKDOWN
                )
            else:
                logger.info(f"❌ User {user_id} still needs to subscribe")
                required_channels = await get_user_channels(context, user_id)
                await query.edit_message_text(
                    "❌ **لم تكمل الاشتراك!**\n\nيرجى الاشتراك في جميع القنوات.",
                    reply_markup=create_subscription_keyboard(required_channels)
                )
    
    except Exception as e:
        logger.error(f"❌ Callback error: {e}")

async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text messages"""
    try:
        user = update.effective_user
        chat = update.effective_chat
        text = update.message.text
        
        if chat.type != ChatType.PRIVATE:
            return
        
        logger.info(f"💬 Message from {user.first_name}: {text[:50]}...")
        
        # Check subscription
        is_subscribed = await check_all_subscriptions(context, user.id)
        if not is_subscribed:
            required_channels = await get_user_channels(context, user.id)
            await update.message.reply_text(
                "⚠️ **يرجى الاشتراك في القنوات أولاً!**",
                reply_markup=create_subscription_keyboard(required_channels)
            )
            return
        
        # Show typing
        await context.bot.send_chat_action(chat.id, ChatAction.TYPING)
        
        # Get response
        response = await get_ai_response(text)
        
        # Send response
        await update.message.reply_text(response)
        logger.info(f"✅ Response sent to {user.first_name}")
    
    except Exception as e:
        logger.error(f"❌ Text handler error: {e}")
        try:
            await update.message.reply_text("حدث خطأ، حاول مرة أخرى")
        except:
            pass

async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle photos"""
    try:
        user = update.effective_user
        chat = update.effective_chat
        
        if chat.type != ChatType.PRIVATE:
            return
        
        logger.info(f"📸 Photo from {user.first_name}")
        
        # Check subscription
        is_subscribed = await check_all_subscriptions(context, user.id)
        if not is_subscribed:
            required_channels = await get_user_channels(context, user.id)
            await update.message.reply_text(
                "⚠️ **يرجى الاشتراك في القنوات أولاً!**",
                reply_markup=create_subscription_keyboard(required_channels)
            )
            return
        
        await context.bot.send_chat_action(chat.id, ChatAction.TYPING)
        
        if gemini_vision:
            try:
                photo = update.message.photo[-1]
                photo_file = await photo.get_file()
                photo_bytes = await photo_file.download_as_bytearray()
                
                prompt = update.message.caption or "اشرح ما تراه في هذه الصورة"
                
                response = await asyncio.wait_for(
                    asyncio.to_thread(
                        gemini_vision.generate_content,
                        [f"أجب باللغة العربية: {prompt}", photo_bytes]
                    ),
                    timeout=30.0
                )
                
                if response and response.text:
                    await update.message.reply_text(response.text.strip())
                else:
                    await update.message.reply_text("لم أتمكن من تحليل الصورة")
                    
            except Exception as e:
                logger.error(f"Vision error: {e}")
                await update.message.reply_text("حدث خطأ في تحليل الصورة")
        else:
            await update.message.reply_text(
                "تحليل الصور غير متاح حالياً. سأتمكن من تحليل الصور عند تفعيل خدمة Gemini Vision."
            )
    
    except Exception as e:
        logger.error(f"❌ Photo handler error: {e}")

async def member_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle bot being added to groups/channels"""
    try:
        chat_member = update.my_chat_member
        chat = update.effective_chat
        
        if chat_member.new_chat_member.status in ['administrator', 'member']:
            logger.info(f"🎉 Bot added to {chat.title} (ID: {chat.id})")
            
            bot_channels[chat.id] = {
                'id': chat.id,
                'title': chat.title,
                'username': chat.username,
                'type': chat.type
            }
            
            # Notify admin
            try:
                await context.bot.send_message(
                    ADMIN_ID,
                    f"""
🎉 **تم إضافة البوت!**

📺 **اسم القناة:** {chat.title}
🆔 **معرف القناة:** {chat.id}
🔗 **يوزرنيم:** @{chat.username}

✅ **البوت يعمل الآن كمشرف**
""",
                    parse_mode=ParseMode.MARKDOWN
                )
            except:
                pass
        
        elif chat_member.new_chat_member.status in ['left', 'kicked']:
            logger.info(f"😞 Bot removed from {chat.title}")
            if chat.id in bot_channels:
                del bot_channels[chat.id]
    
    except Exception as e:
        logger.error(f"❌ Member handler error: {e}")

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    """Handle errors"""
    logger.error(f"❌ Update {update} caused error {context.error}")

def main():
    """Main function"""
    try:
        print("🚀 Initializing bot...")
        
        if not BOT_TOKEN:
            print("❌ No bot token provided!")
            return
        
        # Create application
        app = Application.builder().token(BOT_TOKEN).build()
        
        # Add error handler
        app.add_error_handler(error_handler)
        
        # Add handlers
        app.add_handler(CommandHandler("start", start_command))
        app.add_handler(CallbackQueryHandler(callback_handler))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))
        app.add_handler(MessageHandler(filters.PHOTO, photo_handler))
        app.add_handler(ChatMemberHandler(member_handler, ChatMemberHandler.MY_CHAT_MEMBER))
        
        print("✅ All handlers added")
        
        # Initialize Gemini in background
        async def startup():
            logger.info("🔄 Initializing Gemini...")
            await init_gemini()
        
        # Run startup
        asyncio.create_task(startup())
        
        print("🚀 Starting bot polling...")
        logger.info("✅ Bot ready and running!")
        
        # Start polling
        app.run_polling(drop_pending_updates=True)
        
    except KeyboardInterrupt:
        print("👋 Bot stopped by user")
    except Exception as e:
        print(f"💥 Fatal error: {e}")
        logger.error(f"Fatal error: {e}")

if __name__ == "__main__":
    main()
