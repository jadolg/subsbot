import logging
import os
import re
import requests
import telegram
from telegram import ReplyKeyboardRemove

from crawler import Serie
from fuzzywuzzy import process

logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger()
logger.setLevel(logging.INFO)

from telegram.ext import Updater, CommandHandler, ConversationHandler, MessageHandler, Filters

NAME, NAME_SELECT, SEASON, EPISODE, DOWNLOAD = range(5)

data = {}


def start(bot, update):
    data[update.effective_user.username] = {}
    update.message.reply_text(
        'Hola! Yo buscaré subtítulos para ti.\n\n'
        'Envía /cancelar para terminar nuestra charla.\n\n'
        'Qué serie estás buscando?', reply_markup=ReplyKeyboardRemove())

    return NAME


def name(bot, update):
    names = []
    for serie in process.extractBests(update.message.text, Serie.get_series_list(), limit=3):
        names.append([serie[0].name])
    names.append(['/cancelar'])
    reply_markup = telegram.ReplyKeyboardMarkup(names)
    update.message.reply_text('Alguna de estas?', reply_markup=reply_markup)

    return NAME_SELECT


def name_select(bot, update):
    seasons = []
    for serie in Serie.get_series_list():
        if serie.name == update.message.text:
            seasons = serie.get_seasons()
            data[update.effective_user.username]['serie'] = serie
            break

    if seasons is []:
        update.message.reply_text('No he encontrado nada :(', reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END

    reply_markup = telegram.ReplyKeyboardMarkup([seasons, ['/cancelar']])
    update.message.reply_text('Qué temporada?', reply_markup=reply_markup)
    return SEASON


def season(bot, update):
    if update.message.text in data[update.effective_user.username]['serie'].get_seasons():
        data[update.effective_user.username]['season'] = update.message.text
        episodes = data[update.effective_user.username]['serie'].get_episodes(update.message.text)
        episode_names = [[episode.name] for episode in episodes]
        data[update.effective_user.username]['episodes'] = episodes
        episode_names.append(['/cancelar'])
        reply_markup = telegram.ReplyKeyboardMarkup(episode_names)
        update.message.reply_text('Qué episodio?', reply_markup=reply_markup)
    else:
        update.message.reply_text('No tengo esta temporada :(', reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END
    return EPISODE


def get_filename_from_cd(cd):
    """
    Get filename from content-disposition
    """
    if not cd:
        return None
    fname = re.findall('filename=(.+)', cd)
    if len(fname) == 0:
        return None
    return fname[0][1:-1].encode('ascii', 'ignore').decode('unicode_escape')


def episode(bot, update):
    for episode in data[update.effective_user.username]['episodes']:
        if episode.name == update.message.text:
            for subtitle in episode.subtitles:
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

            update.message.reply_text('desea buscar otro?', reply_markup=telegram.ReplyKeyboardMarkup([['/start']]))
            return ConversationHandler.END

    update.message.reply_text('no tengo ese episodio :(', reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END


def cancel(bot, update):
    user = update.message.from_user
    logger.info("User %s canceled the conversation.", user.first_name)
    update.message.reply_text('Nos vemos!', reply_markup=telegram.ReplyKeyboardMarkup([['/start']]))

    return ConversationHandler.END


updater = Updater(os.environ.get('TELEGRAM_TOKEN'))
dp = updater.dispatcher

try:
    os.makedirs('subs')
except:
    pass

conv_handler = ConversationHandler(
    entry_points=[CommandHandler('start', start)],

    states={
        NAME: [MessageHandler(Filters.text, name)],
        NAME_SELECT: [MessageHandler(Filters.text, name_select)],
        SEASON: [MessageHandler(Filters.text, season)],
        EPISODE: [MessageHandler(Filters.text, episode)],
    },

    fallbacks=[CommandHandler('cancelar', cancel)]
)

dp.add_handler(conv_handler)

updater.start_polling()
updater.idle()
