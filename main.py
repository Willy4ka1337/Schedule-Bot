from html.parser import HTMLParser
from datetime import datetime
import requests
import re
import telebot
from telebot import types
import locale
from lxml import etree
import psycopg2
import time

global connection
connection = psycopg2.connect("postgresql://root:S1k6aChqPHEnzHEYUWmEliHE1Zxf2430@dpg-cu57ei9u0jms73ffn9g0-a.oregon-postgres.render.com/schedule_bt89")
cursor = connection.cursor()

locale.setlocale(locale.LC_ALL, '')
bot = telebot.TeleBot('7460665722:AAEobn7bHcChGKsKc8u4WzNedJ7yUMTk3_U')

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

check_old_site = True

class MyHTMLParser(HTMLParser):
    reading = False
    gid = 0
    readType = -1
    key = -1
    subject = ""
    teacher = ""
    classroom = ""
    def handle_starttag(self, tag, attrs):
        if check_old_site:
            if tag == 'a':
                self.reading = True
                self.readType = 0
                for attr in attrs:
                    m = re.search(r'/site/schedule\?group_id=[0-9]+&day=.+', attr[1])
                    if(m):
                        self.gid = m.group(0).replace('/site/schedule?group_id=', '')
                        self.gid = int(self.gid[:2])
            elif tag == 'tr':
                self.reading = True
                self.readType = 1
        else:
            if tag == 'button':
                for attr in attrs:
                    if attr[1] == 'dateFiel1':
                        self.reading = True
                        self.readType = 0
                    if attr[1] != "Group":
                        groups.append([attr[1], attr[1]])

    def handle_endtag(self, tag):
        if self.reading:
            if check_old_site:
                if tag == 'a':
                    self.reading = False
                elif tag == 'tr':
                    self.reading = False
                    self.readType = 1
                    schedule.append([self.key, self.subject, self.teacher, self.classroom])
            else:
                if tag == 'button':
                    self.reading = False
                elif tag == 'h5':
                    self.reading = False

    def handle_data(self, data):
        if self.reading:
            if self.readType == 0:
                if check_old_site:
                    if(re.search(r'^\s*[А-Я]+[а-я]*\s[0-9]+$', data)):
                        groups.append([self.gid, data])
                    elif(re.search(r"^\D{2}\s*\d{2}\.\d{2}\.\d{4}$", data)):
                        days.append(data)
                else:
                    print(f"reading {data}")
                    if(re.search(r"^\s*\d{4}.\d{2}\.\d{2}$", data)):
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
⏰ Время: {times[i[0]-1][0]} - {times[i[0]-1][1]}\n"
            if(not check_old_site):
                if(i[4] > 0):
                    string += f"👥 Подгруппа: {str(i[4])}\n"
            if(len(i[1])>0):
                string += f"📚 <b>Дисциплина: {i[1]}</b>\n"
            if(len(i[2])>0):
                string += f"👤 Преподаватель: {i[2]}\n"
            if(len(i[3])>0):
                string += f"🏛️ Кабинет: {i[3]}\n"
            result_string = f"{result_string}\n{string}"
    return result_string

@bot.message_handler(commands = ['start'])
def start(message):
    if(tech_jobs and message.from_user.id != 5613054609):
        return bot.send_message(message.from_user.id, f"Бот временно на тех. работах, подождите пожалуйста")
        
    clearData()
    getGroupList()

    rows = checkGroup(message.from_user)

    current_date = datetime.now().strftime('%d.%m.%Y')

    def showH():
        markup = addMainButtons()
        bot.send_message(message.from_user.id, f"👋Привет! Это бот для просмотра расписания!\n👌Нажми кнопку \"Посмотреть расписание\" или введи дату.\nПример: {current_date}", reply_markup=markup)

    def showSelect():
        keyboard = buttonGroups()
        bot.send_message(message.from_user.id, "👋Привет! Это бот для просмотра расписания. \n🎓Сейчас тебе нужно выбрать свою группу.\n☺️Для этого нажми соответствующую кнопку ниже.", reply_markup=keyboard)

    if(rows):
        if(check_old_site):
            if(rows[0][0] > 0):
                showH()
            else:
                showSelect()
        else:
            if(len(str(rows[0][0])) > 0):
                showH()
            else:
                showSelect()
    else:
        showSelect()

    print(f"[{getCurrentTime()}] user: {message.from_user.username} (id: {message.from_user.id}) - show start message")
    query(f'INSERT INTO schedule_log ("time", "name", "telegram_id", "log") VALUES (NOW(), \'{message.from_user.username}\', \'{message.from_user.id}\', \'show start message\')')

@bot.message_handler(commands = ['switchsite'])
def switchsite(message):
    if(message.from_user.id != 5613054609):
        return bot.send_message(message.from_user.id, f"Команда доступна только администратору")
    
    global check_old_site
    check_old_site = not check_old_site
    bot.send_message(message.from_user.id, f"Теперь бот использует {check_old_site and 'старый' or 'новый'} сайт")

    print(f"[{getCurrentTime()}] user: {message.from_user.username} (id: {message.from_user.id}) - switch site")
    query(f'INSERT INTO schedule_log ("time", "name", "telegram_id", "log") VALUES (NOW(), \'{message.from_user.username}\', \'{message.from_user.id}\', \'switch site\')')

@bot.message_handler(commands = ['checksite'])
def checksite(message):
    if(tech_jobs and message.from_user.id != 5613054609):
        return bot.send_message(message.from_user.id, f"Бот временно на тех. работах, подождите пожалуйста")
    
    global check_old_site
    bot.send_message(message.from_user.id, f"Бот использует {check_old_site and 'старый' or 'новый'} сайт")

    print(f"[{getCurrentTime()}] user: {message.from_user.username} (id: {message.from_user.id}) - check site")
    query(f'INSERT INTO schedule_log ("time", "name", "telegram_id", "log") VALUES (NOW(), \'{message.from_user.username}\', \'{message.from_user.id}\', \'check site\')')

@bot.message_handler(content_types=['text'])
def get_text_messages(message):
    if(tech_jobs and message.from_user.id != 5613054609):
        return bot.send_message(message.from_user.id, f"Бот временно на тех. работах, подождите пожалуйста")
    if message.text == 'Посмотреть расписание':
        clearData()
        current_date = datetime.now().strftime('%d.%m.%Y')

        rows = checkGroup(message.from_user)
        if(rows):
            for data in rows:
                
                if check_old_site:
                    getInfoFromOldSite(data[0], current_date)
                else:
                    unix = datetime.now().timestamp()
                    for i in range(3):
                        struct = time.gmtime(unix+i*84000)
                        if struct.tm_wday != 6:
                            days.append("%04d-%02d-%02d" % (struct.tm_year, struct.tm_mon, struct.tm_mday))

                keyboard = buttonsDay()

                bot.send_message(message.from_user.id, 'Выберите дату', reply_markup=keyboard)

                print(f"[{getCurrentTime()}] user: {message.from_user.username} (id: {message.from_user.id}) - show days")
                query(f'INSERT INTO schedule_log ("time", "name", "telegram_id", "log") VALUES (NOW(), \'{message.from_user.username}\', \'{message.from_user.id}\', \'show days\')')

                clearData()
        else:
            bot.send_message(message.from_user.id, 'Вы еще не выбрали группу.')

    elif message.text == 'Изменить группу':
        selectNewGroup(message.from_user)
    elif re.search(r"^\d{2}\.\d{2}\.\d{4}$", message.text):
        markup = addMainButtons()
        clearData()
        rows = checkGroup(message.from_user)
        if(rows):
            for data in rows:
                day = message.text[:2]
                month = message.text[3:5]
                year = message.text[6:]
                if check_old_site:
                    getInfoFromOldSite(data[0], message.text)
                else:
                    payload = {
                        "DateShedule": f"{year}-{month}-{day}",
                        "Group": data[0],
                    }
                    getSchedule(payload)
                            
                date = datetime(int(year), int(month), int(day)).strftime('%A, %d.%m.%Y')
                bot.send_message(message.from_user.id, print_string(date), parse_mode="HTML", reply_markup=markup)
                print(f"[{getCurrentTime()}] user: {message.from_user.username} (id: {message.from_user.id}) - input date")
                query(f'INSERT INTO schedule_log ("time", "name", "telegram_id", "log") VALUES (NOW(), \'{message.from_user.username}\', \'{message.from_user.id}\', \'input date\')')

                clearData()
        else:
            bot.send_message(message.from_user.id, 'Вы еще не выбрали группу.')


@bot.callback_query_handler(func=lambda call: True)
def callback_day(call):
    if(tech_jobs and call.message.chat.id != 5613054609):
        return bot.send_message(call.message.chat.id, f"Бот временно на тех. работах, подождите пожалуйста")
    text = call.data
    
    if(re.search(r'select group +', text)):
        gid = text[13:]
        rows = rows = checkGroup(call.message.chat)
        if(rows):
            query(f'UPDATE schedule_users SET "{check_old_site and "group_id" or "group_string"}"=\'{gid}\' WHERE "telegram_id"=\'{call.message.chat.id}\'')
        else:
            query(f'INSERT INTO schedule_users ("telegram_id", "{check_old_site and "group_id" or "group_string"}", "user_name") VALUES (\'{call.message.chat.id}\', \'{gid}\', \'{call.message.chat.username}\')')

        current_date = datetime.now().strftime('%d.%m.%Y')
        markup = addMainButtons()
        bot.send_message(call.message.chat.id, f"👍Ты успешно выбрал(-а) свою группу.\n👌Нажми на кнопку \"Посмотреть расписание\", или введи дату.\nПример: {current_date}", reply_markup=markup)
        
        print(f"[{getCurrentTime()}] user: {call.message.chat.username} (id: {call.message.chat.id}) - select group")
        query(f'INSERT INTO schedule_log ("time", "name", "telegram_id", "log") VALUES (NOW(), \'{call.message.chat.username}\', \'{call.message.chat.id}\', \'select group\')')
    else:
        rows = checkGroup(call.message.chat)
        markup = addMainButtons()
        if(rows):
            date = check_old_site and text[3:] or text
            day = date[:2]
            month = date[3:5]
            year = date[6:]
            for data in rows:
                clearData()
                if check_old_site:
                    if(int(data[0]) > 0):
                        if(re.search(r"^\D{2}\s*\d{2}\.\d{2}\.\d{4}$", text)):
                            getInfoFromOldSite(data[0], date)
                            date = datetime(int(year), int(month), int(day)).strftime('%A, %d.%m.%Y')
                            bot.send_message(call.message.chat.id, print_string(date), parse_mode="HTML", reply_markup=markup)
                    else:
                        selectNewGroup(call.message.chat)
                else:
                    if(len(str(data[0])) > 0):
                        if(re.search(r"^\s*\d{4}\-\d{2}\-\d{2}$", text)):
                            payload = {
                                "DateShedule": date,
                                "Group": data[0],
                            }
                            getSchedule(payload)
                            year = date[:4]
                            month = date[5:7]
                            day = date[8:]
                            date = datetime(int(year), int(month), int(day)).strftime('%A, %d.%m.%Y')
                            bot.send_message(call.message.chat.id, print_string(date), parse_mode="HTML", reply_markup=markup)
                    else:
                        selectNewGroup(call.message.chat)

                print(f"[{getCurrentTime()}] user: {call.message.chat.username} (id: {call.message.chat.id}) - select day")
                query(f'INSERT INTO schedule_log ("time", "name", "telegram_id", "log") VALUES (NOW(), \'{call.message.chat.username}\', \'{call.message.chat.id}\', \'select day\')')
        else:
            bot.send_message(call.message.chat.id, 'Вы еще не выбрали группу.')

    clearData()

def query(request):
    cursor.execute(request)
    connection.commit()

def checkGroup(message):
    request = f'SELECT "{check_old_site and "group_id" or "group_string"}" FROM schedule_users WHERE "telegram_id" = \'{message.id}\''
    cursor.execute(request)
    rows = cursor.fetchall()
    return rows

def buttonGroups():
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
    return keyboard

def buttonsDay():
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
    return keyboard

def getInfoFromOldSite(group, date):
    response = requests.get(f'https://journal.zifra42.ru/site/schedule?group_id={group}&day={date}')
    parser = MyHTMLParser()
    parser.feed(response.text)


def getGroupList():
    if check_old_site:
        current_date = datetime.now().strftime('%d.%m.%Y')
        getInfoFromOldSite(0, current_date)
    else:
        response = requests.post(f'https://j.zifra42.ru/rasp/aftertomorow/')
        response.encoding = 'utf8'
        parser = MyHTMLParser()
        parser.feed(response.text)

def selectNewGroup(message):
    clearData()
    getGroupList()
    keyboard = buttonGroups()
    bot.send_message(message.id, "☺️Выбери группу нажав на кнопку ниже", reply_markup=keyboard)

def getSchedule(payload):
    response = requests.post(f'https://j.zifra42.ru/rasp/tomorow/php/SheduleTable.php', data=payload)
    parser = MyHTMLParser()
    parser.feed(response.text)
    table = etree.HTML(response.text).find("body/table")
    rows = iter(table)
    for row in rows:
        values = [col.text for col in row]
        if len(values[1]) == 1:
            schedule.append([int(values[1]), values[3], values[4], values[5], int(values[2])])

def addMainButtons():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn1 = types.KeyboardButton("Посмотреть расписание")
    btn2 = types.KeyboardButton("Изменить группу")
    markup.add(btn1, btn2)
    return markup

def getCurrentTime():
    return datetime.now().strftime('%d.%m.%Y %H:%M:%S')

def clearData():
    schedule.clear()
    days.clear()
    groups.clear()

if __name__ == '__main__':
    try:
        bot.infinity_polling(none_stop=True)
        if datetime.now().second == 0:
            requests.get('https://schedule-bot-iyku.onrender.com/')
            print('send request')
    except Exception as e:
        pass