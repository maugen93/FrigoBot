import sqlite3
import polars


def openDbConn(dbpath):
    conn = sqlite3.connect(dbpath)
    ensureStatsCacheSchema(conn)
    return conn


def closeDbConn(conn):
    conn.close()


def ensureStatsCacheSchema(conn):
    '''Crea (se assenti) le tabelle di cache usate per svergiconverters/svergitryers/
    swingscore, cosi' non serve una migrazione separata su ogni frigo.db esistente.'''
    conn.execute('''CREATE TABLE IF NOT EXISTS mon_first_win (
        mon TEXT PRIMARY KEY,
        first_win_progr INTEGER NOT NULL
    )''')
    conn.execute('''CREATE TABLE IF NOT EXISTS player_cesso_stats (
        player TEXT PRIMARY KEY,
        tentativi INTEGER NOT NULL DEFAULT 0,
        vinte INTEGER NOT NULL DEFAULT 0,
        cessi_spawnati INTEGER NOT NULL DEFAULT 0
    )''')
    conn.execute('''CREATE TABLE IF NOT EXISTS player_weekly_stats (
        player TEXT NOT NULL,
        week INTEGER NOT NULL,
        games INTEGER NOT NULL DEFAULT 0,
        wins INTEGER NOT NULL DEFAULT 0,
        PRIMARY KEY (player, week)
    )''')
    conn.commit()


def updateStatsCacheForFrigo(conn, progr, week, participants, spawns, winner, pokewinner):
    '''Aggiorna incrementalmente mon_first_win/player_cesso_stats/player_weekly_stats
    per una singola frigo appena inserita, cosi' svergiconverters/svergitryers/swingscore
    non devono piu' ricalcolarsi rileggendo tutta la storia a ogni chiamata.

    `participants` sono i 4 player1..player4 della frigo (sempre presenti, anche per le
    frigo storiche caricate da CSV senza righe in spawns - usati per player_weekly_stats).
    `spawns` e' una lista di tuple (player, mon, winconato) - la stessa informazione
    passata a insertSpawn per ogni animale della frigo (assente per quelle frigo storiche,
    quindi non contribuiscono a player_cesso_stats, come nella query originale che le
    joinava tramite spawns). Va chiamata una volta per frigo, in ordine di progr crescente
    (rebuildStatsCache si appoggia alla stessa assunzione).
    '''
    cur = conn.cursor()

    cessi_players = set()
    for player, mon, winconato in spawns:
        cur.execute("SELECT 1 FROM mon_first_win WHERE mon=?", (mon,))
        is_cesso = cur.fetchone() is None
        if is_cesso:
            cessi_players.add(player)

        if winconato and is_cesso:
            vinto = 1 if (winner == player and pokewinner == mon) else 0
            cur.execute('''
                INSERT INTO player_cesso_stats (player, tentativi, vinte, cessi_spawnati)
                VALUES (?, 1, ?, 0)
                ON CONFLICT(player) DO UPDATE SET
                    tentativi = tentativi + 1,
                    vinte = vinte + excluded.vinte
            ''', (player, vinto))

    for player in cessi_players:
        cur.execute('''
            INSERT INTO player_cesso_stats (player, tentativi, vinte, cessi_spawnati)
            VALUES (?, 0, 0, 1)
            ON CONFLICT(player) DO UPDATE SET
                cessi_spawnati = cessi_spawnati + 1
        ''', (player,))

    cur.execute("SELECT 1 FROM mon_first_win WHERE mon=?", (pokewinner,))
    if cur.fetchone() is None:
        cur.execute("INSERT INTO mon_first_win (mon, first_win_progr) VALUES (?, ?)",
                    (pokewinner, progr))

    for player in set(participants):
        vinta = 1 if player == winner else 0
        cur.execute('''
            INSERT INTO player_weekly_stats (player, week, games, wins)
            VALUES (?, ?, 1, ?)
            ON CONFLICT(player, week) DO UPDATE SET
                games = games + 1,
                wins = wins + excluded.wins
        ''', (player, week, vinta))

    conn.commit()


def rebuildStatsCache(conn):
    '''Ricostruisce da zero mon_first_win/player_cesso_stats/player_weekly_stats
    leggendo frigos/spawns in ordine di progr. Da rilanciare dopo una migrazione
    iniziale o dopo un backfill che cambia winconato/pokewinner su frigo storiche
    (es. backfill_winconato.py), altrimenti la cache incrementale andrebbe fuori
    sync con quanto effettivamente successo in quelle frigo.'''
    cur = conn.cursor()
    cur.execute("DELETE FROM mon_first_win")
    cur.execute("DELETE FROM player_cesso_stats")
    cur.execute("DELETE FROM player_weekly_stats")
    conn.commit()

    cur.execute('''SELECT progr, week, player1, player2, player3, player4, winner, pokewinner
        FROM frigos ORDER BY progr''')
    frigo_rows = cur.fetchall()

    for progr, week, p1, p2, p3, p4, winner, pokewinner in frigo_rows:
        participants = [p for p in (p1, p2, p3, p4) if p is not None]
        cur.execute("SELECT player, spawn, winconato FROM spawns WHERE frigo=?", (progr,))
        spawns = [(r[0], r[1], bool(r[2])) for r in cur.fetchall()]
        updateStatsCacheForFrigo(conn, progr, week, participants, spawns, winner, pokewinner)


def deleteFrigo(conn, progr):
    '''Rimuove una frigo (e i suoi spawns) e ricostruisce la stats cache da zero,
    cosi' mon_first_win/player_cesso_stats/player_weekly_stats tornano coerenti
    senza dover invertire a mano gli incrementi fatti da updateStatsCacheForFrigo.'''
    conn.execute("DELETE FROM spawns WHERE frigo=?", (progr,))
    conn.execute("DELETE FROM frigos WHERE progr=?", (progr,))
    conn.commit()
    rebuildStatsCache(conn)


def insertNewFrigo(conn, progr, week, data, p1, p2, p3, p4, w, pw, sd_link):
    conn.execute("INSERT INTO frigos (progr, week,data,player1,player2,player3,player4,winner,pokewinner,replay_link) "
                 "VALUES (?,?,?,?,?,?,?,?,?,?)",
                 (progr, week, data, p1, p2, p3, p4,
                  w, pw, sd_link))
    conn.commit()


def insertSpawn(conn, f_nr, player, spawn, winconato=False):
    conn.execute("INSERT INTO spawns (frigo,player,spawn,winconato) VALUES (?,?,?,?)",
                 (f_nr, player, spawn, int(winconato)))
    conn.commit()


def setWinconato(conn, f_nr, player, spawn):
    cur = conn.execute("UPDATE spawns SET winconato=1 WHERE frigo=? AND player=? AND spawn=?",
                        (f_nr, player, spawn))
    conn.commit()
    return cur.rowcount


def getFrigosByMon(conn, mon):
    '''Trova le frigo (progr, replay_link) in cui `mon` compare come spawn di
    qualche giocatore o come pokewinner, per poterle rileggere e correggere
    (es. dopo una fix a replay_reader.get_clean_mon_name). Solo le frigo con
    un replay_link, ordinate per progr.'''
    cur = conn.cursor()
    cur.execute('''SELECT DISTINCT f.progr, f.replay_link
        FROM frigos f
        WHERE f.replay_link IS NOT NULL
        AND (f.pokewinner=? OR f.progr IN (SELECT frigo FROM spawns WHERE spawn=?))
        ORDER BY f.progr''', (mon, mon))
    return cur.fetchall()


def getSpawnsForFrigoPlayer(conn, frigo, player):
    cur = conn.cursor()
    cur.execute("SELECT spawn, winconato FROM spawns WHERE frigo=? AND player=?", (frigo, player))
    return cur.fetchall()


def deleteSpawn(conn, frigo, player, spawn):
    cur = conn.execute("DELETE FROM spawns WHERE frigo=? AND player=? AND spawn=?",
                        (frigo, player, spawn))
    conn.commit()
    return cur.rowcount


def updatePokewinner(conn, frigo, new_pokewinner):
    cur = conn.execute("UPDATE frigos SET pokewinner=? WHERE progr=?", (new_pokewinner, frigo))
    conn.commit()
    return cur.rowcount


def getFrigosToBackfillWinconato(conn, frigo_nrs=None):
    cur = conn.cursor()
    if frigo_nrs:
        placeholders = ','.join('?' * len(frigo_nrs))
        cur.execute(
            "SELECT progr, replay_link FROM frigos "
            "WHERE progr IN ({}) AND replay_link IS NOT NULL ORDER BY progr".format(placeholders),
            frigo_nrs
        )
    else:
        cur.execute(
            "SELECT progr, replay_link FROM frigos "
            "WHERE replay_link IS NOT NULL "
            "AND progr NOT IN (SELECT DISTINCT frigo FROM spawns WHERE winconato = 1) "
            "ORDER BY progr"
        )
    result = cur.fetchall()
    cur.close()
    return result


def isSDReplayAlreadyLoaded(conn, sd_link):
    cur = conn.cursor()
    cur.execute("SELECT * FROM frigos WHERE replay_link=?", (sd_link,))
    result = cur.fetchone()
    exists = False
    if result:
        exists = True
    cur.close()
    return exists


def getFrigoInfoFromNumber(conn, frigo_nr):
    cur = conn.cursor()
    cur.execute("SELECT * FROM frigos WHERE progr=?", (frigo_nr,))
    result = cur.fetchone()
    if result:
        frigo = {'progr': frigo_nr, 'week': result[1], 'date': result[2],
                 'p1': result[3], 'p2': result[4], 'p3': result[5], 'p4': result[6],
                 'winner': result[7], 'pokewinner': result[8], 'sd_replay': result[9]
                 }
        return frigo
    return None


def getPlayerFromSDName(conn, sd_name=""):
    sd_name2 = sd_name.replace(' ', '').lower()
    cur = conn.cursor()
    cur.execute("select frigante from colli where sd_alt=?", (sd_name2,))
    result = cur.fetchall()

    player = None
    for row in result:
        player = row[0]
        break
    cur.close()
    return player


def getNumberOfFrigos(conn, from_reg=False):
    if from_reg:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM frigos WHERE player1 is not null")
        result = cur.fetchone()
        if result[0]:
            return result[0]
        else:
            return 0
    cur = conn.cursor()
    cur.execute("SELECT max(progr) FROM frigos")
    result = cur.fetchone()
    if result[0]:
        return result[0]
    else:
        return 0


def getActualWeek(conn):
    cur = conn.cursor()
    cur.execute("SELECT week from weeks where enddate is null")
    result = cur.fetchone()
    return result[0]


def load_old_frigo_from_csv(db_path, csv_path):
    frigodata = polars.read_csv(csv_path)
    progrs = list(frigodata['Frigo'])
    weeks = list(frigodata['Week'])
    datas = list(frigodata['Data'])
    p1s = list(frigodata['P1'])
    p2s = list(frigodata['P2'])
    p3s = list(frigodata['P3'])
    p4s = list(frigodata['P4'])
    ws = list(frigodata['W'])
    pws = list(frigodata['PW'])

    conn = openDbConn(db_path)
    for i in range(len(progrs)):
        print("insert frigo nr {}".format(progrs[i]))
        insertNewFrigo(conn, progrs[i], weeks[i], datas[i], p1s[i], p2s[i], p3s[i], p4s[i], ws[i], pws[i], None)

    closeDbConn(conn)


def getPlayerLeaderboard(conn, from_frigo=None, to_frigo=None, week=None, only_from_reg=False):
    '''Restituisce 3 vettori di uguale dimensione. Per ogni posto i il vettore
    giocatori contiene il giocatore alla posizione i,vinte il numero di vittorie,
    partecipate il numero di partecipate (ove ha senso).
    Con i parametri di default si restituisce la classifica globale.
    From_frigo e to_frigo servono per un dato intervallo, week solo di una data week.
    Se only_from_reg è True da la classifica globale solo da quando si restituiscono i
    players'''
    giocatori = []
    vinte = []
    partecipate = []

    cur = conn.cursor()

    week_query_part = 'and week=?' if week else ''
    from_frigo_query_part = 'and progr>=?' if from_frigo else ''
    to_frigo_query_part = 'and progr<=?' if to_frigo else ''
    from_reg_query_part = 'and player1 is not null' if only_from_reg else ''

    query = '''WITH PlayerStats AS (
    -- Crea un elenco unico di tutti i giocatori con il conteggio delle partecipazioni
    SELECT player AS nome_giocatore, 
           COUNT(progr) AS partecipate
    FROM (
        SELECT player1 AS player, progr FROM frigos WHERE player1 IS NOT NULL {} {} {}
        UNION ALL
        SELECT player2 AS player, progr FROM frigos WHERE player2 IS NOT NULL {} {} {}
        UNION ALL
        SELECT player3 AS player, progr FROM frigos WHERE player3 IS NOT NULL {} {} {}
        UNION ALL
        SELECT player4 AS player, progr FROM frigos WHERE player4 IS NOT NULL {} {} {}
    ) AS AllPlayers
    GROUP BY player
    ),
    Vittorie AS (
    -- Conteggio delle vittorie per ciascun giocatore
    SELECT winner AS nome_giocatore, 
           COUNT(*) AS vinte
    FROM frigos
    WHERE winner IS NOT NULL {} {} {} {}
    GROUP BY winner
    )

    -- Ora uniamo le statistiche e ordiniamo per vinte e partecipate
    SELECT ps.nome_giocatore, 
       COALESCE(v.vinte, 0) AS vinte, 
       ps.partecipate
    FROM PlayerStats ps
    LEFT JOIN Vittorie v ON ps.nome_giocatore = v.nome_giocatore
    ORDER BY vinte DESC, partecipate ASC;'''.format(week_query_part, from_frigo_query_part, to_frigo_query_part,
                                                    week_query_part, from_frigo_query_part, to_frigo_query_part,
                                                    week_query_part, from_frigo_query_part, to_frigo_query_part,
                                                    week_query_part, from_frigo_query_part, to_frigo_query_part,
                                                    from_reg_query_part, week_query_part, from_frigo_query_part,
                                                    to_frigo_query_part
                                                    )
    parameters = ()
    if week_query_part:
        parameters = (week, week, week, week, week,)
    if from_frigo and not to_frigo:
        parameters = (from_frigo, from_frigo, from_frigo, from_frigo, from_frigo,)
    if to_frigo and not from_frigo:
        parameters = (to_frigo, to_frigo, to_frigo, to_frigo, to_frigo,)
    if to_frigo and from_frigo:
        parameters = (
            from_frigo, to_frigo, from_frigo, to_frigo, from_frigo, to_frigo, from_frigo, to_frigo, from_frigo,
            to_frigo,)
    if only_from_reg:
        parameters = ()

    cur.execute(query, parameters)

    result = cur.fetchall()
    for r in result:
        giocatori.append(r[0])
        vinte.append(r[1])
        partecipate.append(r[2])
    return giocatori, vinte, partecipate


def getLeaderboardPkmn(conn):
    p = []
    w = []
    cur = conn.cursor()
    cur.execute("select pokewinner,count(*) as c from frigos group by pokewinner order by c desc")
    result = cur.fetchall()
    for r in result:
        p.append(r[0])
        w.append(r[1])
    return p, w


def getPartecipiedAtWeek(conn, week, player):
    cur = conn.cursor()
    cur.execute("select count(*) from frigos where week= ? and (player1=? or player2=? or player3=? or player4=?)",
                (week,
                 player, player, player, player,))

    result = cur.fetchone()

    if result[0]:
        return result[0]
    else:
        return 0


def run_custom_query(conn, query):
    conn.execute(query)
    conn.commit()


def getCalippati_old(conn):
    weeks = []
    winners = []
    num_wins = []
    cur = conn.cursor()
    query = '''
        WITH conteggio_vittorie AS (
        SELECT week, winner, COUNT(*) AS num_vittorie
        FROM frigos
        GROUP BY week, winner
        ),
         massimo_vittorie AS (
        SELECT week, MAX(num_vittorie) AS max_vittorie
        FROM conteggio_vittorie
        GROUP BY week
        )
    SELECT cv.week, GROUP_CONCAT(cv.winner, ', ') AS vincitori,cv.num_vittorie
    FROM conteggio_vittorie cv
    JOIN massimo_vittorie mv
    ON cv.week = mv.week AND cv.num_vittorie = mv.max_vittorie
    where cv.week <>(select week from weeks where enddate is null)
    GROUP BY cv.week
    ORDER BY cv.week;
        '''
    cur.execute(query)
    result = cur.fetchall()
    for r in result:
        weeks.append(r[0])
        winners.append(r[1])
        num_wins.append(r[2])
    return weeks, winners, num_wins


def getAllMons(conn):
    p = []
    cur = conn.cursor()
    cur.execute("select distinct spawn from spawns")
    result = cur.fetchall()
    for r in result:
        p.append(r[0])
    return p


def getWinsPkmn(conn, pk):
    winners = []
    wins = []
    cur = conn.cursor()
    query = '''
            select * from (select pokewinner,winner, count(*) as c from frigos
            group by pokewinner,winner)t
            where pokewinner=?
            '''
    cur.execute(query, (pk,))
    result = cur.fetchall()
    if not result:
        return [], []
    for r in result:
        winners.append(r[1])
        wins.append(r[2])
    return winners, wins


def getAllPlayers(conn):
    p = []
    cur = conn.cursor()
    cur.execute("select distinct frigante from colli")
    result = cur.fetchall()
    for r in result:
        p.append(r[0])
    return p


def getNumFrigoWithPlayersSpecified(conn):
    cur = conn.cursor()
    cur.execute("select count(*) ar from frigos where player1 is not null")
    result = cur.fetchone()
    return result[0]


def getPlayerInfo(conn, player):
    cur = conn.cursor()
    cur.execute("select count(*) ar from frigos where winner=?", (player,))
    result = cur.fetchone()
    num_wins = result[0]
    winners_whenPlayed = []
    query = '''select winner from frigos where player1=?
    or player2=? or player3=? or player4=?'''
    result = cur.execute(query, (player, player, player, player,))
    for r in result:
        winners_whenPlayed.append(r[0])
    return num_wins, winners_whenPlayed


def getWeeklyGamesAndWinsByPlayer(conn, player):
    cur = conn.cursor()
    result = cur.execute('''SELECT games, wins FROM player_weekly_stats
        WHERE player=? ORDER BY week ASC''', (player,))
    games = []
    wins = []
    for r in result:
        games.append(r[0])
        wins.append(r[1])
    return games, wins


def getMostPokeWinnerByPlayer(conn, player):
    pks = []
    cnts = []
    cur = conn.cursor()
    query = '''select pokewinner,count(*) c
    from frigos
    where winner=?
    group by pokewinner
    order by c desc'''
    result = cur.execute(query, (player,))
    for r in result:
        pks.append(r[0])
        cnts.append(r[1])
    return pks, cnts


def getDistinctPokeByPlayer(conn, player):
    cur = conn.cursor()
    query = '''select count(distinct pokewinner) 
        from frigos where winner=?'''
    result = cur.execute(query, (player,))
    for r in result:
        num = r[0]
    return num


def getLastWinnedFrigo(conn, player):
    cur = conn.cursor()
    query = '''select max(progr) 
        from frigos where winner=?'''
    result = cur.execute(query, (player,))
    for r in result:
        num = r[0]
    return num


def getLastPartecipiedFrigo(conn, player):
    cur = conn.cursor()
    query = '''select max(progr) from frigos where player1=?
        or player2=? or player3=? or player4=?'''
    result = cur.execute(query, (player, player, player, player,))

    for r in result:
        if not r:
            return None
        num = r[0]
    return num


def getNumberPartecipiedSinceLastWin(conn, player):
    cur = conn.cursor()
    query = '''select count(*) from frigos where (player1=? or player2=? or player3 = ? or player4 = ?) and progr >(
            select max(progr) 
                from frigos where winner=?)'''

    result = cur.execute(query, (player, player, player, player, player))

    for r in result:
        if not r:
            return None
        num = r[0]
    return num


def getTagLastPartecipiers(conn):
    cur = conn.cursor()
    p = []
    query = '''select distinct c.tg_tag from (
        select  distinct player1 as p from frigos where progr>((select max(progr) from frigos)-10)
        union
        select  distinct player2 as p from frigos where progr>((select max(progr) from frigos)-10)
        union
        select  distinct player3 as p from frigos where progr>((select max(progr) from frigos)-10)
        union
        select  distinct player4 as p from frigos where progr>((select max(progr) from frigos)-10)
        )t
        inner join colli c
        on t.p=c.frigante'''
    cur.execute(query)
    result = cur.fetchall()
    for r in result:
        p.append(r[0])
    return p


def getNumberOfFrigoPerWeek(conn):
    cur = conn.cursor()
    f = []
    w = []

    query = '''select week,count(*)as c from frigos group by week'''
    cur.execute(query)
    result = cur.fetchall()
    for r in result:
        w.append(r[0])
        f.append(r[1])
    return w, f


def getRatingPlayer(conn, player):
    cur = conn.cursor()
    rating = None
    rd = None

    query = '''select rating,rd from glicko where player=?'''
    result = cur.execute(query, (player,))
    for r in result:
        rating = r[0]
        rd = r[1]
    return rating, rd


def setRatingPlayer(conn, player, new_rating, new_pd):
    cur = conn.cursor()
    query = '''update glicko set rating=?,rd=? where player=?'''
    cur.execute(query, (new_rating, new_pd, player,))
    conn.commit()


def getFrigoFromTo(conn, from_f, to_f):
    p1 = []
    p2 = []
    p3 = []
    p4 = []
    w = []
    pw = []
    progr = []
    replay_link = []
    query = '''select player1,player2,player3,player4,winner,pokewinner,progr,replay_link from frigos where progr>=? and progr<=? order by progr'''

    cur = conn.cursor()
    cur.execute(query, (from_f, to_f,))
    result = cur.fetchall()
    for r in result:
        p1.append(r[0])
        p2.append(r[1])
        p3.append(r[2])
        p4.append(r[3])
        w.append(r[4])
        pw.append(r[5])
        progr.append(r[6])
        replay_link.append(r[7])
    return p1, p2, p3, p4, w, pw, progr, replay_link


def getTrueskillRatingPlayer(conn, player):
    cur = conn.cursor()
    mu = None
    sigma = None

    query = '''select mu,sigma from trueskill where frigante=?'''
    result = cur.execute(query, (player,))
    for r in result:
        mu = r[0]
        sigma = r[1]
    return mu, sigma


def setTrueskillRatingPlayer(conn, player, new_mu, new_sigma):
    cur = conn.cursor()
    query = '''update trueskill set mu=?,sigma=? where frigante=?'''
    cur.execute(query, (new_mu, new_sigma, player,))
    conn.commit()


def closeweek(conn, w, dt):
    conn.execute("update weeks set enddate=? where week=?",
                 (dt, w))
    conn.commit()


def newweek(conn, w, dt):
    conn.execute("insert into weeks (week,startdate)values(?,?)",
                 (w, dt))
    conn.commit()


def insertCalippo(conn, w, p, wns):
    conn.execute('''insert into califfato(week,califfo,wins)
                    values(?,?,?)''',
                 (w, p, wns))
    conn.commit()


def getCurrentSeason(conn):
    cur = conn.cursor()
    cur.execute("SELECT stagione, from_frigo FROM stagioni WHERE to_frigo IS NULL")
    return cur.fetchone()


def closeSeason(conn, stagione, to_frigo, winner):
    conn.execute("UPDATE stagioni SET to_frigo=?, winner=? WHERE stagione=?",
                 (to_frigo, winner, stagione))
    conn.commit()


def getSeasonOrdinal(conn, stagione):
    '''Posizione cronologica (1-based) della stagione tra tutte quelle in stagioni,
    in base a from_frigo.'''
    cur = conn.cursor()
    cur.execute('''SELECT COUNT(*) FROM stagioni
                   WHERE from_frigo <= (SELECT from_frigo FROM stagioni WHERE stagione=?)''',
                (stagione,))
    return cur.fetchone()[0]


def getSeasonWinCount(conn, player):
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM stagioni WHERE winner=?", (player,))
    result = cur.fetchone()
    return result[0] if result[0] else 0


def getCaliffi(conn):
    califfi = {}
    query = '''select califfo from califfato'''
    cur = conn.cursor()
    cur.execute(query)
    result = cur.fetchall()
    for res in result:
        if '-' in res[0]:
            cals = res[0].split('-')
            for c in cals:
                if c in califfi:
                    califfi[c]['califfi'] = califfi[c]['califfi'] + 1
                    califfi[c]['califfi_cond'] = califfi[c]['califfi_cond'] + 1
                else:
                    califfi[c] = {}
                    califfi[c]['califfi'] = 1
                    califfi[c]['califfi_cond'] = 1
        else:
            if res[0] in califfi:
                califfi[res[0]]['califfi'] = califfi[res[0]]['califfi'] + 1
            else:
                califfi[res[0]] = {}
                califfi[res[0]]['califfi'] = 1
                califfi[res[0]]['califfi_cond'] = 0
    califfi_lista = [(nome, dati) for nome, dati in califfi.items()]
    califfi = sorted(califfi_lista, key=lambda x: (-x[1]['califfi'], x[1]['califfi_cond']))
    return califfi


def getSpawnsWithWinsOfPokemon(conn, pokemon):
    query = '''select spawn,pokewinner from (
    select distinct frigo,spawn from spawns)s
    inner join frigos f on s.frigo=f.progr
    where spawn=?'''

    spawns = []
    wins = []
    cur = conn.cursor()
    cur.execute(query, (pokemon,))
    result = cur.fetchall()
    for r in result:
        spawns.append(r[0])
        wins.append(r[1])
    spawns_count = len(spawns)
    wins_count = len([w for w in wins if w == pokemon])
    return spawns_count, wins_count


def getUnicumByPlayer(conn, player):
    query = ''' SELECT pokewinner,num_wins FROM (
            SELECT pokewinner, winner, COUNT(*) AS num_wins
            FROM frigos
            GROUP BY pokewinner, winner
            HAVING pokewinner IN (
                SELECT pokewinner FROM frigos GROUP BY pokewinner HAVING COUNT(DISTINCT winner) = 1))q
            WHERE winner=?'''

    animali = []
    wins = []
    cur = conn.cursor()
    cur.execute(query, (player,))
    result = cur.fetchall()
    for r in result:
        animali.append(r[0])
        wins.append(r[1])
    return animali, wins


def UnicumLadder(conn):
    query = '''select * from (
    select winner,count(*)as c from (
    SELECT pokewinner, winner, COUNT(*) AS numero_gol
    FROM frigos
    GROUP BY pokewinner, winner
    HAVING pokewinner IN (
        SELECT pokewinner
        FROM frigos
        GROUP BY pokewinner
        HAVING COUNT(DISTINCT winner) = 1
        ) )q group by winner
    )t order by c desc'''

    players = []
    unici = []
    cur = conn.cursor()
    cur.execute(query)
    result = cur.fetchall()
    for r in result:
        players.append(r[0])
        unici.append(r[1])
    return players, unici


def getNonVincenti(conn):
    '''Ritorna la lista dei "cessi" (animali mai vincitori di una frigo) insieme
    al numero di volte in cui sono stati tentati come wincon (spawns.winconato)
    e quindi, essendo cessi, hanno fallito la sverginata.'''
    query = '''select s.spawn, coalesce(w.tentativi, 0) as tentativi from (
    select distinct spawn from spawns
    )s left outer join
    (select distinct pokewinner from frigos)f
    on f.pokewinner=s.spawn
    left outer join
    (select spawn, count(*) as tentativi from spawns where winconato=1 group by spawn)w
    on w.spawn=s.spawn
    where f.pokewinner is null
    order by s.spawn'''

    spwaws = []
    cur = conn.cursor()
    cur.execute(query)
    result = cur.fetchall()
    for r in result:
        spwaws.append((r[0], r[1]))
    return spwaws


def getPokemonWinsPerSpawns(conn):
    query = '''select * from (
select t1.animale as animale,spawns,wins,wins*10000/spawns as wr from (
select spawn as animale,count(*)spawns  from (
    select distinct frigo,spawn from spawns)s
    group by spawn)t1
join (
select pokewinner as animale,count(*) wins from(
select distinct progr,pokewinner from 
frigos f inner join spawns s
on f.progr=s.frigo)i
group by pokewinner)t2
on t1.animale=t2.animale)q
where animale not like 'Arceus%'
order by wr desc'''

    animali = []
    spawns = []
    wins = []
    cur = conn.cursor()
    cur.execute(query)
    result = cur.fetchall()
    for r in result:
        animali.append(r[0])
        spawns.append(r[1])
        wins.append(r[2])
    return animali, spawns, wins


def getUniciVincentiInWeek(conn, week):
    query = '''select distinct pokewinner,winner from frigos where week=?
        and pokewinner not in (select distinct pokewinner from frigos where week<?
        )'''

    cessi = []
    sverginatori = []
    cur = conn.cursor()
    cur.execute(query, (week, week,))
    result = cur.fetchall()
    for r in result:
        cessi.append(r[0])
        sverginatori.append((r[1]))
    return cessi,sverginatori


def getWeekInfo(conn,week):
    cur = conn.cursor()
    cur.execute("select startdate,enddate from weeks where week= ?",
                (week,))

    result = cur.fetchone()

    if result:
        return result[0],result[1] #startdate,enddate
    else:
        return None,None


def getSinceHowManyFrigosSpawn(conn, pokemon):
    query = '''select (select max(progr) from frigos)-(select max(frigo)from spawns
        where spawn=?)'''


    cur = conn.cursor()
    cur.execute(query, (pokemon,))
    result = cur.fetchone()

    if result:
        return result[0]
    return 10000


def getLastFrigoWonByMon(conn, pokemon):
    '''Numero dell\'ultima frigo (frigos.progr più alto) vinta con questo
    animale come pokewinner, o None se non ha mai vinto.'''
    cur = conn.cursor()
    cur.execute("SELECT MAX(progr) FROM frigos WHERE pokewinner=?", (pokemon,))
    result = cur.fetchone()
    return result[0] if result else None


def getWinconCountForPokemon(conn, pokemon):
    '''Quante volte questo animale è stato l'ultimo pokemon in campo (wincon,
    colonna spawns.winconato) per il suo giocatore, indipendentemente dal
    fatto che quel giocatore abbia poi vinto la frigo.'''
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM spawns WHERE spawn=? AND winconato=1", (pokemon,))
    result = cur.fetchone()
    return result[0] if result else 0


def getTopWinconedMons(conn, limit=10):
    '''I `limit` animali scelti più spesso come wincon (spawns.winconato),
    indipendentemente da chi li ha spawnati. Ritorna una lista di tuple
    (spawn, wincon_cnt, wins), dove wins e' quante di quelle volte il
    giocatore che ha tentato la wincon ha poi effettivamente vinto la frigo.
    Ordinata per wincon_cnt decrescente.'''
    cur = conn.cursor()
    cur.execute('''SELECT s.spawn, COUNT(*) AS wincon_cnt,
               SUM(CASE WHEN f.winner = s.player THEN 1 ELSE 0 END) AS wins
        FROM spawns s
        JOIN frigos f ON f.progr = s.frigo
        WHERE s.winconato=1
        GROUP BY s.spawn
        ORDER BY wincon_cnt DESC
        LIMIT ?''', (limit,))
    return cur.fetchall()


def getTopWinconizerForMon(conn, mon):
    '''Tra i giocatori che hanno spawnato questo animale, quello che lo ha
    scelto come wincon (spawns.winconato) nella percentuale più alta rispetto
    alle volte in cui lo ha spawnato. Ritorna (player, wincon_cnt, spawn_cnt)
    o (None, 0, 0) se nessuno lo ha mai winconato.'''
    cur = conn.cursor()
    cur.execute('''
        SELECT player,
               SUM(CASE WHEN winconato=1 THEN 1 ELSE 0 END) AS wincon_cnt,
               COUNT(*) AS spawn_cnt
        FROM spawns
        WHERE spawn=?
        GROUP BY player
        HAVING wincon_cnt > 0
        ORDER BY (wincon_cnt * 1.0 / spawn_cnt) DESC, wincon_cnt DESC
        LIMIT 1
    ''', (mon,))
    result = cur.fetchone()
    if not result:
        return None, 0, 0
    return result[0], result[1], result[2]


def getMostFrequentWinconizerForMon(conn, mon):
    '''Tra i giocatori che hanno spawnato questo animale, quello che lo ha
    scelto come wincon (spawns.winconato) il maggior numero di volte in
    assoluto. Ritorna (player, wincon_cnt, spawn_cnt) o (None, 0, 0) se
    nessuno lo ha mai winconato.'''
    cur = conn.cursor()
    cur.execute('''
        SELECT player,
               SUM(CASE WHEN winconato=1 THEN 1 ELSE 0 END) AS wincon_cnt,
               COUNT(*) AS spawn_cnt
        FROM spawns
        WHERE spawn=?
        GROUP BY player
        HAVING wincon_cnt > 0
        ORDER BY wincon_cnt DESC, (wincon_cnt * 1.0 / spawn_cnt) DESC
        LIMIT 1
    ''', (mon,))
    result = cur.fetchone()
    if not result:
        return None, 0, 0
    return result[0], result[1], result[2]


def getPreferredWinconByPlayer(conn, player):
    '''Tra gli animali spawnati da questo giocatore, quello scelto come wincon
    (spawns.winconato) nella percentuale più alta rispetto alle volte in cui lo
    ha spawnato. Ritorna (mon, wincon_cnt, spawn_cnt) o (None, 0, 0) se il
    giocatore non ha mai winconato nulla.'''
    cur = conn.cursor()
    cur.execute('''
        SELECT spawn,
               SUM(CASE WHEN winconato=1 THEN 1 ELSE 0 END) AS wincon_cnt,
               COUNT(*) AS spawn_cnt
        FROM spawns
        WHERE player=?
        GROUP BY spawn
        HAVING wincon_cnt > 0
        ORDER BY (wincon_cnt * 1.0 / spawn_cnt) DESC, wincon_cnt DESC
        LIMIT 1
    ''', (player,))
    result = cur.fetchone()
    if not result:
        return None, 0, 0
    return result[0], result[1], result[2]


def getMostWinconedByPlayer(conn, player):
    '''Tra gli animali spawnati da questo giocatore, quello scelto come wincon
    (spawns.winconato) il maggior numero di volte in assoluto. Ritorna
    (mon, wincon_cnt, spawn_cnt) o (None, 0, 0) se il giocatore non ha mai
    winconato nulla.'''
    cur = conn.cursor()
    cur.execute('''
        SELECT spawn,
               SUM(CASE WHEN winconato=1 THEN 1 ELSE 0 END) AS wincon_cnt,
               COUNT(*) AS spawn_cnt
        FROM spawns
        WHERE player=?
        GROUP BY spawn
        HAVING wincon_cnt > 0
        ORDER BY wincon_cnt DESC, (wincon_cnt * 1.0 / spawn_cnt) DESC
        LIMIT 1
    ''', (player,))
    result = cur.fetchone()
    if not result:
        return None, 0, 0
    return result[0], result[1], result[2]


def getTopPreferredWinconsByPlayer(conn, player, limit=10):
    '''I `limit` animali spawnati da questo giocatore scelti come wincon
    (spawns.winconato) con la percentuale più alta rispetto alle volte in cui
    li ha spawnati. Ritorna una lista di tuple (mon, wincon_cnt, spawn_cnt)
    ordinata per percentuale decrescente.'''
    cur = conn.cursor()
    cur.execute('''
        SELECT spawn,
               SUM(CASE WHEN winconato=1 THEN 1 ELSE 0 END) AS wincon_cnt,
               COUNT(*) AS spawn_cnt
        FROM spawns
        WHERE player=?
        GROUP BY spawn
        HAVING wincon_cnt > 0
        ORDER BY (wincon_cnt * 1.0 / spawn_cnt) DESC, wincon_cnt DESC
        LIMIT ?
    ''', (player, limit))
    return cur.fetchall()


def getTopMostWinconedByPlayer(conn, player, limit=10):
    '''I `limit` animali spawnati da questo giocatore scelti come wincon
    (spawns.winconato) il maggior numero di volte in assoluto. Ritorna una
    lista di tuple (mon, wincon_cnt, spawn_cnt) ordinata per wincon_cnt
    decrescente.'''
    cur = conn.cursor()
    cur.execute('''
        SELECT spawn,
               SUM(CASE WHEN winconato=1 THEN 1 ELSE 0 END) AS wincon_cnt,
               COUNT(*) AS spawn_cnt
        FROM spawns
        WHERE player=?
        GROUP BY spawn
        HAVING wincon_cnt > 0
        ORDER BY wincon_cnt DESC, (wincon_cnt * 1.0 / spawn_cnt) DESC
        LIMIT ?
    ''', (player, limit))
    return cur.fetchall()


def getMonsMissingTheLongest(conn, limit=10):
    query = '''select spawn, (select max(progr) from frigos) - max(frigo) as since
        from spawns
        group by spawn
        order by since desc
        limit ?'''

    mons = []
    since = []
    cur = conn.cursor()
    cur.execute(query, (limit,))
    result = cur.fetchall()
    for r in result:
        mons.append(r[0])
        since.append(r[1])
    return mons, since


def getCessiWinconByPlayer(conn, player):
    '''Un "cesso" è un animale che, al momento in cui è stato usato come ultimo
    pokemon (wincon, colonna spawns.winconato) da un giocatore in una frigo, non
    aveva ancora mai vinto una frigo (indipendentemente da chi l'avesse usato).
    Restituisce (tentativi, vittorie): quante volte il giocatore ha tentato la
    wincon con un cesso e quante di quelle volte ha effettivamente sverginato
    quell'animale.

    Letto dalla cache player_cesso_stats (mantenuta incrementalmente da
    db.updateStatsCacheForFrigo a ogni nuova frigo inserita).'''
    cur = conn.cursor()
    cur.execute("SELECT tentativi, vinte FROM player_cesso_stats WHERE player=?", (player,))
    result = cur.fetchone()
    if not result:
        return 0, 0
    return result[0], result[1]


def getCessiSpawnsByPlayer(conn, player):
    '''In quante frigo giocate il giocatore ha avuto in squadra almeno un "cesso"
    (un animale che, al momento dello spawn, non aveva ancora mai vinto una frigo),
    indipendentemente dal fatto che sia stato poi usato come wincon (spawns.winconato).
    Conta le frigo, non i singoli spawn: più cessi nella stessa frigo contano una volta sola.

    Letto dalla cache player_cesso_stats (mantenuta incrementalmente da
    db.updateStatsCacheForFrigo a ogni nuova frigo inserita).'''
    cur = conn.cursor()
    cur.execute("SELECT cessi_spawnati FROM player_cesso_stats WHERE player=?", (player,))
    result = cur.fetchone()
    if not result or result[0] is None:
        return 0
    return result[0]


def getCessiWinconStatsForRange(conn, from_frigo, to_frigo):
    '''Come getCessiWinconByPlayer ma calcolato al volo per un intervallo di frigo
    (from_frigo/to_frigo inclusi) invece che sull\'intera storia, per stat di fine
    stagione. Un tentativo (spawns.winconato=1) e\' su un "cesso" se, al progr di
    quella frigo, l\'animale non aveva ancora mai vinto una frigo (in tutta la
    storia, non solo nella stagione). Ritorna una lista di tuple
    (player, tentativi, vinte).'''
    cur = conn.cursor()
    cur.execute('''
        SELECT s.player,
               SUM(CASE WHEN NOT EXISTS (
                        SELECT 1 FROM frigos f2 WHERE f2.pokewinner = s.spawn AND f2.progr < s.frigo
                   ) THEN 1 ELSE 0 END) AS tentativi,
               SUM(CASE WHEN NOT EXISTS (
                        SELECT 1 FROM frigos f2 WHERE f2.pokewinner = s.spawn AND f2.progr < s.frigo
                   ) AND f.winner = s.player AND f.pokewinner = s.spawn THEN 1 ELSE 0 END) AS vinte
        FROM spawns s
        JOIN frigos f ON f.progr = s.frigo
        WHERE s.winconato = 1 AND s.frigo BETWEEN ? AND ?
        GROUP BY s.player
        HAVING tentativi > 0
    ''', (from_frigo, to_frigo))
    return cur.fetchall()


def getTopWinconedMonsForRange(conn, from_frigo, to_frigo, limit=10):
    '''Come getTopWinconedMons ma limitato alle frigo con progr tra from_frigo e
    to_frigo (inclusi), per stat di fine stagione.'''
    cur = conn.cursor()
    cur.execute('''SELECT s.spawn, COUNT(*) AS wincon_cnt,
               SUM(CASE WHEN f.winner = s.player THEN 1 ELSE 0 END) AS wins
        FROM spawns s
        JOIN frigos f ON f.progr = s.frigo
        WHERE s.winconato=1 AND s.frigo BETWEEN ? AND ?
        GROUP BY s.spawn
        ORDER BY wincon_cnt DESC
        LIMIT ?''', (from_frigo, to_frigo, limit))
    return cur.fetchall()