import os
import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

rooms = {}


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🕯️ أهلاً بك في الغرفة 13!\n\n"
        "لعبة غموض وتحقيق جماعية 🔎\n\n"
        "الأوامر:\n"
        "/newroom - إنشاء غرفة جديدة\n"
        "/join - الانضمام للعبة\n"
        "/startgame - بدء التحقيق\n\n"
        "👥 اجمعوا اللاعبين داخل المجموعة وابدؤوا!"
    )


async def new_room(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id

    rooms[chat_id] = {
        "players": {},
        "votes": {},
        "killer": None,
        "playing": False,
    }

    await update.message.reply_text(
        "🚪 تم فتح الغرفة 13!\n\n"
        "على اللاعبين الانضمام بالأمر /join\n"
        "عندما تكونون مستعدين، استخدموا /startgame"
    )


async def join_room(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user = update.effective_user

    if chat_id not in rooms:
        await update.message.reply_text(
            "🚪 ماكو غرفة مفتوحة!\nاستخدم /newroom أولاً."
        )
        return

    room = rooms[chat_id]

    if room["playing"]:
        await update.message.reply_text(
            "🔒 اللعبة بدأت بالفعل، انتظر الجولة القادمة."
        )
        return

    room["players"][user.id] = user.full_name

    await update.message.reply_text(
        f"👤 انضم {user.full_name} إلى الغرفة 13!\n"
        f"عدد اللاعبين: {len(room['players'])}"
    )


async def start_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id

    if chat_id not in rooms:
        await update.message.reply_text(
            "🚪 أنشئ غرفة أولاً باستخدام /newroom"
        )
        return

    room = rooms[chat_id]

    if len(room["players"]) < 2:
        await update.message.reply_text(
            "👥 تحتاجون لاعبين على الأقل لبدء التحقيق!"
        )
        return

    room["killer"] = random.choice(list(room["players"].keys()))
    room["votes"] = {}
    room["playing"] = True

    keyboard = []

    for player_id, name in room["players"].items():
        keyboard.append([
            InlineKeyboardButton(
                f"🔎 {name}",
                callback_data=f"vote:{player_id}"
            )
        ])

    await update.message.reply_text(
        "🌑 بدأت أحداث الغرفة 13...\n\n"
        "حدث أمر غامض، وأحد الموجودين يخفي الحقيقة!\n"
        "🕵️ اختاروا الشخص الذي تشكون به.\n\n"
        "كل لاعب يصوّت مرة واحدة.",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    chat_id = query.message.chat.id
    user_id = query.from_user.id
    data = query.data

    if chat_id not in rooms:
        await query.answer("الغرفة غير موجودة.", show_alert=True)
        return

    room = rooms[chat_id]

    if not room["playing"]:
        await query.answer("ماكو تحقيق فعّال حالياً.", show_alert=True)
        return

    if user_id not in room["players"]:
        await query.answer(
            "انضم للعبة أولاً باستخدام /join",
            show_alert=True,
        )
        return

    if not data.startswith("vote:"):
        return

    suspect_id = int(data.split(":")[1])

    if suspect_id not in room["players"]:
        await query.answer("هذا اللاعب غير موجود.", show_alert=True)
        return

    room["votes"][user_id] = suspect_id

    await query.answer("✅ تم تسجيل تصويتك!")

    total_players = len(room["players"])
    total_votes = len(room["votes"])

    if total_votes < total_players:
        await query.message.reply_text(
            f"🗳️ تم تسجيل تصويت جديد!\n"
            f"التصويتات: {total_votes}/{total_players}"
        )
        return

    counts = {}

    for voted_id in room["votes"].values():
        counts[voted_id] = counts.get(voted_id, 0) + 1

    max_votes = max(counts.values())
    suspects = [
        player_id
        for player_id, count in counts.items()
        if count == max_votes
    ]

    chosen = random.choice(suspects)
    killer = room["killer"]

    if chosen == killer:
        result = (
            "🎉 أحسنتم يا محققين!\n"
            f"🔒 كشفتم المجرم: {room['players'][killer]}\n"
            "انتهى التحقيق بنجاح!"
        )
    else:
        result = (
            "🌑 انتهى التحقيق...\n"
            f"❌ اتهمتم: {room['players'][chosen]}\n"
            f"🩸 الحقيقة كانت: {room['players'][killer]}\n"
            "لقد أفلت المجرم هذه المرة!"
        )

    room["playing"] = False

    await query.message.reply_text(
        "📊 انتهى التصويت!\n\n" + result +
        "\n\nلبدء جولة جديدة استخدموا /startgame"
    )


def main():
    token = os.environ.get("BOT_TOKEN")

    if not token:
        raise RuntimeError("أضف BOT_TOKEN في متغيرات Render.")

    base_url = os.environ.get("RENDER_EXTERNAL_URL")

    if not base_url:
        raise RuntimeError(
            "هذا البوت يحتاج إلى تشغيله على Render Web Service."
        )

    app = Application.builder().token(token).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("newroom", new_room))
    app.add_handler(CommandHandler("join", join_room))
    app.add_handler(CommandHandler("startgame", start_game))
    app.add_handler(CallbackQueryHandler(button))

    print("الغرفة 13 تعمل!")

    app.run_webhook(
        listen="0.0.0.0",
        port=int(os.environ.get("PORT", "10000")),
        url_path=token,
        webhook_url=f"{base_url.rstrip('/')}/{token}",
        drop_pending_updates=True,
    )


if __name__ == "__main__":
    main()
