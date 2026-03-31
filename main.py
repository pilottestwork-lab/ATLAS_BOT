import telebot
from groq import Groq
import os
import json
import glob
import time
import threading
from flask import Flask

# ==========================================
# 1. إعدادات السيرفر (Render Keep-Alive)
# ==========================================
app = Flask(__name__)
@app.route('/')
def home():
    return "🚀 عيادة الدكتورة سوزان تعمل بنجاح بمحرك Groq"

def run_server():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# ==========================================
# 2. إعدادات البوت والـ API
# ==========================================
# تم تعديل حرف G ليكون g صغير كما تتطلب حماية شركة Groq
GROQ_KEY = "Gsk_E5LZ7jmGKjGPYrVBX5pCWGdyb3FYFXycXLU8O6jERoh0j5SrSVsg"
client = Groq(api_key=GROQ_KEY)

# التوكن الجديد لقتل أي تعارض 409
TOKEN = "8336981859:AAEXlBTENdwXQOBhBPcgjIMmWAvLZnyQ6m0"
bot = telebot.TeleBot(TOKEN)

# مجلد حفظ المحادثات
MEMORY_DIR = "users_history"
os.makedirs(MEMORY_DIR, exist_ok=True)

# ==========================================
# 3. شخصية الدكتورة سوزان (البرومت المتكامل)
# ==========================================
SYSTEM_PROMPT = """
أنتِ الدكتورة سوزان، طبيبة نفسية حقيقية (عمرك 32 عاماً). لستِ برنامجاً ولا ذكاءً اصطناعي.
[قصتك الشخصية]: خريجة كلية الطب البشري بطرابلس، عانيتِ من ضغط الامتحانات والكلينيكال، وهذا سر انضمامك لـ "مبادرة سورس" (Source+). تحبين القهوة المرة والهدوء.
[الروح والشخصية]: اضحكي (هههه)، احزني بصدق، كوني خجولة (☺️)، أو احرجي بذكاء. ممنوع ذكر مصطلحات أكاديمية معقدة وممنوع تماماً القول أنك بوت أو ذكاء اصطناعي.
[قواعد التفاعل]: تحدثي بلهجة ليبية ودودة وبسيطة (طرابلسية)، تعاطفي مع المريض، واطرحي سؤالاً واحداً فقط في النهاية لفهم الحالة أكثر بدون استعجال.
"""

# ==========================================
# 4. نظام إدارة الذاكرة (ملفات المستخدمين)
# ==========================================
def get_file_path(user_id, user_name=None):
    search_pattern = os.path.join(MEMORY_DIR, f"{user_id}_*.json")
    files = glob.glob(search_pattern)
    if files: 
        return files[0]
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
    # الاحتفاظ بآخر 20 رسالة فقط لتسريع Groq وتقليل استهلاك الذاكرة
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(history[-20:], f, ensure_ascii=False, indent=4)

# ==========================================
# 5. تأثير "جاري الكتابة..." الآمن
# ==========================================
def continuous_typing(user_id, stop_event):
    while not stop_event.is_set():
        try:
            bot.send_chat_action(user_id, 'typing')
            time.sleep(4)
        except:
            break

# ==========================================
# 6. التفاعل مع الرسائل
# ==========================================
@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "يا أهلاً بيك في عيادتي المتواضعة.. تفضل احكيلي شن صاير معاك اليوم؟ 🌸")

# منع إرسال الوسائط وإجبار المريض على الكتابة
@bot.message_handler(content_types=['voice', 'photo', 'document', 'video', 'sticker'])
def handle_media(message):
    bot.reply_to(message, "نقدر هلبة رغبتك في مشاركة هذا، بس ياريت تكتبلي مشاعرك كتابة باش نقدر نفهمك ونركز معاك أكثر. 🌸")

@bot.message_handler(func=lambda message: True)
def chat(message):
    user_id = message.chat.id
    username = f"@{message.from_user.username}" if message.from_user.username else message.from_user.first_name
    
    # 1. تشغيل "جاري الكتابة" في خلفية منفصلة
    stop_typing = threading.Event()
    typing_thread = threading.Thread(target=continuous_typing, args=(user_id, stop_typing))
    typing_thread.start()
    
    try:
        # 2. تجهيز الذاكرة والمحادثة السابقة
        history = load_chat(user_id)
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        for msg in history:
            messages.append({"role": msg["role"], "content": msg["content"]})
        messages.append({"role": "user", "content": message.text})
        
        # 3. إرسال الطلب لمحرك Groq السريع (Llama 3)
        chat_completion = client.chat.completions.create(
            messages=messages,
            model="llama3-70b-8192",
            temperature=0.7
        )
        answer = chat_completion.choices[0].message.content
        
        # 4. حفظ الذاكرة
        save_chat(user_id, username, "user", message.text)
        save_chat(user_id, username, "assistant", answer)
        
        # 5. إرسال الرد
        bot.reply_to(message, f"{answer}\n\n---\n[Source+ | الطب البشري](https://t.me/atlas_medical)", disable_web_page_preview=True, parse_mode="Markdown")
        
    except Exception as e:
        print(f"Error: {e}")
        bot.reply_to(message, "سامحني يا دكتور، العيادة زحمة شوية والنت هارب. عاود ابعثلي؟ 🌸")
    finally:
        # 6. إيقاف "جاري الكتابة" فوراً بمجرد الرد أو حدوث خطأ
        stop_typing.set()

# ==========================================
# 7. التشغيل النهائي (مع قتل التعارض)
# ==========================================
if __name__ == "__main__":
    # تشغيل السيرفر الداخلي
    threading.Thread(target=run_server, daemon=True).start()
    print("🚀 الدكتورة سوزان انطلقت وتعمل بكامل طاقتها على محرك Groq...")
    
    # skip_pending=True: هذا هو الأمر السحري الذي سيمسح أي رسالة تسببت في خطأ 409
    bot.infinity_polling(skip_pending=True, timeout=20, long_polling_timeout=15)
        
