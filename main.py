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


def start(bot, update):
    update.message.reply_text(
        'Hola! Yo buscaré subtítulos para ti.\n\n'
        'Envía /cancelar para terminar nuestra charla.\n\n'
        'Qué serie estás buscando?', reply_markup=ReplyKeyboardRemove())

    return NAME


def name(bot, update, user_data):
    names = []
    for serie in process.extractBests(update.message.text, Serie.get_series_list(), limit=3):
        names.append([serie[0].name])
    names.append(['/cancelar'])
    reply_markup = telegram.ReplyKeyboardMarkup(names)
    update.message.reply_text('Alguna de estas?', reply_markup=reply_markup)

    return NAME_SELECT


def name_select(bot, update, user_data):
    seasons = []
    for serie in Serie.get_series_list():
        if serie.name == update.message.text:
            seasons = serie.get_seasons()
            user_data['serie'] = serie
            break

    if seasons is []:
        update.message.reply_text('No he encontrado nada :(', reply_markup=ReplyKeyboardRemove())
        user_data.clear()
        return ConversationHandler.END

    reply_markup = telegram.ReplyKeyboardMarkup([seasons, ['/cancelar']])
    update.message.reply_text('Qué temporada?', reply_markup=reply_markup)
    return SEASON


def season(bot, update, user_data):
    if update.message.text in user_data['serie'].get_seasons():
        user_data['season'] = update.message.text
        episodes = user_data['serie'].get_episodes(update.message.text)
        episode_names = [[episode.name] for episode in episodes]
        user_data['episodes'] = episodes
        episode_names.append(['/cancelar'])
        reply_markup = telegram.ReplyKeyboardMarkup(episode_names)
        update.message.reply_text('Qué episodio?', reply_markup=reply_markup)
    else:
        update.message.reply_text('No tengo esta temporada :(', reply_markup=ReplyKeyboardRemove())
        user_data.clear()
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


def episode(bot, update, user_data):
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
                except:
                    pass

            update.message.reply_text('Eso fue todo.\n\nDesea buscar otro?',
                                      reply_markup=telegram.ReplyKeyboardMarkup([['/start']]))
            user_data.clear()
            return ConversationHandler.END

    update.message.reply_text('no tengo ese episodio :(', reply_markup=ReplyKeyboardRemove())
    user_data.clear()
    return ConversationHandler.END


def cancel(bot, update, user_data):
    user = update.message.from_user
    logger.info("User %s canceled the conversation.", user.first_name)
    update.message.reply_text('Nos vemos!', reply_markup=telegram.ReplyKeyboardMarkup([['/start']]))
    user_data.clear()
    return ConversationHandler.END


TOKEN = os.environ.get('TELEGRAM_TOKEN')
updater = Updater(TOKEN)
dp = updater.dispatcher

try:
    os.makedirs('subs')
except:
    pass

conv_handler = ConversationHandler(
    entry_points=[CommandHandler('start', start)],

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
updater.start_webhook(listen="0.0.0.0",
                      port=int(os.environ.get('PORT')),
                      url_path=TOKEN)
updater.bot.setWebhook(f"https://tusubtitulobot.herokuapp.com/{TOKEN}")
updater.idle()
