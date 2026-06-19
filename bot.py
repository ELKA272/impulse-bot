import json
import os
import logging
import threading
from datetime import datetime, date
from pathlib import Path

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from telegram.constants import ParseMode
from telegram.ext import (
    Application, CallbackQueryHandler, CommandHandler,
    ConversationHandler, MessageHandler, filters,
)

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# ── Config ──
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8976558743:AAG1V6pz--7MHXS4muOrVJpC6dsOJ9o_oug")
ADMIN_USERNAME = "@elena_impulse"
BASE_DIR = Path(__file__).parent
CONFIG_FILE = BASE_DIR / "admin_config.json"
USERS_FILE = BASE_DIR / "users.json"
EVENTS_FILE = BASE_DIR / "events.json"
REGS_FILE = BASE_DIR / "registrations.json"
CHECKLIST_FILE = BASE_DIR / "checklist.txt"

def jload(path, default=None):
    if default is None: default = {}
    if path.exists():
        try: return json.loads(path.read_text())
        except: return default
    return default

def jsave(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2))

def load_admin():
    return jload(CONFIG_FILE).get("admin_chat_id", 0)

def save_admin(cid):
    jsave(CONFIG_FILE, {"admin_chat_id": cid})

ADMIN_CHAT_ID = load_admin()

# ── States ──
(ST_MENU, ST_PHONE_CHOICE, ST_PHONE_MANUAL, ST_EVENTS, ST_EVENT,
 ST_REG_NAME, ST_REG_COUNT, ST_REG_PHONE, ST_ADMIN_MSG, ST_BROADCAST) = range(10)

# ── Default events ──
DEFAULT_EVENTS = {
    "1": {"id": 1, "title": "🏛 Аркаим", "date": "12–14 июня 2026",
          "time": "уточняется", "location": "Аркаим, Челябинская область",
          "price": "уточняется", "desc": "«Точка внутренней тишины»\nПоездка в место силы для перезагрузки, отдыха и внутреннего наполнения. 🔥Осталось 2 места",
          "places": 2, "status": "active"},
    "2": {"id": 2, "title": "🆓 Оленьи ручьи", "date": "21 июня 2026",
          "time": "уточняется", "location": "Природный парк «Оленьи ручьи»",
          "price": "БЕСПЛАТНО", "desc": "«Среди своих»\nБЕСПЛАТНЫЙ выезд на природу. Прогулка, общение, новые знакомства и лёгкая атмосфера в кругу единомышленников",
          "places": 0, "status": "active"},
    "3": {"id": 3, "title": "🔥 Девичник с шашлыками", "date": "11 июля 2026",
          "time": "уточняется", "location": "уточняется",
          "price": "уточняется", "desc": "«Деньги без ограничений»\nПрирода, шашлыки, закуски, разговор с психологом о денежных ограничениях, практики, тесты и атмосферные рассказы от чтеца",
          "places": 0, "status": "active"},
    "4": {"id": 4, "title": "🆓 Озеро", "date": "19 июля 2026",
          "time": "уточняется", "location": "уточняется",
          "price": "БЕСПЛАТНО", "desc": "«Лето, которое хочется запомнить»\nБЕСПЛАТНЫЙ день отдыха у воды. Общение, музыка, смех и время в тёплой компании",
          "places": 0, "status": "active"},
    "5": {"id": 5, "title": "🏛 Аркаим", "date": "14–16 августа 2026",
          "time": "уточняется", "location": "Аркаим, Челябинская область",
          "price": "уточняется", "desc": "«Перезагрузка в месте силы»\nПутешествие для тех, кто хочет замедлиться, наполниться энергией и побыть среди своих",
          "places": 0, "status": "active"},
    "6": {"id": 6, "title": "🌊 Тургояк", "date": "19–20 сентября 2026",
          "time": "уточняется", "location": "Озеро Тургояк, Челябинская область",
          "price": "уточняется", "desc": "«В преддверии равноденствия | Время желаний»\nНейрографика на исполнение желаний, поездка на остров Веры, баня, купание в Тургояке и атмосфера внутреннего обновления",
          "places": 0, "status": "active"},
    "7": {"id": 7, "title": "⛰ Дагестан", "date": "1–7 октября 2026",
          "time": "уточняется", "location": "Дагестан",
          "price": "уточняется", "desc": "«Свобода быть собой»\nБольшое путешествие: горы, эмоции, поддержка, новые впечатления и полная перезагрузка",
          "places": 0, "status": "active"},
}

# ── Data helpers ──
def get_users():
    return jload(USERS_FILE, {})

def get_events():
    return DEFAULT_EVENTS

def get_regs():
    return jload(REGS_FILE, [])

def save_reg(data):
    regs = get_regs()
    data["id"] = len(regs) + 1
    data["created_at"] = datetime.now().isoformat()
    data["status"] = "active"
    regs.append(data)
    jsave(REGS_FILE, regs)
    return data["id"]

# ── Keyboards ──
def menu_kb():
    return ReplyKeyboardMarkup([
        ["📅 Мероприятия", "🌿 О клубе"],
        ["📞 Связь с Еленой", "📍 Чек-лист"],
    ], resize_keyboard=True)

def menu_admin_kb():
    return ReplyKeyboardMarkup([
        ["📅 Мероприятия", "🌿 О клубе"],
        ["📞 Связь с Еленой", "📍 Чек-лист"],
        ["📊 Статистика", "📢 Рассылка"],
    ], resize_keyboard=True)

def cancel_kb():
    return ReplyKeyboardMarkup([["❌ Отмена"]], resize_keyboard=True)

# ── Helpers ──
def is_admin(uid):
    return ADMIN_CHAT_ID and uid == ADMIN_CHAT_ID

def kb_for(uid):
    return menu_admin_kb() if is_admin(uid) else menu_kb()

async def to_menu(update: Update, text="Главное меню:", kb=None):
    u = update.effective_user
    k = kb or kb_for(u.id)
    if update.callback_query:
        await update.callback_query.edit_message_text(text, parse_mode=ParseMode.HTML)
        await update.callback_query.message.reply_text("👇 Меню:", reply_markup=k)
    else:
        await update.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=k)

# ── /start ──
async def start(update: Update, ctx):
    uid = update.effective_user.id
    u = update.effective_user
    users = get_users()
    if str(uid) not in users:
        users[str(uid)] = {"first_name": u.first_name or "", "username": u.username or "",
                           "phone": "", "subscribed_at": datetime.now().isoformat(), "subscribed": True}
        jsave(USERS_FILE, users)

    # Show REAL contact share button + text buttons
    phone_kb = ReplyKeyboardMarkup([
        [KeyboardButton("📱 Отправить телефон", request_contact=True)],
        ["✍️ Ввести вручную"],
        ["⏺ Пропустить"],
    ], resize_keyboard=True)
    await update.message.reply_text(
        f"🌸 Привет, {u.first_name or 'подруга'}!\n\n"
        "Это <b>«Импульс»</b> — женский клуб в Екатеринбурге.\n"
        "Ретриты, практикумы, путешествия и душевные встречи.\n\n"
        "Оставь контакт, чтобы получать напоминания 👇",
        parse_mode=ParseMode.HTML,
        reply_markup=phone_kb,
    )
    return ST_PHONE_CHOICE

async def phone_choice(update: Update, ctx):
    uid = update.effective_user.id
    text = update.message.text.strip()

    if text == "📱 Отправить телефон":
        await update.message.reply_text("👇 Нажми кнопку 'Отправить контакт' в меню снизу:")
        return ST_PHONE_CHOICE
    elif text == "✍️ Ввести вручную":
        await update.message.reply_text("📱 Напиши номер телефона:", reply_markup=cancel_kb())
        return ST_PHONE_MANUAL
    elif text == "⏺ Пропустить":
        users = get_users()
        users[str(uid)]["phone"] = ""
        jsave(USERS_FILE, users)
        return await after_contact(update, ctx)
    else:
        users = get_users()
        users[str(uid)]["phone"] = text
        jsave(USERS_FILE, users)
        return await after_contact(update, ctx)

async def phone_manual(update: Update, ctx):
    uid = update.effective_user.id
    text = update.message.text.strip()
    if text == "❌ Отмена":
        return await start(update, ctx)
    users = get_users()
    users[str(uid)]["phone"] = text
    jsave(USERS_FILE, users)
    return await after_contact(update, ctx)

async def phone_contact(update: Update, ctx):
    uid = update.effective_user.id
    phone = update.message.contact.phone_number
    users = get_users()
    users[str(uid)]["phone"] = phone
    jsave(USERS_FILE, users)
    return await after_contact(update, ctx)

async def after_contact(update: Update, ctx):
    k = kb_for(update.effective_user.id)
    await update.message.reply_text(
        "🌿 <b>Добро пожаловать в «Импульс»!</b>\n\n"
        "🎁 В подарок — <b>чек-лист «5 мест силы Свердловской области»</b>\n"
        "👇 Скачай его прямо сейчас 👇",
        parse_mode=ParseMode.HTML,
    )
    try:
        await update.message.reply_document(
            document=open(CHECKLIST_FILE, "rb"),
            filename="5_mest_sily_impuls.txt",
            caption="🌿 Чек-лист «5 мест силы Свердловской области»\nЖенский клуб «ИМПУЛЬС»",
        )
    except Exception as e:
        logger.error(f"Checklist send: {e}")
    await update.message.reply_text(
        "А пока посмотри, что мы запланировали:",
        parse_mode=ParseMode.HTML, reply_markup=k,
    )
    return ST_MENU

# ── Menu Router ──
async def menu_router(update: Update, ctx):
    uid = update.effective_user.id
    text = update.message.text.strip()
    admin = is_admin(uid)

    if text == "📅 Мероприятия":
        return await show_events(update, ctx)
    elif text == "🌿 О клубе":
        await update.message.reply_text(
            "🌿 <b>О клубе «Импульс»</b>\n\n"
            "Мы — женское сообщество в Екатеринбурге.\n"
            "Собираемся, чтобы:\n"
            "• Путешествовать по местам силы 🏔\n"
            "• Медитировать и проводить женские круги 🧘\n"
            "• Участвовать в мастер-классах 🎨\n"
            "• Знакомиться и дружить 🤝\n\n"
            "Присоединяйся! 🌸",
            parse_mode=ParseMode.HTML, reply_markup=kb_for(uid),
        )
        return ST_MENU
    elif text == "📞 Связь с Еленой":
        await update.message.reply_text(
            "📝 Напиши сообщение, и я передам Елене:",
            reply_markup=cancel_kb(),
        )
        return ST_ADMIN_MSG
    elif text == "📍 Чек-лист":
        await update.message.reply_text(
            "🎁 <b>Твой чек-лист «5 мест силы»</b>\n\n"
            "Скачивай файл ниже 👇\n"
            "Сохрани себе, чтобы не потерять! 🌸",
            parse_mode=ParseMode.HTML, reply_markup=kb_for(uid),
        )
        try:
            await update.message.reply_document(
                document=open(CHECKLIST_FILE, "rb"),
                filename="5_mest_sily_impuls.txt",
                caption="🌿 Чек-лист «5 мест силы Свердловской области»\nЖенский клуб «ИМПУЛЬС»",
            )
        except Exception as e:
            logger.error(f"Checklist send error: {e}")
            await update.message.reply_text("❌ Не удалось отправить файл.")
        return ST_MENU
    elif admin and text == "📊 Статистика":
        return await stats(update, ctx)
    elif admin and text == "📢 Рассылка":
        await update.message.reply_text("📢 Напиши текст для рассылки:", reply_markup=cancel_kb())
        return ST_BROADCAST
    else:
        await update.message.reply_text("Используй кнопки меню 👇", reply_markup=kb_for(uid))
        return ST_MENU

# ── Events ──
async def show_events(update: Update, ctx):
    events = get_events()
    active = [e for e in events.values() if e.get("status") == "active"]
    if not active:
        await update.message.reply_text("Пока нет запланированных мероприятий 🌸", reply_markup=kb_for(update.effective_user.id))
        return ST_MENU
    kb = [[InlineKeyboardButton(f"{e['title']} — {e['date']}", callback_data=f"ev_{e['id']}")] for e in active]
    kb.append([InlineKeyboardButton("❌ Закрыть", callback_data="close")])
    await update.message.reply_text("📅 <b>Ближайшие мероприятия:</b>", parse_mode=ParseMode.HTML,
                                    reply_markup=InlineKeyboardMarkup(kb))
    return ST_EVENTS

async def event_callback(update: Update, ctx):
    q = update.callback_query
    await q.answer()
    d = q.data

    if d == "close":
        await q.edit_message_text("❌ Закрыто.")
        await q.message.reply_text("Главное меню 👇", reply_markup=kb_for(update.effective_user.id))
        return ST_MENU

    if d.startswith("ev_"):
        eid = d.replace("ev_", "")
        events = get_events()
        e = events.get(eid)
        if not e:
            await q.edit_message_text("Мероприятие не найдено.")
            return ST_MENU
        ctx.user_data["eid"] = eid

        uid = update.effective_user.id
        regs = get_regs()
        already = any(r.get("event_id") == int(eid) and r.get("user_id") == uid and r.get("status") == "active" for r in regs)

        text = (f"{e['title']}\n\n🗓 <b>Дата:</b> {e['date']}\n⏰ <b>Время:</b> {e['time']}\n"
                f"📍 <b>Место:</b> {e['location']}\n💰 <b>Стоимость:</b> {e['price']}\n\n📝 {e['desc']}")
        kb = []
        if already:
            kb.append([InlineKeyboardButton("❌ Отменить участие", callback_data=f"unreg_{eid}")])
        else:
            kb.append([InlineKeyboardButton("✅ Хочу участвовать!", callback_data=f"reg_{eid}")])
        kb.append([InlineKeyboardButton("◀ Назад", callback_data="back_ev")])

        await q.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(kb))
        return ST_EVENT

    if d.startswith("reg_"):
        eid = d.replace("reg_", "")
        ctx.user_data["reg_eid"] = int(eid)
        events = get_events()
        e = events.get(eid, {})
        await q.edit_message_text(
            f"📝 <b>Регистрация:</b> {e.get('title', '')}\n\nШаг 1 из 3\n\nНапиши <b>своё имя</b>:",
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Отмена", callback_data="cancel")]]),
        )
        return ST_REG_NAME

    if d.startswith("unreg_"):
        eid = d.replace("unreg_", "")
        uid = update.effective_user.id
        regs = get_regs()
        for r in regs:
            if r.get("event_id") == int(eid) and r.get("user_id") == uid and r.get("status") == "active":
                r["status"] = "cancelled"
                jsave(REGS_FILE, regs)
                events = get_events()
                e = events.get(eid, {})
                await q.edit_message_text("❌ Участие отменено.")
                if ADMIN_CHAT_ID:
                    try:
                        await ctx.bot.send_message(
                            chat_id=ADMIN_CHAT_ID,
                            text=(f"❌ <b>Отмена регистрации</b>\n\n👤 {r.get('name', '—')}\n📞 {r.get('phone', '—')}\n"
                                  f"📅 {e.get('title', '—')} | {e.get('date', '—')}"),
                            parse_mode=ParseMode.HTML,
                        )
                    except Exception as ex:
                        logger.error(f"Admin unreg: {ex}")
                return ST_MENU
        await q.edit_message_text("Регистрация не найдена.")
        return ST_MENU

    if d == "back_ev":
        events = get_events()
        active = [e for e in events.values() if e.get("status") == "active"]
        kb = [[InlineKeyboardButton(f"{e['title']} — {e['date']}", callback_data=f"ev_{e['id']}")] for e in active]
        kb.append([InlineKeyboardButton("❌ Закрыть", callback_data="close")])
        await q.edit_message_text("📅 <b>Ближайшие мероприятия:</b>", parse_mode=ParseMode.HTML,
                                  reply_markup=InlineKeyboardMarkup(kb))
        return ST_EVENTS

    if d == "cancel":
        await q.edit_message_text("❌ Отменено.")
        return ST_MENU

    return ST_MENU

# ── Registration steps ──
async def reg_name(update: Update, ctx):
    ctx.user_data["reg_name"] = update.message.text.strip()
    await update.message.reply_text("📝 Шаг 2 из 3\n\nСколько <b>человек</b> будет? (напиши число):",
                                    parse_mode=ParseMode.HTML, reply_markup=cancel_kb())
    return ST_REG_COUNT

async def reg_count(update: Update, ctx):
    text = update.message.text.strip()
    if text == "❌ Отмена":
        u = update.effective_user
        await update.message.reply_text("❌ Отменено.", reply_markup=kb_for(u.id))
        return ST_MENU
    try:
        ctx.user_data["reg_count"] = int(text)
    except:
        await update.message.reply_text("Напиши число, например: 2")
        return ST_REG_COUNT
    await update.message.reply_text("📝 Шаг 3 из 3\n\nНапиши <b>телефон для связи</b>:",
                                    parse_mode=ParseMode.HTML, reply_markup=cancel_kb())
    return ST_REG_PHONE

async def reg_phone(update: Update, ctx):
    text = update.message.text.strip()
    if text == "❌ Отмена":
        await update.message.reply_text("❌ Отменено.", reply_markup=kb_for(update.effective_user.id))
        return ST_MENU
    uid = update.effective_user.id
    u = update.effective_user
    eid = ctx.user_data.get("reg_eid")
    events = get_events()
    e = events.get(str(eid), {})

    users = get_users()
    if str(uid) in users:
        users[str(uid)]["phone"] = text
        jsave(USERS_FILE, users)

    data = {"event_id": eid, "user_id": uid, "name": ctx.user_data.get("reg_name", ""),
            "count": ctx.user_data.get("reg_count", 1), "phone": text, "username": u.username or ""}
    rid = save_reg(data)

    await update.message.reply_text(
        f"✅ <b>Ты зарегистрирована!</b>\n\n"
        f"📅 {e.get('title', '')}\n🗓 {e.get('date', '')} в {e.get('time', '')}\n"
        f"👤 {data['name']}, {data['count']} чел.\n\n"
        f"🔔 Пришлю напоминание за 24 часа.\nВопросы — {ADMIN_USERNAME}\n\nДо встречи! 🌸",
        parse_mode=ParseMode.HTML, reply_markup=kb_for(uid),
    )
    if ADMIN_CHAT_ID:
        try:
            await ctx.bot.send_message(
                chat_id=ADMIN_CHAT_ID,
                text=(f"✅ <b>Новая регистрация</b>\n\n📅 {e.get('title', '')}\n"
                      f"🗓 {e.get('date', '')} | {e.get('time', '')}\n"
                      f"👤 {data['name']}\n👥 {data['count']} чел.\n📞 {text}\n🆔 {uid}"),
                parse_mode=ParseMode.HTML,
            )
        except Exception as ex:
            logger.error(f"Admin reg: {ex}")
    return ST_MENU

# ── Admin message ──
async def admin_msg(update: Update, ctx):
    text = update.message.text.strip()
    if text == "❌ Отмена":
        await update.message.reply_text("❌ Отменено.", reply_markup=kb_for(update.effective_user.id))
        return ST_MENU
    u = update.effective_user
    if ADMIN_CHAT_ID:
        try:
            await ctx.bot.send_message(
                chat_id=ADMIN_CHAT_ID,
                text=(f"💬 <b>Сообщение от участницы</b>\n\n"
                      f"👤 {u.full_name or '—'} (@{u.username or '—'})\n🆔 {u.id}\n\n{text}"),
                parse_mode=ParseMode.HTML,
            )
            await update.message.reply_text("✅ Передано Елене! Она ответит 🌸", reply_markup=kb_for(u.id))
        except Exception as e:
            logger.error(f"Admin msg: {e}")
            await update.message.reply_text("❌ Ошибка.", reply_markup=kb_for(u.id))
    else:
        await update.message.reply_text("❌ Админ не подключён.", reply_markup=kb_for(u.id))
    return ST_MENU

# ── Admin: stats ──
async def stats(update: Update, ctx):
    users = get_users()
    regs = get_regs()
    active_regs = [r for r in regs if r.get("status") == "active"]
    with_phone = [u for u in users.values() if u.get("phone")]
    await update.message.reply_text(
        f"📊 <b>Статистика</b>\n\n👤 Подписчиков: <b>{len(users)}</b>\n"
        f"📱 С телефоном: <b>{len(with_phone)}</b>\n"
        f"✅ Активных регистраций: <b>{len(active_regs)}</b>\n"
        f"📅 Всего мероприятий: <b>{len(get_events())}</b>",
        parse_mode=ParseMode.HTML, reply_markup=kb_for(update.effective_user.id),
    )
    return ST_MENU

# ── Admin: broadcast ──
async def broadcast(update: Update, ctx):
    text = update.message.text.strip()
    if text == "❌ Отмена":
        await update.message.reply_text("❌ Отменено.", reply_markup=kb_for(update.effective_user.id))
        return ST_MENU
    users = get_users()
    sent = 0
    failed = 0
    for uid_str in users:
        try:
            await ctx.bot.send_message(chat_id=int(uid_str),
                text=f"📢 <b>«Импульс»</b>\n\n{text}",
                parse_mode=ParseMode.HTML)
            sent += 1
        except Exception as e:
            failed += 1
            logger.error(f"Broadcast {uid_str}: {e}")
    await update.message.reply_text(f"✅ Отправлено: {sent}\n❌ Ошибок: {failed}",
                                    reply_markup=kb_for(update.effective_user.id))
    return ST_MENU

# ── /setadmin ──
async def set_admin(update: Update, ctx):
    save_admin(update.effective_user.id)
    global ADMIN_CHAT_ID
    ADMIN_CHAT_ID = update.effective_user.id
    await update.message.reply_text(
        "✅ Ты администратор!\n\nКоманды:\n/stats — статистика\n/broadcast — рассылка\n\n"
        "В меню появились кнопки 📊 и 📢",
        reply_markup=menu_admin_kb(),
    )

# ── /stats ──
async def stats_cmd(update: Update, ctx):
    if not is_admin(update.effective_user.id):
        return
    return await stats(update, ctx)

# ── /broadcast ──
async def broadcast_cmd(update: Update, ctx):
    if not is_admin(update.effective_user.id):
        return
    await update.message.reply_text("📢 Напиши текст для рассылки:", reply_markup=cancel_kb())
    return ST_BROADCAST

# ── Cancel fallback ──
async def cancel_all(update: Update, ctx):
    await update.message.reply_text("❌", reply_markup=kb_for(update.effective_user.id))
    return ST_MENU

# ── HTTP Server (CRM + API) ──
def start_http():
    import http.server
    import socketserver

    PORT = int(os.environ.get("PORT", 8080))

    class Handler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(BASE_DIR), **kwargs)

        def do_GET(self):
            if self.path == "/api/users":
                self.send_json(BASE_DIR / "users.json")
            elif self.path == "/api/regs":
                self.send_json(BASE_DIR / "registrations.json")
            elif self.path == "/api/events":
                self.send_json(BASE_DIR / "events.json")
            else:
                super().do_GET()

        def send_json(self, path):
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            try:
                self.wfile.write(path.read_bytes())
            except:
                self.wfile.write(b"{}")

        def log_message(self, fmt, *args):
            logger.info(f"HTTP: {args[0]} {args[1]}")

    try:
        httpd = socketserver.TCPServer(("0.0.0.0", PORT), Handler)
        logger.info(f"📡 CRM сервер: http://0.0.0.0:{PORT}/crm.html")
        httpd.serve_forever()
    except Exception as e:
        logger.error(f"HTTP server: {e}")

# ── Main ──
def main():
    import asyncio
    import signal

    # Sync events to file for CRM API
    jsave(EVENTS_FILE, DEFAULT_EVENTS)

    # Start HTTP server in background
    t = threading.Thread(target=start_http, daemon=True)
    t.start()

    async def run():
        app = Application.builder().token(BOT_TOKEN).build()

        app.add_handler(CommandHandler("setadmin", set_admin))
        app.add_handler(CommandHandler("stats", stats_cmd))
        app.add_handler(CommandHandler("broadcast", broadcast_cmd))
        conv = ConversationHandler(
            entry_points=[CommandHandler("start", start)],
            states={
                ST_PHONE_CHOICE: [
                    MessageHandler(filters.CONTACT, phone_contact),
                    MessageHandler(filters.TEXT & ~filters.COMMAND, phone_choice),
                ],
                ST_PHONE_MANUAL: [MessageHandler(filters.TEXT & ~filters.COMMAND, phone_manual)],
                ST_MENU: [MessageHandler(filters.TEXT & ~filters.COMMAND, menu_router)],
                ST_EVENTS: [CallbackQueryHandler(event_callback)],
                ST_EVENT: [CallbackQueryHandler(event_callback)],
                ST_REG_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, reg_name),
                              CallbackQueryHandler(event_callback)],
                ST_REG_COUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, reg_count)],
                ST_REG_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, reg_phone)],
                ST_ADMIN_MSG: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_msg)],
                ST_BROADCAST: [MessageHandler(filters.TEXT & ~filters.COMMAND, broadcast)],
            },
            fallbacks=[CommandHandler("cancel", cancel_all)],
            per_message=False,
            name="impulse",
        )
        app.add_handler(conv)

        logger.info("🌸 Бот «Импульс» запущен!")

        await app.initialize()
        await app.updater.start_polling()
        logger.info("✅ Бот работает 24/7")
        # Block forever — keep bot alive
        await asyncio.Event().wait()

    while True:
        try:
            asyncio.run(run())
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"⚠️ Бот упал: {e}. Перезапуск через 5 секунд...")
            import time
            time.sleep(5)

if __name__ == "__main__":
    main()
