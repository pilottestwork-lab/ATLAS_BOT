import os
import logging
import io
import threading
from flask import Flask
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters
import google.generativeai as genai
from PIL import Image

# 1. إعداد السجلات
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# 2. إعداد المفاتيح
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

genai.configure(api_key=GOOGLE_API_KEY)

# 3. إعداد الموديل
SYSTEM_INSTRUCTION = """
أنت البروفيسور أطلس، خبير أكاديمي طبي متخصص.
دورك هو مساعدة الطلاب في حل الأسئلة الطبية، شرح صور الأشعة، وتحليل التقارير.
عندما تستلم صورة سؤال، قم بحله وشرح السبب.
عندما تستلم صورة أشعة، قدم تقريراً طبياً وافياً.
إذا طلب الطالب حل أسئلة (MCQs)، قم بتحليل كل خيار ولماذا هو صح أو خطأ.
لغة التواصل: العربية بشكل أساسي، مع ذكر المصطلحات الطبية بالإنجليزية بين أقواس.
في نهاية كل رسالة، ذكرهم بالقناة: https://t.me/atlas_medical.
"""

model = genai.GenerativeModel(
    model_name="gemini-2.5-Pro",
    system_instruction=SYSTEM_INSTRUCTION
)

# --- سيرفر وهمي لإرضاء Render (حل مشكلة Timeout) ---
flask_app = Flask(__name__)
@flask_app.route('/')
def health_check():
    return "Professor Atlas is Alive!", 200

def run_flask():
    # Render يمرر البورت في متغير بيئة اسمه PORT
    port = int(os.environ.get("PORT", 8000))
    flask_app.run(host='0.0.0.0', port=port)

# --- دوال البوت ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("أهلاً بك يا دكتور! أنا البروفيسور أطلس. أرسل لي أي سؤال، صورة أشعة، أو ملف وسأقوم بتحليله فوراً.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    content = []
    
    # معالجة النص
    if update.message.text:
        content.append(update.message.text)
    
    # معالجة الصور
    if update.message.photo:
        await update.message.reply_text("جاري تحليل الصورة طبياً... لحظة واحدة ⏳")
        photo_file = await update.message.photo[-1].get_file()
        photo_bytes = await photo_file.download_as_bytearray()
        image = Image.open(io.BytesIO(photo_bytes))
        content.append(image)
        if update.message.caption:
            content.append(update.message.caption)
        else:
            content.append("حلل هذه الصورة الطبية بدقة.")

  # إذا كانت الرسالة ملف (PDF مثلاً)
    if update.message.document:
        doc_file = await update.message.document.get_file()
        doc_byte_array = await doc_file.download_as_bytearray()
        
        # الحل هنا: تحويل bytearray إلى bytes ليفهمها Gemini
        doc_bytes = bytes(doc_byte_array) 
        
        content.append({
            "mime_type": update.message.document.mime_type,
            "data": doc_bytes
        })
        content.append(update.message.caption if update.message.caption else "قم بتحليل هذا الملف الطبي بدقة")

    if not content:
        return

    try:
        response = model.generate_content(content)
        # تقسيم الرسائل الطويلة لتجنب خطأ تليجرام
        full_response = response.text
        if len(full_response) > 4000:
            for i in range(0, len(full_response), 4000):
                await update.message.reply_text(full_response[i:i+4000])
        else:
            await update.message.reply_text(full_response)
    except Exception as e:
        await update.message.reply_text(f"عذراً يا دكتور، حدث خطأ تقني: {str(e)}")

# --- التشغيل الرئيسي ---
if __name__ == '__main__':
    if not TELEGRAM_TOKEN or not GOOGLE_API_KEY:
        print("Error: المفاتيح غير موجودة!")
    else:
        # تشغيل السيرفر الوهمي في خيط (Thread) منفصل
        threading.Thread(target=run_flask, daemon=True).start()
        
        # تشغيل البوت
        application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
        
        # دمج كل أنواع الرسائل في معالج واحد
        application.add_handler(CommandHandler('start', start))
        application.add_handler(MessageHandler(filters.TEXT | filters.PHOTO | filters.Document.ALL, handle_message))
        
        print("Professor Atlas is running with Flask health check...")
        application.run_polling()



