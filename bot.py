from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.ext import (
    Application,
    ApplicationHandlerStop,
    CallbackQueryHandler,
    ContextTypes,
    MessageHandler,
    CommandHandler,
    filters,
)
from dotenv import load_dotenv
from functools import partial
import os
import time

import worker

load_dotenv()
SUPER_USERS = [int(uid) for uid in os.environ.get('SUPER_USERS', '').split(',') if uid.strip()]

TROLL_USERNAME = os.environ.get('TROLL_USERNAME', '').lstrip('@').lower()
TROLL_COOLDOWN_SECONDS = 60
TROLL_BAN_SECONDS = 5 * 60

# user_id -> unix timestamp of their last replay post
_troll_last_replay = {}
# user_id -> unix timestamp until which they are banned
_troll_banned_until = {}

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE, path):
    user = update.message.from_user
    if user.username and user.username.lower() == TROLL_USERNAME:
        _troll_last_replay[user.id] = time.time()

    message = worker.insertResult(path, update.message.text)
    if message:
        await update.message.reply_text(
            message, parse_mode='HTML', reply_markup=ReplyKeyboardRemove()
        )
    time.sleep(5)
    await context.bot.send_message(update.message.chat_id, 'prossima')
    return


async def troll_guard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not user or not user.username or user.username.lower() != TROLL_USERNAME:
        # only the troll user is subject to this guard; everyone else is unaffected
        return

    now = time.time()

    ban_until = _troll_banned_until.get(user.id)
    if ban_until and now < ban_until:
        raise ApplicationHandlerStop

    last_replay = _troll_last_replay.get(user.id)
    if last_replay and now - last_replay < TROLL_COOLDOWN_SECONDS:
        await update.message.reply_text('col cazzo Felaco che ti metti a spammare comandi')
        await update.message.reply_text("ti ho appena registrato la tua merda di frigo, adesso te ne stai zitto")
        _troll_banned_until[user.id] = now + TROLL_BAN_SECONDS
        raise ApplicationHandlerStop


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
            'Che è, ti vuoi cheattare il califfo?', parse_mode='HTML', reply_markup=ReplyKeyboardRemove()
        )
        return
    message = worker.closeWeek(path)
    await update.message.reply_text(
        message, parse_mode='HTML', reply_markup=ReplyKeyboardRemove()
    )
    return


async def clf_command(update: Update, context: ContextTypes.DEFAULT_TYPE, path):
    user = update.message.from_user
    if user.id not in SUPER_USERS:
        await update.message.reply_text(
            'Ti piacerebbe, porco', parse_mode='HTML', reply_markup=ReplyKeyboardRemove()
        )
        return

    progr, message = worker.lastFrigoCancellationPreview(path)
    if progr is None:
        await update.message.reply_text(message, parse_mode='HTML', reply_markup=ReplyKeyboardRemove())
        return

    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ Sì, cancella", callback_data="clf_confirm:{}".format(progr)),
        InlineKeyboardButton("❌ No, lascia stare", callback_data="clf_cancel"),
    ]])
    await update.message.reply_text(message, parse_mode='HTML', reply_markup=keyboard)
    return


async def clf_callback(update: Update, context: ContextTypes.DEFAULT_TYPE, path):
    query = update.callback_query
    user = query.from_user
    if user.id not in SUPER_USERS:
        await query.answer('Ti piacerebbe, porco', show_alert=True)
        return

    if query.data == 'clf_cancel':
        await query.answer()
        await query.edit_message_text('Operazione annullata.', parse_mode='HTML')
        return

    progr = int(query.data.split(':', 1)[1])
    message = worker.cancelLastFrigo(path, progr)
    await query.answer()
    if message is None:
        await query.edit_message_text(
            'Nel frattempo è cambiato qualcosa (nuova frigo caricata?), annullo per sicurezza.',
            parse_mode='HTML'
        )
        return
    await query.edit_message_text(message, parse_mode='HTML')
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
        if arg.lower() == 'random':
            message = worker.frigoInfoRandom(path)
        elif arg.lower() in ('last', 'ultima'):
            message = worker.frigoInfoLast(path)
        elif arg.isdigit():
            message = worker.frigoInfo(int(arg), path)
        else:
            message = worker.frigoInfoForMon(arg, path)
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


COMMAND_SECTIONS = [
    ("📊 Classifiche", [
        ("week", "classifica settimana in corso"),
        ("global", "classifica all time"),
        ("season / siso", "classifica stagione in corso"),
        ("score", "classifica per punteggio MarvWr"),
        ("califfi", "albo d'oro califfi"),
        ("swingers", "giocatori più altalenanti di settimana in settimana"),
    ]),
    ("🐽 Animali", [
        ("animali", "classifica animali per vittorie"),
        ("animali2", "classifica animali per winrate"),
        ("animale &lt;nome&gt;", "statistiche su un animale"),
        ("wincons", "animali più winconati"),
        ("cessi", "animali da sverginare"),
        ("desaparecidos", "animali che non spawnano da più tempo"),
        ("unicums", "classifica vittorie con animali unici"),
        ("unicum &lt;nome&gt;", "animali unici sverginati da un giocatore"),
        ("pokewinners &lt;nome&gt;", "animali con cui un giocatore trionfa di più"),
    ]),
    ("👤 Giocatori", [
        ("player &lt;nome&gt;", "scheda giocatore"),
        ("predilette &lt;nome&gt;", "wincon preferite (per numero)"),
        ("affettive &lt;nome&gt;", "wincon preferite (per percentuale)"),
        ("secchezza &lt;nome&gt;", "da quante frigo non vince"),
        ("svergiconverters", "classifica conversione cessi winconati"),
        ("svergitryers", "classifica tentativi su cessi spawnati"),
    ]),
    ("🧊 Altro", [
        ("frigo &lt;numero&gt;", "dettagli di una frigo specifica"),
        ("andazzo", "grafico frigo giocate per settimana"),
        ("calc", "link al damage calc di Showdown"),
        ("ladder", "vedi tu"),
        ("comandi", "vedi questa lista tipo?"),
    ]),
]


async def comandi_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sections = []
    for title, commands in COMMAND_SECTIONS:
        lines = "\n".join(f"<code>/{cmd}</code> - {desc}" for cmd, desc in commands)
        sections.append(f"<b>{title}</b>\n{lines}")
    message = "Comandi!\n\n" + "\n\n".join(sections)
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

    c_clf = CommandHandler("clf", partial(clf_command, path=db_path))
    cb_clf = CallbackQueryHandler(partial(clf_callback, path=db_path), pattern="^clf_")

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

    application.add_handler(MessageHandler(filters.COMMAND, troll_guard), group=-1)

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
    application.add_handler(c_clf)
    application.add_handler(cb_clf)
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
