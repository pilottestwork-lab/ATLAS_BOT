import telebot
import g4f
import os
import json
import glob
import time
import threading
from flask import Flask

# ==========================================
# 1. إعدادات السيرفر (لمنع البوت من النوم على Render)
# ==========================================
app = Flask(__name__)

@app.route('/')
def home():
    return "🚀 عيادة دكتورة سوزان تعمل بنجاح (مبادرة سورس)"

def run_server():
    # Render يعطينا بورت (Port) تلقائي، يجب أن نستخدمه
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# ==========================================
# 2. إعدادات البوت والذاكرة
# ==========================================
TOKEN = "8336981859:AAEXlBTENdwXQOBhBPcgjIMmWAvLZnyQ6m0"
bot = telebot.TeleBot(TOKEN)

MEMORY_DIR = "users_history"
os.makedirs(MEMORY_DIR, exist_ok=True)

# ==========================================
# 3. شخصية الدكتورة سوزان (البرومت المتكامل)
# ==========================================
SYSTEM_PROMPT = """
أنتِ الدكتورة سوزان، طبيبة نفسية حقيقية (عمرك 32 عاماً). لستِ برنامجاً ولا ذكاءً اصطناعي.
[قصتك الشخصية]: خريجة كلية الطب البشري بطرابلس، عانيتِ من ضغط الامتحانات والكلينيكال، وهذا سر انضمامك لـ "مبادرة سورس" (Source+). تحبين القهوة المرة والهدوء.
[الروح والشخصية]: اضحكي (هههه)، احزني بصدق، كوني خجولة (☺️)، أو احرجي بذكاء. ممنوع ذكر مصطلحات أكاديمية معقدة مثل (CBT، CBL، تقنيات) وممنوع تماماً القول أنك بوت.
[قواعد التفاعل]: تحدثي بلهجة ليبية ودودة وبسيطة، تعاطفي مع المريض، واطرحي سؤالاً واحداً فقط في نهاية رسالتك لفهم الحالة أكثر بدون استعجال.
"""

# ==========================================
# 4. نظام إدارة الملفات (بأسماء المستخدمين)
# ==========================================
def get_file_path(user_id, user_name=None):
    search_pattern = os.path.join(MEMORY_DIR, f"{user_id}_*.json")
    files = glob.glob(search_pattern)
    if files: 
        return files[0]
    # تنظيف الاسم من الرموز المزعجة
    clean_name = str(user_name).replace("/", "").replace("\\", "").replace(" ", "_") if user_name else "User"
    return os.path.join(MEMORY_DIR, f"{user_id}_{clean_name}.json")

def load_chat(user_id):
    file_path = get_file_path(user_id)
    if os.path.exists(file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return []
    return []

def save_chat(user_id, user_name, role, content):
    file_path = get_file_path(user_id, user_name)
    history = load_chat(user_id)
    history.append({"role": role, "content": content})
    # نحتفظ بآخر 30 رسالة فقط لكي لا نستهلك ذاكرة الذكاء الاصطناعي ويصبح بطيئاً
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(history[-30:], f, ensure_ascii=False, indent=4)

# ==========================================
# 5. محرك الذكاء الاصطناعي (مضاد للانهيار 404)
# ==========================================
def get_suzan_ai_response(user_id, user_name, user_text):
    history = load_chat(user_id)
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    
    for msg in history:
        messages.append({"role": msg["role"], "content": msg["content"]})
    messages.append({"role": "user", "content": user_text})

    # قائمة بأكثر المزودات استقراراً حالياً
    providers = [
        g4f.Provider.BlackboxPro,
        g4f.Provider.ChatGptEs,
        g4f.Provider.DarkAI,
        g4f.Provider.Liaobots
    ]

    for provider in providers:
        try:
            response = g4f.ChatCompletion.create(
                model="gpt-4o", 
                messages=messages,
                provider=provider,
                stream=False
            )
            # التحقق من أن الرد ليس فارغاً
            if response and len(str(response)) > 5:
                res_text = str(response).strip()
                save_chat(user_id, user_name, "user", user_text)
                save_chat(user_id, user_name, "assistant", res_text)
                return res_text
        except Exception as e:
            # إذا فشل مزود، ننتقل للذي بعده بصمت
            continue 

    return "سامحني يا دكتور، العيادة اليوم زحمة والنت ضعيف شوية. عاود ابعثلي؟ 🌸"

# ==========================================
# 6. تأثير "جاري الكتابة..." المستمر والذكي
# ==========================================
def continuous_typing(user_id, stop_event):
    while not stop_event.is_set():
        try:
            bot.send_chat_action(user_id, 'typing')
            time.sleep(4)
        except:
            break

# ==========================================
# 7. التفاعل مع الرسائل (النصوص والوسائط)
# ==========================================
@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "يا أهلاً بيك في عيادتي المتواضعة.. تفضل احكيلي شن صاير معاك اليوم؟ 🌸")

# منع المريض من إرسال صور أو صوتيات وإجباره على الكتابة
@bot.message_handler(content_types=['voice', 'photo', 'document', 'video', 'sticker'])
def handle_media(message):
    bot.reply_to(message, "نقدر هلبة رغبتك في مشاركة هذا، بس ياريت تكتبلي مشاعرك كتابة باش نقدر نفهمك ونركز معاك أكثر. 🌸")

@bot.message_handler(func=lambda message: True)
def chat(message):
    user_id = message.chat.id
    # التقاط يوزرنيم أو الاسم الأول لبرمجة اسم الملف
    username = f"@{message.from_user.username}" if message.from_user.username else message.from_user.first_name
    
    # تشغيل تأثير "جاري الكتابة" في خلفية منفصلة لكي لا يوقف الكود
    stop_typing = threading.Event()
    typing_thread = threading.Thread(target=continuous_typing, args=(user_id, stop_typing))
    typing_thread.start()
    
    try:
        # استدعاء الرد
        answer = get_suzan_ai_response(user_id, username, message.text)
        # إرسال الرد مع حقوق مبادرة سورس
        bot.reply_to(message, f"{answer}\n\n---\n[Source+ | الطب البشري](https://t.me/atlas_medical)", disable_web_page_preview=True, parse_mode="Markdown")
    finally:
        # إيقاف تأثير "جاري الكتابة" فوراً بمجرد جاهزية الرد
        stop_typing.set()

# ==========================================
# التشغيل النهائي
# ==========================================
if __name__ == "__main__":
    # 1. تشغيل سيرفر الويب في الخلفية (Daemon) ليتصل به Render
    threading.Thread(target=run_server, daemon=True).start()
    
    # 2. تشغيل البوت مع إعدادات تمنع فصل الاتصال (Timeout)
    print("🚀 الدكتورة سوزان انطلقت وتعمل الآن بكامل طاقتها...")
    bot.infinity_polling(timeout=20, long_polling_timeout=15)
    
