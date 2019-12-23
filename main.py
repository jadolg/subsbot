import logging
import os
import pickle
import re
import sys
from functools import wraps

import boto3
import requests
import telegram
from fuzzywuzzy import process
from telegram import ChatAction
from telegram import ReplyKeyboardRemove
from telegram.ext import Updater, CommandHandler, ConversationHandler, MessageHandler, Filters
from telegram.utils.promise import Promise

from crawler import Serie

logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger()
logger.setLevel(logging.INFO)

NAME, NAME_SELECT, SEASON, EPISODE = range(4)

AWS_SERVER_PUBLIC_KEY = os.environ.get('AWS_SERVER_PUBLIC_KEY')
AWS_SERVER_SECRET_KEY = os.environ.get('AWS_SERVER_SECRET_KEY')
AWS_REGION = os.environ.get('AWS_REGION')
bucket_name = os.environ.get('S3_BUCKET_NAME')

session = boto3.Session(
    aws_access_key_id=AWS_SERVER_PUBLIC_KEY,
    aws_secret_access_key=AWS_SERVER_SECRET_KEY,
)

s3 = session.client('s3', region_name=AWS_REGION)


def save_data():
    # Before pickling
    resolved = dict()
    for k, v in conv_handler.conversations.items():
        if isinstance(v, tuple) and len(v) is 2 and isinstance(v[1], Promise):
            try:
                new_state = v[1].result()  # Result of async function
            except:
                new_state = v[0]  # In case async function raised an error, fallback to old state
            resolved[k] = new_state
        else:
            resolved[k] = v + 1
    try:
        f = open('backup/conversations', 'wb')
        pickle.dump(resolved, f)
        f.close()
        f = open('backup/userdata', 'wb')
        pickle.dump(dp.user_data, f)
        f.close()
        s3.upload_file('backup/conversations', bucket_name, 'conversations')
        s3.upload_file('backup/userdata', bucket_name, 'userdata')
    except:
        logging.error(sys.exc_info()[0])


def load_data():
    try:
        s3.download_file(bucket_name, 'conversations', 'backup/conversations')
        s3.download_file(bucket_name, 'userdata', 'backup/userdata')
    except:
        logging.error(sys.exc_info()[0])

    try:
        f = open('backup/conversations', 'rb')
        conv_handler.conversations = pickle.load(f)
        f.close()
        f = open('backup/userdata', 'rb')
        dp.user_data = pickle.load(f)
        f.close()
    except FileNotFoundError:
        logging.error("Data file not found")
    except:
        logging.error(sys.exc_info()[0])


def send_action(action):
    """Sends `action` while processing func command."""

    def decorator(func):
        @wraps(func)
        def command_func(*args, **kwargs):
            bot, update = args
            bot.send_chat_action(chat_id=update.effective_message.chat_id, action=action)
            return func(bot, update, **kwargs)

        return command_func

    return decorator


def start(bot, update, user_data):
    update.message.reply_text(
        'Hola! Yo buscaré subtítulos para ti.\n\n'
        'Envía /cancelar para terminar nuestra charla.\n\n'
        'Qué serie estás buscando?', reply_markup=ReplyKeyboardRemove())
    save_data()
    return NAME


def restart(update, user_data):
    user_data.clear()
    save_data()
    update.message.reply_text(
        'Envía /cancelar para terminar nuestra charla.\n\n'
        'Qué serie estás buscando?', reply_markup=ReplyKeyboardRemove())
    return NAME


@send_action(ChatAction.TYPING)
def name(bot, update, user_data):
    save_data()
    names = []
    for serie in process.extractBests(update.message.text, Serie.get_series_list(), limit=3):
        names.append([serie[0].name])
    names.append(['/cancelar'])
    reply_markup = telegram.ReplyKeyboardMarkup(names)
    update.message.reply_text('Alguna de estas?', reply_markup=reply_markup)
    save_data()
    return NAME_SELECT


@send_action(ChatAction.TYPING)
def name_select(bot, update, user_data):
    seasons = []
    for serie in Serie.get_series_list():
        if serie.name == update.message.text:
            seasons = serie.get_seasons()
            user_data['serie'] = serie
            break

    if seasons is []:
        update.message.reply_text('No he encontrado nada :(', reply_markup=ReplyKeyboardRemove())
        return restart(update, user_data)

    reply_markup = telegram.ReplyKeyboardMarkup([seasons, ['/cancelar']])
    update.message.reply_text('Qué temporada?', reply_markup=reply_markup)
    save_data()
    return SEASON


@send_action(ChatAction.TYPING)
def season(bot, update, user_data):
    save_data()
    if update.message.text in user_data['serie'].get_seasons():
        user_data['season'] = update.message.text
        episodes = user_data['serie'].get_episodes(update.message.text)
        episode_names = [[episode.name] for episode in episodes]
        user_data['episodes'] = episodes
        save_data()
        episode_names.append(['/cancelar'])
        reply_markup = telegram.ReplyKeyboardMarkup(episode_names)
        update.message.reply_text('Qué episodio?', reply_markup=reply_markup)
    else:
        update.message.reply_text('No tengo esta temporada :(', reply_markup=ReplyKeyboardRemove())
        user_data.clear()
        save_data()
        return restart(update, user_data)
    return EPISODE


def get_filename_from_cd(cd):
    """
    Get filename from content-disposition
    """
    if not cd:
        return None
    file_name = re.findall('filename=(.+)', cd)
    if len(file_name) == 0:
        return None
    return file_name[0][1:-1].encode('ascii', 'ignore').decode('unicode_escape')


@send_action(ChatAction.UPLOAD_DOCUMENT)
def episode(bot, update, user_data):
    save_data()
    for episode in user_data['episodes']:
        if episode.name == update.message.text:
            for subtitle in episode.subtitles:
                try:
                    subtitle_download = requests.get(subtitle[1],
                                                     headers={'authority': 'www.tusubtitulo.com',
                                                              'upgrade-insecure-requests': '1',
                                                              'referer': 'https://www.tusubtitulo.com/'})
                    filename = f"./subs/{get_filename_from_cd(subtitle_download.headers.get('content-disposition'))}"
                    downloaded_sub = open(filename, 'wb')
                    downloaded_sub.write(subtitle_download.content)
                    downloaded_sub.close()
                    bot.send_document(chat_id=update.effective_chat.id, document=open(downloaded_sub.name, 'rb'))
                    bot.send_message(chat_id=update.effective_chat.id, text=subtitle[0])
                    save_data()
                except:
                    logging.error(sys.exc_info()[0])
            return restart(update, user_data)

    update.message.reply_text('no tengo ese episodio :(', reply_markup=ReplyKeyboardRemove())
    return restart(update, user_data)


def cancel(bot, update, user_data):
    user = update.message.from_user
    logger.info("User %s canceled the conversation.", user.first_name)
    update.message.reply_text('Nos vemos!', reply_markup=telegram.ReplyKeyboardMarkup([['/start']]))
    user_data.clear()
    save_data()
    return ConversationHandler.END


TOKEN = os.environ.get('TELEGRAM_TOKEN')
updater = Updater(TOKEN)
dp = updater.dispatcher

try:
    os.makedirs('subs')
except:
    pass

try:
    os.makedirs('backup')
except:
    pass

conv_handler = ConversationHandler(
    entry_points=[CommandHandler('start', start, pass_user_data=True)],

    states={
        NAME: [MessageHandler(Filters.text, name, pass_user_data=True)],
        NAME_SELECT: [MessageHandler(Filters.text, name_select, pass_user_data=True)],
        SEASON: [MessageHandler(Filters.text, season, pass_user_data=True)],
        EPISODE: [MessageHandler(Filters.text, episode, pass_user_data=True)],
    },

    fallbacks=[MessageHandler(Filters.text, cancel, pass_user_data=True),
               CommandHandler('cancelar', cancel, pass_user_data=True)]
)

dp.add_handler(conv_handler)
load_data()
updater.start_webhook(listen="0.0.0.0",
                      port=int(os.environ.get('PORT')),
                      url_path=TOKEN)

if os.environ.get('LOCAL') == 'true':
    updater.bot.setWebhook(f"https://26d9413f.ngrok.io/{TOKEN}")
else:
    updater.bot.setWebhook(f"https://tusubtitulobot.herokuapp.com/{TOKEN}")

updater.idle()
