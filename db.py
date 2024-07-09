import sqlite3
import pandas


def openDbConn(dbpath):
    conn = sqlite3.connect(dbpath)
    return conn


def closeDbConn(conn):
    conn.close()


def insertNewFrigo(conn, progr, week, data, p1, p2, p3, p4, w, pw, sd_link):
    conn.execute("INSERT INTO frigos (progr, week,data,player1,player2,player3,player4,winner,pokewinner,replay_link) "
                 "VALUES (?,?,?,?,?,?,?,?,?,?)",
                 (progr, week, data, p1, p2, p3, p4,
                  w, pw, sd_link))
    conn.commit()


def isSDReplayAlreadyLoaded(conn, sd_link):
    cur = conn.cursor()
    cur.execute("SELECT * FROM frigos WHERE replay_link=?", (sd_link,))
    result = cur.fetchone()
    exists = False
    if result:
        exists = True
    cur.close()
    return exists


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


def getNumberOfFrigos(conn):
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


def load_from_csv(db_path, csv_path):
    frigodata = pandas.read_csv(csv_path)
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


def getLeaderboardAll(conn):
    p = []
    w = []
    cur = conn.cursor()
    cur.execute("select winner,count(*) as c from frigos group by winner order by c desc")
    result = cur.fetchall()
    for r in result:
        p.append(r[0])
        w.append(r[1])
    return p, w


def getLeaderboardSummer(conn):
    p = []
    w = []
    cur = conn.cursor()
    cur.execute("select winner,count(*) as c from frigos where progr>=360 group by winner order by c desc")
    result = cur.fetchall()
    for r in result:
        p.append(r[0])
        w.append(r[1])
    return p, w


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


def getLeaderboardWeek(conn, week):
    p = []
    w = []
    cur = conn.cursor()
    cur.execute("select winner,count(*) as c from frigos where week= ? group by winner order by c desc", (week,))
    result = cur.fetchall()
    for r in result:
        p.append(r[0])
        w.append(r[1])
    return p, w


def run_custom_query(conn, query):
    conn.execute(query)
    conn.commit()


def getCalippati(conn):
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
    cur.execute("select distinct pokewinner from frigos")
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

def getNumberPartecipiedSinceLastWin(conn,player):
    cur=conn.cursor()
    query='''select count(*) from frigos where (player1=? or player2=? or player3 = ? or player4 = ?) and progr >(
            select max(progr) 
                from frigos where winner=?)'''

    result = cur.execute(query, (player, player, player, player,player))

    for r in result:
        if not r:
            return None
        num = r[0]
    return num