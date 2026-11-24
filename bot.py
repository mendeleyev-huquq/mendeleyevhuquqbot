import json
import os
import time
import telebot

TOKEN = "9056487122:AAEl1kfEeN8VsaOX5anIw-QARnoEtDeo7M0"
ADMIN_ID = 5593934290

bot = telebot.TeleBot(TOKEN)

DATA_FILE = "bot_data.json"


def load_data():
  if os.path.exists(DATA_FILE):
    try:
      with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)
    except Exception:
      pass
  return {"answer_key": "", "submissions": []}


def save_data(data):
  with open(DATA_FILE, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)


db = load_data()
user_states = {}


def is_admin(user_id):
  return user_id == ADMIN_ID


def grade_answers(student_ans, key_ans):
  s = student_ans.strip().lower().replace(" ", "")
  k = key_ans.strip().lower().replace(" ", "")
  if not k:
    return None, 0, 0
  total = len(k)
  correct = 0
  for i in range(min(len(s), total)):
    if s[i] == k[i]:
      correct += 1
  percent = round((correct / total) * 100, 1) if total > 0 else 0
  return correct, total, percent


@bot.message_handler(commands=["start"])
def start_handler(message):
  chat_id = message.chat.id
  user_states[chat_id] = {}

  text = (
      "Assalomu alaykum! *Mendeleyev Huquq* test tizimiga xush kelibsiz.\n\n"
      "Ism-sharifingizni kiriting (lotin harflarida, masalan: *Ali Valiyev*):"
  )
  if is_admin(message.from_user.id):
    text += (
        "\n\n*Admin buyruqlari:*\n"
        "/setkey — Test kalit javobini kiritish\n"
        "/results — O'quvchilar natijalarini ko'rish\n"
        "/clear — Bazani tozalash"
    )

  bot.send_message(chat_id, text, parse_mode="Markdown")
  bot.register_next_step_handler(message, get_name)


def get_name(message):
  chat_id = message.chat.id
  if message.text and message.text.startswith("/"):
    handle_admin_command(message)
    return

  full_name = (message.text or "").strip()
  if len(full_name) < 3:
    bot.send_message(
        chat_id, "Iltimos, ism-sharifingizni to'liqroq kiriting:"
    )
    bot.register_next_step_handler(message, get_name)
    return

  user_states[chat_id] = {"name": full_name}
  bot.send_message(
      chat_id,
      f"Rahmat, *{full_name}*!\n"
      "Endi test javoblaringizni yuboring (masalan: *abcdabcd...*):",
      parse_mode="Markdown",
  )
  bot.register_next_step_handler(message, get_answers)


def get_answers(message):
  chat_id = message.chat.id
  if message.text and message.text.startswith("/"):
    handle_admin_command(message)
    return

  answers = (message.text or "").strip()
  full_name = user_states.get(chat_id, {}).get("name", "Noma'lum o'quvchi")

  key = db.get("answer_key", "")
  correct, total, percent = grade_answers(answers, key)

  record = {
      "user_id": message.from_user.id,
      "name": full_name,
      "answers": answers,
      "correct": correct,
      "total": total,
      "percent": percent,
  }
  db["submissions"].append(record)
  save_data(db)

  if correct is not None:
    reply = (
        "✅ *Javoblaringiz qabul qilindi va tekshirildi!*\n\n"
        f"👤 O'quvchi: *{full_name}*\n"
        f"📝 Kiritilgan belgilar: *{len(answers)}* ta\n"
        f"✔️ To'g'ri javoblar: *{correct} / {total}*\n"
        f"📊 Natija: *{percent}%*\n\n"
        "Qayta topshirish uchun /start bosing."
    )
  else:
    reply = (
        "✅ *Javoblaringiz qabul qilindi!*\n\n"
        f"👤 O'quvchi: *{full_name}*\n"
        f"📝 Kiritilgan belgilar: *{len(answers)}* ta\n"
        "⏳ Kalit javob hali kiritilmagan, natija admin tomonidan e'lon"
        " qilinadi.\n\n"
        "Qayta topshirish uchun /start bosing."
    )

  bot.send_message(chat_id, reply, parse_mode="Markdown")


@bot.message_handler(commands=["setkey", "results", "clear"])
def handle_admin_command(message):
  user_id = message.from_user.id
  chat_id = message.chat.id

  if not is_admin(user_id):
    bot.send_message(chat_id, "Bu buyruq faqat administrator uchun.")
    return

  cmd = message.text.split()[0].lower()

  if cmd == "/setkey":
    bot.send_message(
        chat_id,
        "Test kalit javoblarini yuboring (masalan: *abcdabcd...*):",
        parse_mode="Markdown",
    )
    bot.register_next_step_handler(message, save_answer_key)

  elif cmd == "/results":
    subs = db.get("submissions", [])
    if not subs:
      bot.send_message(chat_id, "Hozircha hech kim test topshirmagan.")
      return

    lines = ["📊 *O'quvchilar natijalari:*\n"]
    for idx, item in enumerate(subs, start=1):
      if item.get("correct") is not None:
        lines.append(
            f"{idx}. *{item['name']}* — {item['correct']}/{item['total']}"
            f" ({item['percent']}%)"
        )
      else:
        lines.append(
            f"{idx}. *{item['name']}* — {len(item['answers'])} ta belgi"
            " (kalit kutilmoqda)"
        )

    bot.send_message(chat_id, "\n".join(lines), parse_mode="Markdown")

  elif cmd == "/clear":
    db["submissions"] = []
    save_data(db)
    bot.send_message(chat_id, "🗑 O'quvchilar natijalari tozalandi.")


def save_answer_key(message):
  chat_id = message.chat.id
  if not is_admin(message.from_user.id):
    return

  key_text = (message.text or "").strip()
  if not key_text:
    bot.send_message(chat_id, "Kalit bo'sh bo'lmasligi kerak. Qaytadan kiriting:")
    bot.register_next_step_handler(message, save_answer_key)
    return

  db["answer_key"] = key_text

  for item in db.get("submissions", []):
    correct, total, percent = grade_answers(item.get("answers", ""), key_text)
    item["correct"] = correct
    item["total"] = total
    item["percent"] = percent

  save_data(db)
  bot.send_message(
      chat_id,
      f"✅ Kalit saqlandi ({len(key_text)} ta belgi) va mavjud natijalar"
      " yangilandi!",
  )


print("Bot ishga tushdi...")
while True:
  try:
    bot.infinity_polling(none_stop=True, timeout=20, long_polling_timeout=20)
  except Exception as e:
    print("Ulanishda vaqtinchalik xato:", e)
    time.sleep(5)
