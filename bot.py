import json
import os
import requests
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters,
    CallbackQueryHandler, ConversationHandler, ContextTypes
)

# --------------------------------
# توكن البوت
# --------------------------------
BOT_TOKEN = "8016337460:AAFQePlgf-FMu-QOXJEBajSGYhTVE_0gXkQ"

# ملف لحفظ بيانات المستخدمين
DATA_FILE = "users.json"

# تحميل بيانات المستخدمين من ملف
if os.path.exists(DATA_FILE):
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        user_data = json.load(f)
else:
    user_data = {}

# حفظ البيانات في ملف
def save_data():
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(user_data, f, ensure_ascii=False, indent=4)


# --------------------------------
# دوال مساعدة لعرض الفليكس
# --------------------------------
def format_flex_amount(amount):
    if amount is None:
        return "غير متاح"
    try:
        val = float(amount)
        if val == 0.0:
            return "أكبر من 30 ألف فليكس"
        if val.is_integer():
            return f"{int(val)} فليكس"
        return f"{val} فليكس"
    except Exception:
        return f"{amount} فليكس"


# --------------------------------
# دوال الاتصال بحساب Vodafone لجلب الفليكس والرصيد
# --------------------------------
def vodafone_login_get_token(number: str, password: str):
    token_url = "https://mobile.vodafone.com.eg/auth/realms/vf-realm/protocol/openid-connect/token"
    payload = {
        'grant_type': "password",
        'username': number,
        'password': password,
        'client_secret': "95fd95fb-7489-4958-8ae6-d31a525cd20a",
        'client_id': "ana-vodafone-app"
    }
    headers = {
        'User-Agent': "okhttp/4.11.0",
        'Accept': "application/json, text/plain, */*",
        'Accept-Encoding': "gzip",
        'silentLogin': "false",
        'x-agent-operatingsystem': "13",
        'clientId': "AnaVodafoneAndroid",
        'Accept-Language': "ar",
        'x-agent-device': "Xiaomi 21061119AG",
        'x-agent-version': "2024.12.1",
        'x-agent-build': "946",
        'digitalId': "28RI9U7IINOOB"
    }

    try:
        r = requests.post(token_url, data=payload, headers=headers, timeout=15)
        r.raise_for_status()
        tok = r.json().get('access_token')
        return tok
    except Exception:
        return None


def get_flex_and_balance(number: str, token: str):
    flex_amount = None
    real_balance = None

    flex_url = f"https://web.vodafone.com.eg/services/dxl/usage/usageConsumptionReport?bucket.product.publicIdentifier={number}&@type=aggregated"
    flex_headers = {
        'User-Agent': "Mozilla/5.0",
        'Accept': "application/json",
        'Accept-Encoding': "gzip, deflate, br",
        'Authorization': f"Bearer {token}",
        'Accept-Language': "AR",
        'msisdn': number,
        'Content-Type': "application/json"
    }

    try:
        flex_r = requests.get(flex_url, headers=flex_headers, timeout=15)
        flex_r.raise_for_status()
        data = flex_r.json()
        iterable = [data] if isinstance(data, dict) else (data if isinstance(data, list) else [])

        for item in iterable:
            if isinstance(item, dict) and "bucket" in item:
                for bucket in item.get("bucket", []):
                    if bucket.get("usageType") == "limit":
                        for balance in bucket.get("bucketBalance", []):
                            if balance.get("@type") == "Remaining":
                                flex_amount = balance["remainingValue"].get("amount")
                                break
                    if flex_amount is not None:
                        break
            if flex_amount is not None:
                break
    except Exception:
        flex_amount = None

    balance_url = "https://web.vodafone.com.eg/services/dxl/financial/financials/balance"
    try:
        bal_r = requests.get(balance_url, headers=flex_headers, timeout=15)
        bal_r.raise_for_status()
        balance_data = bal_r.json()
        possible = balance_data.get("balance") or balance_data.get("balances") or {}
        if isinstance(possible, dict):
            real_balance = possible.get("monetaryBalance", {}).get("amount") or possible.get("value") or possible.get("amount")
        else:
            real_balance = None
    except Exception:
        real_balance = None

    return flex_amount, real_balance


async def real_check_and_update(user_id: str, number: str, password: str):
    token = vodafone_login_get_token(number, password)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if not token:
        for item in user_data.get(user_id, []):
            if item["number"] == number:
                item["balance"] = "فشل تسجيل الدخول"
                item["last_update"] = now
                save_data()
                return False, None, None

    flex_amount, real_balance = get_flex_and_balance(number, token)

    flex_text = format_flex_amount(flex_amount)
    balance_text = f"{real_balance} جنيه" if real_balance is not None else "غير متاح"

    for item in user_data.get(user_id, []):
        if item["number"] == number:
            item["balance"] = flex_text
            item["money_balance"] = balance_text
            item["last_update"] = now
            save_data()
            return True, flex_amount, real_balance

    return False, flex_amount, real_balance


# --------------------------------
# القوائم
# --------------------------------
def main_menu_keyboard():
    keyboard = [
        [InlineKeyboardButton("📱 عرض جميع الأرقام", callback_data="show_numbers")],
        [InlineKeyboardButton("➕ إضافة رقم جديد", callback_data="add_number")],
        [InlineKeyboardButton("🔄 تحديث جميع الأرقام", callback_data="update_all")],
        [InlineKeyboardButton("🗑️ حذف جميع البيانات", callback_data="delete_all")],
    ]
    return InlineKeyboardMarkup(keyboard)


def back_menu_keyboard():
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("⬅️ العودة للقائمة الرئيسية", callback_data="main_menu")]]
    )


# --------------------------------
# حالات ConversationHandler
# --------------------------------
SAVE_NUMBER, SAVE_PASSWORD = range(2)


# --------------------------------
# القائمة الرئيسية
# --------------------------------
async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, edit=False):
    text = (
        "🎉 بوت فحص رصيد فليكسات فودافون\n\n"
        "🔹 يمكنك إضافة أكثر من رقم ومراقبة أرصدتها\n"
        "🔹 فحص رصيد رقم محدد\n"
        "🔹 تحديث جميع الأرصدة دفعة واحدة\n\n"
        "اختر من القائمة أدناه:"
    )

    if edit:
        query = update.callback_query
        await query.answer()
        await query.edit_message_text(text, reply_markup=main_menu_keyboard())
    else:
        await update.message.reply_text(text, reply_markup=main_menu_keyboard())


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await show_main_menu(update, context, edit=False)


async def main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await show_main_menu(update, context, edit=True)


# --------------------------------
# عرض الأرقام والفحص المباشر
# --------------------------------
async def show_numbers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = str(query.from_user.id)
    numbers = user_data.get(user_id, [])

    if not numbers:
        await query.edit_message_text("⚠️ لا توجد أرقام محفوظة.", reply_markup=back_menu_keyboard())
        return

    text = "📱 جميع الأرقام المحفوظة:\n\n"
    keyboard = []
    for idx, item in enumerate(numbers, start=1):
        text += (
            f"{idx}. 📱 <b>{item['number']}</b>\n"
            f"💎 الفليكسات: {item.get('balance','غير محدد')}\n"
            f"💰 الرصيد: {item.get('money_balance','-')}\n"
            f"⏰ آخر تحديث: {item.get('last_update','-')}\n\n"
        )
        keyboard.append([
            InlineKeyboardButton(f"📊 فحص {item['number']}", callback_data=f"check_{item['number']}"),
            InlineKeyboardButton("🗑️ حذف", callback_data=f"delete_{item['number']}")
        ])
    keyboard.append([InlineKeyboardButton("⬅️ العودة للقائمة الرئيسية", callback_data="main_menu")])

    await query.edit_message_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))


async def check_number(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    number = query.data.split("_", 1)[1]
    user_id = str(query.from_user.id)

    item = next((x for x in user_data.get(user_id, []) if x["number"] == number), None)
    if not item:
        await query.edit_message_text("❌ الرقم غير موجود.", reply_markup=back_menu_keyboard())
        return

    await query.edit_message_text(f"⏳ جاري فحص الرقم {number} ...")

    ok, flex_amount, real_balance = await real_check_and_update(user_id, number, item.get("password", ""))
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if not ok:
        result = f"❌ فشل تسجيل الدخول أو الحصول على بيانات للرقم <b>{number}</b>.\n⏰ آخر محاولة: {now}"
    else:
        flex_text = format_flex_amount(flex_amount)
        balance_text = f"{real_balance} جنيه" if real_balance is not None else "غير متاح"
        result = (
            f"📊 نتائج الفحص للرقم <b>{number}</b>\n\n"
            f"💎 الفليكسات: {flex_text}\n"
            f"💰 الرصيد: {balance_text}\n"
            f"⏰ آخر تحديث: {now}"
        )

    await query.edit_message_text(result, parse_mode="HTML", reply_markup=back_menu_keyboard())


# --------------------------------
# إضافة رقم جديد
# --------------------------------
async def add_number(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("📱 من فضلك أرسل الرقم الجديد (مثال: 01XXXXXXXXX):")
    return SAVE_NUMBER


async def save_number(update: Update, context: ContextTypes.DEFAULT_TYPE):
    number = update.message.text.strip()
    if not (number.isdigit() and len(number) == 11 and number.startswith("01")):
        await update.message.reply_text("❌ الرقم غير صالح، ارسله بنفس الصيغة (01...). حاول تاني:")
        return SAVE_NUMBER

    context.user_data["new_number"] = number
    await update.message.reply_text("🔑 الآن أرسل كلمة السر (الباسورد) لهذا الرقم:")
    return SAVE_PASSWORD


async def save_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    password = update.message.text.strip()
    number = context.user_data.get("new_number")
    user_id = str(update.effective_user.id)

    if user_id not in user_data:
        user_data[user_id] = []

    exists = any(x["number"] == number for x in user_data[user_id])
    if exists:
        await update.message.reply_text("⚠️ الرقم موجود بالفعل في قائمتك.", reply_markup=back_menu_keyboard())
        return ConversationHandler.END

    user_data[user_id].append({
        "number": number,
        "password": password,
        "balance": "غير محدد",
        "money_balance": "-",
        "last_update": "لم يتم التحديث"
    })
    save_data()

    await update.message.reply_text(f"⏳ جاري تسجيل الدخول وفحص الرصيد للرقم {number} ...")

    ok, flex_amount, real_balance = await real_check_and_update(user_id, number, password)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if not ok:
        result = f"❌ فشل تسجيل الدخول أو الحصول على بيانات للرقم <b>{number}</b>.\n⏰ آخر محاولة: {now}"
    else:
        flex_text = format_flex_amount(flex_amount)
        balance_text = f"{real_balance} جنيه" if real_balance is not None else "غير متاح"
        result = (
            f"📊 نتائج الفحص للرقم <b>{number}</b>\n\n"
            f"💎 الفليكسات: {flex_text}\n"
            f"💰 الرصيد: {balance_text}\n"
            f"⏰ آخر تحديث: {now}"
        )

    await update.message.reply_text(result, parse_mode="HTML", reply_markup=back_menu_keyboard())
    return ConversationHandler.END


# --------------------------------
# تحديث رقم واحد
# --------------------------------
async def update_one(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    number = query.data.split("_", 1)[1]
    user_id = str(query.from_user.id)

    item = next((x for x in user_data.get(user_id, []) if x["number"] == number), None)
    if not item:
        await query.edit_message_text("❌ الرقم غير موجود.", reply_markup=back_menu_keyboard())
        return

    token = vodafone_login_get_token(item["number"], item.get("password", ""))
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if not token:
        item["balance"] = "فشل تسجيل الدخول"
        item["last_update"] = now
        save_data()
        await query.edit_message_text(f"❌ فشل تسجيل الدخول للرقم {number}.", reply_markup=back_menu_keyboard())
    else:
        flex_amount, real_balance = get_flex_and_balance(item["number"], token)
        item["balance"] = format_flex_amount(flex_amount)
        item["money_balance"] = f"{real_balance} جنيه" if real_balance is not None else "غير متاح"
        item["last_update"] = now
        save_data()
        await query.edit_message_text(f"✅ تم تحديث الرصيد للرقم {number}.", reply_markup=back_menu_keyboard())


# --------------------------------
# تحديث كل الأرقام
# --------------------------------
async def update_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = str(query.from_user.id)

    if user_id not in user_data or not user_data[user_id]:
        await query.edit_message_text("⚠️ لا توجد أرقام لتحديثها.", reply_markup=back_menu_keyboard())
        return

    await query.edit_message_text("⏳ جاري تحديث جميع الأرقام، انتظر لحظة...", reply_markup=back_menu_keyboard())

    for item in user_data[user_id]:
        token = vodafone_login_get_token(item["number"], item.get("password", ""))
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if not token:
            item["balance"] = "فشل تسجيل الدخول"
            item["last_update"] = now
        else:
            flex_amount, real_balance = get_flex_and_balance(item["number"], token)
            item["balance"] = format_flex_amount(flex_amount)
            item["money_balance"] = f"{real_balance} جنيه" if real_balance is not None else "غير متاح"
            item["last_update"] = now
        save_data()

    await query.edit_message_text("✅ تم تحديث جميع الأرقام بنجاح.", reply_markup=back_menu_keyboard())


# --------------------------------
# حذف رقم
# --------------------------------
async def delete_one(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    number = query.data.split("_", 1)[1]
    user_id = str(query.from_user.id)
    before = len(user_data.get(user_id, []))
    user_data[user_id] = [n for n in user_data.get(user_id, []) if n["number"] != number]
    save_data()
    after = len(user_data.get(user_id, []))

    if before == after:
        await query.edit_message_text(f"❌ لم أجد الرقم {number}.", reply_markup=back_menu_keyboard())
    else:
        await query.edit_message_text(f"🗑️ تم حذف الرقم {number}.", reply_markup=back_menu_keyboard())


# --------------------------------
# حذف كل البيانات
# --------------------------------
async def delete_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = str(query.from_user.id)
    user_data[user_id] = []
    save_data()
    await query.edit_message_text("🗑️ تم حذف جميع البيانات بنجاح.", reply_markup=back_menu_keyboard())


# --------------------------------
# تشغيل البوت
# --------------------------------
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(add_number, pattern="add_number")],
        states={
            SAVE_NUMBER: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_number)],
            SAVE_PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_password)],
        },
        fallbacks=[],
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(conv_handler)

    app.add_handler(CallbackQueryHandler(main_menu, pattern="main_menu"))
    app.add_handler(CallbackQueryHandler(show_numbers, pattern="show_numbers"))
    app.add_handler(CallbackQueryHandler(add_number, pattern="add_number"))
    app.add_handler(CallbackQueryHandler(update_all, pattern="update_all"))
    app.add_handler(CallbackQueryHandler(update_one, pattern=r"^update_\d+"))
    app.add_handler(CallbackQueryHandler(delete_one, pattern=r"^delete_\d+"))
    app.add_handler(CallbackQueryHandler(delete_all, pattern="delete_all"))
    app.add_handler(CallbackQueryHandler(check_number, pattern=r"^check_\d+"))

    print("🤖 البوت شغال...")
    app.run_polling()


if __name__ == "__main__":
    main()