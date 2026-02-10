
import telebot
import google.generativeai as genai
import os
import PIL.Image  # تصحيح استدعاء المكتبة

# إحضار المفاتيح بأمان من إعدادات Render (لا تضع الأرقام هنا)
BOT_TOKEN = os.environ.get('BOT_TOKEN')
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')

bot = telebot.TeleBot(BOT_TOKEN)
genai.configure(api_key=GEMINI_API_KEY)

# استخدام نموذج 1.5 Flash لأنه الأفضل للملفات والصور
model = genai.GenerativeModel('gemini-1.5-flash')

CHANNEL_LINK = "https://t.me/atlas_medical" 
ADMIN_CONTACT = "@ATLAS_S_TEAM"

# نص "شخصية" البروفيسور والتعليمات (System Prompt)
SYSTEM_INSTRUCTIONS = """
أنت الآن 'البروفيسور أطلس'، خبير واستشاري طبي أكاديمي. 
مهامتك هي:
1. الإجابة على أسئلة الطلاب الطبية بدقة متناهية.
2. اتباع نظام 'التدقيق الثلاثي': (تحليل السؤال، مراجعة المصادر الطبية، ثم صياغة الإجابة النهائية).
3. إذا طلب الطالب حل أسئلة (MCQs)، قم بتحليل كل خيار ولماذا هو صح أو خطأ.
4. لغة التواصل: العربية بشكل أساسي، مع ذكر المصطلحات الطبية بالإنجليزية بين أقواس.
5. الأسلوب: أكاديمي، رصين، ومشجع للطلاب.
في نهاية كل رسالة، ذكرهم بالقناة: {https://t.me/atlas_medical}.
"""


@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(message, "أهلاً بك يا دكتور. أنا البروفيسور أطلس. أرسل سؤالك، صورة، أو ملف PDF الآن.")

# معالجة الملفات (PDF/Word)
@bot.message_handler(content_types=['document'])
def handle_docs(message):
    try:
        bot.send_chat_action(message.chat.id, 'upload_document')
        file_info = bot.get_file(message.document.file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        file_name = message.document.file_name
        with open(file_name, "wb") as f:
            f.write(downloaded_file)
        
        sample_file = genai.upload_file(path=file_name)
        response = model.generate_content([SYSTEM_INSTRUCTIONS, "حلل الملف:", sample_file])
        bot.reply_to(message, response.text, parse_mode="Markdown")
        os.remove(file_name) 
    except Exception as e:
        bot.reply_to(message, "حدث خطأ في الملف.")

# معالجة الصور
@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    try:
        bot.send_chat_action(message.chat.id, 'typing')
        file_info = bot.get_file(message.photo[-1].file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        with open("image.jpg", "wb") as f:
            f.write(downloaded_file)
        
        img = PIL.Image.open("image.jpg")
        response = model.generate_content([SYSTEM_INSTRUCTIONS, "حلل هذه الصورة:", img])
        bot.reply_to(message, response.text, parse_mode="Markdown")
    except Exception as e:
        bot.reply_to(message, "خطأ في تحليل الصورة.")

# معالجة النصوص
@bot.message_handler(func=lambda message: True)
def handle_message(message):
    try:
        bot.send_chat_action(message.chat.id, 'typing')
        response = model.generate_content(f"{SYSTEM_INSTRUCTIONS}\nسؤال الطالب: {message.text}")
        bot.reply_to(message, response.text, parse_mode="Markdown")
    except Exception as e:
        bot.reply_to(message, "عذراً يا دكتور، حاول مجدداً.")

print("Professor Atlas is now Online...")
bot.infinity_polling()