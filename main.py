import telebot
from telebot import types
import openai
import traceback
import random
import words
from time import *
import os 
from config import TOKEN_BOT, BLOCKED_USERS, STOP_MSG, WELCOME_MSG, INFO_MSG, UNIT_NAMES, APIKEY
bot = telebot.TeleBot(TOKEN_BOT)


modelsAi = []
for i in range(0, len(APIKEY)):
    openai.api_key = APIKEY[i]
    modelsAi.append([openai.chat.completions, 0])


def communicateAi(receivedText):
    
    message = []
    answer = None
    for indexModel in range(0, len(modelsAi)): #choose ai model for generating 
        if modelsAi[indexModel][1] == 0:
            modelsAi[indexModel][1] = 1 
            break
    print(f"generating... model: {indexModel}")

    try:
        message.append({
            'role': 'user',
            'content': receivedText})
        response = modelsAi[indexModel][0].create(
            model='gpt-3.5-turbo',
            messages= message)
        answer = response.choices[0].message.content
        message.append({
            'role': 'assistant',
            'content': answer})
        modelsAi[indexModel][1] = 0
    except: 
        modelsAi[indexModel][1] = 1
    return answer


def chooseCommunicateText(comm, selectedUnit, sentence = '', userAnswer = ''): #choose text appeal 
        print(f'{comm}, unit = {selectedUnit}')
        wordsGen = words.wordsArray[f'unit{selectedUnit}']
        random.shuffle(wordsGen)
        if comm == "gen":
            return f'''Составь с одним - пятью словами из списка: "{wordsGen}" одно небольшое предложение. Не используй слова, которых нет в списке! Можешь добавить грамматику: {words.grammarArray[f'unit{selectedUnit}']}. После напиши "|" и правильный перевод твоего предложения на русский язык.'''
        elif comm == "com":
            return f'''Мне дали список китайский слов: {words.wordsArray[f'unit{selectedUnit}']}. Также дали предложение, которое я должен перевести на китайский с использованием этого списка слов. Это предложение надо перевести: {sentence}. Мой перевод: {userAnswer}. Подскажи, правильно ли я дословно перевел, если есть ошибки, то кратко объясни их. Дай очень краткий ответ.'''


@bot.message_handler(commands = ['start', 'info', 'stop', 'testing']) #choose message processing
def command_processing(message):
    global typeTesting, selectedUnit, answerFlag, testing, userAnswer
    if message.chat.id not in BLOCKED_USERS:
        if message.text.startswith('/'):
            if message.text == '/start':
                bot.send_message(message.chat.id, WELCOME_MSG)
            elif message.text == '/info':
                bot.send_message(message.chat.id, INFO_MSG, parse_mode='HTML')
            elif message.text == '/stop':
                bot.send_message(message.chat.id, STOP_MSG)
                testing = 0
            elif message.text == '/testing':
                item = []
                markup = types.InlineKeyboardMarkup(row_width=2)
                for i in range(0, len(UNIT_NAMES)):
                    item.append(types.InlineKeyboardButton(f"{i + 1}: {UNIT_NAMES[i]}", callback_data=f"Unit {i + 1}"))
                for i in range(0, len(UNIT_NAMES)):
                    markup.add(item[i])
                bot.send_message(message.chat.id, "Выберите UNIT, которых хотите практиковать", reply_markup=markup)
                
                answerFlag = 1
                selectedUnit = 0
                typeTesting = 0
                while answerFlag: pass
                print(selectedUnit, typeTesting)

                item = []
                markup = types.InlineKeyboardMarkup(row_width=2)
                item.append(types.InlineKeyboardButton("Voice", callback_data="Voice"))
                item.append(types.InlineKeyboardButton("Text", callback_data="Text"))
                markup.add(item[0])
                markup.add(item[1])

                bot.send_message(message.chat.id, "Выберите режим, в котором будет проходить тренировка", reply_markup=markup)

                answerFlag = 1
                while answerFlag: pass
                print(selectedUnit, typeTesting)

                #---TESTING---
                bot.send_message(message.chat.id, f"Тестирование запущено!")

                testing = 1
                while testing:
                    bot.send_chat_action(message.chat.id, 'typing')
                    try:
                        sentence, translate = communicateAi(chooseCommunicateText("gen", selectedUnit=selectedUnit)).split("|")
                    except:
                        try:
                            sentence, translate = communicateAi(chooseCommunicateText("gen", selectedUnit=selectedUnit)).split("|")
                        except:
                            bot.send_message(message.chat.id, "Извините, произошла ошибка. Тестирование завершено.")
                            break
                    
                    bot.send_message(message.chat.id, f'<b>Переведите:</b>\n{translate.lstrip()}', parse_mode='HTML')
                    userAnswer = ''
                    while userAnswer == '': pass
                    bot.send_chat_action(message.chat.id, 'typing')
                    botAnswer = communicateAi(chooseCommunicateText("com", selectedUnit=selectedUnit, sentence=sentence, userAnswer=userAnswer))
                    bot.send_message(message.chat.id, botAnswer)
                    sleep(1)


@bot.message_handler(func= lambda massage: True) #choose message processing
def text_processing(message):
    global userAnswer
    if testing and typeTesting == 2:
        userAnswer = message.text
    elif typeTesting == 1:
        bot.send_message(message.chat.id, "Простите, ваш режим - Voice. Отправьте голосовое сообщение с переводом.")


@bot.callback_query_handler(func=lambda message:True)
def checkCallbackUnitType(callback):
    global typeTesting, selectedUnit, answerFlag
    if callback.data.split(' ')[0] == "Unit":
        selectedUnit = int(callback.data.split(' ')[1])
    elif callback.data.split(' ')[0] == "Voice":
        typeTesting = 1
    elif callback.data.split(' ')[0] == "Text":
        typeTesting = 2
    answerFlag = 0
    bot.delete_message(callback.message.chat.id, callback.message.id)


@bot.message_handler(content_types=['voice'])
def repeat_all_message(message):
    global userAnswer, testing, typeTesting
    if testing and typeTesting == 1: 
        file_info = bot.get_file(message.voice.file_id)
        downloaded_file = bot.download_file(file_info.file_path)

        with open(f'{message.chat.id}{message.id}.ogg', 'wb') as file: 
            file.write(downloaded_file)
        audio_file = open(f'{message.chat.id}{message.id}.ogg', "rb")

        transcript = openai.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file,
            language="zh"
        )
        
        userAnswer = transcript.text
        os.remove(f'{message.chat.id}{message.id}.ogg')
    elif typeTesting == 2:
        bot.send_message(message.chat.id, "Простите, ваш решим - Text. Напишите перевод текстом.")


if __name__ == '__main__':
    bot.polling(none_stop=True)