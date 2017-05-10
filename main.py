'''
Created on 24 mar 2017

@author: Geko - Rocco
'''



from telegram.ext import Updater, CommandHandler, CallbackQueryHandler
import logging
import urllib
import requests
import telegram
import json
import googlemaps
import os
import sys
import datetime
import django
import numpy as np
from math import radians, cos, sin, asin, sqrt
from motionless import DecoratedMap, LatLonMarker
from telegram.keyboardbutton import KeyboardButton
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import MessageHandler, Filters
from builtins import str
from emoji import emojize
from future.utils import bytes_to_native_str
from array import array
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from numpy import choose
#from urllib.request import urlopen
#from smartBot.bot.models import UserAssociation
#from django.contrib.sessions.models import Session
#from smartBotWebApp.login.models import User as Login



TOKEN = "343706215:AAEaTYl_qXHsPxKMwC5rXRnrnESKEuThT2Y"
gmaps = googlemaps.Client(key='AIzaSyCHw4CGzrZOpOleKM3KCPPMI7jJV_MDkDI')
URL = "https://api.telegram.org/bot{}/".format(TOKEN)
WEBAPP = "https://enigmatic-woodland-33608.herokuapp.com//accounts/login"
choosenPosition = ''

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

def getEmoticon(b):
    return bytes_to_native_str(b)

''' web source: '''
''' https://github.com/python-telegram-bot/python-telegram-bot/blob/master/telegram/emoji.py '''

ZERO_KEYCAP = getEmoticon(b'\x30\xE2\x83\xA3')
ONE_KEYCAP = getEmoticon(b'\x31\xE2\x83\xA3')
TWO_KEYCAP = getEmoticon(b'\x32\xE2\x83\xA3')    
THREE_KEYCAP = getEmoticon(b'\x33\xE2\x83\xA3')
FOUR_KEYCAP = getEmoticon(b'\x34\xE2\x83\xA3')
FIVE_KEYCAP = getEmoticon(b'\x35\xE2\x83\xA3')
SIX_KEYCAP = getEmoticon(b'\x36\xE2\x83\xA3')
SEVEN_KEYCAP = getEmoticon(b'\x37\xE2\x83\xA3')
EIGHT_KEYCAP = getEmoticon(b'\x38\xE2\x83\xA3')
NINE_KEYCAP = getEmoticon(b'\x39\xE2\x83\xA3')
#emoticons dichiarate


def start(bot, update, args, chat_data):
    name = update.message.from_user["first_name"]
    surname = update.message.from_user["last_name"]
    utente = User()
    utente.name = name
    utente.surname = surname
    utente.lastCommand = "start"
    utente.chat_id = update.message.chat_id
    utente.save()
    settings.USER = utente.chat_id
    createCronology(bot, update, utente)
    
    print("__________CHAT_ID__________")
    print(utente)
    
    
    #(test)associamo l'id utente
#     user_association = UserAssociation()
#     user_association.user_id = utente.id
#     user_association.chat_id = update.message.chat_id
#     user_association.save()
    
    #sheet = pe.get_sheet(file_name="csv_botlogger.csv")
    #row = [utente.name, utente.surname, str(utente.chat_id)]
    update.message.reply_text('Hi ' + name + ' ' + surname + ', I\'m Smartbot!')
    update.message.reply_text('Type /parking to search the closest parking in Amsterdam')

def location(bot, update):
    urld = 'http://api.citysdk.waag.org/layers/parking.garage/objects?per_page=25'
    user = User.objects.get(chat_id=update.message.chat_id)
    User.objects.filter(chat_id=update.message.chat_id).update(lastCommand="parking")
    createCronology(bot, update, user)
    r = urllib.request.urlopen(urld) 
    data = json.loads(r.read().decode(r.info().get_param('charset') or 'utf-8'))
    closestParkings = calculate_parkings_distance(bot, update, data['features']);
    getDecoratedMap(bot, update, closestParkings, data['features'])
    #sendMessageForParkings(closestParkings, data['features'], bot, update)
    print(bot.getUpdates(offset=update.message.chat_id))
    

def parking(bot, update, args, chat_data):
    user = User.objects.get(chat_id=update.message.chat_id)
    User.objects.filter(chat_id=update.message.chat_id).update(lastCommand = "parking")
    createCronology(bot, update, user)
    locationGPS_keyboard = KeyboardButton(text="Send my GPS location", request_location=True)
    locationUser_keyboard = KeyboardButton(text="Choose another location")
    custom_keyboard = [[ locationGPS_keyboard], [locationUser_keyboard]]
    addPreferencesKeyboard(custom_keyboard, user)
    print(custom_keyboard)
    reply_markup = telegram.ReplyKeyboardMarkup(custom_keyboard, resize_keyboard=True, one_time_keyboard=True)
    bot.sendMessage(chat_id=update.message.chat_id, text="Would you mind sharing your location to search the closest parking?", reply_markup=reply_markup)
    
    #text = update
    print(update)
    
def profile(bot, update, args, chat_data):
    user = User.objects.get(chat_id=update.message.chat_id)
    User.objects.filter(chat_id=update.message.chat_id).update(lastCommand = "webappUser")
    createCronology(bot, update, user)
    bot.sendMessage(chat_id=update.message.chat_id, 
                    text='<a href="' + WEBAPP + '?chatId=' + str(update.message.chat_id) + '">User Cronology</a>', 
                    parse_mode=telegram.ParseMode.HTML)

def addPreferencesKeyboard(keyboard, user):
    preferences = Preference.objects.filter(bot_user = user)
    for p in preferences:
        button = KeyboardButton(text=p.label)
        keyboard.append([button])
    
def createCronology(bot, update, user):
    print(user)
    cronology = Cronology()
    cronology.bot_user = user
    cronology.command = user.lastCommand
    cronology.date = datetime.datetime.now()
    cronology.save()
    
   
def getDecoratedMap(bot, update, closestParkings, data):
    road_styles = [{
    'feature': 'road.highway',
    'element': 'geomoetry',
    'rules': {
        'visibility': 'simplified',
        'color': '#c280e9'
    }
    }, {
    'feature': 'transit.line',
    'rules': {
        'visibility': 'simplified',
        'color': '#bababa'
    }
    }]
    dmap = DecoratedMap(style=road_styles)
    utente = User.objects.get(chat_id=update.message.chat_id)
    lat = utente.lat
    lon = utente.lon
    dmap.add_marker(LatLonMarker(lat, lon, label='S', color='blue'))
    i = 0
    keyboard = [[]]
    for p in closestParkings:
        dmap.add_marker(LatLonMarker(lat=data[p]['geometry']['coordinates'][1], lon=data[p]['geometry']['coordinates'][0],label=str(i+1)))
        keyboard[0].append(InlineKeyboardButton(text=str(i+1), callback_data= str(p)))
        i += 1
    url = dmap.generate_url()
    reply_markup = InlineKeyboardMarkup(keyboard, one_time_keyboard=True)
    bot.sendPhoto(chat_id = update.message.chat_id, photo=url)
    bot.sendMessage(chat_id = update.message.chat_id, text="Choose for details: ", reply_markup=reply_markup)
    reply_markup = telegram.ReplyKeyboardRemove()
    bot.sendMessage(chat_id = update.message.chat_id, text="Type /parking to start another search.", reply_markup=reply_markup)
    
   
def sendMessageForParkings(closestParkings, data, bot, update):
    emoticons = [ONE_KEYCAP, TWO_KEYCAP, THREE_KEYCAP]
    i=0
    for p in closestParkings:
        message = emoticons[i] + " The parking is: " + data[p]['properties']['title'] + "\n"
        #bot.sendMessage(chat_id=update.message.chat_id, text=message)
        bot.sendLocation(update.message.chat_id, data[p]['geometry']['coordinates'][1], data[p]['geometry']['coordinates'][0])
        keyboard = [[InlineKeyboardButton("Show Details", callback_data= str(p))]]         
        reply_markup = InlineKeyboardMarkup(keyboard)
        update.message.reply_text(text=message, reply_markup=reply_markup) 
        i += 1
    bot.sendMessage(chat_id=update.message.chat_id, text = "Click on show details to get more informations or start a new search typing /parking")  

def sendMessageForSingleParking(bot, update, index):
    
    urld = 'http://api.citysdk.waag.org/layers/parking.garage/objects?per_page=25'
    # utente.lastCommand = "location"
    r = urlopen(urld)
    data = json.loads(r.read().decode(r.info().get_param('charset') or 'utf-8'))
    print(data['features'])
    message = " The parking is: " + data['features'][int(index)]['properties']['title'] + "\n"
    message += "Free short parkings: " + str(data['features'][int(index)]['properties']['layers']['parking.garage']['data']['FreeSpaceShort']) + "\n"
    message += "Free long parkings: " + str(data['features'][int(index)]['properties']['layers']['parking.garage']['data']['FreeSpaceLong']) + "\n"
    reverse_geocode_result = gmaps.reverse_geocode((data['features'][int(index)]['geometry']['coordinates'][1], data['features'][int(index)]['geometry']['coordinates'][0]))
    message += "The address of the parking is: " + reverse_geocode_result[0]['formatted_address']
    #bot.sendMessage(chat_id=update.message.chat_id, text=message)
    bot.sendLocation(update.message.chat_id, data['features'][int(index)]['geometry']['coordinates'][1], data['features'][int(index)]['geometry']['coordinates'][0]) 
    bot.sendMessage(chat_id=update.message.chat_id, text = message)
    bot.sendMessage(chat_id=update.message.chat_id, text = 'Type /parking to start another search.')  
    

def error(bot, update, error):
    logger.warning('Update "%s" caused error "%s"' % (update, error))

def getLocation(bot, update):
    latid = update.message.location["latitude"]
    long = update.message.location["longitude"]
    User.objects.filter(chat_id=update.message.chat_id).update(lat=latid, lon=long)
    reverse_geocode_result = gmaps.reverse_geocode((latid, long))
    print(reverse_geocode_result[0]['formatted_address'])
    name = update.message.from_user["first_name"]
    message = name + " you are located in: " + reverse_geocode_result[0]['formatted_address']
    bot.sendMessage(chat_id=update.message.chat_id, 
                        text = message)
    location(bot, update)
    
def analyzeText(bot, update):
    utente = User.objects.get(chat_id=update.message.chat_id)
    address = ''
    print(utente.lastCommand)
    print(update.message.text)
    if utente.lastCommand == "parking":
        textToAnalyze = update.message.text
        if checkPreferences(utente, textToAnalyze, bot, update):
            preference = Preference.objects.get(bot_user=utente, label=textToAnalyze)
            User.objects.filter(chat_id=update.message.chat_id).update(lat=preference.lat, lon=preference.lon)
            location(bot, update)
        else:
        #print(utente.lastCommand)
            bot.sendMessage(chat_id=update.message.chat_id, text = "Please insert the location you want to start")
            choosenPosition = update.message.text
            print('Posizione scelta: ' + choosenPosition)
            newCommand = utente.lastCommand + ".preference"
            User.objects.filter(chat_id=update.message.chat_id).update(lastCommand = newCommand)
    elif utente.lastCommand == "parking.preference":
            textToAnalyze = update.message.text
            geocode_result = gmaps.geocode(textToAnalyze)
            if geocode_result:
                User.objects.filter(chat_id=update.message.chat_id).update(positionName=textToAnalyze)
                savePreferences(bot, update)
            else:
                message = "I couldn't find this location. \nType again"
                bot.sendMessage(chat_id=update.message.chat_id, text = message )
    elif utente.lastCommand == "parking.result":
        print("sono nel parking.result")
        #print(utente.lastCommand)
        user = User.objects.get(chat_id=update.message.chat_id)
        parkingResult(bot, update)
        print(geocode_result)
    elif utente.lastCommand == "parking.preference.choose":
        print('Sono nel parking.prefenrece.choose')
        textToAnalyze = update.message.text
        user = User.objects.get(chat_id=update.message.chat_id)        
        geocode_result = gmaps.geocode(user.positionName)
        if geocode_result:
            address = geocode_result[0]['formatted_address']
            message = "You inserted this location " + address
            latid = geocode_result[0]['geometry']['location']['lat']
            long = geocode_result[0]['geometry']['location']['lng']
            User.objects.filter(chat_id=update.message.chat_id).update(lat=latid, lon=long)
            if textToAnalyze == "YES":
                bot.sendMessage(chat_id=update.message.chat_id, text = "Choose the name you want to save this position: " )
                newCommand = utente.lastCommand + ".save"
                User.objects.filter(chat_id=update.message.chat_id).update(lastCommand = newCommand)
            else:
                newCommand = "parking.result"
                User.objects.filter(chat_id=update.message.chat_id).update(lastCommand = newCommand)
                user = User.objects.get(chat_id=update.message.chat_id)
                parkingResult(bot, update)
                
        else:
            message = "I couldn't find this location. \nType again"
            bot.sendMessage(chat_id=update.message.chat_id, text = message )
            #bot.sendMessage(chat_id=update.message.chat_id, text = "Type /parking if you want to start another search." )
    elif utente.lastCommand == "parking.preference.choose.save":
        textToAnalyze = update.message.text
        bot.sendMessage(chat_id=update.message.chat_id, text = "The current position has been saved with the name: " + textToAnalyze)
        user = User.objects.get(chat_id=update.message.chat_id)
        print('ADDRESS: ' + address)
        newCommand = "parking.result"
        User.objects.filter(chat_id=update.message.chat_id).update(lastCommand = newCommand)
        createPreference(textToAnalyze, user, address)
        parkingResult(bot, update)
    else:
        bot.sendMessage(chat_id=update.message.chat_id, text = "I couldn't understand you" )
    
def parkingResult(bot, update):
    user = User.objects.get(chat_id=update.message.chat_id)
    geocode_result = gmaps.geocode(user.positionName)
    if geocode_result:
        address = geocode_result[0]['formatted_address']
        message = "You inserted this location " + address
        latid = geocode_result[0]['geometry']['location']['lat']
        long = geocode_result[0]['geometry']['location']['lng']
        User.objects.filter(chat_id=update.message.chat_id).update(lat=latid, lon=long)
        bot.sendMessage(chat_id=update.message.chat_id, text=message)
        location(bot, update)
    else:
        message = "I couldn't find this location. \nType again"
        User.objects.filter(chat_id=update.message.chat_id).update(lastCommand='parking')
        bot.sendMessage(chat_id=update.message.chat_id, text=message)
    
def checkPreferences(utente, text, bot, update):
    preferences = Preference.objects.filter(bot_user=utente)
    for p in preferences:
        if p.label == text:
            return True
    return False
    
def savePreferences(bot, update):
    yes_keyboard = KeyboardButton(text="YES")
    no_keyboard = KeyboardButton(text="NO")
    custom_keyboard = [[ yes_keyboard], [no_keyboard]]
    reply_markup = telegram.ReplyKeyboardMarkup(custom_keyboard, resize_keyboard=True, one_time_keyboard=True)
    user = User.objects.get(chat_id=update.message.chat_id)
    newCommand = user.lastCommand + ".choose"
    User.objects.filter(chat_id=update.message.chat_id).update(lastCommand = newCommand)
    bot.sendMessage(chat_id=update.message.chat_id, text = "Do you want to save this location for future searches?", reply_markup=reply_markup)
    
def createPreference(text, user, address):
    preference = Preference()
    preference.label = text
    preference.lat = user.lat
    preference.lon = user.lon
    reverse_geocode_result = gmaps.reverse_geocode((user.lat, user.lon))
    preference.address = reverse_geocode_result[0]['formatted_address']
    preference.bot_user = user
    preference.save()  
    
def main():
    updater = Updater(TOKEN)
    choosenPosition = 'posizione'
    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    # on different commands - answer in Telegram
    dp.add_handler(CommandHandler("start", start, pass_args=True, pass_chat_data=True))
    dp.add_handler(CommandHandler("help", start))
    dp.add_handler(CommandHandler("parking", parking, pass_args=True, pass_chat_data=True))
    dp.add_handler(CommandHandler("profile", profile, pass_args=True, pass_chat_data=True))
    dp.add_handler(MessageHandler([Filters.location], getLocation))
    dp.add_handler(MessageHandler([Filters.text], analyzeText))
    dp.add_handler(CallbackQueryHandler(get_inlineKeyboardButton))
    # log all errors
    dp.add_error_handler(error)

    # Start the Bot
    updater.start_polling()
    # Block until you press Ctrl-C or the process receives SIGINT, SIGTERM or
    # SIGABRT. This should be used most of the time, since start_polling() is
    # non-blocking and will stop the bot gracefully.
    updater.idle()
    
    
def get_inlineKeyboardButton(bot, update):
    query = update.callback_query
    sendMessageForSingleParking(bot, query, query.data)

    
def calculate_parkings_distance(bot, update, parkings):
    utente = User.objects.get(chat_id=update.message.chat_id)
    lat = utente.lat
    lon = utente.lon
    distanceArray = []
    for p in parkings:
        distance = haversine(lon, lat, p['geometry']['coordinates'][0], p['geometry']['coordinates'][1])
        distanceArray.append(distance)
    arr = np.array(distanceArray)
    return arr.argsort()[:3]
   
    

def haversine(lon1, lat1, lon2, lat2):
    """
    Calculate the great circle distance between two points 
    on the earth (specified in decimal degrees)
    """
    # convert decimal degrees to radians 
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
    # haversine formula 
    dlon = lon2 - lon1 
    dlat = lat2 - lat1 
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a)) 
    km = 6367 * c
    return km

def send_message(text, chat_id, reply_markup=None):
    text = urllib.parse.quote_plus(text)
    url = URL + "sendMessage?text={}&chat_id={}&parse_mode=Markdown".format(text, chat_id)
    if reply_markup:
        url += "&reply_markup={}".format(reply_markup)
    get_url(url)

def get_url(url):
    response = requests.get(url)
    content = response.content.decode("utf8")
    return content



if __name__ == '__main__':
    sys.path.append("C:\\Users\\Geko\\workspace\\smartBot\\smartBot") #Set it to the root of your project
    print(sys.path)
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smartBot.settings')
    django.setup() 
    from bot.models import *
    main()