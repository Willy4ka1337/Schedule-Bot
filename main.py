from html.parser import HTMLParser
from datetime import datetime
import requests
import re
import telebot
from telebot import types
import locale
import time
import mysql.connector as mysql

connection = mysql.connect(
    host='localhost',
    user='root',
    password='',
    database='schedule'
)
cursor = connection.cursor()

locale.setlocale(locale.LC_ALL, '')
bot = telebot.TeleBot('7460665722:AAHoum36rIGL3sovFiG0vdJ_oJ-fdt6VgTQ')

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
groups = []

tech_jobs = False

class MyHTMLParser(HTMLParser):
    reading = False
    gid = 0
    readType = -1
    key = -1
    subject = ""
    teacher = ""
    classroom = ""
    def handle_starttag(self, tag, attrs):
        if tag == 'a':
            self.reading = True
            self.readType = 0
            for attr in attrs:
                m = re.search(r'/site/schedule\?group_id=[0-9]+&day=.+&onlyMine=', attr[1])
                if(m):
                    self.gid = m.group(0).replace('/site/schedule?group_id=', '')
                    self.gid = int(self.gid[:2])
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
            if self.readType == 0:
                if(re.search(r'^\s*[А-Я]+[а-я]*\s[0-9]+$', data)):
                    groups.append([self.gid, data])
                elif(re.search(r"^\D{2}\s*\d{2}\.\d{2}\.\d{4}$", data)):
                    days.append(data)
            elif self.readType == 1:
                if data != '-':
                    if re.search(r"^\d{1}$", data):
                        self.key = int(data)
                    elif re.search(r"^\d{4}$", data) or data == "спортзал" or data == "дистант":
                        self.classroom = data
                    elif re.search(r"^[А-Я][а-я]+\s[А-Я][а-я\.]+\s[А-Я][а-я\.]+$", data):
                        self.teacher = data
                    elif len(data) > 1:
                        self.subject = data
                else:
                    self.subject = ""
                    self.teacher = ""
                    self.classroom = ""

def print_string(date):
    result_string = f"Расписание на {date} \n"
    for i in schedule:
        if(len(i[1]) > 1):
            string = f"{numbers[i[0]-1]} Пара\n\
⏰ Время: {times[i[0]-1][0]} - {times[i[0]-1][1]}\n\
{i[1] and f'📚 <b>Предмет: {i[1]}</b>\n' or ''}\
{i[2] and f'👤 Преподаватель: {i[2]}\n' or ''}\
{i[3] and f'🏛️ Кабинет: {i[3]}\n' or ''}"
            
            result_string = f"{result_string}\n{string}"
    return result_string

@bot.message_handler(commands = ['start'])
def start(message):
    if(tech_jobs and message.from_user.id != 5613054609):
        return bot.send_message(message.from_user.id, f"Бот временно на тех. работах, подождите пожалуйста")
        
    schedule.clear()
    days.clear()
    groups.clear()
    current_date = datetime.now().strftime('%d.%m.%Y')
    response = requests.get(f'https://journal.zifra42.ru/site/schedule?group_id=0&day={current_date}&onlyMine=')
    parser = MyHTMLParser()
    parser.feed(response.text)

    # SQL Request
    
    request = f"SELECT `group_id` FROM `schedule_users` WHERE `telegram_id` = '{message.from_user.id}'"
    cursor.execute(request)
    rows = cursor.fetchall()

    current_date = datetime.now().strftime('%d.%m.%Y')

    if(rows):
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        btn1 = types.KeyboardButton("Посмотреть расписание")
        btn2 = types.KeyboardButton("Изменить группу")
        markup.add(btn1, btn2)
        bot.send_message(message.from_user.id, f"👋Привет! Это бот для просмотра расписания!\n👌Нажми кнопку \"Посмотреть расписание\" или введи дату.\nПример: {current_date}", reply_markup=markup)
    else:
        keyboard = types.InlineKeyboardMarkup()
        btns_in_row = 3
        keyboard.row_width = btns_in_row
        btn_count = len(groups)
        btn_list = []
        for i in range(0, btn_count, 3):
            btn_list = []
            for n in range(3):
                if(i+n >= btn_count):
                    break
                btn = types.InlineKeyboardButton(groups[i+n][1], callback_data = f"select group {groups[i+n][0]}")
                btn_list.append(btn)
            keyboard.row(*btn_list)
        bot.send_message(message.from_user.id, "👋Привет! Это бот для просмотра расписания. \n🎓Сейчас тебе нужно выбрать свою группу.\n☺️Для этого нажми соответствующую кнопку ниже.", reply_markup=keyboard)

    ccurrent_date = datetime.now().strftime('%d.%m.%Y %H:%M:%S')

    print(f"[{ccurrent_date}] user: {message.from_user.username} (id: {message.from_user.id}) - show start message")
    query(f"INSERT INTO `schedule_log` (`time`, `name`, `telegram_id`, `log`) VALUES (NOW(), '{message.from_user.username}', '{message.from_user.id}', 'show start message')")

@bot.message_handler(content_types=['text'])
def get_text_messages(message):
    if(tech_jobs and message.from_user.id != 5613054609):
        return bot.send_message(message.from_user.id, f"Бот временно на тех. работах, подождите пожалуйста")
    if message.text == 'Посмотреть расписание':
        schedule.clear()
        days.clear()
        groups.clear()
        current_date = datetime.now().strftime('%d.%m.%Y')

        request = f"SELECT `group_id` FROM `schedule_users` WHERE `telegram_id` = '{message.from_user.id}'"
        cursor.execute(request)
        rows = cursor.fetchall()
        if(rows):
            for data in rows:
                response = requests.get(f'https://journal.zifra42.ru/site/schedule?group_id={data[0]}&day={current_date}&onlyMine=')
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

                markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
                btn1 = types.KeyboardButton("Посмотреть расписание")
                btn2 = types.KeyboardButton("Изменить группу")
                markup.add(btn1, btn2)

                bot.send_message(message.from_user.id, 'Выберите дату', reply_markup=keyboard)
                ccurrent_date = datetime.now().strftime('%d.%m.%Y %H:%M:%S')

                print(f"[{ccurrent_date}] user: {message.from_user.username} (id: {message.from_user.id}) - show days")
                query(f"INSERT INTO `schedule_log` (`time`, `name`, `telegram_id`, `log`) VALUES (NOW(), '{message.from_user.username}', '{message.from_user.id}', 'show days')")

                schedule.clear()
                days.clear()
                groups.clear()
        else:
            bot.send_message(message.from_user.id, 'Вы еще не выбрали группу.')

    elif message.text == 'Изменить группу':
        schedule.clear()
        days.clear()
        groups.clear()

        current_date = datetime.now().strftime('%d.%m.%Y')
        response = requests.get(f'https://journal.zifra42.ru/site/schedule?group_id=0&day={current_date}&onlyMine=')
        parser = MyHTMLParser()
        parser.feed(response.text)

        keyboard = types.InlineKeyboardMarkup()
        btns_in_row = 3
        keyboard.row_width = btns_in_row
        btn_count = len(groups)
        btn_list = []
        for i in range(0, btn_count, 3):
            btn_list = []
            for n in range(3):
                if(i+n >= btn_count):
                    break
                btn = types.InlineKeyboardButton(groups[i+n][1], callback_data = f"select group {groups[i+n][0]}")
                btn_list.append(btn)
            keyboard.row(*btn_list)
        bot.send_message(message.from_user.id, "☺️Выбери группу нажав на кнопку ниже", reply_markup=keyboard)
    elif re.search(r"^\d{2}\.\d{2}\.\d{4}$", message.text):
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        btn1 = types.KeyboardButton("Посмотреть расписание")
        btn2 = types.KeyboardButton("Изменить группу")
        markup.add(btn1, btn2)

        schedule.clear()
        days.clear()
        groups.clear()

        request = f"SELECT `group_id` FROM `schedule_users` WHERE `telegram_id` = '{message.from_user.id}'"
        cursor.execute(request)
        rows = cursor.fetchall()
        if(rows):
            for data in rows:
                day = message.text[:2]
                month = message.text[3:5]
                year = message.text[6:]
                date = datetime(int(year), int(month), int(day)).strftime('%A, %d.%m.%Y')

                response = requests.get(f'https://journal.zifra42.ru/site/schedule?group_id={data[0]}&day={message.text}&onlyMine=')
                parser = MyHTMLParser()
                parser.feed(response.text)
                bot.send_message(message.from_user.id, print_string(date), parse_mode="HTML")
                current_date = datetime.now().strftime('%d.%m.%Y %H:%M:%S')
                print(f"[{current_date}] user: {message.from_user.username} (id: {message.from_user.id}) - input date")
                query(f"INSERT INTO `schedule_log` (`time`, `name`, `telegram_id`, `log`) VALUES (NOW(), '{message.from_user.username}', '{message.from_user.id}', 'input date')")

                schedule.clear()
                days.clear()
                groups.clear()
        else:
            bot.send_message(message.from_user.id, 'Вы еще не выбрали группу.')
    # elif(message.text == 'mtest'):
        # request = f"SELECT * FROM `schedule_users`"
        # cursor.execute(request)
        # rows = cursor.fetchall()
        # if(rows):
        #     for data in rows:
        #         userid = data[1]
        #         UsrInfo = bot.get_chat_member(userid, userid).user
        #         query(f"UPDATE `schedule_users` SET `user_name`='{UsrInfo.username}' WHERE `telegram_id`='{userid}'")



@bot.callback_query_handler(func=lambda call: True)
def callback_day(call):
    if(tech_jobs and call.message.chat.id != 5613054609):
        return bot.send_message(call.message.chat.id, f"Бот временно на тех. работах, подождите пожалуйста")
    text = call.data
    
    ccurrent_date = datetime.now().strftime('%d.%m.%Y %H:%M:%S')
    if(re.search(r'select group \d+', text)):
        gid = text[13:]
        request = f"SELECT `group_id` FROM `schedule_users` WHERE `telegram_id` = '{call.message.chat.id}'"
        cursor.execute(request)
        rows = cursor.fetchall()
        if(rows):
            query(f"UPDATE `schedule_users` SET `group_id`='{gid}' WHERE `telegram_id`='{call.message.chat.id}'")
        else:
            query(f"INSERT INTO `schedule_users` (`telegram_id`, `group_id`, `user_name`) VALUES ('{call.message.chat.id}', '{gid}', '{call.message.chat.username}')")

        
        current_date = datetime.now().strftime('%d.%m.%Y')
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        btn1 = types.KeyboardButton("Посмотреть расписание")
        btn2 = types.KeyboardButton("Изменить группу")
        markup.add(btn1, btn2)
        bot.send_message(call.message.chat.id, f"👍Ты успешно выбрал(-а) свою группу.\n👌Нажми на кнопку \"Посмотреть расписание\", или введи дату.\nПример: {current_date}", reply_markup=markup)
        
        print(f"[{ccurrent_date}] user: {call.message.chat.username} (id: {call.message.chat.id}) - select group")
        query(f"INSERT INTO `schedule_log` (`time`, `name`, `telegram_id`, `log`) VALUES (NOW(), '{call.message.chat.username}', '{call.message.chat.id}', 'select group')")
    else:
        request = f"SELECT `group_id` FROM `schedule_users` WHERE `telegram_id` = '{call.message.chat.id}'"
        cursor.execute(request)
        rows = cursor.fetchall()
        if(rows):
            for data in rows:
                markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
                btn1 = types.KeyboardButton("Посмотреть расписание")
                btn2 = types.KeyboardButton("Изменить группу")
                markup.add(btn1, btn2)

                schedule.clear()
                days.clear()
                groups.clear()
                date = text[3:]
                response = requests.get(f'https://journal.zifra42.ru/site/schedule?group_id={data[0]}&day={date}&onlyMine=')
                parser = MyHTMLParser()
                parser.feed(response.text)

                day = date[:2]
                month = date[3:5]
                year = date[6:]
                date = datetime(int(year), int(month), int(day)).strftime('%A, %d.%m.%Y')

                bot.send_message(call.message.chat.id, print_string(date), parse_mode="HTML")
                print(f"[{ccurrent_date}] user: {call.message.chat.username} (id: {call.message.chat.id}) - select day")
                query(f"INSERT INTO `schedule_log` (`time`, `name`, `telegram_id`, `log`) VALUES (NOW(), '{call.message.chat.username}', '{call.message.chat.id}', 'select day')")
        else:
            bot.send_message(call.message.chat.id, 'Вы еще не выбрали группу.')

    schedule.clear()
    days.clear()
    groups.clear()

def query(request):
    cursor.execute(request)
    connection.commit()

if __name__ == '__main__':
    try:
        bot.infinity_polling(none_stop=True)
    except Exception as e:
        time.sleep(15)
