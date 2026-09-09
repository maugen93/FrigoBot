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
    await context.bot.send_message(update.message.chat_id, 'prossima')
    return


async def global_rank_command(update: Update, context: ContextTypes.DEFAULT_TYPE, path):
    await update.message.reply_text(
        worker.rank_all(path), reply_markup=ReplyKeyboardRemove()
    )
    return


async def week_command(update: Update, context: ContextTypes.DEFAULT_TYPE, path):
    await update.message.reply_text(
        worker.rank_week(path), reply_markup=ReplyKeyboardRemove()
    )
    return


async def animali_command(update: Update, context: ContextTypes.DEFAULT_TYPE, path):
    await update.message.reply_text(
        worker.rank_pkmn(path), reply_markup=ReplyKeyboardRemove()
    )
    return


async def season_command(update: Update, context: ContextTypes.DEFAULT_TYPE, path):
    await update.message.reply_text(
        worker.rank_season(path), reply_markup=ReplyKeyboardRemove()
    )
    return


async def score_command(update: Update, context: ContextTypes.DEFAULT_TYPE, path):
    await update.message.reply_text(
        worker.global_score(path), reply_markup=ReplyKeyboardRemove()
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


async def closeweek_command(update: Update, context: ContextTypes.DEFAULT_TYPE, path):
    user = update.message.from_user
    if user.id != 170532946:
        await update.message.reply_text(
            'Ti piacerebbe, porco', reply_markup=ReplyKeyboardRemove()
        )
        return
    message = worker.closeWeek(path)
    await update.message.reply_text(
        message, reply_markup=ReplyKeyboardRemove()
    )
    return


async def tag_command(update: Update, context: ContextTypes.DEFAULT_TYPE, path):
    command = update.message.text
    user = update.message.from_user
    if user.id != 170532946:
        await update.message.reply_text(
            'Ti piacerebbe, porco', reply_markup=ReplyKeyboardRemove()
        )
        return

    message = worker.tagger(path)

    if message:
        await update.message.reply_text(
            message, reply_markup=ReplyKeyboardRemove()
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


async def andazzo_command(update: Update, context: ContextTypes.DEFAULT_TYPE, path):
    plot_path = worker.frigoFrequency(path)

    await update.message.reply_photo(
        plot_path, caption='Numero di Frigo fatte per week', reply_markup=ReplyKeyboardRemove()
    )
    return


async def ladder_command(update: Update, context: ContextTypes.DEFAULT_TYPE, path):
    # tab_path = worker.Ladder(path)

    # await update.message.reply_photo(
    #    tab_path,caption='Ladder', reply_markup=ReplyKeyboardRemove()
    # )
    # return
    await update.message.reply_text(
        'fottiti', reply_markup=ReplyKeyboardRemove()
    )
    return


async def send_link_calc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        'https://calc.pokemonshowdown.com/randoms.html?mode=randoms', reply_markup=ReplyKeyboardRemove()
    )
    return


async def unicum_ladder_command(update: Update, context: ContextTypes.DEFAULT_TYPE, path):
    await update.message.reply_text(
        worker.LadderUnici(path), reply_markup=ReplyKeyboardRemove()
    )
    return


async def unicum_player_command(update: Update, context: ContextTypes.DEFAULT_TYPE, path):
    command = update.message.text
    cmds = command.split(' ')
    if len(cmds) > 1:
        player = command.replace("/unicum ", '')
        message = worker.UniciPlayer(player, path)
        await update.message.reply_text(
            message, reply_markup=ReplyKeyboardRemove()
        )
        return
    else:
        await update.message.reply_text(
            'e dimmi chi', reply_markup=ReplyKeyboardRemove()
        )
        return


async def cessi_list_command(update: Update, context: ContextTypes.DEFAULT_TYPE, path):
    await update.message.reply_text(
        worker.ListOfCessi(path), reply_markup=ReplyKeyboardRemove()
    )
    return


async def animali2_command(update: Update, context: ContextTypes.DEFAULT_TYPE, path):
    await update.message.reply_text(
        worker.WinrateAnimali(path), reply_markup=ReplyKeyboardRemove()
    )
    return


async def desaparecidos_command(update: Update, context: ContextTypes.DEFAULT_TYPE, path):
    await update.message.reply_text(
        worker.desaparecidos(path), reply_markup=ReplyKeyboardRemove()
    )
    return


def start_bot(token, db_path):
    application = Application.builder().token(token).build()

    # Aggiungo gestori comandi
    m = MessageHandler(filters.Regex("(?=.*replay)(?=.*pokemonshowdown)(?=.*freeforallrandombattle)"),
                       partial(handle_message, path=db_path))

    c_week = CommandHandler("week", partial(week_command, path=db_path))
    c_animali = CommandHandler("animali", partial(animali_command, path=db_path))
    c_season = CommandHandler("season", partial(season_command, path=db_path))
    c_season2 = CommandHandler("siso", partial(season_command, path=db_path))
    c_califfi = CommandHandler("califfi", partial(cal_command, path=db_path))
    c_score = CommandHandler("score", partial(score_command, path=db_path))
    c_animale = CommandHandler("animale", partial(animale_command, path=db_path))
    c_global = CommandHandler("global", partial(global_rank_command, path=db_path))

    c_query = CommandHandler("query", partial(query_command, path=db_path))
    c_tag = CommandHandler("tag", partial(tag_command, path=db_path))

    c_pl = CommandHandler("player", partial(player_command, path=db_path))
    c_sec = CommandHandler("secchezza", partial(secchezza_command, path=db_path))

    c_and = CommandHandler("andazzo", partial(andazzo_command, path=db_path))

    c_lad = CommandHandler("ladder", partial(ladder_command, path=db_path))

    c_cw = CommandHandler("closeweek", partial(closeweek_command, path=db_path))

    c_calc = CommandHandler("calc", send_link_calc)

    c_uni_lad = CommandHandler("unicums", partial(unicum_ladder_command, path=db_path))
    c_uni_pl = CommandHandler("unicum", partial(unicum_player_command, path=db_path))

    c_cessi = CommandHandler("cessi", partial(cessi_list_command, path=db_path))

    c_animali2 = CommandHandler("animali2", partial(animali2_command, path=db_path))

    c_desaparecidos = CommandHandler("desaparecidos", partial(desaparecidos_command, path=db_path))

    application.add_handler(m)
    application.add_handler(c_week)
    application.add_handler(c_animali)
    application.add_handler(c_season)
    application.add_handler(c_season2)
    application.add_handler(c_califfi)
    application.add_handler(c_score)
    application.add_handler(c_query)
    application.add_handler(c_tag)
    application.add_handler(c_animale)
    application.add_handler(c_global)
    application.add_handler(c_pl)
    application.add_handler(c_sec)
    application.add_handler(c_and)
    application.add_handler(c_lad)
    application.add_handler(c_cw)
    application.add_handler(c_calc)
    application.add_handler(c_uni_lad)
    application.add_handler(c_uni_pl)
    application.add_handler(c_cessi)
    application.add_handler(c_animali2)
    application.add_handler(c_desaparecidos)
    # Run the bot until the user presses Ctrl-C
    application.run_polling(allowed_updates=Update.ALL_TYPES)


def testLadder(db_path):
    worker.Ladder(db_path)
