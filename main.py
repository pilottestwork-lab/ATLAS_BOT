import os
import logging
import io
import threading
from flask import Flask
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters
import google.generativeai as genai
from PIL import Image
import openai  # مكتبة ديب سيك

# 1. إعداد السجلات
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# 2. إعداد المفاتيح
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")

# إعداد جيمناي (للصور والملفات)
genai.configure(api_key=GOOGLE_API_KEY)
gemini_model = genai.GenerativeModel(
    model_name="gemini-1.5-flash", # نستخدم 1.5 لأنه مستقر وحصته كبيرة
    system_instruction="أنت البروفيسور أطلس. حلل هذه الصورة الطبية أو الملف بدقة وقدم تقريراً وافياً."
)

# إعداد ديب سيك (للنصوص)
deepseek_client = openai.OpenAI(
    api_key=DEEPSEEK_API_KEY, 
    base_url="https://api.deepseek.com"
)

# التعليمات الأساسية لديب سيك
SYSTEM_INSTRUCTION = """
أنت البروفيسور أطلس، خبير أكاديمي طبي.
دورك هو مساعدة الطلاب في الأسئلة الطبية وشرح الحالات.
لغة التواصل: العربية بشكل أساسي.
في نهاية كل رسالة، ذكرهم بالقناة: https://t.me/atlas_medical.
"""

# --- سيرفر وهمي لإرضاء Render ---
flask_app = Flask(__name__)
@flask_app.route('/')
def health_check():
    return "Professor Atlas is Online (Hybrid Mode)!", 200

def run_flask():
    port = int(os.environ.get("PORT", 8000))
    flask_app.run(host='0.0.0.0', port=port)

# --- دوال المعالجة (الذكاء الاصطناعي) ---

# دالة التعامل مع ديب سيك (للنصوص)
def ask_deepseek(text_prompt):
    try:
        response = deepseek_client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": SYSTEM_INSTRUCTION},
                {"role": "user", "content": text_prompt}
            ],
            stream=False
        )
        return response.choices[0].message.content
    except Exception as e:
        # إذا فشل ديب سيك، نستخدم جيمناي كاحتياطي
        logging.error(f"DeepSeek Error: {e}")
        return str(gemini_model.generate_content(text_prompt).text)

# دالة التعامل مع جيمناي (للوسائط)
def ask_gemini_media(content_list):
    try:
        response = gemini_model.generate_content(content_list)
        return response.text
    except Exception as e:
        return f"عذراً، حدث خطأ أثناء تحليل الملف/الصورة: {str(e)}"

# --- دوال البوت ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("أهلاً بك دكتور! أنا البروفيسور أطلس.\n- أرسل سؤالاً نصياً (سيجيبك ديب سيك 🧠).\n- أرسل صورة أو ملف (سيحلله جيمناي 👁️).")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    status_msg = await update.message.reply_text("جاري التحليل... ⏳")
    
    try:
        final_response = ""

        # الحالة 1: المستخدم أرسل صورة (نستخدم Gemini)
        if update.message.photo:
            photo_file = await update.message.photo[-1].get_file()
            photo_bytes = await photo_file.download_as_bytearray()
            image = Image.open(io.BytesIO(photo_bytes))
            
            caption = update.message.caption or "حلل هذه الصورة الطبية"
            final_response = ask_gemini_media([caption, image])

        # الحالة 2: المستخدم أرسل ملف PDF أو مستند (نستخدم Gemini لأنه يدعم الملفات)
        elif update.message.document:
            doc_file = await update.message.document.get_file()
            doc_data = await doc_file.download_as_bytearray()
            
            # تجهيز الملف لجيمناي
            content_list = [
                {"mime_type": update.message.document.mime_type, "data": bytes(doc_data)},
                update.message.caption or "لخص وحلل هذا الملف الطبي"
            ]
            final_response = ask_gemini_media(content_list)

        # الحالة 3: المستخدم أرسل نصاً فقط (نستخدم DeepSeek)
        elif update.message.text:
            user_text = update.message.text
            final_response = ask_deepseek(user_text)

        # إرسال الرد (مع تقسيم الرسائل الطويلة)
        if final_response:
            if len(final_response) > 4000:
                for i in range(0, len(final_response), 4000):
                    await update.message.reply_text(final_response[i:i+4000])
            else:
                await update.message.reply_text(final_response)
        
    except Exception as e:
        await update.message.reply_text(f"حدث خطأ غير متوقع: {str(e)}")
    
    finally:
        # حذف رسالة "جاري التحليل" لترتيب المحادثة
        try:
            await status_msg.delete()
        except:
            pass

# --- التشغيل الرئيسي ---
if __name__ == '__main__':
    # تشغيل Flask
    threading.Thread(target=run_flask, daemon=True).start()
    
    # تشغيل البوت
    if not TELEGRAM_TOKEN:
        print("Error: TELEGRAM_TOKEN missing")
    else:
        app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
        app.add_handler(CommandHandler('start', start))
        app.add_handler(MessageHandler(filters.ALL, handle_message))
        
        print("Professor Atlas Hybrid (DeepSeek + Gemini) is Running...")
        app.run_polling()





