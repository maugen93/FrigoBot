import json
import re
import requests


def get_clean_mon_name(mon_name):
    ALT_FORMS = """Busted|Tera|Continental|Unova|Monsoon|Jungle|Marine|Sandstorm|Rainbow-Swirl|Sun|Ruby-Cream|Terastal|Hero|Four|Tundra|Droopy|River|\
    Savanna|Archipelago|Icy Snow|Mint-Cream|Matcha-Cream|Dada|Ocean|Modern|Original|Garden|Summer|Winter|Spring|Fall|Autumn|Ruby-Swirl|Caramel-Swirl|\
Violet|Polar|East|West|Hoenn|Sinnoh|Kalos|Kanto|Hangry|Teal|Combat|Three-Segment|Johto|Lemon-Cream|Salted-Cream|Indigo|Blue|Green|Red|Orange|Yellow|Antique|Elegant|World|\
    Three-Segment|White|Noice|Stretchy|Low-Key|Blue-Striped|Original|Resolute|HighPlains|Masterpiece|Stellar|Savanna|High Plains|Jungle|Marine\
    """
    # formes that look cosmetic (and would match ALT_FORMS below) but are
    # actually distinct Pokemon with their own stats/moves, so they must
    # NOT be collapsed into their base species
    NON_COSMETIC_FORMS = ['Kyurem-White', 'Kyurem-Black']
    other_animals=['Pikachu']
    s = mon_name.rstrip()
    s = re.sub(r'^([a-zA-Z-]+)\(\1-([a-zA-Z-]+)\)$', r'\1-\2', s)
    s = re.sub(r'\((active)\)$', '', s)
    s = re.sub(r'\((par)\)$', '', s)
    s = re.sub(r'\((.*%)\)$', '', s)
    s = re.sub(r'\((.*%\|[a-z]{1,3})\)$', '', s)
    s = re.sub(r'\(fainted\)$', '', s)
    match = re.search(r'\(([^)]+)\)', s)
    s = match.group(1) if match else s
    if s not in NON_COSMETIC_FORMS:
        s = re.sub(rf'\-({ALT_FORMS})$', '', s)
    for ot_n in other_animals:
        if ot_n in s:
            return ot_n
    return s


def get_num_turns(log_rows):
    '''Numero totale di turni giocati in una frigo, letto dalle righe |turn|N
    del log Showdown (N e' il numero del turno appena iniziato, quindi l'ultimo
    valore visto e' il totale di turni della partita). Torna 0 se non c'e'
    nessuna riga |turn| nel log.'''
    num_turns = 0
    for log_i in log_rows:
        if log_i.startswith('|turn|'):
            num_turns = int(log_i.split('|')[2])
    return num_turns


def get_first_last_timestamps(log_rows):
    '''Primo e ultimo unix timestamp trovato nelle righe |t:|N del log Showdown
    (righe intervallate tra i messaggi chat, non una per messaggio). Il primo
    segna l'inizio della battaglia, l'ultimo la fine. Torna (None, None) se il
    log non ha nessuna riga |t:|.'''
    timestamps = [int(log_i.split('|')[2]) for log_i in log_rows if log_i.startswith('|t:|')]
    if not timestamps:
        return None, None
    return timestamps[0], timestamps[-1]


def elab_sd_replay(link_replay):
    data = json.loads(
        requests.get(link_replay + ".json").content)

    players = data['players']

    players = {'p1': {'collo': None, 'animali': [], 'ultimo_in_campo': None},
               'p2': {'collo': None, 'animali': [], 'ultimo_in_campo': None},
               'p3': {'collo': None, 'animali': [], 'ultimo_in_campo': None},
               'p4': {'collo': None, 'animali': [], 'ultimo_in_campo': None}
               }

    log_rows = data['log'].split('\n')
    for i in range(len(log_rows)):

        log_i = log_rows[i]

        # individuazione collo (gestisce anche la sostituzione di un
        # giocatore a metà partita: |player|p1| svuota il nome quando il
        # giocatore lascia, la riga successiva con un nome nuovo lo sostituisce)
        if log_i.startswith('|player|'):
            pid = log_i.split('|')[2]
            nome = log_i.split('|')[3]
            if nome:
                players[pid]['collo'] = nome

        # individuazione animale (e tracciamento dell'ultimo animale mandato in
        # campo da ogni giocatore, per capire con chi ha tentato il wincon anche
        # in caso di forfeit)
        if log_i.startswith('|switch|') or log_i.startswith('|drag|') or log_i.startswith('|replace|'):
            pid = log_i.split('|')[2][:2]
            animale = log_i.split('|')[3].split(',')[0]
            animale = get_clean_mon_name(animale)
            if animale not in players[pid]['animali']:
                players[pid]['animali'].append(animale)
            players[pid]['ultimo_in_campo'] = animale

        if log_i.startswith('|win|'):
            winner = log_i.split('|')[2]

    for k, p in players.items():
        if p.get('collo') == winner:
            winner_id = k

    # il pokewinner e' il wincon del vincitore, cioe' l'ultimo animale che ha mandato in campo
    pokewinner = players[winner_id]['ultimo_in_campo']

    num_turns = get_num_turns(log_rows)
    start_time, end_time = get_first_last_timestamps(log_rows)

    return players, winner, pokewinner, num_turns, start_time, end_time



