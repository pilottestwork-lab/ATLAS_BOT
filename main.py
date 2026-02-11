import os
import logging
import threading
import google.generativeai as genai
import openai
from flask import Flask
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters
from PIL import Image
import io

# 1. إعداد السيرفر للبقاء حياً على Render
app = Flask(__name__)
@app.route('/')
def home():
    return "Professor Atlas is Online (Gemini 2.5 + DeepSeek)!", 200

def run_flask():
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port)

# 2. إعداد مفاتيح الـ API
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
DEEPSEEK_CLIENT = openai.OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com"
)

# 3. وظيفة معالجة الصور عبر Gemini 2.5
def ask_gemini_vision(image_data, prompt):
    try:
        model = genai.GenerativeModel("gemini-2.5-flash") # الموديل المطلوب
        response = model.generate_content([prompt, image_data])
        return response.text
    except Exception as e:
        if "429" in str(e):
            return "⚠️ ضغط كبير على موديل الصور حالياً، حاول مجدداً بعد دقيقة."
        return f"خطأ في تحليل الصورة: {str(e)}"

# 4. وظيفة معالجة النصوص عبر DeepSeek (مجاني ومستقر)
def ask_deepseek_text(prompt):
    try:
        response = DEEPSEEK_CLIENT.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"خطأ في محرك النصوص: {str(e)}"

# 5. معالجة رسائل تليجرام
async def handle_atlas_logic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text or update.message.caption or "حلل هذه الحالة"
    status_msg = await update.message.reply_text("⏳ البروفيسور أطلس يراجع الحالة...")

    try:
        # إذا أرسل صورة أو ملف (استخدام Gemini 2.5)
        if update.message.photo or update.message.document:
            if update.message.photo:
                file = await update.message.photo[-1].get_file()
                file_bytes = await file.download_as_bytearray()
                image = Image.open(io.BytesIO(file_bytes))
                result = ask_gemini_vision(image, user_text)
            else:
                # معالجة الـ PDF عبر Gemini
                doc = await update.message.document.get_file()
                doc_bytes = await doc.download_as_bytearray()
                pdf_part = {"mime_type": "application/pdf", "data": bytes(doc_bytes)}
                result = ask_gemini_vision(pdf_part, user_text)
        
        # إذا أرسل نصاً فقط (استخدام DeepSeek)
        else:
            result = ask_deepseek_text(user_text)

        # الرد على المستخدم
        await update.message.reply_text(result)

    except Exception as e:
        await update.message.reply_text(f"عذراً يا دكتور، حدثت مشكلة: {str(e)}")
    finally:
        await status_msg.delete()

if __name__ == '__main__':
    # تشغيل السيرفر في الخلفية
    threading.Thread(target=run_flask, daemon=True).start()
    
    # تشغيل البوت
    TOKEN = os.getenv("TELEGRAM_TOKEN")
    app_bot = ApplicationBuilder().token(TOKEN).build()
    app_bot.add_handler(MessageHandler(filters.ALL, handle_atlas_logic))
    
    print("Professor Atlas is booting up...")
    app_bot.run_polling()





