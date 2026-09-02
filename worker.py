from datetime import datetime
import difflib
import graph
import statistics
import db
import joks
import logics
import replay_reader


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
    # salvataggio spawns
    for pid in list(players.keys()):
        player = players[pid]['id']
        for an in players[pid]['animali']:
            db.insertSpawn(c, progr, player, an)

    winner_name = db.getPlayerFromSDName(c, winner)
    data = datetime.now().strftime('%d/%m/%y')

    # insert
    db.insertNewFrigo(c, progr, db.getActualWeek(c), data, players['p1']['id'], players['p2']['id'],
                      players['p3']['id'], players['p4']['id'],
                      winner_name, poke_winner, sd_link)

    message = "Inserita Frigo Nr {}\n\nPartecipanti:".format(progr)
    for pid in list(players.keys()):
        # message = message + '\n{} : {}'.format(players[pid]['id'], str(players[pid]['animali']).replace("'", ''))
        message = message + '\n{}'.format(players[pid]['id'])
    message = message + '\n' + joks.messForWinnerOnReg(winner_name, poke_winner)

    return message


def rank_all(db_path):
    c = db.openDbConn(db_path)
    players, wins, partecipate = db.getPlayerLeaderboard(c)
    message = 'Classifica All Time\n\n'
    for i in range(len(players)):
        message = message + "{}) {}  {}\n".format(i + 1, players[i], wins[i])
    db.closeDbConn(c)
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
    for i in range(len(ordinati)):
        message = message + "{}) {:<10} {}  [{}/{}]\n".format(i + 1, ordinati[i]['player'], ordinati[i]['5-1'],
                                                              ordinati[i]['wins'], ordinati[i]['part'])

    message = message + '\nF counter: {}\n'.format(sum(wins))
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
            message = message + "\n[{}] ({} wins): ".format(pos, actual_wins)
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
    message = 'Classifica Settimana {}\n\n'.format(w)
    for i in range(len(players)):
        message = message + "{}) {:<10} {}  [{}]\n".format(i + 1, players[i], vinte[i], partecipate[i])
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


def global_score(path):
    conn = db.openDbConn(path)
    players, vinte, partecipate = db.getPlayerLeaderboard(conn, only_from_reg=True)
    db.closeDbConn(conn)
    scores = []
    message = 'Classifica per score [MarvPondWR]\nPunteggio calcolato su {} f\n'.format(sum(vinte))
    for i in range(len(players)):
        # scores.append(int((vinte[i] / partecipate[i]) * math.log(partecipate[i]) * 1000))
        scores.append(logics.calcMarvWr(partecipate[i], vinte[i], sum(vinte)))
    comb = sorted(zip(players, vinte, partecipate, scores), key=lambda x: x[3], reverse=True)
    players_ord, vinte_ord, partecipate_ord, scores_ord = zip(*comb)
    players_ord = list(players_ord)
    vinte_ord = list(vinte_ord)

    partecipate_ord = list(partecipate_ord)
    scores_ord = list(scores_ord)
    for i in range(len(players)):
        message = message + "\n{}) {}: ".format(i + 1, players_ord[i])
        message = message + "{} ".format(scores_ord[i])
        message = message + "[{}/{}]".format(vinte_ord[i], partecipate_ord[i])

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

    spawn_message='\n\nApparso letteralmente nell\'ultima frigo giocata' if n_last_spawn==0 else '\n\nNon si vede in giro da {} frigo'.format(n_last_spawn)

    spawns_count, wins_count = db.getSpawnsWithWinsOfPokemon(conn, top_similar)
    if len(wins) == 0:
        return 'Sto cesso di {} non ha mai vinto una sebbene sia spawnato in almeno {} frigo'.format(top_similar,
                                                                                                     spawns_count)+spawn_message

    message = "Vittorie di {}: {}\n\n".format(top_similar, sum(wins))
    for w in range(len(winners)):
        message = message + "{} con {}\n".format(wins[w], winners[w])

    message = message + '\nSu {} spawn registrati ha vinto {} volte'.format(spawns_count, wins_count)
    message =message +spawn_message
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
    winsWhenPlayed = len([j for j in winners_whenPlayed if j == top_similar])
    winrate_perc = (winsWhenPlayed / len(winners_whenPlayed)) * 100 if len(winners_whenPlayed) > 0 else 0
    marvWr = logics.calcMarvWr(len(winners_whenPlayed), winsWhenPlayed, db.getNumberOfFrigos(conn, from_reg=True))
    animali_unici, wins_unici = db.getUnicumByPlayer(conn, top_similar)

    message = top_similar + '\n\n'
    message = message + 'Frigo vinte overall {}\n'.format(num_wins)
    message = message + 'Winrate {0:.2f}% '.format(winrate_perc)

    message = message + '({} vinte su {} giocate su {} registrate)\n'.format(
        winsWhenPlayed, len(winners_whenPlayed), db.getNumFrigoWithPlayersSpecified(conn)
    )

    message = message + 'MarvWr Score: {} '.format(marvWr)

    message = message + '\n\nDistinto al {0:.2f}%'.format(num_distinct_pk * 100 / num_wins)
    message = message + ' con {} distinti animali\n'.format(num_distinct_pk)
    message = message +'Animali Unici: {}\n'.format( len(animali_unici))
    pk, cnts = db.getMostPokeWinnerByPlayer(conn, top_similar)
    db.closeDbConn(conn)

    cnt_i = cnts[0]
    message = message + "Amici Vincenti:\n\t\t[{}]: ".format(cnt_i)

    for i in range(len(pk)):
        if i < 10:
            if cnts[i] < cnt_i:
                cnt_i = cnts[i]
                message = message[:-1]
                message = message + "\n\t\t[{}]: ".format(cnt_i)
                message = message + "{}, ".format(pk[i])
            else:
                message = message + "{}, ".format(pk[i])

    if 'Amici Vincenti' in message:
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
    secchezza = db.getNumberPartecipiedSinceLastWin(conn, top_similar)
    last = db.getLastPartecipiedFrigo(conn, top_similar)
    if not last:
        return 'non gioca da indefinite frigo'
    else:
        notgame = db.getNumberOfFrigos(conn) - db.getLastPartecipiedFrigo(conn, top_similar)
    if secchezza == 0:
        message = "il porco ha vinto l'ultima frigo che ha giocato\n"
    else:
        message = '{} non vince da {} frigo giocate\n'.format(top_similar, secchezza)
    message = message + 'ultima frigo giocata {} frigo fa\n'.format(notgame)

    w = db.getActualWeek(conn)
    print(w)
    num_in_week = db.getPartecipiedAtWeek(conn, w, top_similar)
    message = message + 'Frigo giocate in settimana: {}'.format(num_in_week)
    db.closeDbConn(conn)
    return message


def tagger(db_path):
    conn = db.openDbConn(db_path)
    tags = db.getTagLastPartecipiers(conn)
    db.closeDbConn(conn)
    message = ''
    for t in tags:
        message = message + '{} '.format(t)
    return message + 'frigo'


def frigoFrequency(db_path):
    conn = db.openDbConn(db_path)
    w, f = db.getNumberOfFrigoPerWeek(conn)
    db.closeDbConn(conn)
    save_path = r'C:\Users\mgent\Desktop\SVIL PERSONALE\FrigoBot\frequenza.png'
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
    message = '🔴Chiusa settimana {}\n\n'.format(actual_w)
    message = message + '👳Califfa {} con {} vittorie\n\n'.format(calippo, vinte[0])
    message = message + '🐖Porco di settimana: {} ({} su {})\n'.format(most_pig, vinte[players.index(most_pig)],
                                                                      partecipate[players.index(most_pig)])
    message = message + '🤏Il più rachitico: {} ({} su {})\n\n'.format(most_thin, vinte[players.index(most_thin)],
                                                                      partecipate[players.index(most_thin)])
    message = message + '😆E in tutto ciò chi ride?\n'
    message = message + '¬ Di certo non {} ({} MarvWr points)\n'.format(who_not_smile, min_increment)
    message = message + '¬ Tendenzialmente ride {} (+{} MarvWr points)\n\n'.format(who_smile, max_increment)

    if len(cessi) > 0:
        message = message + '🔞Sono stati sverginati {} cessi, principalmente da {}\n\n'.format(
            len(list(set(cessi))), joks.str_sverg(sverginatori))
    else:
        message = message + '🔞Nessun cesso è stato sverginato\n\n'

    message = message + '🧊La settimana è durata {} giorni e si è frigato per un ammontare complessivo di {} frigo, '.format(durata_giorni,sum(vinte))
    f_per_day=sum(vinte)/durata_giorni
    message = message + 'per una media {} '.format(joks.commentoMedia(f_per_day))
    message = message + 'di {0:.2f} frigo al giorno\n\n'.format(f_per_day)
    w, f = db.getNumberOfFrigoPerWeek(conn)

    start_date_week_prec,end_date_week_prec=db.getWeekInfo(conn,actual_w-1)
    durata_giorni_week_prec =  (datetime.strptime(end_date_week_prec, "%d/%m/%y") - datetime.strptime(start_date_week_prec, "%d/%m/%y")).days
    p_week_prec, vinte_week_prec, part_week_prec = db.getPlayerLeaderboard(conn, week=actual_w-1)
    f_per_day_prec = sum(vinte_week_prec) / durata_giorni_week_prec

    differenziale = (f_per_day - f_per_day_prec)
    if differenziale>=0:
        message = message + '📊+{0:.2f} frigo al giorno '.format(differenziale)
    else:
        message = message + '📊{0:.2f} frigo al giorno '.format(differenziale)
    message = message + 'rispetto a settimana {}\n\n'.format(w[-2])
    message = message + '🏃‍♂️‍➡️Maggior contribuente: {} ({})'.format(players[partecipate.index(max(partecipate))],
                                                                      max(partecipate))

    db.closeDbConn(conn)
    return message


def LadderUnici(db_path):
    c = db.openDbConn(db_path)

    players, unici = db.UnicumLadder(c)
    message = 'Wins con animali unici ({})\n'.format(sum(unici))
    for i in range(len(players)):
        message = message + '\n{}) {} {}'.format(i + 1, players[i], unici[i])

    db.closeDbConn(c)
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
    message = 'Unici di {}: {}\n\n'.format(top_similar, len(animali))
    for i in range(len(animali)):
        add_on = '{} ({}), '.format(animali[i], wins[i]) if wins[i] > 1 else '{}, '.format(animali[i])
        message = message + add_on

    db.closeDbConn(c)
    return message


def ListOfCessi(db_path):
    c = db.openDbConn(db_path)
    cess = db.getNonVincenti(c)

    #manual fix
    #cess.remove('Magearna-Original-Mega')
    #cess.remove('Vivillon-Jungle')
    #cess.remove('Vivillon-Marine')
    #cess.remove('Morpeko-Hangry')
    #end manual fix

    message = 'Animali che non hanno mai vinto una frigo\nTotale: {}\n\n'.format(len(cess))
    message = message + str(cess).replace("'", "").replace('[', '').replace(']', '')
    db.closeDbConn(c)
    return message


def WinrateAnimali(db_path):
    c = db.openDbConn(db_path)
    animali, spawns, wins = db.getPokemonWinsPerSpawns(c)
    message = 'Classifica animali per winrate (campione di {} f)\n'.format(sum(wins))

    for i in range(10):
        message = message + "\n{}) {} : ".format(i + 1, animali[i])
        message = message + '{0:.2f}% '.format(wins[i] * 100 / spawns[i])
        message = message + ' [{}/{}]'.format(wins[i], spawns[i])
    db.closeDbConn(c)
    message = message + '\n\nN.B. Vari Arceus esclusi dal calcolo'
    return message


def calippi(db_path):
    c = db.openDbConn(db_path)
    califfi = db.getCaliffi(c)
    message = "Albo d'oro califfi\n\n"

    pos = 1
    for k in califfi:
        mess_cond = "(cond {})".format(k[1]['califfi_cond']) if k[1]['califfi_cond'] > 0 else ''
        message = message + '{}) {} {} {}\n'.format(pos, k[0], k[1]['califfi'], mess_cond)
        pos += 1
    db.closeDbConn(c)
    return message
