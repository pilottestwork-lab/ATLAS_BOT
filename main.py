import os
import logging
import io
import threading
from flask import Flask
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters
from PIL import Image
# المكتبة البديلة للمحاكاة (تأكد من تثبيتها)
from gemini_web_api import GeminiClient 

# 1. إعداد السجلات
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# 2. إعداد المفاتيح (من Render Environment Variables)
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
# هنا نضع الكوكي بدلاً من الـ API Key
GEMINI_COOKIE = os.getenv("GEMINI_COOKIE") 

# تهيئة "الجسر" (Bridge) باستخدام حسابك الشخصي
try:
    # نقوم بتمرير الكوكي للمحاكي
    client = GeminiClient(GEMINI_COOKIE)
    logging.info("تم تفعيل الجسر بنجاح باستخدام حسابك الشخصي!")
except Exception as e:
    logging.error(f"فشل الاتصال عبر الكوكيز: {e}")

# --- سيرفر Flask لإبقاء البوت حياً على Render ---
flask_app = Flask(__name__)
@flask_app.route('/')
def health_check():
    return "Professor Atlas Bridge is Alive!", 200

def run_flask():
    port = int(os.environ.get("PORT", 8000))
    flask_app.run(host='0.0.0.0', port=port)

# --- دوال البوت المعدلة ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("أهلاً بك يا دكتور! أنا البروفيسور أطلس (نسخة الجسر). أرسل لي أي سؤال أو صورة.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_prompt = ""
    
    # تحضير النص
    if update.message.text:
        user_prompt = update.message.text
    elif update.message.caption:
        user_prompt = update.message.caption
    
    # إذا كانت هناك صورة (المكتبات غير الرسمية أحياناً تواجه صعوبة في رفع الصور)
    # سنحاول معالجة النص أولاً لضمان عمل الجسر
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

    try:
        # إضافة تعليمات البروفيسور أطلس كبادئة (لأن الكوكيز لا تدعم System Instruction رسمياً)
        full_prompt = f"أنت البروفيسور أطلس، خبير أكاديمي طبي. أجب على السؤال التالي: {user_prompt}"
        
        # إرسال الطلب عبر الجسر
        response = client.ask(full_prompt)
        
        # الرد على المستخدم
        await update.message.reply_text(response.text + "\n\n🔗 https://t.me/atlas_medical")
        
    except Exception as e:
        logging.error(f"خطأ في الجسر: {e}")
        await update.message.reply_text(f"عذراً يا دكتور، الجسر يحتاج تحديث كوكيز أو حدث خطأ: {str(e)}")

# --- التشغيل الرئيسي ---
if __name__ == '__main__':
    if not TELEGRAM_TOKEN or not GEMINI_COOKIE:
        print("Error: TELEGRAM_TOKEN أو GEMINI_COOKIE مفقودة!")
    else:
        # تشغيل سيرفر الصحة
        threading.Thread(target=run_flask, daemon=True).start()
        
        # تشغيل البوت بنظام Polling
        application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
        
        application.add_handler(CommandHandler('start', start))
        application.add_handler(MessageHandler(filters.TEXT | filters.PHOTO | filters.Document.ALL, handle_message))
        
        print("Professor Atlas Bridge is running...")
        application.run_polling()
