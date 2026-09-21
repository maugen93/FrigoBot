from datetime import datetime
import difflib
import html
import random
import graph
import db
import joks
import logics
import replay_reader

MAX_RANKING_NAME_WIDTH = 10


def _capped_name_width(names):
    return min(max((len(n) for n in names), default=0), MAX_RANKING_NAME_WIDTH)


def _truncate_name(name, width):
    return name if len(name) <= width else name[:width]


def insertResult(db_path, sd_link):
    # check on link name
    if 'replay' not in sd_link:
        return None
    if 'freeforallrandombattle' not in sd_link:
        return None

    c = db.openDbConn(db_path)
    if db.isSDReplayAlreadyLoaded(c, sd_link):
        c.close()
        return "Replay già caricato"

    players, winner, poke_winner = replay_reader.elab_sd_replay(sd_link)

    # controllo nick registrati
    for pid in list(players.keys()):
        played_sd = players[pid]['collo']
        player = db.getPlayerFromSDName(c, played_sd)

        if not player:
            c.close()
            return 'Collo {} non presente nel DB'.format(played_sd)
        players[pid]['id'] = player

    progr = db.getNumberOfFrigos(c) + 1
    week = db.getActualWeek(c)
    # salvataggio spawns
    spawns_for_cache = []
    for pid in list(players.keys()):
        player = players[pid]['id']
        ultimo_in_campo = players[pid]['ultimo_in_campo']
        for an in players[pid]['animali']:
            winconato = (an == ultimo_in_campo)
            db.insertSpawn(c, progr, player, an, winconato=winconato)
            spawns_for_cache.append((player, an, winconato))

    winner_name = db.getPlayerFromSDName(c, winner)
    data = datetime.now().strftime('%d/%m/%y')

    # insert
    participants = [players['p1']['id'], players['p2']['id'], players['p3']['id'], players['p4']['id']]
    db.insertNewFrigo(c, progr, week, data, *participants, winner_name, poke_winner, sd_link)
    db.updateStatsCacheForFrigo(c, progr, week, participants, spawns_for_cache, winner_name, poke_winner)

    message = "Inserita Frigo Nr <code>{}</code>\n\nPartecipanti:".format(progr)
    for pid in list(players.keys()):
        # message = message + '\n{} : {}'.format(players[pid]['id'], str(players[pid]['animali']).replace("'", ''))
        message = message + '\n{}'.format(players[pid]['id'])
    message = message + '\n' + joks.messForWinnerOnReg(winner_name, poke_winner)

    return message


def lastFrigoCancellationPreview(db_path):
    '''Ritorna (progr, messaggio) con i dettagli dell'ultima frigo caricata, da
    mostrare come richiesta di conferma prima di cancellarla. Ritorna (None,
    messaggio) se non c'e' nessuna frigo da cancellare.'''
    conn = db.openDbConn(db_path)
    progr = db.getNumberOfFrigos(conn)
    if not progr:
        db.closeDbConn(conn)
        return None, "Non c'è nessuna frigo da cancellare"

    frigo = db.getFrigoInfoFromNumber(conn, progr)
    db.closeDbConn(conn)

    players = ', '.join(p for p in (frigo['p1'], frigo['p2'], frigo['p3'], frigo['p4']) if p)
    message = (
        "Sicuro di voler cancellare la Frigo Nr <code>{}</code>?\n"
        "Partecipanti: {}\n"
        "Vincitore: {} (con {})\n\n"
        "Verranno rimossi anche tutti gli spawn e le statistiche legate a questa frigo."
    ).format(progr, players, frigo['winner'], frigo['pokewinner'])
    return progr, message


def cancelLastFrigo(db_path, progr):
    '''Cancella la frigo `progr` solo se e' ancora l'ultima caricata (evita di
    cancellare la frigo sbagliata se nel frattempo ne e' stata inserita una
    nuova mentre si aspettava la conferma). Ritorna None in quel caso.'''
    conn = db.openDbConn(db_path)
    if db.getNumberOfFrigos(conn) != progr:
        db.closeDbConn(conn)
        return None

    db.deleteFrigo(conn, progr)
    db.closeDbConn(conn)
    return "Frigo Nr <code>{}</code> cancellata, con tutto quel che c'era sopra.".format(progr)


def frigoInfo(frigo_nr, db_path):
    conn = db.openDbConn(db_path)
    frigo = db.getFrigoInfoFromNumber(conn, frigo_nr)
    db.closeDbConn(conn)

    if not frigo:
        return "Se magari mi dessi una frigo non inventata"

    players = [frigo['p1'], frigo['p2'], frigo['p3'], frigo['p4']]

    message = "Frigo # <code>{}</code>".format(frigo['progr'])
    for p in players:
        if p:
            message = message + '\n{}'.format(p)
    if any(p is None for p in players):
        message = message + '\n\n(frigo dell\'età della pietra, dati parziali)\n'
    message = message + '\n' + joks.messForWinnerOnReg(frigo['winner'], frigo['pokewinner'])

    if frigo['sd_replay']:

        message = message + '\n\n<a href="{}">&lt;clicca-qui-per-il-replay&gt;</a>'.format(html.escape(frigo['sd_replay'], quote=True))

    return message


def frigoInfoRandom(db_path):
    conn = db.openDbConn(db_path)
    max_frigo = db.getNumberOfFrigos(conn)
    db.closeDbConn(conn)

    if not max_frigo:
        return "Se magari mi dessi una frigo non inventata"

    return frigoInfo(random.randint(1, max_frigo), db_path)


def frigoInfoLast(db_path):
    conn = db.openDbConn(db_path)
    max_frigo = db.getNumberOfFrigos(conn)
    db.closeDbConn(conn)

    if not max_frigo:
        return "Se magari mi dessi una frigo non inventata"

    return frigoInfo(max_frigo, db_path)


def frigoInfoForMon(animale, db_path):
    conn = db.openDbConn(db_path)
    mons = db.getAllMons(conn)
    top_similar = None
    top_similitude = 0
    for m in mons:
        seq = difflib.SequenceMatcher(a=animale.lower(), b=m.lower())
        if seq.ratio() > 0.7 and seq.ratio() > top_similitude:
            top_similar = m
            top_similitude = seq.ratio()

    if not top_similar:
        db.closeDbConn(conn)
        return "non mi risulta che qualcosa chiamato {} abbia mai solcato i palchi".format(animale)

    _, wins = db.getWinsPkmn(conn, top_similar)
    if not wins:
        db.closeDbConn(conn)
        return "che frigo vuoi vedere che è ancora un cesso"

    last_frigo_nr = db.getLastFrigoWonByMon(conn, top_similar)
    db.closeDbConn(conn)

    if not last_frigo_nr:
        return "che frigo vuoi vedere che è ancora un cesso"

    return frigoInfo(last_frigo_nr, db_path)


def rank_all(db_path):
    c = db.openDbConn(db_path)
    players, wins, partecipate = db.getPlayerLeaderboard(c)
    db.closeDbConn(c)

    message = 'Classifica All Time\n\n'

    rank_width = len(str(len(players)))
    name_width = max((len(p) for p in players), default=0)
    wins_width = max((len(str(w)) for w in wins), default=1)

    for i in range(len(players)):
        message = message + "<code>{rank:>{rw}}) {name:<{nw}}  {wins:>{ww}}</code>\n".format(
            rank=i + 1, name=players[i], wins=wins[i],
            rw=rank_width, nw=name_width, ww=wins_width
        )
    return message


def rank_season(db_path):
    # return 'Ma che siso e siso, le frigo sono morte'
    c = db.openDbConn(db_path)
    players, wins, partecipate = db.getPlayerLeaderboard(c, from_frigo=1844, to_frigo=None)
    message = 'Classifica DefinizioneScientifica Siso\n\n'

    players_dict_arr=[]
    for i in range(len(players)):
        player_dict={'player':players[i],'wins':wins[i],'part':partecipate[i],
                     '5-1':(wins[i] * 5 - (partecipate[i] -wins[i]))
                     }
        players_dict_arr.append(player_dict)
    ordinati = sorted(players_dict_arr, key=lambda x: x["5-1"], reverse=True)

    rank_width = len(str(len(ordinati)))
    name_width = max((len(o['player']) for o in ordinati), default=0)
    score_width = max((len(str(o['5-1'])) for o in ordinati), default=1)
    wins_width = max((len(str(o['wins'])) for o in ordinati), default=1)
    part_width = max((len(str(o['part'])) for o in ordinati), default=1)

    for i in range(len(ordinati)):
        message = message + "<code>{rank:>{rw}}) {name:<{nw}} {score:>{sw}}  [{wins:>{ww}}/{part:>{pw}}]</code>\n".format(
            rank=i + 1, name=ordinati[i]['player'], score=ordinati[i]['5-1'],
            wins=ordinati[i]['wins'], part=ordinati[i]['part'],
            rw=rank_width, nw=name_width, sw=score_width, ww=wins_width, pw=part_width
        )

    message = message + '\nF counter: <code>{}</code>\n'.format(sum(wins))
    message = message + "Metodo Calcolo: 5-1\n"
    message = message + "Started: 01/07/2026\n"
    message = message + "Will end: 30/09/2026"
    db.closeDbConn(c)
    return message


def rank_pkmn(db_path, limit=5):
    c = db.openDbConn(db_path)
    pk, wins = db.getLeaderboardPkmn(c)
    message = 'Classifica Animali\n\n-'

    actual_wins = wins[0] + 1
    pos = 0
    for i in range(len(pk)):
        if wins[i] < actual_wins:
            pos = pos + 1
            actual_wins = wins[i]
            if pos > limit:
                break
            message = message[:-2]
            message = message + "\n[<code>{}</code>] (<code>{}</code> wins): ".format(pos, actual_wins)
        message = message + pk[i]
        message = message + ', '
        # if i < limit:
        #    message = message + "{}) {}  {}\n".format(i + 1, pk[i], wins[i])
    db.closeDbConn(c)
    message = message[:-2]
    return message


def rank_week(db_path):
    c = db.openDbConn(db_path)
    w = db.getActualWeek(c)
    players, vinte, partecipate = db.getPlayerLeaderboard(c, week=w)
    db.closeDbConn(c)

    message = 'Classifica Settimana <code>{}</code>\n\n'.format(w)

    rank_width = len(str(len(players)))
    name_width = max((len(p) for p in players), default=0)
    wins_width = max((len(str(v)) for v in vinte), default=1)
    part_width = max((len(str(p)) for p in partecipate), default=1)

    for i in range(len(players)):
        message = message + "<code>{rank:>{rw}}) {name:<{nw}} {wins:>{ww}}  [{part:>{pw}}]</code>\n".format(
            rank=i + 1, name=players[i], wins=vinte[i], part=partecipate[i],
            rw=rank_width, nw=name_width, ww=wins_width, pw=part_width
        )
    return message


def run_query(query, db_path):
    c = db.openDbConn(db_path)
    try:
        db.run_custom_query(c, query)
        db.closeDbConn(c)
        return True
    except Exception:
        db.closeDbConn(c)
        return False


def global_score(path):
    conn = db.openDbConn(path)
    players, vinte, partecipate = db.getPlayerLeaderboard(conn, only_from_reg=True)
    db.closeDbConn(conn)
    scores = []
    message = 'Classifica per score [MarvPondWR]\nPunteggio calcolato su <code>{}</code> f\n'.format(sum(vinte))
    for i in range(len(players)):
        # scores.append(int((vinte[i] / partecipate[i]) * math.log(partecipate[i]) * 1000))
        scores.append(logics.calcMarvWr(partecipate[i], vinte[i], sum(vinte)))
    comb = sorted(zip(players, vinte, partecipate, scores), key=lambda x: x[3], reverse=True)
    players_ord, vinte_ord, partecipate_ord, scores_ord = zip(*comb)
    players_ord = list(players_ord)
    vinte_ord = list(vinte_ord)

    partecipate_ord = list(partecipate_ord)
    scores_ord = list(scores_ord)

    rank_width = len(str(len(players_ord)))
    name_width = max((len(p) for p in players_ord), default=0)
    score_width = max((len(str(s)) for s in scores_ord), default=1)
    wins_width = max((len(str(v)) for v in vinte_ord), default=1)
    part_width = max((len(str(p)) for p in partecipate_ord), default=1)

    for i in range(len(players)):
        message = message + "\n<code>{rank:>{rw}}) {name:<{nw}} {score:>{sw}}  [{wins:>{ww}}/{part:>{pw}}]</code>".format(
            rank=i + 1, name=players_ord[i], score=scores_ord[i],
            wins=vinte_ord[i], part=partecipate_ord[i],
            rw=rank_width, nw=name_width, sw=score_width, ww=wins_width, pw=part_width
        )

    return message


def swingRanking(db_path):
    conn = db.openDbConn(db_path)
    players = db.getAllPlayers(conn)
    results = []
    for p in players:
        weekly_games, weekly_wins = db.getWeeklyGamesAndWinsByPlayer(conn, p)
        swing = logics.calcWinrateVariability(weekly_games, weekly_wins)
        if swing is not None:
            results.append((p, swing))
    db.closeDbConn(conn)

    results.sort(key=lambda x: x[1]['score'], reverse=True)

    message = 'SwingScore Ranking\n(win rate stimato con intervallo di confidenza)\n\n'

    rank_width = len(str(len(results)))
    name_width = _capped_name_width(player for player, _ in results)
    score_width = max((len(str(swing['score'])) for _, swing in results), default=1)

    for i, (player, swing) in enumerate(results):
        message = message + "<code>{rank:>{rw}}) {name:<{nw}} {score:>{sw}} ({mean:.0f}%±{std:.0f})</code>\n".format(
            rank=i + 1, name=_truncate_name(player, name_width), score=swing['score'], mean=swing['mean_wr'], std=swing['true_stdev'],
            rw=rank_width, nw=name_width, sw=score_width
        )
    return message


def svergiconvertersRanking(db_path):
    conn = db.openDbConn(db_path)
    players = db.getAllPlayers(conn)
    results = []
    for p in players:
        tentativi, vinte = db.getCessiWinconByPlayer(conn, p)
        if tentativi > 0:
            _, winners_whenPlayed = db.getPlayerInfo(conn, p)
            results.append((p, vinte, tentativi, vinte / tentativi * 100, len(winners_whenPlayed)))
    db.closeDbConn(conn)

    results.sort(key=lambda x: x[3], reverse=True)

    message = 'Svergiconversione Ranking\n(sverginate / frigo cessi winconati — frigo giocate)\n\n'

    rank_width = len(str(len(results)))
    name_width = _capped_name_width(player for player, _, _, _, _ in results)
    vinte_width = max((len(str(vinte)) for _, vinte, _, _, _ in results), default=1)
    tentativi_width = max((len(str(tentativi)) for _, _, tentativi, _, _ in results), default=1)
    giocate_width = max((len(str(giocate)) for _, _, _, _, giocate in results), default=1)

    for i, (player, vinte, tentativi, perc, giocate) in enumerate(results):
        message = message + "<code>{rank:>{rw}}) {name:<{nw}} {perc:>{pw}.0f}% ({vinte:>{vw}}/{tentativi:>{tw}} — {giocate:>{gw}})</code>\n".format(
            rank=i + 1, name=_truncate_name(player, name_width), perc=perc, vinte=vinte, tentativi=tentativi, giocate=giocate,
            rw=rank_width, nw=name_width, pw=3, vw=vinte_width, tw=tentativi_width, gw=giocate_width
        )
    return message


def svergitryersRanking(db_path):
    conn = db.openDbConn(db_path)
    players = db.getAllPlayers(conn)
    results = []
    for p in players:
        tentativi, vinte = db.getCessiWinconByPlayer(conn, p)
        cessi_spawnati = db.getCessiSpawnsByPlayer(conn, p)
        if cessi_spawnati > 0:
            results.append((p, vinte, tentativi, cessi_spawnati, tentativi / cessi_spawnati * 100))
    db.closeDbConn(conn)

    results.sort(key=lambda x: x[4], reverse=True)

    message = 'Svergitentativi Ranking\n(frigo cessi winconati / frigo cessi spawnati, sverginate)\n\n'

    rank_width = len(str(len(results)))
    name_width = _capped_name_width(player for player, _, _, _, _ in results)
    tentativi_width = max((len(str(tentativi)) for _, _, tentativi, _, _ in results), default=1)
    spawnati_width = max((len(str(cs)) for _, _, _, cs, _ in results), default=1)
    vinte_width = max((len(str(vinte)) for _, vinte, _, _, _ in results), default=1)

    for i, (player, vinte, tentativi, cessi_spawnati, perc) in enumerate(results):
        message = message + "<code>{rank:>{rw}}) {name:<{nw}} {perc:>{pw}.0f}% ({tentativi:>{tw}}/{cs:>{cw}}, {vinte:>{vw}})</code>\n".format(
            rank=i + 1, name=_truncate_name(player, name_width), perc=perc, tentativi=tentativi, cs=cessi_spawnati, vinte=vinte,
            rw=rank_width, nw=name_width, pw=3, tw=tentativi_width, cw=spawnati_width, vw=vinte_width
        )
    return message


def wins_animale(animale, path):
    conn = db.openDbConn(path)
    mons = db.getAllMons(conn)
    top_similar = None
    top_similitude = 0
    for m in mons:
        seq = difflib.SequenceMatcher(a=animale.lower(), b=m.lower())
        if seq.ratio() > 0.7 and seq.ratio() > top_similitude:
            top_similar = m
            top_similitude = seq.ratio()

    if not top_similar:
        db.closeDbConn(conn)
        return "non mi risulta che qualcosa chiamato {} abbia mai solcato i palchi".format(animale)

    winners, wins = db.getWinsPkmn(conn, top_similar)

    n_last_spawn=db.getSinceHowManyFrigosSpawn(conn, top_similar)

    spawn_message='\n\nApparso letteralmente nell\'ultima frigo giocata' if n_last_spawn==0 else '\n\nNon si vede in giro da <code>{}</code> frigo'.format(n_last_spawn)

    spawns_count, wins_count = db.getSpawnsWithWinsOfPokemon(conn, top_similar)
    wincon_count = db.getWinconCountForPokemon(conn, top_similar)
    wincon_message = '\n\nWinconato <code>{}</code> volte'.format(wincon_count)
    affettiva_player, affettiva_wincon_cnt, affettiva_spawn_cnt = db.getTopWinconizerForMon(conn, top_similar)
    prediletta_player, prediletta_wincon_cnt, prediletta_spawn_cnt = db.getMostFrequentWinconizerForMon(conn, top_similar)

    if affettiva_player and affettiva_player == prediletta_player:
        wincon_message = wincon_message + '\nWincon affettiva e prediletta di {} (<code>{:.1f}%</code>, <code>{}/{}</code>)'.format(
            affettiva_player, affettiva_wincon_cnt / affettiva_spawn_cnt * 100, affettiva_wincon_cnt, affettiva_spawn_cnt
        )
    else:
        if affettiva_player:
            wincon_message = wincon_message + '\nWincon maggiormente affettiva per {} (<code>{:.1f}%</code>, <code>{}/{}</code>)'.format(
                affettiva_player, affettiva_wincon_cnt / affettiva_spawn_cnt * 100, affettiva_wincon_cnt, affettiva_spawn_cnt
            )
        if prediletta_player:
            wincon_message = wincon_message + '\nWincon prediletta maggiormente da {} (<code>{}/{}</code>)'.format(
                prediletta_player, prediletta_wincon_cnt, prediletta_spawn_cnt
            )
    if len(wins) == 0:
        db.closeDbConn(conn)
        return 'Sto cesso di {} non ha mai vinto una sebbene sia spawnato in almeno <code>{}</code> frigo'.format(top_similar,
                                                                                                     spawns_count)+wincon_message+spawn_message

    message = "Vittorie di {}: <code>{}</code>\n\n".format(top_similar, sum(wins))
    for w in range(len(winners)):
        message = message + "<code>{}</code> con {}\n".format(wins[w], winners[w])

    message = message + '\nSu <code>{}</code> spawn registrati ha vinto <code>{}</code> volte'.format(spawns_count, wins_count)
    message = message + wincon_message
    message =message +spawn_message
    db.closeDbConn(conn)
    return message


def _ordinal(n):
    if 10 <= n % 100 <= 20:
        suffix = 'th'
    else:
        suffix = {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')
    return '{}{}'.format(n, suffix)


def _formatRank(value, all_values):
    better = sum(1 for v in all_values if v > value)
    rank = better + 1
    tied = sum(1 for v in all_values if v == value) > 1
    label = _ordinal(rank)
    if tied:
        label = 't-{}'.format(label)
    medal = {1: '🥇 ', 2: '🥈 ', 3: '🥉 '}.get(rank, '') if not tied else ''
    return ' [{}{}]'.format(medal, label)


def playerCard(player, db_path):
    conn = db.openDbConn(db_path)
    players = db.getAllPlayers(conn)
    top_similar = None
    top_similitude = 0
    for m in players:
        seq = difflib.SequenceMatcher(a=player.lower(), b=m.lower())
        if seq.ratio() > 0.7 and seq.ratio() > top_similitude:
            top_similar = m
            top_similitude = seq.ratio()

    if not top_similar:
        db.closeDbConn(conn)
        return "non conosco questo {}".format(player)

    total_frigos_from_reg = db.getNumberOfFrigos(conn, from_reg=True)

    all_wins = []
    all_winrates = []
    all_marvwr = []
    all_swing = []
    all_animali_unici = []
    all_cessi_wr = []

    num_wins = winners_whenPlayed = winsWhenPlayed = winrate_perc = None
    marvWr = animali_unici = winrate_variability = None
    cessi_tentativi = cessi_vinte = None

    for p in players:
        p_num_wins, p_winners_whenPlayed = db.getPlayerInfo(conn, p)
        p_winsWhenPlayed = len([j for j in p_winners_whenPlayed if j == p])
        p_winrate = (p_winsWhenPlayed / len(p_winners_whenPlayed)) * 100 if len(p_winners_whenPlayed) > 0 else 0
        p_marvwr = logics.calcMarvWr(len(p_winners_whenPlayed), p_winsWhenPlayed, total_frigos_from_reg)
        p_animali_unici, _ = db.getUnicumByPlayer(conn, p)
        p_weekly_games, p_weekly_wins = db.getWeeklyGamesAndWinsByPlayer(conn, p)
        p_swing = logics.calcWinrateVariability(p_weekly_games, p_weekly_wins)
        p_cessi_tentativi, p_cessi_vinte = db.getCessiWinconByPlayer(conn, p)

        all_wins.append(p_num_wins)
        all_winrates.append(p_winrate)
        all_marvwr.append(p_marvwr)
        all_animali_unici.append(len(p_animali_unici))
        if p_swing is not None:
            all_swing.append(p_swing['score'])
        if p_cessi_tentativi > 0:
            all_cessi_wr.append(p_cessi_vinte / p_cessi_tentativi * 100)

        if p == top_similar:
            num_wins = p_num_wins
            winners_whenPlayed = p_winners_whenPlayed
            winsWhenPlayed = p_winsWhenPlayed
            winrate_perc = p_winrate
            marvWr = p_marvwr
            animali_unici = p_animali_unici
            winrate_variability = p_swing
            cessi_tentativi = p_cessi_tentativi
            cessi_vinte = p_cessi_vinte

    num_distinct_pk = db.getDistinctPokeByPlayer(conn, top_similar)

    message = f"<b>{top_similar}</b>\n\n"
    message = message + 'Frigo vinte overall <code>{}</code>{}\n'.format(num_wins, _formatRank(num_wins, all_wins))
    message = message + 'Winrate <code>{0:.2f}%</code>{1} '.format(winrate_perc, _formatRank(winrate_perc, all_winrates))

    message = message + '(<code>{}</code>/<code>{}</code> su <code>{}</code> registrate)\n'.format(
        winsWhenPlayed, len(winners_whenPlayed), db.getNumFrigoWithPlayersSpecified(conn)
    )

    message = message + 'MarvWr Score: <code>{}</code>{} '.format(marvWr, _formatRank(marvWr, all_marvwr))

    if winrate_variability is None:
        message = message + '\n→ SwingScore: n/d (dati non sufizienti)\n'
    else:
        message = message + '\n→ SwingScore: <code>{}</code>{} (EWR <code>{:.1f}%</code> ± <code>{:.1f}</code>)\n'.format(
            winrate_variability['score'], _formatRank(winrate_variability['score'], all_swing),
            winrate_variability['mean_wr'], winrate_variability['true_stdev']
        )

    message = message + '\nDistinto al <code>{0:.1f}%</code>'.format(num_distinct_pk * 100 / num_wins)
    message = message + ' con <code>{}</code> distinti animali\n'.format(num_distinct_pk)
    message = message + 'Animali Unici: <code>{}</code>{}\n'.format(
        len(animali_unici), _formatRank(len(animali_unici), all_animali_unici)
    )

    if cessi_tentativi == 0:
        message = message + 'Svergiconversione: n/d (e quando mai ci ha provato)\n\n'
    else:
        cessi_wr = cessi_vinte / cessi_tentativi * 100
        message = message + 'Svergiconversione: <code>{0:.1f}%</code>{1} (<code>{2}</code> su <code>{3}</code> tentativi)\n\n'.format(
            cessi_wr, _formatRank(cessi_wr, all_cessi_wr), cessi_vinte, cessi_tentativi
        )

    affettiva_mon, affettiva_wincon_cnt, affettiva_spawn_cnt = db.getPreferredWinconByPlayer(conn, top_similar)
    prediletta_mon, prediletta_wincon_cnt, prediletta_spawn_cnt = db.getMostWinconedByPlayer(conn, top_similar)

    if affettiva_mon and affettiva_mon == prediletta_mon:
        message = message + 'Wincon affettiva e prediletta: {} <code>{:.1f}%</code> (<code>{}</code>/<code>{}</code>)\n'.format(
            affettiva_mon, affettiva_wincon_cnt / affettiva_spawn_cnt * 100, affettiva_wincon_cnt, affettiva_spawn_cnt
        )
    else:
        if affettiva_mon:
            message = message + 'Wincon affettiva: {} <code>{:.1f}%</code> (<code>{}</code>/<code>{}</code>)\n'.format(
                affettiva_mon, affettiva_wincon_cnt / affettiva_spawn_cnt * 100, affettiva_wincon_cnt, affettiva_spawn_cnt
            )
        if prediletta_mon:
            message = message + 'Wincon prediletta: {} (<code>{}</code>/<code>{}</code>)\n'.format(
                prediletta_mon, prediletta_wincon_cnt, prediletta_spawn_cnt
            )

    pk, cnts = db.getMostPokeWinnerByPlayer(conn, top_similar)
    db.closeDbConn(conn)

    cnt_i = cnts[0]
    message = message + "\nAmici Vincenti:\n\t\t[<code>{}</code>]: ".format(cnt_i)

    for i in range(len(pk)):
        if i < 10:
            if cnts[i] < cnt_i:
                cnt_i = cnts[i]
                message = message[:-2]
                message = message + "\n\t\t[<code>{}</code>]: ".format(cnt_i)
                message = message + "{}, ".format(pk[i])
            else:
                message = message + "{}, ".format(pk[i])

    if 'Amici Vincenti' in message:
        message = message[:-2]
    return message


def pokewinners(player, db_path):
    conn = db.openDbConn(db_path)
    players = db.getAllPlayers(conn)
    top_similar = None
    top_similitude = 0
    for m in players:
        seq = difflib.SequenceMatcher(a=player.lower(), b=m.lower())
        if seq.ratio() > 0.7 and seq.ratio() > top_similitude:
            top_similar = m
            top_similitude = seq.ratio()

    if not top_similar:
        db.closeDbConn(conn)
        return "non conosco questo {}".format(player)

    pks, cnts = db.getMostPokeWinnerByPlayer(conn, top_similar)
    db.closeDbConn(conn)

    if not pks:
        return "{} non ha mai vinto una frigo, scarsismo".format(top_similar)

    cnt_i = cnts[0]
    message = "<b>{}</b> ha trionfato con codesti animali:\n\n\t\t[<code>{}</code>]: ".format(top_similar, cnt_i)
    for i in range(len(pks)):
        if cnts[i] < cnt_i:
            cnt_i = cnts[i]
            message = message[:-2]
            message = message + "\n\t\t[<code>{}</code>]: ".format(cnt_i)
            message = message + "{}, ".format(pks[i])
        else:
            message = message + "{}, ".format(pks[i])
    message = message[:-2]
    return message


def predilette(player, db_path, limit=10):
    conn = db.openDbConn(db_path)
    players = db.getAllPlayers(conn)
    top_similar = None
    top_similitude = 0
    for m in players:
        seq = difflib.SequenceMatcher(a=player.lower(), b=m.lower())
        if seq.ratio() > 0.7 and seq.ratio() > top_similitude:
            top_similar = m
            top_similitude = seq.ratio()

    if not top_similar:
        db.closeDbConn(conn)
        return "non conosco questo {}".format(player)

    top = db.getTopMostWinconedByPlayer(conn, top_similar, limit)
    db.closeDbConn(conn)

    if not top:
        return "{} non ha mai winconato nulla, scarsismo".format(top_similar)

    message = "<b>{}</b> - Top {} wincon predilette (per numero di volte):\n".format(top_similar, len(top))

    rank_width = len(str(len(top)))
    name_width = max((len(mon) for mon, _, _ in top), default=0)
    cnt_width = max((len(str(wincon_cnt)) for _, wincon_cnt, _ in top), default=1)

    for i, (mon, wincon_cnt, spawn_cnt) in enumerate(top):
        wr = wincon_cnt / spawn_cnt * 100
        message = message + "\n<code>{rank:>{rw}}) {name:<{nw}} {cnt:>{cw}} ({wr:>3.0f}%)</code>".format(
            rank=i + 1, name=mon, cnt=wincon_cnt, wr=wr,
            rw=rank_width, nw=name_width, cw=cnt_width
        )
    return message


def affettive(player, db_path, limit=10):
    conn = db.openDbConn(db_path)
    players = db.getAllPlayers(conn)
    top_similar = None
    top_similitude = 0
    for m in players:
        seq = difflib.SequenceMatcher(a=player.lower(), b=m.lower())
        if seq.ratio() > 0.7 and seq.ratio() > top_similitude:
            top_similar = m
            top_similitude = seq.ratio()

    if not top_similar:
        db.closeDbConn(conn)
        return "non conosco questo {}".format(player)

    top = db.getTopPreferredWinconsByPlayer(conn, top_similar, limit)
    db.closeDbConn(conn)

    if not top:
        return "{} non ha mai winconato nulla, scarsismo".format(top_similar)

    message = "<b>{}</b> - Top {} wincon affettive (per percentuale):\n".format(top_similar, len(top))

    rank_width = len(str(len(top)))
    name_width = max((len(mon) for mon, _, _ in top), default=0)
    cnt_width = max((len(str(wincon_cnt)) for _, wincon_cnt, _ in top), default=1)
    spawn_width = max((len(str(spawn_cnt)) for _, _, spawn_cnt in top), default=1)

    for i, (mon, wincon_cnt, spawn_cnt) in enumerate(top):
        wr = wincon_cnt / spawn_cnt * 100
        message = message + "\n<code>{rank:>{rw}}) {name:<{nw}} {wr:>3.0f}% ({cnt:>{cw}}/{spawn:>{sw}})</code>".format(
            rank=i + 1, name=mon, wr=wr, cnt=wincon_cnt, spawn=spawn_cnt,
            rw=rank_width, nw=name_width, cw=cnt_width, sw=spawn_width
        )
    return message


def secchezza(player, db_path):
    conn = db.openDbConn(db_path)
    players = db.getAllPlayers(conn)
    top_similar = None
    top_similitude = 0
    for m in players:
        seq = difflib.SequenceMatcher(a=player.lower(), b=m.lower())
        if seq.ratio() > 0.7 and seq.ratio() > top_similitude:
            top_similar = m
            top_similitude = seq.ratio()

    if not top_similar:
        db.closeDbConn(conn)
        return "non conosco questo {}".format(player)

    # secchezza=db.getNumberOfFrigos(conn)-db.getLastWinnedFrigo(conn,top_similar)
    secchezza = db.getNumberPartecipiedSinceLastWin(conn, top_similar)
    last = db.getLastPartecipiedFrigo(conn, top_similar)
    if not last:
        return 'non gioca da indefinite frigo'
    else:
        notgame = db.getNumberOfFrigos(conn) - db.getLastPartecipiedFrigo(conn, top_similar)
    if secchezza == 0:
        message = "il porco ha vinto l'ultima frigo che ha giocato\n"
    else:
        message = '{} non vince da <code>{}</code> frigo giocate\n'.format(top_similar, secchezza)
    message = message + 'ultima frigo giocata <code>{}</code> frigo fa\n'.format(notgame)

    w = db.getActualWeek(conn)
    print(w)
    num_in_week = db.getPartecipiedAtWeek(conn, w, top_similar)
    message = message + 'Frigo giocate in settimana: <code>{}</code>'.format(num_in_week)
    db.closeDbConn(conn)
    return message


def tagger(db_path):
    conn = db.openDbConn(db_path)
    tags = db.getTagLastPartecipiers(conn)
    db.closeDbConn(conn)
    message = ''
    for t in tags:
        if not t:
            continue
        message = message + '{} '.format(t)
    return message + 'frigo'


def frigoFrequency(db_path):
    conn = db.openDbConn(db_path)
    w, f = db.getNumberOfFrigoPerWeek(conn)
    db.closeDbConn(conn)
    save_path = r'frequenza.png'
    graph.save_hist(w, f, save_path)
    db.closeDbConn(conn)
    return save_path


def closeWeek(db_path):
    conn = db.openDbConn(db_path)
    data_today = datetime.now().strftime('%d/%m/%y')
    actual_w = db.getActualWeek(conn)
    dt_start_actual_week,x=db.getWeekInfo(conn,actual_w)

    # durata week in giorni
    durata_giorni = days_difference = (datetime.now() - datetime.strptime(dt_start_actual_week, "%d/%m/%y")).days


    db.closeweek(conn, actual_w, data_today)

    # dump calippo
    players, vinte, partecipate = db.getPlayerLeaderboard(conn, week=actual_w)

    cessi, sverginatori = db.getUniciVincentiInWeek(conn, week=actual_w)

    calippo = players[0]
    for i in range(1, len(players)):
        if vinte[i] == vinte[0] and partecipate[i] == partecipate[0]:
            calippo = calippo + '-' + players[i]

    db.insertCalippo(conn, actual_w, calippo, vinte[0])

    db.newweek(conn, actual_w + 1, data_today)

    # most pig
    most_pig = players[0]
    most_pig_score = 0
    most_thin = players[0]
    most_thin_score = 10000
    for i in range(len(players)):
        score_i = vinte[i] * 4 - (partecipate[i] - vinte[i])
        if score_i > most_pig_score:
            most_pig = players[i]
            most_pig_score = score_i
        if score_i <= most_thin_score:
            most_thin = players[i]
            most_thin_score = score_i

    # who smiles
    players_tot, vinte_tot, partecipate_tot = db.getPlayerLeaderboard(conn, only_from_reg=True)
    who_smile = players[0]
    who_not_smile = players[0]
    max_increment = 0
    min_increment = 50000
    for i in range(len(players)):
        i_tot = players_tot.index(players[i])
        score_old = logics.calcMarvWr(partecipate_tot[i_tot] - partecipate[i], vinte_tot[i_tot] - vinte[i],
                                      sum(vinte_tot) - sum(vinte))
        score_now = logics.calcMarvWr(partecipate_tot[i_tot], vinte_tot[i_tot], sum(vinte_tot))
        score_diff = score_now - score_old
        if score_diff > max_increment:
            max_increment = score_diff
            who_smile = players[i]
        if score_diff < min_increment:
            min_increment = score_diff
            who_not_smile = players[i]
    message = '🔴 Chiusa settimana <code>{}</code>\n\n'.format(actual_w)
    message = message + '👳 Califfa {} con <code>{}</code> vittorie\n\n'.format(calippo, vinte[0])
    message = message + '🐖 Porco di settimana: {} (<code>{}</code> su <code>{}</code>)\n'.format(most_pig, vinte[players.index(most_pig)],
                                                                      partecipate[players.index(most_pig)])
    message = message + '🤏 Il più rachitico: {} (<code>{}</code> su <code>{}</code>)\n\n'.format(most_thin, vinte[players.index(most_thin)],
                                                                      partecipate[players.index(most_thin)])
    message = message + '😆 E in tutto ciò chi ride?\n'
    message = message + '¬ Di certo non {} (<code>{}</code> MarvWr points)\n'.format(who_not_smile, min_increment)
    message = message + '¬ Tendenzialmente ride {} (+<code>{}</code> MarvWr points)\n\n'.format(who_smile, max_increment)

    if len(cessi) > 0:
        message = message + '🔞 Sono stati sverginati <code>{}</code> cessi, principalmente da {}\n\n'.format(
            len(list(set(cessi))), joks.str_sverg(sverginatori))
    else:
        message = message + '🔞 Nessun cesso è stato sverginato\n\n'

    message = message + '🧊 La settimana è durata <code>{}</code> giorni e si è frigato per un ammontare complessivo di <code>{}</code> frigo, '.format(durata_giorni,sum(vinte))
    f_per_day=sum(vinte)/durata_giorni
    message = message + 'per una media {} '.format(joks.commentoMedia(f_per_day))
    message = message + 'di <code>{0:.2f}</code> frigo al giorno\n\n'.format(f_per_day)
    w, f = db.getNumberOfFrigoPerWeek(conn)

    start_date_week_prec,end_date_week_prec=db.getWeekInfo(conn,actual_w-1)
    durata_giorni_week_prec =  (datetime.strptime(end_date_week_prec, "%d/%m/%y") - datetime.strptime(start_date_week_prec, "%d/%m/%y")).days
    p_week_prec, vinte_week_prec, part_week_prec = db.getPlayerLeaderboard(conn, week=actual_w-1)
    f_per_day_prec = sum(vinte_week_prec) / durata_giorni_week_prec

    differenziale = (f_per_day - f_per_day_prec)
    if differenziale>=0:
        message = message + '📊+<code>{0:.2f}</code> frigo al giorno '.format(differenziale)
    else:
        message = message + '📊<code>{0:.2f}</code> frigo al giorno '.format(differenziale)
    message = message + 'rispetto a settimana <code>{}</code>\n\n'.format(w[-2])
    message = message + '🏃‍♂️‍➡️Maggior contribuente: {} (<code>{}</code>)'.format(players[partecipate.index(max(partecipate))],
                                                                      max(partecipate))

    db.closeDbConn(conn)
    return message


def LadderUnici(db_path):
    c = db.openDbConn(db_path)

    players, unici = db.UnicumLadder(c)
    db.closeDbConn(c)

    message = 'Wins con animali unici (<code>{}</code>)\n'.format(sum(unici))

    rank_width = len(str(len(players)))
    name_width = max((len(p) for p in players), default=0)
    unici_width = max((len(str(u)) for u in unici), default=1)

    for i in range(len(players)):
        message = message + '\n<code>{rank:>{rw}}) {name:<{nw}} {unici:>{uw}}</code>'.format(
            rank=i + 1, name=players[i], unici=unici[i],
            rw=rank_width, nw=name_width, uw=unici_width
        )

    return message


def UniciPlayer(player, db_path):
    c = db.openDbConn(db_path)
    players = db.getAllPlayers(c)
    top_similar = None
    top_similitude = 0
    for m in players:
        seq = difflib.SequenceMatcher(a=player.lower(), b=m.lower())
        if seq.ratio() > 0.7 and seq.ratio() > top_similitude:
            top_similar = m
            top_similitude = seq.ratio()

    if not top_similar:
        db.closeDbConn(c)
        return "non conosco questo {}".format(player)

    animali, wins = db.getUnicumByPlayer(c, top_similar)
    message = 'Unici di {}: <code>{}</code>\n\n'.format(top_similar, len(animali))
    message = message + ', '.join(
        '{} (<code>{}</code>)'.format(animali[i], wins[i]) if wins[i] > 1 else animali[i]
        for i in range(len(animali))
    )

    db.closeDbConn(c)
    return message


def ListOfCessi(db_path):
    c = db.openDbConn(db_path)
    cess = db.getNonVincenti(c)

    message = 'Animali che non hanno mai vinto una frigo\nTotale: <code>{}</code>\n\n'.format(len(cess))
    message = message + ', '.join('{} ({})'.format(mon, tentativi) for mon, tentativi in cess)
    db.closeDbConn(c)
    return message


def WinrateAnimali(db_path):
    c = db.openDbConn(db_path)
    animali, spawns, wins = db.getPokemonWinsPerSpawns(c)
    message = 'Classifica animali per winrate (campione di <code>{}</code> f)\n'.format(sum(wins))

    top10 = list(range(10))
    name_width = max((len(animali[i]) for i in top10), default=0)
    wins_width = max((len(str(wins[i])) for i in top10), default=1)
    spawns_width = max((len(str(spawns[i])) for i in top10), default=1)

    for i in top10:
        wr = wins[i] * 100 / spawns[i]
        message = message + "\n<code>{rank:>2}) {name:<{nw}} {wr:>6.2f}%  [{wins:>{ww}}/{spawns:>{sw}}]</code>".format(
            rank=i + 1, name=animali[i], wr=wr, wins=wins[i], spawns=spawns[i],
            nw=name_width, ww=wins_width, sw=spawns_width
        )
    db.closeDbConn(c)
    message = message + '\n\nN.B. Vari Arceus esclusi dal calcolo'
    return message


def desaparecidos(db_path, limit=10):
    c = db.openDbConn(db_path)
    mons, since = db.getMonsMissingTheLongest(c, limit)
    db.closeDbConn(c)

    message = 'Animali scomparsi da più tempo\n'

    rank_width = len(str(len(mons)))
    name_width = max((len(m) for m in mons), default=0)

    for i in range(len(mons)):
        spawn_message = 'apparso nell\'ultima frigo giocata' if since[i] == 0 else str(since[i])
        message = message + "\n<code>{rank:>{rw}}) {name:<{nw}} : {spawn}</code>".format(
            rank=i + 1, name=mons[i], spawn=spawn_message,
            rw=rank_width, nw=name_width
        )
    return message


def topWincons(db_path, limit=10):
    if limit >= 50:
        return 'Ma quanti cazzo ne vuoi'

    c = db.openDbConn(db_path)
    top = db.getTopWinconedMons(c, limit)
    db.closeDbConn(c)

    message = 'Top {} animali più winconati\n'.format(limit)

    rank_width = len(str(len(top)))
    name_width = max((len(mon) for mon, _, _ in top), default=0)
    cnt_width = max((len(str(wincon_cnt)) for _, wincon_cnt, _ in top), default=1)

    for i, (mon, wincon_cnt, wins) in enumerate(top):
        wr = wins / wincon_cnt * 100
        message = message + "\n<code>{rank:>{rw}}) {name:<{nw}} {cnt:>{cw}} ({wr:>3.0f}%)</code>".format(
            rank=i + 1, name=mon, cnt=wincon_cnt, wr=wr,
            rw=rank_width, nw=name_width, cw=cnt_width
        )
    return message


def calippi(db_path):
    c = db.openDbConn(db_path)
    califfi = db.getCaliffi(c)
    message = "Albo d'oro califfi\n\n"

    rank_width = len(str(len(califfi)))
    name_width = max((len(k[0]) for k in califfi), default=0)
    cnt_width = max((len(str(k[1]['califfi'])) for k in califfi), default=1)

    for i, k in enumerate(califfi):
        mess_cond = "(cond {})".format(k[1]['califfi_cond']) if k[1]['califfi_cond'] > 0 else ''
        message = message + '<code>{rank:>{rw}}) {name:<{nw}} {cnt:>{cw}}</code> {cond}\n'.format(
            rank=i + 1, name=k[0], cnt=k[1]['califfi'], cond=mess_cond,
            rw=rank_width, nw=name_width, cw=cnt_width
        )
    db.closeDbConn(c)
    return message
