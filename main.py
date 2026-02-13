import os
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters
from Gemini import Gemini  # المكتبة التي يتم تثبيتها عبر الرابط في requirements

# إعداد التنبيهات
logging.basicConfig(level=logging.INFO)

# --- الإعدادات ---
# تأكد من وضع التوكن الخاص بك في متغيرات بيئة Render كـ TELEGRAM_TOKEN
TOKEN = "8336981859:AAFZVS-OFQT8CGfwTvROsMGaSg4VQlY1fHo"
# تأكد من وضع الـ Cookie في متغيرات بيئة Render كـ GEMINI_COOKIE
COOKIE_VALUE = os.getenv("g.a0006gimZfq-ZxSbv2N3sneOJbn6eEwfD2Sj25N2GPNa34LyLt7isXQy9FBjSWoxN0_-NHgXCgACgYKAWgSARUSFQHGX2MiqbNlitbc0yPmNyOHw3FidhoVAUF8yKrz3iQUMQ3OdNwp0604-Cty0076")

# تهيئة الجسر باستخدام الكوكيز
try:
    # نقوم بتمرير الكوكي بصيغة قاموس (Dictionary)
    client = Gemini(cookies={"__Secure-1PSID": COOKIE_VALUE})
    print("تم الاتصال بنجاح عبر الكوكيز")
except Exception as e:
    print(f"فشل في تهيئة الجسر: {e}")

async def handle_response(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    
    try:
        # استخدام موديل مستقر لتجنب خطأ 400
        # نستخدم gemini-2.5-flash لأنه الأسرع والأكثر استقراراً مع الكوكيز
        response = client.generate_content(user_text)
        await update.message.reply_text(response.text)
    except Exception as e:
        # في حال ظهر خطأ name format مجدداً، سنعرف السبب من هنا
        await update.message.reply_text(f"عذراً، حدث خطأ في معالجة الطلب: {str(e)}")

if __name__ == '__main__':
    application = ApplicationBuilder().token(TOKEN).build()
    
    # معالج الرسائل النصية
    message_handler = MessageHandler(filters.TEXT & (~filters.COMMAND), handle_response)
    application.add_handler(message_handler)
    
    print("البوت ينبض بالحياة...")
    application.run_polling()
