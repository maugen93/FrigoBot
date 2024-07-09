from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.ext import (
    Application,
    ContextTypes,
    MessageHandler,
    CommandHandler,
    filters,
)
from functools import partial
import time

import worker


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE, path):
    message = worker.insertResult(path, update.message.text)
    if message:
        await update.message.reply_text(
            message, reply_markup=ReplyKeyboardRemove()
        )
    time.sleep(5)
    await context.bot.send_message(update.message.chat_id,'prossima')
    return


async def rank_command(update: Update, context: ContextTypes.DEFAULT_TYPE, path):
    command = update.message.text
    cmds = command.split(' ')
    if len(cmds) > 1:
        if cmds[1] == 'week':
            await update.message.reply_text(
                worker.rank_week(path), reply_markup=ReplyKeyboardRemove()
            )
            return
        if cmds[1] == 'pkmn' or cmds[1] == 'pokemon' or cmds[1] == 'animali':
            await update.message.reply_text(
                worker.rank_pkmn(path), reply_markup=ReplyKeyboardRemove()
            )
            return
        if cmds[1] == 'global':
            await update.message.reply_text(
                worker.rank_all(path), reply_markup=ReplyKeyboardRemove()
            )
            return
    await update.message.reply_text(
        worker.rank_season(path), reply_markup=ReplyKeyboardRemove()
    )
    return


async def query_command(update: Update, context: ContextTypes.DEFAULT_TYPE, path):
    command = update.message.text
    user = update.message.from_user
    if user.id != 170532946:
        await update.message.reply_text(
            'Ti piacerebbe, porco', reply_markup=ReplyKeyboardRemove()
        )
        return

    execution = worker.run_query(command.replace('/query ', ''), path)

    if execution:
        mess = "Fatto"
    else:
        mess = 'Ma che cazzo hai scritto, non funziona'
    await update.message.reply_text(
        mess, reply_markup=ReplyKeyboardRemove()
    )
    return


async def cal_command(update: Update, context: ContextTypes.DEFAULT_TYPE, path):
    await update.message.reply_text(
        worker.calippi(path), reply_markup=ReplyKeyboardRemove()
    )
    return


async def animale_command(update: Update, context: ContextTypes.DEFAULT_TYPE, path):
    command = update.message.text
    cmds = command.split(' ')
    if len(cmds) > 1:
        animale = command.replace("/animale ", '')
        message = worker.wins_animale(animale, path)
        await update.message.reply_text(
            message, reply_markup=ReplyKeyboardRemove()
        )
        return
    else:
        await update.message.reply_text(
            'e dammi un animale', reply_markup=ReplyKeyboardRemove()
        )
        return


async def player_command(update: Update, context: ContextTypes.DEFAULT_TYPE, path):
    command = update.message.text
    cmds = command.split(' ')
    if len(cmds) > 1:
        player = command.replace("/player ", '')
        message = worker.playerCard(player, path)
        await update.message.reply_text(
            message, reply_markup=ReplyKeyboardRemove()
        )
        return
    else:
        await update.message.reply_text(
            'e dimmi chi', reply_markup=ReplyKeyboardRemove()
        )
        return

async def secchezza_command(update: Update, context: ContextTypes.DEFAULT_TYPE, path):
    command = update.message.text
    cmds = command.split(' ')
    if len(cmds) > 1:
        player = command.replace("/secchezza ", '')
        message = worker.secchezza(player, path)
        await update.message.reply_text(
            message, reply_markup=ReplyKeyboardRemove()
        )
        return
    else:
        await update.message.reply_text(
            'e dimmi chi', reply_markup=ReplyKeyboardRemove()
        )
        return

def start_bot(token, db_path):
    application = Application.builder().token(token).build()

    # Aggiungo gestori comandi
    m = MessageHandler(filters.Regex("(?=.*replay)(?=.*pokemonshowdown)(?=.*freeforallrandombattle)"),
                       partial(handle_message, path=db_path))

    c_rank = CommandHandler("rank", partial(rank_command, path=db_path))

    c_query = CommandHandler("query", partial(query_command, path=db_path))

    c_cal = CommandHandler("calippi", partial(cal_command, path=db_path))
    c_an = CommandHandler("animale", partial(animale_command, path=db_path))

    c_pl = CommandHandler("player", partial(player_command, path=db_path))
    c_sec = CommandHandler("secchezza", partial(secchezza_command, path=db_path))
    application.add_handler(m)
    application.add_handler(c_rank)
    application.add_handler(c_query)
    application.add_handler(c_cal)
    application.add_handler(c_an)
    application.add_handler(c_pl)
    application.add_handler(c_sec)
    # Run the bot until the user presses Ctrl-C
    application.run_polling(allowed_updates=Update.ALL_TYPES)
