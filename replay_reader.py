import json
import re
import requests


def get_clean_mon_name(mon_name):
    ALT_FORMS = """Busted|Tera|Continental|Unova|Monsoon|Jungle|Marine|Sandstorm|Rainbow-Swirl|Sun|Ruby-Cream|Terastal|Hero|Four|Tundra|Droopy|River|\
    Savanna|Archipelago|Icy Snow|Mint-Cream|Matcha-Cream|Dada|Ocean|Modern|Original|Garden|Summer|Winter|Spring|Fall|Autumn|Ruby-Swirl|Caramel-Swirl|\
Violet|Polar|East|West|Hoenn|Sinnoh|Kalos|Kanto|Hangry|Teal|Combat|Three-Segment|Johto|Lemon-Cream|Salted-Cream|Indigo|Blue|Green|Red|Orange|Yellow|Antique|Elegant|World|\
    Three-Segment|White|Noice|Stretchy|Low-Key|Blue-Striped|Original|Resolute|HighPlains|Masterpiece|Stellar|Savanna|High Plains|Jungle|Marine\
    """
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
    s = re.sub(rf'\-({ALT_FORMS})$', '', s)
    for ot_n in other_animals:
        if ot_n in s:
            return ot_n
    return s


def elab_sd_replay(link_replay):
    data = json.loads(
        requests.get(link_replay + ".json").content)

    pokewinner = None
    players = data['players']

    players = {'p1': {'collo': None, 'animali': []},
               'p2': {'collo': None, 'animali': []},
               'p3': {'collo': None, 'animali': []},
               'p4': {'collo': None, 'animali': []}
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

        # individuazione animale
        if log_i.startswith('|switch|') or log_i.startswith('|drag|') or log_i.startswith('|replace|'):
            pid = log_i.split('|')[2][:2]
            animale = log_i.split('|')[3].split(',')[0]
            animale = get_clean_mon_name(animale)
            if animale not in players[pid]['animali']:
                players[pid]['animali'].append(animale)

        if log_i.startswith('|win|'):
            winner = log_i.split('|')[2]

    for k, p in players.items():
        if p.get('collo') == winner:
            winner_id = k

    # scorro al contrario per trovare il pokewinner
    for i in range(len(log_rows) - 1, 0, -1):
        log = log_rows[i]
        if winner_id in log and ": " in log:
            pokewinner = log.split(': ')[1].split('|')[0]
            break

    # adjust pokewinner
    for pkmn in players[winner_id]['animali']:
        if pokewinner in pkmn:
            pokewinner = pkmn
            break

    return players, winner, pokewinner



