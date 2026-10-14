
import os
import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

rooms = {}

CASES = [
    {
        "story": "اختفت وثيقة سرية من غرفة مغلقة. ثلاثة أشخاص دخلوا المبنى تلك الليلة. من السارق؟",
        "suspects": ["الحارس", "السكرتير", "الطبيب"],
        "answer": "السكرتير",
    },
    {
        "story": "انطفأت الأنوار في المتحف واختفى مفتاح الخزنة. من أخذه؟",
        "suspects": ["المرشد", "المصور", "المدير"],
        "answer": "المصور",
    },
    {
        "story": "وصلت رسالة مجهولة قبل منتصف الليل. الشخص الذي أرسلها يعرف سر الجميع. من هو؟",
        "suspects": ["الجار", "السائق", "المحاسب"],
        "answer": "السائق",
    },
]


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🚪 إنشاء غرفة", callback_data="create")],
        [InlineKeyboardButton("🔎 الانضمام لغرفة", callback_data="join")],
        [InlineKeyboardButton("📜 طريقة اللعب", callback_data="help")],
    ]
    await update.message.reply_text(
        "🕯️ أهلاً بك في الغرفة 13\n"
        "لعبة الغموض والتحقيق الجماعية.\n\n"
        "أنشئ غرفة وادعُ أصدقاءك!",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = query.from_user

    if query.data == "create":
        code = str(random.randint(1000, 9999))
        while code in rooms:
            code = str(random.randint(1000, 9999))

        rooms[code] = {
            "players": {user.id: user.first_name},
            "case": random.choice(CASES),
            "votes": {},
            "started": False,
        }

        await query.edit_message_text(
            f"🚪 تم إنشاء الغرفة!\n"
            f"رمز الغرفة: {code}\n\n"
            f"أرسل لأصدقائك:\n/join {code}\n\n"
            f"لبدء اللعبة:\n/startgame {code}"
        )

    elif query.data == "join":
        await query.edit_message_text(
            "للانضمام أرسل الأمر مع رمز الغرفة:\n/join 1234"
        )

    elif query.data == "help":
        await query.edit_message_text(
            "🕵️ طريقة اللعب:\n"
            "1. أنشئ غرفة.\n"
            "2. ادعُ أصدقاءك.\n"
            "3. ابدأ التحقيق بالأمر /startgame رمز_الغرفة.\n"
            "4. صوّت للمشتبه به."
        )

    elif query.data.startswith("vote:"):
        _, code, suspect = query.data.split(":", 2)
        room = rooms.get(code)

        if not room or not room["started"]:
            await query.edit_message_text("انتهت هذه الجولة أو الغرفة غير موجودة.")
            return

        if query.from_user.id not in room["players"]:
            await query.edit_message_text("أنت لست لاعباً في هذه الغرفة.")
            return

        room["votes"][query.from_user.id] = suspect
        await query.edit_message_text(f"✅ تم تسجيل تصويتك: {suspect}")

        if len(room["votes"]) >= len(room["players"]):
            counts = {}
            for choice in room["votes"].values():
                counts[choice] = counts.get(choice, 0) + 1

            highest = max(counts.values())
            winners = [name for name, count in counts.items() if count == highest]
            answer = room["case"]["answer"]

            if len(winners) > 1:
                result = "تعادل في التصويت!"
            elif winners[0] == answer:
                result = f"🎉 أحسنتم! اكتشفتم المشتبه به: {answer}"
            else:
                result = f"❌ لم تنجحوا! المشتبه به الصحيح هو: {answer}"

            for player_id in room["players"]:
                try:
                    await context.bot.send_message(
                        chat_id=player_id,
                        text=f"🏁 انتهت الجولة!\n{result}",
                    )
                except Exception:
                    pass

            room["started"] = False


async def join_room(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("استخدم: /join رمز_الغرفة")
        return

    code = context.args[0]
    room = rooms.get(code)

    if not room:
        await update.message.reply_text("❌ الغرفة غير موجودة.")
        return

    user = update.effective_user

    if room["started"]:
        await update.message.reply_text("الجولة بدأت بالفعل.")
        return

    room["players"][user.id] = user.first_name

    names = "\n".join(room["players"].values())
    await update.message.reply_text(
        f"✅ انضممت للغرفة {code}!\n\n"
        f"اللاعبون:\n{names}\n\n"
        f"ابدأ اللعبة بالأمر:\n/startgame {code}"
    )


async def start_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("استخدم: /startgame رمز_الغرفة")
        return

    code = context.args[0]
    room = rooms.get(code)

    if not room:
        await update.message.reply_text("❌ الغرفة غير موجودة.")
        return

    if len(room["players"]) < 2:
        await update.message.reply_text("تحتاج إلى لاعبين اثنين على الأقل.")
        return

    if room["started"]:
        await update.message.reply_text("الجولة بدأت بالفعل.")
        return

    room["started"] = True
    room["votes"] = {}
    case = room["case"]

    keyboard = [
        [InlineKeyboardButton(name, callback_data=f"vote:{code}:{name}")]
        for name in case["suspects"]
    ]

    for player_id in room["players"]:
        try:
            await context.bot.send_message(
                chat_id=player_id,
                text=f"🕵️ بدأت القضية!\n\n{case['story']}\n\nمن المشتبه به؟",
                reply_markup=InlineKeyboardMarkup(keyboard),
            )
        except Exception:
            pass

    await update.message.reply_text("🔍 أرسلت القضية للاعبين.")


def main():
    token = os.environ.get("BOT_TOKEN")
    if not token:
        raise RuntimeError("أضف BOT_TOKEN في متغيرات البيئة.")

    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("join", join_room))
    app.add_handler(CommandHandler("startgame", start_game))
    app.add_handler(CallbackQueryHandler(button))
    print("الغرفة 13 تعمل!")
    app.run_polling()


if __name__ == "__main__":
    main()
