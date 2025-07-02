async def get_gemini_response(text, user_name="المستخدم"):
    """Get direct response from Gemini"""
    if not gemini_model:
        return get_direct_fallback(text)
    
    try:
        # Direct prompt without prefixes
        prompt = f"""
أجب على السؤال التالي باللغة العربية بشكل مباشر ومفيد بدون مقدمات:

السؤال: {text}

أجب مباشرة على السؤال. لا تبدأ بعبارات مثل "إليك الإجابة" أو "بالطبع يمكنني مساعدتك". 
فقط أعط الإجابة المباشرة والمفيدة.
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
        return "أحتاج إلى مفتاح Gemini API للترجمة الدقيقة. يمكنك الحصول عليه مجاناً من makersuite.google.com"
    
    # Math
    elif any(word in text_lower for word in ['احسب', 'حل', 'math', '+', '-', '*', '/', '=']):
        # Try basic calculation
        basic_calc = calculate_basic(text)
        if basic_calc:
            return basic_calc
        return "أحتاج إلى مفتاح Gemini API لحل المسائل المعقدة. يمكنك الحصول عليه مجاناً من makersuite.google.com"
    
    # Programming
    elif any(word in text_lower for word in ['برمجة', 'كود', 'python', 'javascript', 'html', 'css']):
        return "أحتاج إلى مفتاح Gemini API للمساعدة في البرمجة. يمكنك الحصول عليه مجاناً من makersuite.google.com وإضافته في إعدادات Railway."
    
    # General questions
    else:
        return f"سؤال مثير للاهتمام! أحتاج إلى مفتاح Gemini API لأعطيك إجابة شاملة. يمكنك الحصول عليه مجاناً من makersuite.google.com"
