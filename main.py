import os
import threading
import logging
import google.generativeai as genai
from flask import Flask
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters
from PIL import Image
import io

# --- 1. قائمة المفاتيح (ضع كل مفاتيحك هنا) ---
# كل مفتاح يعطيك 20 طلباً مجانياً لـ Gemini 2.5
API_KEYS = [
    "AIzaSyA1_YOUR_KEY_01",
    "AIzaSyB2_YOUR_KEY_02",
    "AIzaSyC3_YOUR_KEY_03",
    "AIzaSyD4_YOUR_KEY_04",
    "AIzaSyE5_YOUR_KEY_05",
    "AIzaSyF6_YOUR_KEY_06",
    "AIzaSyG7_YOUR_KEY_07",
    "AIzaSyH8_YOUR_KEY_08",
    "AIzaSyI9_YOUR_KEY_09",
    "AIzaSyJ10_YOUR_KEY_10",
    "AIzaSyK11_YOUR_KEY_11",
    "AIzaSyL12_YOUR_KEY_12",
    "AIzaSyM13_YOUR_KEY_13",
    "AIzaSyN14_YOUR_KEY_14",
    "AIzaSyO15_YOUR_KEY_15",
    "AIzaSyP16_YOUR_KEY_16",
    "AIzaSyQ17_YOUR_KEY_17",
    "AIzaSyR18_YOUR_KEY_18",
    "AIzaSyS19_YOUR_KEY_19",
    "AIzaSyT20_YOUR_KEY_20"
    # يمكنك إضافة حتى 20 مفتاحاً هنا لزيادة السعة
]

# --- 2. إعدادات السيرفر والذاكرة ---
app = Flask(__name__)
user_memory = {} # قاموس لتخزين تاريخ المحادثات (الذاكرة)

@app.route('/')
def home(): return "Professor Atlas 2.5 (Final Edition) is Online!", 200

def run_flask():
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port)

# --- 3. وظيفة الحصول على رد مع المداورة والذاكرة ---
def get_smart_response(user_id, content_list):
    # استرجاع الذاكرة السابقة لهذا المستخدم
    if user_id not in user_memory:
        user_memory[user_id] = []
    
    # تجربة المفاتيح واحداً تلو الآخر عند الحاجة
    for key in API_KEYS:
        try:
            genai.configure(api_key=key)
            model = genai.GenerativeModel("gemini-2.5-flash") # الاسم التقني الصحيح
            
            # بدء محادثة بالذاكرة المخزنة
            chat = model.start_chat(history=user_memory[user_id])
            response = chat.send_message(content_list)
            
            # تحديث الذاكرة بعد الرد الناجح
            user_memory[user_id] = chat.history 
            return response.text
            
        except Exception as e:
            if "429" in str(e): # إذا نفدت حصة هذا المفتاح
                continue # جرب المفتاح التالي تلقائياً
            return f"عذراً يا دكتور، حدث خطأ تقني: {str(e)}"
            
    return "⚠️ جميع مفاتيح الـ API استنفدت حصتها (20 طلب لكل مفتاح). يرجى الانتظار دقيقة."

# --- 4. معالجة رسائل تليجرام الشاملة ---
async def handle_atlas_final(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    user_id = msg.from_user.id
    status = await msg.reply_text("⏳ البروفيسور أطلس يراجع الطلب والذاكرة...")

    prompt = msg.text or msg.caption or "حلل هذا المحتوى طبياً"
    content_list = [prompt]

    try:
        # أ. معالجة الصور والأشعة
        if msg.photo:
            file = await msg.photo[-1].get_file()
            img_bytes = await file.download_as_bytearray()
            content_list.append(Image.open(io.BytesIO(img_bytes)))

        # ب. معالجة البصمات الصوتية (Native Audio)
        elif msg.voice:
            audio = await msg.voice.get_file()
            audio_bytes = await audio.download_as_bytearray()
            content_list.append({"mime_type": "audio/ogg", "data": bytes(audio_bytes)})

        # ج. معالجة ملفات الـ PDF
        elif msg.document and msg.document.mime_type == 'application/pdf':
            doc = await msg.document.get_file()
            doc_bytes = await doc.download_as_bytearray()
            content_list.append({"mime_type": "application/pdf", "data": bytes(doc_bytes)})

        # طلب الرد من المحرك الذكي
        response_text = get_smart_response(user_id, content_list)
        await msg.reply_text(response_text)

    except Exception as e:
        await msg.reply_text(f"حدث خطأ في معالجة الطلب: {str(e)}")
    finally:
        await status.delete()

# --- 5. التشغيل النهائي ---
if __name__ == '__main__':
    # تشغيل سيرفر Flask للبقاء حياً على Render
    threading.Thread(target=run_flask, daemon=True).start()
    
    # تشغيل البوت باستخدام التوكن السري الخاص بك
    TOKEN = os.getenv("TELEGRAM_TOKEN")
    app_bot = ApplicationBuilder().token(TOKEN).build()
    app_bot.add_handler(MessageHandler(filters.ALL, handle_atlas_final))
    
    print("Professor Atlas 2.5 is now FULLY OPERATIONAL!")
    app_bot.run_polling()


