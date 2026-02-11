import os
import threading
import requests
from flask import Flask
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters

# --- 1. الإعدادات والمفاتيح ---
# مفتاح Groq وتوكن التلجرام يتم جلبهم من إعدادات Render للحماية
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

# --- 2. إعدادات السيرفر والذاكرة ---
app = Flask(__name__)
user_memory = {} # الذاكرة: هنا بنخزن المحادثات لكل مستخدم

@app.route('/')
def home():
    return "Professor Atlas (DeepSeek Edition) is Online!", 200

def run_flask():
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port)

# --- 3. وظيفة العقل الذكي (DeepSeek via Groq) ---
def get_deepseek_response(user_id, user_text):
    # 1. تجهيز الذاكرة للمستخدم الجديد
    if user_id not in user_memory:
        user_memory[user_id] = [
            {"role": "system", "content": "أنت مساعد ذكي ومفيد."}
        ]
    
    # 2. إضافة رسالة المستخدم الحالية للذاكرة
    user_memory[user_id].append({"role": "user", "content": user_text})

    # 3. إعداد الاتصال بـ Groq
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    
    # نبعث الذاكرة كاملة عشان يفهم السياق
    data = {
        "model": "deepseek-r1-distill-llama-70b", # الموديل السريع والمجاني
        "messages": user_memory[user_id]
    }

    try:
        response = requests.post(url, headers=headers, json=data)
        
        if response.status_code == 200:
            bot_reply = response.json()['choices'][0]['message']['content']
            
            # 4. حفظ رد البوت في الذاكرة للمرة الجاية
            user_memory[user_id].append({"role": "assistant", "content": bot_reply})
            
            # تنظيف الذاكرة لو كبرت هلبا (نحتفظ بآخر 10 رسائل بس عشان السرعة)
            if len(user_memory[user_id]) > 20:
                user_memory[user_id] = user_memory[user_id][-10:]
                
            return bot_reply
        else:
            return f"خطأ من المصدر: {response.status_code}"
            
    except Exception as e:
        return f"حدث خطأ في الاتصال: {str(e)}"

# --- 4. معالجة رسائل تليجرام ---
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    user_id = msg.from_user.id
    
    # نتأكد إن الرسالة نصية (لأن ديب سيك هذا ما يشوفش صور)
    if not msg.text:
        await msg.reply_text("عذراً، أنا حالياً أتعامل مع النصوص والأسئلة المكتوبة فقط 📝")
        return

    # إظهار "جاري الكتابة..."
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

    # جلب الرد
    response_text = get_deepseek_response(user_id, msg.text)
    
    # الرد على المستخدم
    await msg.reply_text(response_text)

# --- 5. التشغيل النهائي ---
if __name__ == '__main__':
    # تشغيل سيرفر Flask للبقاء حياً
    threading.Thread(target=run_flask, daemon=True).start()
    
    # تشغيل البوت
    app_bot = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app_bot.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    
    print("Professor Atlas (DeepSeek) is ready!")
    app_bot.run_polling()

