import telebot
from telebot import types
import requests
import xml.etree.ElementTree as ET
import json
import os
import time

#ссылка на бота @siriusexchanger_bot

with open("key.json", "r") as f:
    config = json.load(f)
    bot_token = config["telegram_bot_token"]

bot = telebot.TeleBot(bot_token) 

JSON_FILE = "cbr_rates.json"

# Переменные для хранения состояния
chosen_currency = None
amount = None

# Начало
@bot.message_handler(commands=["start", "help"])
def welcome(message):
    global chosen_currency, amount
    bot.send_message(message.chat.id, "Приветствую вас! Меня зовут Sirius Exchanger\r\nЯ обмениваю USD, EUR, CNY")
    # Кнопки выбора
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("Обмен '$'"), types.KeyboardButton("Обмен '€'"), types.KeyboardButton("Обмен '¥'"), types.KeyboardButton("Текущий курс"), types.KeyboardButton('Назад'))
    bot.send_message(message.chat.id, "Выберите валюту:", reply_markup=markup)

def get_cbr_rates(currency_code):
    """Получает курс валюты с cbr.ru или из JSON-файла."""
    if os.path.exists(JSON_FILE):
        try:
            with open(JSON_FILE, "r") as f:
                rates = json.load(f)
                return rates.get(currency_code)
        except (json.JSONDecodeError, KeyError) as e:
            print(f"Ошибка чтения или парсинга JSON-файла: {e}")

    try:
        url = "https://www.cbr.ru/scripts/XML_daily.asp"
        response = requests.get(url)
        response.raise_for_status()
        root = ET.fromstring(response.content)

        rates = {}
        for valute in root.findall('.//Valute'):
            code = valute.find('CharCode').text
            if code in ('USD', 'EUR', 'CNY'):
                rate = float(valute.find('Value').text.replace(',', '.'))
                rates[code] = rate
        with open(JSON_FILE, "w") as f:
            json.dump(rates, f)
        return rates.get(currency_code)

    except requests.exceptions.RequestException as e:
        print(f"Ошибка запроса: {e}")
        return None  # если ошибка запроса
    except ET.ParseError as e:
        print(f"Ошибка парсинга XML: {e}")
        return None
    except (AttributeError, ValueError) as e:
        print(f"Ошибка обработки данных: {e}")
        return None
    except Exception as e:
        print(f"Непредвиденная ошибка: {e}")
        return None

def update_json_from_cbr():
    """обновление JSON файла ."""
    try:
        url = "https://www.cbr.ru/scripts/XML_daily.asp"
        response = requests.get(url)
        response.raise_for_status()
        root = ET.fromstring(response.content)

        rates = {}
        for valute in root.findall('.//Valute'):
            code = valute.find('CharCode').text
            if code in ('USD', 'EUR', 'CNY'):
                rate = float(valute.find('Value').text.replace(',', '.'))
                rates[code] = rate
        with open(JSON_FILE, "w") as f:
            json.dump(rates, f)
        return True  
    except Exception as e:
        print(f"Error updating JSON from CBR: {e}")
        return False



@bot.message_handler(func=lambda message: True) 
# Обработчик всех текстовых сообщений
def handle_message(message):
    global chosen_currency, amount

    if not update_json_from_cbr():
        print("Warning: Failed to update JSON from cbr.ru. Using cached data.")
        # обновление данных json файла
    if message.text in ["Обмен '$'", "Обмен '€'", "Обмен '¥'"]:
        currency_mapping = {"'$'": "USD", "'€'": "EUR", "'¥'": "CNY"}
        chosen_currency = currency_mapping.get(message.text.split()[1])
        if chosen_currency:
            bot.reply_to(message, f"Введите сумму {chosen_currency} для конвертации в рубли:")
        else:
            bot.reply_to(message, "Ошибка: Неизвестная валюта.")
#проверка на дурака
    elif chosen_currency and message.text.isdigit(): #пришло ли число сообщением
        amount = float(message.text)
        rate = get_cbr_rates(chosen_currency)
        if rate:
            result = amount * rate
            bot.reply_to(message, f"Результат конвертации: {amount} {chosen_currency} = {result:.2f} RUB")
            chosen_currency = None
            amount = None
        else:
            #данные из JSON, если запрос к cbr.ru не удался
            try:
                with open(JSON_FILE, 'r') as f:
                    rates = json.load(f)
                    rate = rates.get(chosen_currency)
                    if rate:
                        result = amount * rate
                        bot.reply_to(message, f"Результат конвертации (данные из кэша): {amount} {chosen_currency} = {result:.2f} RUB")
                    else:
                        bot.reply_to(message, "Ошибка: Курс валюты не найден (ни в онлайн-источнике, ни в кэше).")
            except (FileNotFoundError, json.JSONDecodeError):
                bot.reply_to(message, "Ошибка: Кэш курсов валют недоступен.")

    elif message.text == "Назад":
        welcome(message)
    elif message.text == "Текущий курс":
        currencies = {"USD": "Доллар США", "EUR": "Евро", "CNY": "Юань"}
        rates_data = {}
        for cur, name in currencies.items():
            rate = get_cbr_rates(cur)
            if rate:
              rates_data[name] = rate
            else:
              rates_data[name] = "Ошибка получения курса"
        result = '\n'.join([f"{name}: {rate:.2f}" for name, rate in rates_data.items()])
        bot.reply_to(message, f"Текущие курсы:\n{result}")


bot.infinity_polling()
