import os
import threading
import google.generativeai as genai
from flask import Flask
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters
from PIL import Image
import io

# 1. سيرفر Flask للبقاء أونلاين على Render
app = Flask(__name__)
@app.route('/')
def home():
    return "Professor Atlas (Gemini 2.5 Edition) is Running!", 200

def run_flask():
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port)

# 2. إعداد الموديل الجبار (Gemini 2.5 Flash)
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
MODEL_ID = "gemini-2.5-flash-aative-audio-dialog" # هذا هو المعرف التقني لنسخة 2.5 الشاملة

# 3. معالجة كافة أنواع الرسائل (صوت، صورة، نص)
async def handle_atlas_comprehensive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_msg = update.message
    prompt = user_msg.text or user_msg.caption or "حلل هذا المحتوى طبياً"
    status = await user_msg.reply_text("⏳ البروفيسور أطلس يراجع الحالة (Gemini 2.5)...")

    content_list = [prompt]

    try:
        # أ. إذا أرسل صورة (أشعة/تحاليل)
        if user_msg.photo:
            file = await user_msg.photo[-1].get_file()
            img_bytes = await file.download_as_bytearray()
            image = Image.open(io.BytesIO(img_bytes))
            content_list.append(image)

        # ب. إذا أرسل بصمة صوتية (Native Audio)
        elif user_msg.voice or user_msg.audio:
            audio_file = await (user_msg.voice or user_msg.audio).get_file()
            audio_bytes = await audio_file.download_as_bytearray()
            audio_data = {"mime_type": "audio/ogg", "data": bytes(audio_bytes)}
            content_list.append(audio_data)

        # ج. إذا أرسل ملف PDF
        elif user_msg.document and user_msg.document.mime_type == 'application/pdf':
            doc = await user_msg.document.get_file()
            doc_bytes = await doc.download_as_bytearray()
            pdf_data = {"mime_type": "application/pdf", "data": bytes(doc_bytes)}
            content_list.append(pdf_data)

        # إرسال الطلب للموديل
        model = genai.GenerativeModel(MODEL_ID)
        response = model.generate_content(content_list)
        
        await user_msg.reply_text(response.text)

    except Exception as e:
        # التعامل مع حد الـ 20 طلباً
        if "429" in str(e):
            await user_msg.reply_text("⚠️ يا دكتور، وصلنا لحد الـ 20 طلباً المجانية لـ Gemini 2.5. انتظر دقيقة وسأعود للعمل.")
        else:
            await user_msg.reply_text(f"حدث خطأ: {str(e)}")
    finally:
        await status.delete()

if __name__ == '__main__':
    # تشغيل Flask
    threading.Thread(target=run_flask, daemon=True).start()
    
    # تشغيل البوت
    TOKEN = os.getenv("TELEGRAM_TOKEN")
    application = ApplicationBuilder().token(TOKEN).build()
    application.add_handler(MessageHandler(filters.ALL, handle_atlas_comprehensive))
    
    print("Professor Atlas 2.5 is Online!")
    application.run_polling()



