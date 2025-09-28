import json
import requests
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    ContextTypes, ConversationHandler, filters
)

# =========================
# حالات الـ Conversation
# =========================
NUMBER, PASSWORD, SERIAL = range(3)

# =========================
# رسالة البداية (مستبدلة كما طلبت)
# =========================
START_TEXT = """اهلا بيك في بوت 2000 ميجا اورانج

شرح طريقة الاستخدام:

1. أرسل رقم هاتفك

2. أرسل رمز حساب ماي أورانج

3. أرسل السيريال (اتصل بالكود ده واختار سيريال هيطلع معاك #119#) 💸💰

يلا نبداء بسم الله ...دخل رقم تليفونك:"""

# =========================
# ابدأ البوت
# =========================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(START_TEXT)
    return NUMBER

# =========================
# استقبال الرقم
# =========================
async def get_number(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['number'] = update.message.text
    await update.message.reply_text("تمام، دلوقتي ادخل رمز حساب ماي أورانج:")
    return PASSWORD

# =========================
# استقبال الباسورد
# =========================
async def get_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['password'] = update.message.text
    await update.message.reply_text("تمام، دلوقتي ادخل رقم السيريال (اتصل #119# للحصول عليه):")
    return SERIAL

# =========================
# استقبال الـ Serial وتنفيذ الريكوست
# =========================
async def get_serial(update: Update, context: ContextTypes.DEFAULT_TYPE):
    serial = update.message.text
    number = context.user_data.get('number')
    password = context.user_data.get('password')

    await update.message.reply_text("⏳ جاري التحقق وإضافة 2000 ميجا...")

    # تسجيل الدخول
    url_login = "https://services.orange.eg/SignIn.svc/SignInUser"
    payload_login = {
        "appVersion": "9.3.0",
        "channel": {"ChannelName": "MobinilAndMe", "Password": "ig3yh*mk5l42@oj7QAR8yF"},
        "dialNumber": number,
        "isAndroid": True,
        "lang": "ar",
        "password": password,
    }
    headers_login = {
        'User-Agent': "okhttp/4.10.0",
        'Connection': "Keep-Alive",
        'Accept-Encoding': "gzip",
        'Content-Type': "application/json; charset=UTF-8"
    }

    try:
        response = requests.post(url_login, data=json.dumps(payload_login), headers=headers_login, timeout=20)
        response.raise_for_status()
        data = response.json()
        tok = data['SignInUserResult']['AccessToken']
    except Exception:
        await update.message.reply_text("❌ تأكد من الرقم أو رمز الحساب")
        return ConversationHandler.END

    # التحقق من الـ Serial
    url_check = "https://services.orange.eg/APIs/Profile/api/UserSubDials/CheckSIMSerial"
    payload_check = {
        "ChannelName": "MobinilAndMe",
        "ChannelPassword": "ig3yh*mk5l42@oj7QAR8yF",
        "Home4gDial": number,
        "Home4gSimSerial": serial,
        "Language": "ar",
        "VoiceDial": number,
    }
    headers_check = {
        'User-Agent': "okhttp/4.10.0",
        'Connection': "Keep-Alive",
        'Accept-Encoding': "gzip",
        'Content-Type': "application/json",
        'IsAndroid': "true",
        'OsVersion': "13",
        'AppVersion': "9.4.0",
        'isEasyLogin': "true",
        'Token': tok,
    }

    try:
        response = requests.post(url_check, data=json.dumps(payload_check), headers=headers_check, timeout=20)
        result = response.json()
    except Exception as e:
        await update.message.reply_text(f"❌ حدث خطأ في الاتصال: {e}")
        return ConversationHandler.END

    if result.get('ErrorDescription') == "Success":
        await update.message.reply_text("✅ تم إضافة 2000 ميجا بنجاح!")
    else:
        await update.message.reply_text(f"❌ حدث خطأ: {result.get('ErrorDescription')}")

    return ConversationHandler.END

# =========================
# أمر إلغاء
# =========================
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("تم إلغاء العملية 🚫")
    return ConversationHandler.END

# =========================
# تشغيل البوت (استبدل BOT_TOKEN بالتوكن الخاص بك)
# =========================
BOT_TOKEN = "8069840277:AAFdMPbn8A_BfiinQ7oJAksenF9aGOvwoAQ"

app = ApplicationBuilder().token(BOT_TOKEN).build()

conv_handler = ConversationHandler(
    entry_points=[CommandHandler('start', start)],
    states={
        NUMBER: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_number)],
        PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_password)],
        SERIAL: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_serial)],
    },
    fallbacks=[CommandHandler('cancel', cancel)]
)

app.add_handler(conv_handler)

if __name__ == '__main__':
    print("البوت شغال...")
    app.run_polling()
