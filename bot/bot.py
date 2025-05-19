from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    ContextTypes, ConversationHandler, CallbackQueryHandler, filters
)
import aiohttp
import datetime

ASK_CITY = 1
WEATHER_API_KEY = 'c8c03c910db2cb5bf18fdb6cce5c5fe0'
EXCHANGE_API_KEY = "da8e4d0600a4a2e30e525897"

# Главное меню
def main_menu():
    keyboard = [
        [InlineKeyboardButton("🌤 Погода", callback_data='weather')],
        [InlineKeyboardButton("💱 Курс валют", callback_data='exchange')],
    ]
    return InlineKeyboardMarkup(keyboard)

# Команда /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Добро пожаловать! Выберите действие:", reply_markup=main_menu())

# Команда /weather
async def weather_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🌍 В каком городе показать погоду?")
    return ASK_CITY

# Эмоджи по иконке
def weather_emoji(icon: str) -> str:
    mapping = {
        "01d": "☀️", "01n": "🌙", "02d": "🌤", "02n": "🌤",
        "03d": "☁️", "03n": "☁️", "04d": "☁️", "04n": "☁️",
        "09d": "🌧", "09n": "🌧", "10d": "🌦", "10n": "🌧",
        "11d": "⛈", "11n": "⛈", "13d": "❄️", "13n": "❄️",
        "50d": "🌫", "50n": "🌫"
    }
    return mapping.get(icon, "🌈")

# Получение погоды на сегодня
async def fetch_weather(city: str) -> str:
    url = f"http://api.openweathermap.org/data/2.5/forecast?q={city}&appid={WEATHER_API_KEY}&units=metric&lang=ru"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                data = await response.json()
                forecast_list = data['list']
                today = datetime.datetime.now().date()

                result = f"📍 *Прогноз погоды в {city.title()} на сегодня:*\n\n"
                periods = {}

                for item in forecast_list:
                    dt = datetime.datetime.fromtimestamp(item['dt'])
                    if dt.date() != today:
                        continue

                    hour = dt.hour
                    period = (
                        "🌙 Ночь" if hour < 6 else
                        "🕖 Утро" if hour < 12 else
                        "🌤 День" if hour < 18 else
                        "🌆 Вечер"
                    )

                    temp = item['main']['temp']
                    desc = item['weather'][0]['description'].capitalize()
                    emoji = weather_emoji(item['weather'][0]['icon'])

                    if period not in periods:
                        periods[period] = f"{period}: {emoji} *{desc}*, {temp:.0f}°C"

                if not periods:
                    return "⚠️ Прогноз на сегодня недоступен."

                for part in ["🌙 Ночь", "🕖 Утро", "🌤 День", "🌆 Вечер"]:
                    if part in periods:
                        result += periods[part] + "\n"

                return result
            else:
                return "⚠️ Город не найден. Попробуй снова."

# Прогноз на 5 дней
async def fetch_weather_forecast(city: str) -> str:
    url = f"http://api.openweathermap.org/data/2.5/forecast?q={city}&appid={WEATHER_API_KEY}&units=metric&lang=ru"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                data = await response.json()
                forecast_list = data['list']
                result = f"📍 *Прогноз погоды в {city.title()} на 5 дней:*\n\n"
                daily_data = {}

                for item in forecast_list:
                    dt = datetime.datetime.fromtimestamp(item['dt'])
                    date_str = dt.strftime('%d.%m')
                    hour = dt.hour
                    period = (
                        "🌙 Ночь" if hour < 6 else
                        "🕖 Утро" if hour < 12 else
                        "🌤 День" if hour < 18 else
                        "🌆 Вечер"
                    )

                    temp = item['main']['temp']
                    desc = item['weather'][0]['description'].capitalize()
                    emoji = weather_emoji(item['weather'][0]['icon'])

                    line = f"{period}: {emoji} *{desc}*, {temp:.0f}°C"
                    daily_data.setdefault(date_str, {})[period] = line

                for date, parts in list(daily_data.items())[:5]:
                    result += f"📆 *{date}*\n"
                    for part in ["🌙 Ночь", "🕖 Утро", "🌤 День", "🌆 Вечер"]:
                        if part in parts:
                            result += parts[part] + "\n"
                    result += "\n"

                return result
            else:
                return "⚠️ Город не найден. Попробуй снова."

# После ввода города
async def handle_city(update: Update, context: ContextTypes.DEFAULT_TYPE):
    city = update.message.text
    context.user_data["city"] = city

    keyboard = [
        [InlineKeyboardButton("🌤 Текущая погода", callback_data='current')],
        [InlineKeyboardButton("📅 Прогноз на 5 дней", callback_data='forecast')],
        [InlineKeyboardButton("🔙 Назад", callback_data='menu')],
    ]
    await update.message.reply_text("Что показать?", reply_markup=InlineKeyboardMarkup(keyboard))
    return ConversationHandler.END

# Обработка кнопок
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "menu":
        await query.edit_message_text("🏠 Главное меню:", reply_markup=main_menu())
        return

    if data == "weather":
        await query.edit_message_text("🌍 В каком городе показать погоду?")
        context.user_data["awaiting_city"] = True
        return

    if data == "exchange":
        result = await fetch_exchange()
        await query.edit_message_text(result, reply_markup=main_menu())
        return

    city = context.user_data.get("city")
    if not city:
        await query.edit_message_text("Сначала введите город через /weather.")
        return

    result = await (fetch_weather(city) if data == "current" else fetch_weather_forecast(city))
    await query.edit_message_text(result, parse_mode="Markdown", reply_markup=main_menu())

# Курс валют
async def fetch_exchange():
    url = f"https://v6.exchangerate-api.com/v6/{EXCHANGE_API_KEY}/latest/USD"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                data = await response.json()
                rates = data["conversion_rates"]
                return (
                    f"💱 Курсы валют (1 USD):\n"
                    f"🇷🇺 RUB: {rates['RUB']}\n"
                    f"🇪🇺 EUR: {rates['EUR']}\n"
                    f"🇰🇿 KZT: {rates['KZT']}\n"
                    f"🇨🇳 CNY: {rates['CNY']}"
                )
            return "❌ Не удалось получить курсы валют."

# Отмена
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Окей, отменено.", reply_markup=main_menu())
    return ConversationHandler.END

# Обработка текстовых сообщений
async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get("awaiting_city"):
        context.user_data["awaiting_city"] = False
        return await handle_city(update, context)

# Запуск
def main():
    application = Application.builder().token("7728372588:AAHuDpRe3YghR48fK5kqlwQH3AmsLQqDgtQ").build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("weather", weather_command)],
        states={ASK_CITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_city)]},
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    application.add_handler(CommandHandler("start", start))
    application.add_handler(conv_handler)
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))
    application.run_polling()

if __name__ == '__main__':
    main()
