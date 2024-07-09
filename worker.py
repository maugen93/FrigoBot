import requests
import json
from datetime import datetime
import difflib

import db


def elab_sd_replay(link_replay):
    data = json.loads(
        requests.get(link_replay + ".json").content)

    pokewinner = None
    players = data['players']
    players_ids = []
    players_log = []
    log_rows = data['log'].split('\n')
    for i in range(len(log_rows)):
        log = log_rows[i]
        if log.startswith('|player|'):
            id = log.split('|')[2]
            if id not in players_ids:
                players_ids.append(id)
                players_log.append(log.split('|')[3])
        if log.startswith('|win|'):
            winner = log.split('|')[2]

    winner_id = players_ids[players_log.index(winner)]

    # scorro al contrario per trovare il pokewinner
    for i in range(len(log_rows) - 1, 0, -1):
        log = log_rows[i]
        if winner_id in log and ": " in log:
            pokewinner = log.split(': ')[1].split('|')[0]
            break

    return players, winner, pokewinner


def openNewWeek(db_path, tg_id):
    pass


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

    players, winner, poke_winner = elab_sd_replay(sd_link)
    players_names = []

    for p in players:
        pn = db.getPlayerFromSDName(c, p)
        if not pn:
            c.close()
            return 'Collo {} non presente nel DB'.format(p)
        players_names.append(pn)
    winner_name = db.getPlayerFromSDName(c, winner)
    if not winner_name:
        c.close()
        return 'Collo {} non presente nel DB'.format(winner)

    data = datetime.now().strftime('%d/%m/%y')
    progr = db.getNumberOfFrigos(c) + 1

    # insert
    db.insertNewFrigo(c, progr, db.getActualWeek(c), data, players_names[0], players_names[1], players_names[2],
                      players_names[3], winner_name, poke_winner, sd_link)

    return "Inserita Frigo Nr {}\nPartecipanti: {}, {}, {}, {}\nVincitore {} con {}".format(
        progr, players_names[0], players_names[1], players_names[2],
        players_names[3], winner_name, poke_winner
    )


def rank_all(db_path):
    c = db.openDbConn(db_path)
    players, wins = db.getLeaderboardAll(c)
    message = 'Classifica All Time\n\n'
    for i in range(len(players)):
        message = message + "{}) {}  {}\n".format(i + 1, players[i], wins[i])
    db.closeDbConn(c)
    return message


def rank_season(db_path):
    c = db.openDbConn(db_path)
    # players, wins = db.getLeaderboardAll(c)
    players, wins = db.getLeaderboardSummer(c)
    message = 'Classifica Summer Siso\n\n'
    for i in range(len(players)):
        message = message + "{}) {}  {}\n".format(i + 1, players[i], wins[i])
    message = message + "\n *from 21/06 to 23/09*"
    db.closeDbConn(c)
    return message


def rank_pkmn(db_path, limit=5):
    c = db.openDbConn(db_path)
    pk, wins = db.getLeaderboardPkmn(c)
    message = 'Classifica Animali\n\n-'

    actual_wins=wins[0]+1
    pos=0
    for i in range(len(pk)):
        if wins[i]<actual_wins:
            pos=pos+1
            actual_wins=wins[i]
            if pos>limit:
                break
            message = message[:-2]
            message = message + "\n[{}] ({} wins): ".format(pos,actual_wins)
        message=message+pk[i]
        message=message+', '
        #if i < limit:
        #    message = message + "{}) {}  {}\n".format(i + 1, pk[i], wins[i])
    db.closeDbConn(c)
    message = message[:-2]
    return message


def rank_week(db_path):
    c = db.openDbConn(db_path)
    w = db.getActualWeek(c)

    p, wins = db.getLeaderboardWeek(c, w)
    message = 'Classifica Settimana {}\n\n'.format(w)
    for i in range(len(p)):
        message = message + "{}) {}  {}\n".format(i + 1, p[i], wins[i])
    db.closeDbConn(c)
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


def calippi(db_path):
    conn = db.openDbConn(db_path)
    weeks, winners, wins = db.getCalippati(conn)
    calippame = {}
    calippame_cond = {}
    for i in range(len(weeks)):
        w_split = winners[i].split(',')
        for w in w_split:
            w_r = w.replace(' ', '')
            if w_r in calippame:
                calippame[w_r] += 1

            else:
                calippame[w_r] = 1
    for i in range(len(weeks)):
        if ',' in winners[i]:
            w_split = winners[i].split(',')
            for w in w_split:
                w_r = w.replace(' ', '')
                if w_r in calippame_cond:
                    calippame_cond[w_r] += 1

                else:
                    calippame_cond[w_r] = 1
    calippame = dict(sorted(calippame.items(), key=lambda item: item[1], reverse=True))
    message = 'Calippi overall\n\n'
    for c in list(calippame.keys()):
        try:
            cond = ' di cui {} condiriso'.format(calippame_cond[c])
        except KeyError:
            cond = ''
        message = message + c + ': {}{}\n'.format(calippame[c], cond)
    db.closeDbConn(conn)
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
        return "non mi risulta che qualcosa chiamato {} abbia mai vinto una frigo".format(animale)

    winners, wins = db.getWinsPkmn(conn, top_similar)
    message = "Vittorie di {}: {}\n\n".format(top_similar, sum(wins))
    for w in range(len(winners)):
        message = message + "{} con {}\n".format(wins[w], winners[w])
    db.closeDbConn(conn)
    return message


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

    num_wins, winners_whenPlayed = db.getPlayerInfo(conn, top_similar)
    num_distinct_pk = db.getDistinctPokeByPlayer(conn, top_similar)

    message = top_similar + '\n\n'
    message = message + 'Frigo vinte overall {}\n'.format(num_wins)
    message = message + 'Distinto al {0:.2f}%'.format(num_distinct_pk*100/num_wins)
    message = message + ' con {} distinti animali\n'.format(num_distinct_pk)

    winsWhenPlayed = len([j for j in winners_whenPlayed if j == top_similar])
    perc = (winsWhenPlayed / len(winners_whenPlayed)) * 100 if len(winners_whenPlayed) > 0 else 0


    message = message + 'Winrate {0:.2f}% '.format(perc)

    message=message+ '({} vinte su {} giocate su {} registrate)\n\n'.format(
        winsWhenPlayed, len(winners_whenPlayed), db.getNumFrigoWithPlayersSpecified(conn)
    )
    pk, cnts = db.getMostPokeWinnerByPlayer(conn, top_similar)
    db.closeDbConn(conn)
    message = message + "Top animali:  "
    for i in range(len(pk)):
        if i < 10:
            message = message + "{} ({}), ".format(pk[i], cnts[i])

    if 'Top animali' in message:
        message = message[:-2]
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
    secchezza=db.getNumberPartecipiedSinceLastWin(conn,top_similar)
    last=db.getLastPartecipiedFrigo(conn,top_similar)
    if not last:
        return 'non gioca da indefinite frigo'
    else:
        notgame=db.getNumberOfFrigos(conn)-db.getLastPartecipiedFrigo(conn,top_similar)
    if secchezza==0:
        message= "il porco ha vinto l'ultima frigo che ha giocato\n"
    else:
        message='{} non vince da {} frigo giocate\n'.format(top_similar,secchezza)
    message=message+'ultima frigo giocata {} frigo fa'.format(notgame)

    return message