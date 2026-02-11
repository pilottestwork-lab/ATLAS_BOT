import os
import threading
from flask import Flask
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters
from openai import OpenAI
from PIL import Image
import io
import base64

# 1. إعداد سيرفر صغير لبقاء البوت حياً على Render
app = Flask(__name__)
@app.route('/')
def home():
    return "Professor Atlas (OpenRouter Vision) is Online!", 200

def run_flask():
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port)

# 2. إعداد الاتصال بـ OpenRouter (متوافق مع OpenAI API)
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY")
)

# 3. وظيفة الحصول على رد من الذكاء الاصطناعي (تدعم النصوص والصور وملفات PDF)
def get_ai_response(content_parts):
    try:
        # نستخدم موديل يدعم الرؤية والنصوص ومجاني في OpenRouter
        # هذا الموديل هو الأفضل والأكثر استقراراً حالياً لدعم الرؤية والنصوص مجاناً
        model_name = "google/gemini-flash-1.5-8b:free" 
        
        # بناء الرسالة للموديل
        messages_payload = [{"role": "user", "content": content_parts}]

        response = client.chat.completions.create(
            model=model_name,
            messages=messages_payload
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"عذراً يا دكتور، حدث خطأ في محرك الذكاء الاصطناعي: {str(e)}"

# 4. معالجة رسائل تليجرام (صور، نصوص، ملفات PDF)
async def handle_atlas_full(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    status_msg = await msg.reply_text("⏳ البروفيسور أطلس يراجع الحالة (صور وملفات)...")

    content_for_ai = []
    user_prompt = msg.caption or msg.text or "حلل هذا المحتوى طبياً"

    # إضافة النص أولاً
    content_for_ai.append({"type": "text", "text": user_prompt})

    try:
        # أ. معالجة الصور
        if msg.photo:
            file = await msg.photo[-1].get_file()
            img_bytes = await file.download_as_bytearray()
            # تحويل الصورة إلى Base64 (مطلوب من OpenRouter للموديلات البصرية)
            base64_image = base64.b64encode(img_bytes).decode('utf-8')
            content_for_ai.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}
            })
        
        # ب. معالجة ملفات PDF
        elif msg.document and msg.document.mime_type == 'application/pdf':
            doc = await msg.document.get_file()
            doc_bytes = await doc.download_as_bytearray()
            # تحويل الـ PDF إلى Base64
            base64_pdf = base64.b64encode(doc_bytes).decode('utf-8')
            content_for_ai.append({
                "type": "image_url", # OpenRouter يتعامل مع الـ PDF كنوع من أنواع الصورة للموديلات البصرية
                "image_url": {"url": f"data:application/pdf;base64,{base64_pdf}"}
            })

        # ج. معالجة النصوص (إذا لم يكن هناك صور أو ملفات)
        # هذا الجزء سيكون مغطى بالـ msg.caption أو msg.text بالفعل
        
        response_text = get_ai_response(content_for_ai)
        
        # إرسال الإجابة (وتقسيمها إذا كانت طويلة)
        if len(response_text) > 4000:
            for i in range(0, len(response_text), 4000):
                await msg.reply_text(response_text[i:i+4000])
        else:
            await msg.reply_text(response_text)
            
    except Exception as e:
        await msg.reply_text(f"عذراً يا دكتور، حدث خطأ أثناء المعالجة: {str(e)}")
    finally:
        await status_msg.delete()

if __name__ == '__main__':
    # تشغيل Flask في الخلفية للحفاظ على السيرفر نشطاً
    threading.Thread(target=run_flask, daemon=True).start()
    
    # إعداد وتشغيل بوت تليجرام
    TOKEN = os.getenv("TELEGRAM_TOKEN")
    if not TOKEN:
        print("خطأ: لم يتم العثور على TELEGRAM_TOKEN في متغيرات البيئة.")
    else:
        application = ApplicationBuilder().token(TOKEN).build()
        # يستقبل كل أنواع الرسائل (نصوص، صور، ملفات)
        application.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle_atlas_full))
        
        print("Professor Atlas (OpenRouter Vision) is starting...")
        application.run_polling()


