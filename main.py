from html.parser import HTMLParser
import datetime
import requests
import re
import telebot
from telebot import types

bot = telebot.TeleBot('')

schedule = []
days = []
times = [
    ['08:30', '09:45'],
    ['09:55', '11:10'],
    ['11:50', '13:05'],
    ['13:15', '14:30'],
    ['15:10', '16:25'],
    ['16:35', '17:50'],
]
numbers = ['1️⃣','2️⃣','3️⃣','4️⃣','5️⃣','6️⃣']

class MyHTMLParser(HTMLParser):
    reading = False
    readType = -1
    key = -1
    subject = ""
    teacher = ""
    classroom = ""
    def handle_starttag(self, tag, attrs):
        if tag == 'a':
            self.reading = True
            self.readType = 0
        elif tag == 'tr':
            self.reading = True
            self.readType = 1

    def handle_endtag(self, tag):
        if tag == 'a':
            self.reading = False
        elif tag == 'tr':
            self.reading = False
            self.readType = 1
            schedule.append([self.key, self.subject, self.teacher, self.classroom])

    def handle_data(self, data):
        if self.reading:
            if re.search(regular(self.readType), data):
                if self.readType == 0:
                    days.append(data)
                if self.readType == 1:
                    if data != '-':
                        if re.search("^\d{1}$", data):
                            self.key = int(data)
                        elif re.search("^\d{4}$", data) or data == "спортзал":
                            self.classroom = data
                        elif re.search("^[А-Я][а-я]+\s[А-Я][а-я\.]+\s[А-Я][а-я\.]+$", data):
                            self.teacher = data
                        elif len(data) > 1:
                            self.subject = data
                    else:
                        self.subject = ""
                        self.teacher = ""
                        self.classroom = ""

def regular(x):
    if x == 0: return "^\D{2}\s*\d{2}\.\d{2}\.\d{4}$"
    elif x == 1: return ".*"

def print_string(date):
    result_string = f"Расписание на {date}\n"
    for i in schedule:
        if(len(i[1]) > 1):
            string = f"{numbers[i[0]-1]} Пара\n\
⏰ Время: {times[i[0]-1][0]} - {times[i[0]-1][1]}\n\
{i[1] and f"📚 Предмет: {i[1]}\n" or ""}\
{i[2] and f"👤 Преподаватель: {i[2]}\n" or ""}\
{i[3] and f"🏛️ Кабинет: {i[3]}\n" or ""}"
            
            result_string = f"{result_string}\n{string}"
    return result_string

@bot.message_handler(commands = ['start'])
def start(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn1 = types.KeyboardButton("Посмотреть расписание")
    markup.add(btn1)
    current_date = datetime.datetime.now().strftime('%d.%m.%Y')
    bot.send_message(message.from_user.id, f"Привет! Это бот для просмотра расписания!\nНажми кнопку \"Посмотреть расписание\" или введи дату.\nПример: {current_date}", reply_markup=markup)

@bot.message_handler(content_types=['text'])
def get_text_messages(message):

    if message.text == 'Посмотреть расписание':
        schedule.clear()
        days.clear()
        current_date = datetime.datetime.now().strftime('%d.%m.%Y')
        response = requests.get(f'https://journal.zifra42.ru/site/schedule?group_id=54&day={current_date}&onlyMine=')
        parser = MyHTMLParser()
        parser.feed(response.text)

        buttons = []
        for button in days:
            buttons.append(types.KeyboardButton(text=button))

        keyboard = types.InlineKeyboardMarkup()
        btns_in_row = 1
        keyboard.row_width = btns_in_row
        btn_count = len(buttons)
        row_count = btn_count//btns_in_row
        for i in range(row_count):
            btn_list = []
            for N in range(btns_in_row):
                btn = types.InlineKeyboardButton(days[i], callback_data = days[i])
                btn_list.append(btn)
            keyboard.row(*btn_list)
        bot.send_message(message.from_user.id, 'Выберите дату', reply_markup=keyboard)

        schedule.clear()
        days.clear()
    elif re.search("^\d{2}\.\d{2}\.\d{4}$", message.text):
        schedule.clear()
        days.clear()

        response = requests.get(f'https://journal.zifra42.ru/site/schedule?group_id=54&day={message.text}&onlyMine=')
        parser = MyHTMLParser()
        parser.feed(response.text)
        bot.send_message(message.from_user.id, print_string(message.text), parse_mode="HTML")
            
        schedule.clear()
        days.clear()


@bot.callback_query_handler(func=lambda call: True)
def callback_day(call):
    schedule.clear()
    days.clear()
    date = call.data[3:]
    response = requests.get(f'https://journal.zifra42.ru/site/schedule?group_id=54&day={date}&onlyMine=')
    parser = MyHTMLParser()
    parser.feed(response.text)
    bot.send_message(call.message.chat.id, print_string(date), parse_mode="HTML")
        
    schedule.clear()
    days.clear()

bot.infinity_polling(timeout=10, long_polling_timeout = 5)
