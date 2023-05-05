import asyncio
import datetime
from typing import List

from clients.tg_client import TgClient
from clients.pills_client import PillsClient
from clients.dcs import UpdateObj, ReplyKeyboardMarkup

button_text = {"getPills": "Когда закончатся?", "safeAddPills": "Добавить без записи" , "addPills": "Добавить таблеток", "setMed": "Новый препарат", "deleteMed": "Удалить препарат"}
main_buttons = [ [{"text": "Когда закончатся?"}],  
    [{"text": "Добавить таблеток"}, {"text": "Добавить без записи"}],
    [{"text": "Новый препарат"}, {"text": "Удалить препарат"}] ]
main_keyboard = ReplyKeyboardMarkup.Schema().load({"keyboard": main_buttons, "one_time_keyboard": True})

class Worker:
    def __init__(self, token: str, queue: asyncio.Queue, concurrent_workers: int):
        self.tg_client = TgClient(token)
        self.pills_client = PillsClient()
        self.queue = queue
        self.concurrent_workers = concurrent_workers
        self._tasks: List[asyncio.Task] = []

    async def handle_update(self, upd: UpdateObj):
        text = upd.message.text
        get_user_state = await self.pills_client.get_user_state(upd.message.from_.username)
        try: 
            state = get_user_state["user_state"]
        except:
            state = ""
        print(state)
        if state == "start": state = ""

        if text.lower().__contains__("назад") or text.lower().__contains__("меню") or text.lower().__contains__("start"):
            await start(upd, self.tg_client, self.pills_client)
        elif text.lower().__contains__(button_text["getPills"].lower()):
            await getPills(upd, self.tg_client, self.pills_client)
        elif text.lower().__contains__("добавить таблеток") or state.__contains__("addPills"):
            await addPills(upd, state, self.tg_client, self.pills_client)
        elif text.lower().__contains__("добавить без записи") or state.__contains__("safeAddPills"):
            await safeAddPills(upd, state, self.tg_client, self.pills_client)
        elif text.lower().__contains__(button_text["setMed"].lower()) or state.__contains__("setMed"):
            await setMed(upd, state, self.tg_client, self.pills_client)
        elif text.lower().__contains__(button_text["deleteMed"].lower()) or state.__contains__("deleteMed"):
            await deleteMed(upd, state, self.tg_client, self.pills_client)
        else:
            await start(upd, self.tg_client, self.pills_client)

    async def _worker(self):
        while True:
            upd = await self.queue.get()
            try:
                await self.handle_update(upd)
            finally:
                self.queue.task_done()

    async def start(self):
        self._tasks = [asyncio.create_task(self._worker()) for _ in range(self.concurrent_workers)]

    async def stop(self):
        await self.queue.join()
        for t in self._tasks:
            t.cancel()



async def start(upd: UpdateObj, tg_client: TgClient, pills_client: PillsClient):
    text = "Привет! Я бот, который может считать все твои лекарства и говорить, когда лекарства кончатся"
    await tg_client.send_message(upd.message.chat.id, text, reply_markup=main_keyboard)
    await pills_client.user_state(upd.message.from_.username, "start")

async def getPills(upd: UpdateObj, tg_client: TgClient, pills_client: PillsClient):
    login = upd.message.from_.username
    pills = await pills_client.pills_count(login)
    print(pills)
    text = ""
    for pill, date in pills.items():
        text +=  f"{str(pill)}: {str(date)}\n"
    await tg_client.send_message(upd.message.chat.id, text, reply_markup=main_keyboard) 
    await pills_client.user_state(login, "getPills")

async def addPills(upd: UpdateObj, state: str, tg_client: TgClient, pills_client: PillsClient):
    login = upd.message.from_.username
    message = upd.message.text
    if state == "addPills_choiceRetry" or state == "addPills_countRetry" or not state.__contains__("addPills") :
        pills = await pills_client.get_me(login)
        i = 0
        buttons = []
        button = []
        for pill, cont in pills.items():
            i+=1
            button.append({"text": str(pill)})
            if i%2 == 0:
                buttons.append(button)
                button = []
        if i%2 != 0:
            buttons.append(button)
            button.append({"text": "Назад"})
        else:
            buttons.append([{"text": "Назад"}])
        text = "Выбери тот препарат, к которому хочешь добавить таблетки"
        keyboard = ReplyKeyboardMarkup.Schema().load({"keyboard": buttons, "one_time_keyboard": True})
        await tg_client.send_message(upd.message.chat.id, text, reply_markup=keyboard) 
        await pills_client.user_state(login, "addPills_choice")
    elif state == "addPills_choice":
        pills = await pills_client.get_me(login)
        try:
            pills[message]
        except:
            text = "Нужно выбрать :)"
            await tg_client.send_message(upd.message.chat.id, text) 
            await addPills(upd, "addPills_choiceRetry", tg_client, pills_client)
            return
        text = "Напиши числом, сколько таблеток нужно добавить"
        buttons = [ [{"text": "Назад"}] ]
        keyboard = ReplyKeyboardMarkup.Schema().load({"keyboard": buttons, "one_time_keyboard": True})
        await tg_client.send_message(upd.message.chat.id, text)
        await pills_client.user_state(login, f"addPills_count_{message}") #Туть конец стейта будет именем препарата
    elif state.__contains__("addPills_count_"):
        try:
            count = int(message)
            if count > 10000 or count < 0: raise Exception('Wrong int!')
        except:
            text = "Нужно написать число :з"
            await tg_client.send_message(upd.message.chat.id, text) 
            await addPills(upd, "addPills_countRetry", tg_client, pills_client)
            return
        pill = str(state.replace("addPills_count_", ""))
        await pills_client.add_pills(login, pill, count)
        text = "Все отлично, таблетки добавлены!"
        await tg_client.send_message(upd.message.chat.id, text, reply_markup=main_keyboard)
        await pills_client.user_state(upd.message.from_.username, "start")
        
async def safeAddPills(upd: UpdateObj, state: str, tg_client: TgClient, pills_client: PillsClient):
    login = upd.message.from_.username
    message = upd.message.text
    if state == "safeAddPills_choiceRetry" or state == "safeAddPills_countRetry" or not state.__contains__("safeAddPills") :
        pills = await pills_client.get_me(login)
        i = 0
        buttons = []
        button = []
        for pill, cont in pills.items():
            i+=1
            button.append({"text": str(pill)})
            if i%2 == 0:
                buttons.append(button)
                button = []
        if i%2 != 0:
            buttons.append(button)
            button.append({"text": "Назад"})
        else:
            buttons.append([{"text": "Назад"}])
        text = "Это безопасное добавление, которое нужно для планирования. В конце я выведу дату, когда кончится препарат, если купить введенное количество таблеток"
        await tg_client.send_message(upd.message.chat.id, text)
        text = "Выбери тот препарат, к которому хочешь добавить таблетки. "
        keyboard = ReplyKeyboardMarkup.Schema().load({"keyboard": buttons, "one_time_keyboard": True})
        await tg_client.send_message(upd.message.chat.id, text, reply_markup=keyboard) 
        await pills_client.user_state(login, "safeAddPills_choice")
    elif state == "safeAddPills_choice":
        pills = await pills_client.get_me(login)
        try:
            pills[message]
        except:
            text = "Нужно выбрать :)"
            await tg_client.send_message(upd.message.chat.id, text) 
            await safeAddPills(upd, "safeAddPills_choiceRetry", tg_client, pills_client)
            return
        text = "Напиши числом, сколько таблеток нужно добавить"
        buttons = [ [{"text": "Назад"}] ]
        keyboard = ReplyKeyboardMarkup.Schema().load({"keyboard": buttons, "one_time_keyboard": True})
        await tg_client.send_message(upd.message.chat.id, text)
        await pills_client.user_state(login, f"safeAddPills_count_{message}") #Туть конец стейта будет именем препарата
    elif state.__contains__("safeAddPills_count_"):
        try:
            count = int(message)
            if count > 10000 or count < 0: raise Exception('Wrong int!')
        except:
            text = "Нужно написать число :з"
            await tg_client.send_message(upd.message.chat.id, text) 
            await safeAddPills(upd, "safeAddPills_countRetry", tg_client, pills_client)
            return
        pill = str(state.replace("safeAddPills_count_", ""))
        date = (await pills_client.pills_safe_count(login, pill, count))["Последний день"]
        text = f"Последний день приема - {date}"
        await tg_client.send_message(upd.message.chat.id, text, reply_markup=main_keyboard)
        await pills_client.user_state(upd.message.from_.username, "start")

async def setMed(upd: UpdateObj, state: str, tg_client: TgClient, pills_client: PillsClient):
    login = upd.message.from_.username
    message = upd.message.text
    if state == "setMed_Retry" or not state.__contains__("setMed") :
        text = "Напиши название нового препарата"
        keyboard = ReplyKeyboardMarkup.Schema().load({"keyboard": [[{"text": "Назад"}]], "one_time_keyboard": True})
        await tg_client.send_message(upd.message.chat.id, text, reply_markup=keyboard) 
        await pills_client.user_state(login, "setMed_nameChoice")
    elif state == "setMed_nameChoice":
        pills = await pills_client.get_me(login)
        exsisting_pills = []
        for pill, cont in pills.items():
            exsisting_pills.append(pill)
        if message in exsisting_pills:
            text = "Препарат с таким названием уже существует :с"
            await tg_client.send_message(upd.message.chat.id, text)
            await setMed(upd, "setMed_Retry", tg_client, pills_client)
            return
        text = "Напиши числом, сколько таблеток в день ты принимаешь"
        buttons = [ [{"text": "Назад"}] ]
        keyboard = ReplyKeyboardMarkup.Schema().load({"keyboard": buttons, "one_time_keyboard": True})
        await tg_client.send_message(upd.message.chat.id, text)
        await pills_client.user_state(login, f"setMed_count_{message}") #Туть конец стейта будет именем препарата
    elif state.__contains__("setMed_count_"):
        try:
            count = int(message)
            if count > 100 or count < 1: raise Exception('Wrong int!')
        except:
            text = "Нужно написать число от 1 до 100 :з"
            await tg_client.send_message(upd.message.chat.id, text) 
            await setMed(upd, "setMed_Retry", tg_client, pills_client)
            return
        pill = str(state.replace("setMed_count_", ""))
        text = "А теперь напиши числом, сколько таблеток у тебя сейчас есть"
        buttons = [ [{"text": "Назад"}] ]
        keyboard = ReplyKeyboardMarkup.Schema().load({"keyboard": buttons, "one_time_keyboard": True})
        await tg_client.send_message(upd.message.chat.id, text)
        await pills_client.user_state(login, f"setMed_end_{pill}_{count}")
    elif state.__contains__("setMed_end_"):
        try:
            count = int(message)
            if count > 9999 or count < 0: raise Exception('Wrong int!')
        except:
            text = "Нужно написать число от 0 до 9999 :з"
            await tg_client.send_message(upd.message.chat.id, text) 
            await setMed(upd, "setMed_Retry", tg_client, pills_client)
            return
        info = str(state.replace("setMed_end_", "")).split("_")
        pill = info[0]
        pills_use = info[1]
        print (await pills_client.set_med(login, pill, count, pills_use))
        text = "Все отлично, новый препарат добавлен!"
        await tg_client.send_message(upd.message.chat.id, text, reply_markup=main_keyboard)
        await pills_client.user_state(upd.message.from_.username, "start")

async def deleteMed(upd: UpdateObj, state: str, tg_client: TgClient, pills_client: PillsClient):
    login = upd.message.from_.username
    message = upd.message.text
    if state == "deleteMed_Retry" or not state.__contains__("deleteMed") :
        pills = await pills_client.get_me(login)
        i = 0
        buttons = []
        button = []
        for pill, cont in pills.items():
            i+=1
            button.append({"text": str(pill)})
            if i%2 == 0:
                buttons.append(button)
                button = []
        if i%2 != 0:
            buttons.append(button)
            button.append({"text": "Назад"})
        else:
            buttons.append([{"text": "Назад"}])
        text = "ВНИМАНИЕ, ЭТО НЕОБРАТИМО\n\nВыбери тот препарат, который хочешь удалить"
        keyboard = ReplyKeyboardMarkup.Schema().load({"keyboard": buttons, "one_time_keyboard": True})
        await tg_client.send_message(upd.message.chat.id, text, reply_markup=keyboard) 
        await pills_client.user_state(login, "deleteMed_choice")
    elif state == "deleteMed_choice":
        pills = await pills_client.get_me(login)
        try:
            pills[message]
        except:
            text = "Нужно выбрать :)"
            await tg_client.send_message(upd.message.chat.id, text) 
            await addPills(upd, "addPills_choiceRetry", tg_client, pills_client)
            return
        print (await pills_client.delete_med(login, message))
        text = "Препарат успешно удален!"
        await tg_client.send_message(upd.message.chat.id, text, reply_markup=main_keyboard)
        await pills_client.user_state(login, "start")
    