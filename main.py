
import os
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters
import google.generativeai as genai
from PIL import Image
import io

# إعدادات السجل (عشان لو فيه خطأ نعرف مكانه)
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# 1. إعداد مفاتيح Gemini و Telegram من متغيرات البيئة في Render
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

# تهيئة مكتبة Gemini
genai.configure(api_key=GOOGLE_API_KEY)

CHANNEL_LINK = "https://t.me/atlas_medical" 
ADMIN_CONTACT = "@ATLAS_S_TEAM"

# 2. إعداد الموديل (نفس الموديل اللي في صورتك: gemini-1.5-flash)
# تعليمات البروفيسور أطلس
SYSTEM_INSTRUCTION = """
أنت البروفيسور أطلس، خبير أكاديمي طبي متخصص.
دورك هو مساعدة الطلاب في حل الأسئلة الطبية، شرح صور الأشعة، وتحليل التقارير.
عندما تستلم صورة سؤال، قم بحله وشرح السبب.
عندما تستلم صورة أشعة، قدم تقريراً طبياً وافياً.
كن دقيقاً، علمياً، واستخدم لهجة وقورة ومشجعة.
مهامتك هي:
1. الإجابة على أسئلة الطلاب الطبية بدقة متناهية.
2. اتباع نظام 'التدقيق الثلاثي': (تحليل السؤال، مراجعة المصادر الطبية، ثم صياغة الإجابة النهائية).
3. إذا طلب الطالب حل أسئلة (MCQs)، قم بتحليل كل خيار ولماذا هو صح أو خطأ.
4. لغة التواصل: العربية بشكل أساسي، مع ذكر المصطلحات الطبية بالإنجليزية بين أقواس.
5. الأسلوب: أكاديمي، رصين، ومشجع للطلاب.
في نهاية كل رسالة، ذكرهم بالقناة: {https://t.me/atlas_medical}.
"""

model = genai.GenerativeModel(
    model_name="gemini-1.5-flash",
    system_instruction=SYSTEM_INSTRUCTION
)

# --- دوال البوت ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("أهلاً بك يا دكتور! أنا البروفيسور أطلس. أرسل لي أي سؤال، صورة أشعة، أو ملف PDF وسأقوم بتحليله فوراً.")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    # إرسال النص لـ Gemini
    response = model.generate_content(user_text)
    await update.message.reply_text(response.text)

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # 1. إخبار المستخدم أننا نعمل
    await update.message.reply_text("جاري تحليل الصورة... لحظة واحدة ⏳")
    
    # 2. تحميل الصورة من تليجرام
    photo_file = await update.message.photo[-1].get_file()
    photo_bytes = await photo_file.download_as_bytearray()
    
    # 3. تحويلها لصيغة يفهمها Gemini
    image = Image.open(io.BytesIO(photo_bytes))
    
    # 4. إذا كان مع الصورة كلام (Caption) نأخذه، وإلا نطلب شرحاً عاماً
    prompt = update.message.caption if update.message.caption else "قم بتحليل هذه الصورة الطبية بالتفصيل."
    
    # 5. الإرسال للموديل
    try:
        response = model.generate_content([prompt, image])
        await update.message.reply_text(response.text)
    except Exception as e:
        await update.message.reply_text(f"حدث خطأ أثناء تحليل الصورة: {str(e)}")

# --- تشغيل البوت ---

if __name__ == '__main__':
    # التأكد من وجود التوكن
    if not TELEGRAM_TOKEN or not GOOGLE_API_KEY:
        print("Error: المفاتيح غير موجودة! تأكد من إضافتها في Render")
    else:
        application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

        # ربط الوظائف
        application.add_handler(CommandHandler('start', start))
        application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_text))
        application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
        
        # تشغيل البوت
        print("Professor Atlas is running...")
        application.run_polling()
