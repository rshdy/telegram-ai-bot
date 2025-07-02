--- gemini_channel_bot.py
+++ gemini_channel_bot.py
@@ -0,0 +1,481 @@
+import os
+import logging
+import asyncio
+from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
+from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler, ChatMemberHandler
+from telegram.constants import ParseMode, ChatAction, ChatType
+from telegram.error import BadRequest, Forbidden
+
+# Configure logging to reduce HTTP messages
+logging.basicConfig(
+    level=logging.INFO,
+    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
+)
+logger = logging.getLogger(__name__)
+
+# Reduce httpx logging
+httpx_logger = logging.getLogger("httpx")
+httpx_logger.setLevel(logging.WARNING)
+
+# Bot Configuration
+BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '7500826569:AAHSXBY9elBf89fyAhV_EmGuUGrryGXdVq8')
+ADMIN_ID = int(os.getenv('ADMIN_USER_ID', '606898749'))
+
+# Only Gemini Configuration
+GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', '').strip()
+
+logger.info(f"🤖 Gemini Channel Bot starting...")
+logger.info(f"👤 Admin ID: {ADMIN_ID}")
+logger.info(f"🔮 Gemini: {len(GEMINI_API_KEY)} chars")
+
+# Bot data
+bot_channels = {}  # Store channels where bot is admin
+
+# Initialize Gemini
+gemini_model = None
+gemini_vision = None
+
+if GEMINI_API_KEY:
+    try:
+        import google.generativeai as genai
+        genai.configure(api_key=GEMINI_API_KEY)
+        gemini_model = genai.GenerativeModel('gemini-pro')
+        gemini_vision = genai.GenerativeModel('gemini-pro-vision')
+        logger.info("✅ Gemini Pro ready")
+    except Exception as e:
+        logger.error(f"❌ Gemini error: {e}")
+        gemini_model = None
+        gemini_vision = None
+else:
+    logger.info("⚠️ No Gemini API key provided")
+
+async def get_user_channels(context, user_id):
+    """Get channels where user should be subscribed"""
+    user_channels = []
+    for channel_id, channel_info in bot_channels.items():
+        try:
+            member = await context.bot.get_chat_member(channel_id, user_id)
+            if member.status not in ['member', 'administrator', 'creator']:
+                user_channels.append(channel_info)
+        except Exception as e:
+            logger.error(f"Error checking {channel_id}: {e}")
+    return user_channels
+
+async def check_all_subscriptions(context, user_id):
+    """Check if user subscribed to all channels"""
+    required_channels = await get_user_channels(context, user_id)
+    return len(required_channels) == 0
+
+def create_subscription_keyboard(required_channels):
+    """Create subscription keyboard"""
+    keyboard = []
+    for channel in required_channels:
+        channel_name = channel.get('title', 'القناة')
+        username = channel.get('username', '').replace('@', '')
+        if username:
+            channel_link = f"https://t.me/{username}"
+            keyboard.append([InlineKeyboardButton(f"📺 اشترك في {channel_name}", url=channel_link)])
+    
+    keyboard.append([InlineKeyboardButton("✅ تحقق من الاشتراك", callback_data="check_subs")])
+    return InlineKeyboardMarkup(keyboard)
+
+async def get_gemini_response(text, user_name="المستخدم"):
+    """Get response from Gemini"""
+    if not gemini_model:
+        return get_fallback_response(text, user_name)
+    
+    try:
+        prompt = f"""
+أنت مساعد ذكي متطور يجيب باللغة العربية. 
+اسم المستخدم: {user_name}
+السؤال: {text}
+
+أجب بشكل مفصل ومفيد وودود. يمكنك:
+- الإجابة على الأسئلة العامة
+- الترجمة بين اللغات
+- حل المسائل الرياضية  
+- المساعدة في البرمجة
+- تحليل النصوص
+- تقديم النصائح والاستشارات
+
+الرجاء الإجابة بطريقة احترافية ومفيدة.
+"""
+        
+        response = await asyncio.to_thread(gemini_model.generate_content, prompt)
+        return f"🔮 **Gemini Pro:**\n\n{response.text}"
+        
+    except Exception as e:
+        logger.error(f"Gemini error: {e}")
+        return get_fallback_response(text, user_name)
+
+def get_fallback_response(text, user_name):
+    """Fallback response when Gemini is not available"""
+    text_lower = text.lower()
+    
+    # Greetings
+    if any(word in text_lower for word in ['مرحبا', 'السلام', 'أهلا', 'hello', 'hi']):
+        return f"""
+🌟 **أهلاً وسهلاً {user_name}!**
+
+مرحباً بك في بوت الذكاء الاصطناعي المتطور!
+
+🔮 **مدعوم بـ Google Gemini**
+
+🧠 **يمكنني مساعدتك في:**
+• الإجابة على جميع الأسئلة
+• الترجمة بين اللغات
+• حل المسائل الرياضية
+• المساعدة في البرمجة
+• تحليل الصور والنصوص
+• كتابة وتحرير المحتوى
+
+💬 **ابدأ بسؤالك الآن...**
+
+⚠️ **ملاحظة:** لتفعيل الذكاء الاصطناعي الكامل، يرجى إضافة مفتاح Gemini API.
+"""
+    
+    # Translation
+    elif any(word in text_lower for word in ['ترجم', 'translate']):
+        return f"""
+🔤 **خدمة الترجمة**
+
+📝 **النص:** {text}
+
+🌍 **اللغة المكتشفة:** {'العربية' if any(ord(c) > 1000 for c in text) else 'الإنجليزية'}
+
+🔮 **مع Gemini ستحصل على:**
+• ترجمة دقيقة 100%
+• ترجمة طبيعية ومفهومة
+• دعم أكثر من 100 لغة
+• تصحيح نحوي تلقائي
+
+💡 **أضف مفتاح Gemini API للترجمة المتقدمة!**
+"""
+    
+    # Math
+    elif any(word in text_lower for word in ['احسب', 'حل', 'math', '+', '-', '*', '/', '=']):
+        return f"""
+🧮 **حاسبة ذكية**
+
+📊 **المسألة:** {text}
+
+🔮 **مع Gemini ستحصل على:**
+• حل دقيق للمسائل المعقدة
+• شرح خطوة بخطوة
+• معادلات رياضية متقدمة
+• رسوم بيانية وتوضيحات
+
+💡 **أضف مفتاح Gemini API للحلول المتقدمة!**
+"""
+    
+    # Programming
+    elif any(word in text_lower for word in ['برمجة', 'كود', 'python', 'javascript', 'html']):
+        return f"""
+💻 **مساعد البرمجة**
+
+👨‍💻 **استفسارك:** {text}
+
+🔮 **مع Gemini ستحصل على:**
+• كتابة كود كامل
+• إصلاح الأخطاء
+• شرح المفاهيم البرمجية
+• مراجعة وتحسين الكود
+• دعم جميع لغات البرمجة
+
+💡 **أضف مفتاح Gemini API للمساعدة الكاملة!**
+"""
+    
+    # General questions
+    else:
+        return f"""
+🤔 **سؤال ذكي من {user_name}**
+
+❓ **سؤالك:** {text}
+
+📊 **تحليل أساسي:**
+• الطول: {len(text)} حرف
+• الكلمات: {len(text.split())} كلمة
+• اللغة: {'العربية' if any(ord(c) > 1000 for c in text) else 'الإنجليزية'}
+
+🔮 **مع Google Gemini ستحصل على:**
+• إجابات مفصلة ودقيقة
+• معلومات حديثة ومحدثة
+• تحليل شامل للموضوع
+• أمثلة ومصادر
+• شرح مبسط وواضح
+
+💡 **لتفعيل الذكاء الاصطناعي الكامل:**
+أضف متغير GEMINI_API_KEY في إعدادات Railway
+
+🌟 **الحصول على مفتاح مجاني:**
+1. اذهب إلى makersuite.google.com
+2. سجل دخول بحساب Google
+3. اطلب API Key مجاني
+4. أضفه في Railway
+
+⚙️ **حالة النظام:**
+• Gemini: {'🟢 نشط' if gemini_model else '🔴 يحتاج تفعيل'}
+"""
+
+async def analyze_image(image_data, prompt="اشرح ما تراه في هذه الصورة"):
+    """Analyze image with Gemini Vision"""
+    if not gemini_vision:
+        return """
+📸 **تحليل الصور**
+
+❗ **تحليل الصور غير مفعل حالياً**
+
+🔮 **لتفعيل تحليل الصور بـ Gemini:**
+أضف متغير GEMINI_API_KEY في Railway
+
+🚀 **مع Gemini Vision ستحصل على:**
+• وصف تفصيلي للصورة
+• تحليل المحتوى والألوان
+• قراءة النصوص في الصور
+• تعريف الأشياء والأماكن
+• الإجابة على أسئلة حول الصورة
+
+💡 **مفتاح Gemini مجاني ومتاح للجميع!**
+"""
+    
+    try:
+        response = await asyncio.to_thread(
+            gemini_vision.generate_content,
+            [f"أجب باللغة العربية: {prompt}", image_data]
+        )
+        return f"📸 **تحليل الصورة - Gemini Vision:**\n\n{response.text}"
+    except Exception as e:
+        logger.error(f"Vision error: {e}")
+        return f"❌ **خطأ في تحليل الصورة:** {str(e)}"
+
+async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
+    """Start command"""
+    user = update.effective_user
+    chat = update.effective_chat
+    
+    logger.info(f"📨 /start from {user.first_name}")
+    
+    if chat.type == ChatType.PRIVATE:
+        required_channels = await get_user_channels(context, user.id)
+        
+        if required_channels:
+            text = f"""
+🤖 **مرحباً {user.first_name}!**
+
+أهلاً بك في **بوت الذكاء الاصطناعي** المدعوم بـ Google Gemini!
+
+🔮 **قدرات Gemini المتقدمة:**
+• إجابة جميع الأسئلة
+• ترجمة فورية لجميع اللغات
+• حل المسائل الرياضية المعقدة
+• مساعدة شاملة في البرمجة
+• تحليل الصور والنصوص
+• كتابة وتحرير المحتوى
+
+⚠️ **شرط الاستخدام:**
+للاستفادة من البوت، يرجى الاشتراك في القنوات أولاً:
+"""
+            
+            await update.message.reply_text(
+                text,
+                parse_mode=ParseMode.MARKDOWN,
+                reply_markup=create_subscription_keyboard(required_channels)
+            )
+        else:
+            text = f"""
+🎉 **أهلاً وسهلاً {user.first_name}!**
+
+مرحباً بك في بوت الذكاء الاصطناعي المدعوم بـ **Google Gemini**!
+
+🔮 **حالة Gemini:**
+• Gemini Pro: {'🟢 نشط' if gemini_model else '🔴 يحتاج تفعيل'}
+• Gemini Vision: {'🟢 نشط' if gemini_vision else '🔴 يحتاج تفعيل'}
+
+💬 **كيفية الاستخدام:**
+أرسل أي سؤال أو صورة وسأجيب بذكاء!
+
+🎯 **أمثلة:**
+• "ما هو الذكاء الاصطناعي؟"
+• "ترجم إلى الإنجليزية: مرحبا بك"
+• "احسب 25 × 15 + 100"
+• "كيف أتعلم Python؟"
+• أرسل صورة مع سؤال
+
+🚀 **ابدأ الآن بسؤالك...**
+"""
+            
+            await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
+    
+    elif user.id == ADMIN_ID:
+        await update.message.reply_text(
+            f"""
+👑 **مرحباً أيها المدير!**
+
+🤖 **البوت في القناة:** {chat.title}
+🔮 **Gemini:** {'🟢 نشط' if gemini_model else '🔴 محتاج مفتاح'}
+
+✅ **البوت جاهز للعمل كمشرف!**
+""",
+            parse_mode=ParseMode.MARKDOWN
+        )
+
+async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
+    """Handle callbacks"""
+    query = update.callback_query
+    await query.answer()
+    
+    if query.data == "check_subs":
+        user_id = query.from_user.id
+        is_subscribed = await check_all_subscriptions(context, user_id)
+        
+        if is_subscribed:
+            await query.edit_message_text(
+                f"""
+✅ **تم التحقق بنجاح!**
+
+🎉 **مرحباً بك {query.from_user.first_name}!**
+
+🔮 **Gemini جاهز لخدمتك:**
+• اسأل أي سؤال
+• أرسل صورة للتحليل
+• اطلب الترجمة
+• احتج لحل مسائل
+• اطلب مساعدة برمجية
+
+💬 **ابدأ بسؤالك الآن...**
+""",
+                parse_mode=ParseMode.MARKDOWN
+            )
+        else:
+            required_channels = await get_user_channels(context, user_id)
+            await query.edit_message_text(
+                f"❌ **لم تكمل الاشتراك!**\n\nيرجى الاشتراك في جميع القنوات المطلوبة.",
+                reply_markup=create_subscription_keyboard(required_channels)
+            )
+
+async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
+    """Handle text messages"""
+    user = update.effective_user
+    chat = update.effective_chat
+    text = update.message.text
+    
+    if chat.type != ChatType.PRIVATE:
+        return
+    
+    is_subscribed = await check_all_subscriptions(context, user.id)
+    if not is_subscribed:
+        required_channels = await get_user_channels(context, user.id)
+        await update.message.reply_text(
+            "⚠️ **يرجى الاشتراك في القنوات أولاً!**",
+            reply_markup=create_subscription_keyboard(required_channels)
+        )
+        return
+    
+    logger.info(f"💬 {user.first_name}: {text[:30]}...")
+    
+    await context.bot.send_chat_action(chat.id, ChatAction.TYPING)
+    response = await get_gemini_response(text, user.first_name)
+    
+    await update.message.reply_text(response, parse_mode=ParseMode.MARKDOWN)
+
+async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
+    """Handle photos"""
+    user = update.effective_user
+    chat = update.effective_chat
+    
+    if chat.type != ChatType.PRIVATE:
+        return
+    
+    is_subscribed = await check_all_subscriptions(context, user.id)
+    if not is_subscribed:
+        required_channels = await get_user_channels(context, user.id)
+        await update.message.reply_text(
+            "⚠️ **يرجى الاشتراك في القنوات أولاً!**",
+            reply_markup=create_subscription_keyboard(required_channels)
+        )
+        return
+    
+    logger.info(f"📸 Photo from {user.first_name}")
+    
+    try:
+        await context.bot.send_chat_action(chat.id, ChatAction.TYPING)
+        
+        photo = update.message.photo[-1]
+        photo_file = await photo.get_file()
+        photo_bytes = await photo_file.download_as_bytearray()
+        
+        prompt = update.message.caption or "اشرح ما تراه في هذه الصورة بالتفصيل"
+        response = await analyze_image(photo_bytes, prompt)
+        
+        await update.message.reply_text(response, parse_mode=ParseMode.MARKDOWN)
+        
+    except Exception as e:
+        logger.error(f"Photo error: {e}")
+        await update.message.reply_text("❌ خطأ في تحليل الصورة")
+
+async def my_chat_member_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
+    """Handle bot being added to channels"""
+    chat_member = update.my_chat_member
+    chat = update.effective_chat
+    
+    if chat_member.new_chat_member.status in ['administrator', 'member']:
+        logger.info(f"🎉 Bot added to {chat.title}")
+        
+        bot_channels[chat.id] = {
+            'id': chat.id,
+            'title': chat.title,
+            'username': chat.username,
+            'type': chat.type
+        }
+        
+        try:
+            await context.bot.send_message(
+                ADMIN_ID,
+                f"""
+🎉 **تم إضافة البوت بنجاح!**
+
+📺 **القناة:** {chat.title}
+🆔 **ID:** {chat.id}
+🔮 **Gemini:** {'🟢 نشط' if gemini_model else '🔴 محتاج مفتاح'}
+
+✅ **البوت يعمل الآن كمشرف**
+المستخدمون يجب الاشتراك لاستخدام البوت
+
+🚀 **جاهز للعمل!**
+""",
+                parse_mode=ParseMode.MARKDOWN
+            )
+        except:
+            pass
+    
+    elif chat_member.new_chat_member.status in ['left', 'kicked']:
+        logger.info(f"😞 Bot removed from {chat.title}")
+        if chat.id in bot_channels:
+            del bot_channels[chat.id]
+
+def main():
+    """Main function"""
+    try:
+        logger.info("🚀 Starting Gemini Channel Bot...")
+        
+        if not BOT_TOKEN:
+            logger.error("❌ No bot token!")
+            return
+        
+        app = Application.builder().token(BOT_TOKEN).build()
+        
+        # Add handlers
+        app.add_handler(CommandHandler("start", start_command))
+        app.add_handler(CallbackQueryHandler(callback_handler))
+        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))
+        app.add_handler(MessageHandler(filters.PHOTO, photo_handler))
+        app.add_handler(ChatMemberHandler(my_chat_member_handler, ChatMemberHandler.MY_CHAT_MEMBER))
+        
+        logger.info("✅ Gemini Channel Bot ready!")
+        app.run_polling(drop_pending_updates=True)
+        
+    except Exception as e:
+        logger.error(f"Fatal error: {e}")
+
+if __name__ == "__main__":
+    main()
