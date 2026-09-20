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

SUPER_USERS = [170532946]

RESTRICTED_COMMANDS = {"query", "tag", "closeweek"}

ALL_COMMANDS = [
    "week", "animali", "animali2", "season", "siso", "califfi", "score", "animale",
    "global", "query", "tag", "player", "pokewinners", "predilette", "affettive",
    "secchezza", "andazzo", "ladder", "closeweek", "calc", "unicums", "unicum",
    "cessi", "desaparecidos", "swingers", "wincons", "svergiconverters",
    "svergitryers", "comandi", "frigo",
]

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE, path):
    message = worker.insertResult(path, update.message.text)
    if message:
        await update.message.reply_text(
            message, parse_mode='HTML', reply_markup=ReplyKeyboardRemove()
        )
    time.sleep(5)
    await context.bot.send_message(update.message.chat_id, 'prossima')
    return


async def global_rank_command(update: Update, context: ContextTypes.DEFAULT_TYPE, path):
    await update.message.reply_text(
        worker.rank_all(path), parse_mode='HTML', reply_markup=ReplyKeyboardRemove()
    )
    return


async def week_command(update: Update, context: ContextTypes.DEFAULT_TYPE, path):
    await update.message.reply_text(
        worker.rank_week(path), parse_mode='HTML', reply_markup=ReplyKeyboardRemove()
    )
    return


async def animali_command(update: Update, context: ContextTypes.DEFAULT_TYPE, path):
    await update.message.reply_text(
        worker.rank_pkmn(path), parse_mode='HTML', reply_markup=ReplyKeyboardRemove()
    )
    return


async def season_command(update: Update, context: ContextTypes.DEFAULT_TYPE, path):
    await update.message.reply_text(
        worker.rank_season(path), parse_mode='HTML', reply_markup=ReplyKeyboardRemove()
    )
    return


async def score_command(update: Update, context: ContextTypes.DEFAULT_TYPE, path):
    await update.message.reply_text(
        worker.global_score(path), parse_mode='HTML', reply_markup=ReplyKeyboardRemove()
    )
    return


async def query_command(update: Update, context: ContextTypes.DEFAULT_TYPE, path):
    command = update.message.text
    user = update.message.from_user
    if user.id not in SUPER_USERS:
        await update.message.reply_text(
            'Ti piacerebbe, porco', parse_mode='HTML', reply_markup=ReplyKeyboardRemove()
        )
        return

    execution = worker.run_query(command.replace('/query ', ''), path)

    if execution:
        mess = "Fatto"
    else:
        mess = 'Ma che cazzo hai scritto, non funziona'
    await update.message.reply_text(
        mess, parse_mode='HTML', reply_markup=ReplyKeyboardRemove()
    )
    return


async def closeweek_command(update: Update, context: ContextTypes.DEFAULT_TYPE, path):
    user = update.message.from_user
    if user.id not in SUPER_USERS:
        await update.message.reply_text(
            'Ti piacerebbe, porco', parse_mode='HTML', reply_markup=ReplyKeyboardRemove()
        )
        return
    message = worker.closeWeek(path)
    await update.message.reply_text(
        message, parse_mode='HTML', reply_markup=ReplyKeyboardRemove()
    )
    return


async def tag_command(update: Update, context: ContextTypes.DEFAULT_TYPE, path):
    command = update.message.text
    user = update.message.from_user
    if user.id not in SUPER_USERS:
        await update.message.reply_text(
            'Ti piacerebbe, porco', parse_mode='HTML', reply_markup=ReplyKeyboardRemove()
        )
        return

    message = worker.tagger(path)

    if message:
        await update.message.reply_text(
            message, parse_mode='HTML', reply_markup=ReplyKeyboardRemove()
        )
    return


async def cal_command(update: Update, context: ContextTypes.DEFAULT_TYPE, path):
    await update.message.reply_text(
        worker.calippi(path), parse_mode='HTML', reply_markup=ReplyKeyboardRemove()
    )
    return


async def animale_command(update: Update, context: ContextTypes.DEFAULT_TYPE, path):
    command = update.message.text
    cmds = command.split(' ')
    if len(cmds) > 1:
        animale = command.replace("/animale ", '')
        message = worker.wins_animale(animale, path)
        await update.message.reply_text(
            message, parse_mode='HTML', reply_markup=ReplyKeyboardRemove()
        )
        return
    else:
        await update.message.reply_text(
            'e dammi un animale', parse_mode='HTML', reply_markup=ReplyKeyboardRemove()
        )
        return


async def player_command(update: Update, context: ContextTypes.DEFAULT_TYPE, path):
    command = update.message.text
    cmds = command.split(' ')
    if len(cmds) > 1:
        player = command.replace("/player ", '')
        message = worker.playerCard(player, path)
        await update.message.reply_text(
            message, parse_mode='HTML', reply_markup=ReplyKeyboardRemove()
        )
        return
    else:
        await update.message.reply_text(
            'e dimmi chi', parse_mode='HTML', reply_markup=ReplyKeyboardRemove()
        )
        return


async def frigo_command(update: Update, context: ContextTypes.DEFAULT_TYPE, path):
    command = update.message.text
    cmds = command.split(' ')
    if len(cmds) > 1:
        arg = command.replace("/frigo ", '').strip()
        if not arg.isdigit():
            await update.message.reply_text(
                'e dammi un numero', parse_mode='HTML', reply_markup=ReplyKeyboardRemove()
            )
            return
        message = worker.frigoInfo(int(arg), path)
        await update.message.reply_text(
            message, parse_mode='HTML', reply_markup=ReplyKeyboardRemove()
        )
        return
    else:
        await update.message.reply_text(
            'e dammi un numero', parse_mode='HTML', reply_markup=ReplyKeyboardRemove()
        )
        return


async def pokewinners_command(update: Update, context: ContextTypes.DEFAULT_TYPE, path):
    command = update.message.text
    cmds = command.split(' ')
    if len(cmds) > 1:
        player = command.replace("/pokewinners ", '')
        message = worker.pokewinners(player, path)
        await update.message.reply_text(
            message, parse_mode='HTML', reply_markup=ReplyKeyboardRemove()
        )
        return
    else:
        await update.message.reply_text(
            'e dimmi chi', parse_mode='HTML', reply_markup=ReplyKeyboardRemove()
        )
        return


async def predilette_command(update: Update, context: ContextTypes.DEFAULT_TYPE, path):
    command = update.message.text
    cmds = command.split(' ')
    if len(cmds) > 1:
        player = command.replace("/predilette ", '')
        message = worker.predilette(player, path)
        await update.message.reply_text(
            message, parse_mode='HTML', reply_markup=ReplyKeyboardRemove()
        )
        return
    else:
        await update.message.reply_text(
            'e dimmi chi', parse_mode='HTML', reply_markup=ReplyKeyboardRemove()
        )
        return


async def affettive_command(update: Update, context: ContextTypes.DEFAULT_TYPE, path):
    command = update.message.text
    cmds = command.split(' ')
    if len(cmds) > 1:
        player = command.replace("/affettive ", '')
        message = worker.affettive(player, path)
        await update.message.reply_text(
            message, parse_mode='HTML', reply_markup=ReplyKeyboardRemove()
        )
        return
    else:
        await update.message.reply_text(
            'e dimmi chi', parse_mode='HTML', reply_markup=ReplyKeyboardRemove()
        )
        return


async def secchezza_command(update: Update, context: ContextTypes.DEFAULT_TYPE, path):
    command = update.message.text
    cmds = command.split(' ')
    if len(cmds) > 1:
        player = command.replace("/secchezza ", '')
        message = worker.secchezza(player, path)
        await update.message.reply_text(
            message, parse_mode='HTML', reply_markup=ReplyKeyboardRemove()
        )
        return
    else:
        await update.message.reply_text(
            'e dimmi chi', parse_mode='HTML', reply_markup=ReplyKeyboardRemove()
        )
        return


async def andazzo_command(update: Update, context: ContextTypes.DEFAULT_TYPE, path):
    plot_path = worker.frigoFrequency(path)

    await update.message.reply_photo(
        plot_path, caption='Numero di Frigo fatte per week', parse_mode='HTML', reply_markup=ReplyKeyboardRemove()
    )
    return


async def ladder_command(update: Update, context: ContextTypes.DEFAULT_TYPE, path):
    await update.message.reply_text(
        'fottiti', parse_mode='HTML', reply_markup=ReplyKeyboardRemove()
    )
    return


async def comandi_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    comandi = sorted(c for c in ALL_COMMANDS if c not in RESTRICTED_COMMANDS)
    message = "Ecco i comandi che puoi usare:\n\n" + "\n".join(f"/{c}" for c in comandi)
    await update.message.reply_text(
        message, parse_mode='HTML', reply_markup=ReplyKeyboardRemove()
    )
    return


async def send_link_calc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        'https://calc.pokemonshowdown.com/randoms.html?mode=randoms', parse_mode='HTML', reply_markup=ReplyKeyboardRemove()
    )
    return


async def unicum_ladder_command(update: Update, context: ContextTypes.DEFAULT_TYPE, path):
    await update.message.reply_text(
        worker.LadderUnici(path), parse_mode='HTML', reply_markup=ReplyKeyboardRemove()
    )
    return


async def unicum_player_command(update: Update, context: ContextTypes.DEFAULT_TYPE, path):
    command = update.message.text
    cmds = command.split(' ')
    if len(cmds) > 1:
        player = command.replace("/unicum ", '')
        message = worker.UniciPlayer(player, path)
        await update.message.reply_text(
            message, parse_mode='HTML', reply_markup=ReplyKeyboardRemove()
        )
        return
    else:
        await update.message.reply_text(
            'e dimmi chi', parse_mode='HTML', reply_markup=ReplyKeyboardRemove()
        )
        return


async def cessi_list_command(update: Update, context: ContextTypes.DEFAULT_TYPE, path):
    await update.message.reply_text(
        worker.ListOfCessi(path), parse_mode='HTML', reply_markup=ReplyKeyboardRemove()
    )
    return


async def animali2_command(update: Update, context: ContextTypes.DEFAULT_TYPE, path):
    await update.message.reply_text(
        worker.WinrateAnimali(path), parse_mode='HTML', reply_markup=ReplyKeyboardRemove()
    )
    return


async def desaparecidos_command(update: Update, context: ContextTypes.DEFAULT_TYPE, path):
    await update.message.reply_text(
        worker.desaparecidos(path), parse_mode='HTML', reply_markup=ReplyKeyboardRemove()
    )
    return


async def swingers_command(update: Update, context: ContextTypes.DEFAULT_TYPE, path):
    await update.message.reply_text(
        worker.swingRanking(path), parse_mode='HTML', reply_markup=ReplyKeyboardRemove()
    )
    return


async def wincons_command(update: Update, context: ContextTypes.DEFAULT_TYPE, path):
    await update.message.reply_text(
        worker.topWincons(path), parse_mode='HTML', reply_markup=ReplyKeyboardRemove()
    )
    return


async def svergiconverters_command(update: Update, context: ContextTypes.DEFAULT_TYPE, path):
    await update.message.reply_text(
        worker.svergiconvertersRanking(path), parse_mode='HTML', reply_markup=ReplyKeyboardRemove()
    )
    return


async def svergitryers_command(update: Update, context: ContextTypes.DEFAULT_TYPE, path):
    await update.message.reply_text(
        worker.svergitryersRanking(path), parse_mode='HTML', reply_markup=ReplyKeyboardRemove()
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

    c_frigo = CommandHandler("frigo", partial(frigo_command, path=db_path))

    c_pl = CommandHandler("player", partial(player_command, path=db_path))
    c_pokewinners = CommandHandler("pokewinners", partial(pokewinners_command, path=db_path))
    c_predilette = CommandHandler("predilette", partial(predilette_command, path=db_path))
    c_affettive = CommandHandler("affettive", partial(affettive_command, path=db_path))
    c_sec = CommandHandler("secchezza", partial(secchezza_command, path=db_path))

    c_and = CommandHandler("andazzo", partial(andazzo_command, path=db_path))

    c_lad = CommandHandler("ladder", partial(ladder_command, path=db_path))

    c_cw = CommandHandler("closeweek", partial(closeweek_command, path=db_path))

    c_calc = CommandHandler("calc", send_link_calc)

    c_comandi = CommandHandler("comandi", comandi_command)

    c_uni_lad = CommandHandler("unicums", partial(unicum_ladder_command, path=db_path))
    c_uni_pl = CommandHandler("unicum", partial(unicum_player_command, path=db_path))

    c_cessi = CommandHandler("cessi", partial(cessi_list_command, path=db_path))

    c_animali2 = CommandHandler("animali2", partial(animali2_command, path=db_path))

    c_desaparecidos = CommandHandler("desaparecidos", partial(desaparecidos_command, path=db_path))

    c_swingers = CommandHandler("swingers", partial(swingers_command, path=db_path))

    c_wincons = CommandHandler("wincons", partial(wincons_command, path=db_path))

    c_svergiconverters = CommandHandler("svergiconverters", partial(svergiconverters_command, path=db_path))
    c_svergitryers = CommandHandler("svergitryers", partial(svergitryers_command, path=db_path))

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
    application.add_handler(c_frigo)
    application.add_handler(c_pl)
    application.add_handler(c_pokewinners)
    application.add_handler(c_predilette)
    application.add_handler(c_affettive)
    application.add_handler(c_sec)
    application.add_handler(c_and)
    application.add_handler(c_lad)
    application.add_handler(c_cw)
    application.add_handler(c_calc)
    application.add_handler(c_comandi)
    application.add_handler(c_uni_lad)
    application.add_handler(c_uni_pl)
    application.add_handler(c_cessi)
    application.add_handler(c_animali2)
    application.add_handler(c_desaparecidos)
    application.add_handler(c_swingers)
    application.add_handler(c_wincons)
    application.add_handler(c_svergiconverters)
    application.add_handler(c_svergitryers)
    # Run the bot until the user presses Ctrl-C
    application.run_polling(allowed_updates=Update.ALL_TYPES)


def testLadder(db_path):
    worker.Ladder(db_path)
