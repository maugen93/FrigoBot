import random
from collections import Counter

ORDINALI_IT = {
    1: 'prima', 2: 'seconda', 3: 'terza', 4: 'quarta', 5: 'quinta',
    6: 'sesta', 7: 'settima', 8: 'ottava', 9: 'nona', 10: 'decima',
}


def ordinale_it(n):
    return ORDINALI_IT.get(n, '{}-esima'.format(n))


def messForCloseToTop5(player, streak):
    templates = [
        "🚨 Ocio, <b>{}</b> è a una win dall'entrare in top 5 winstric (<code>{}</code>)",
        "🚨 <b>{}</b> sta per sfondare la top 5 winstrix, <code>{}</code> vittorie di fila",
        "🚨 Oh calma, <b>{}</b> è in striscia di <code>{}</code> winz",
    ]
    return random.choice(templates).format(player, streak)


def messForWinnerOnReg(winner_name, pk_winner):
    winner_name = f'<b>{winner_name}</b>'
    specific_users = {
        'mule': 'Ancora una volta obnubilati dalle lagne di quel maledetto porco. LO ODIO ({})'.format(pk_winner),
        'marviglio': 'Concessa al solito ({})'.format(pk_winner),
        'bot': 'Parterre talmente scarso che vince il bot con {}'.format(pk_winner),
        'ilfato': 'Ma è possibile essere così impediti da far vincere ciccio giunta con {}'.format(pk_winner),
        'fraga':'Zitto zitto arriva raga con {}'.format(pk_winner),
        'spite':'Vabbe solo spites poteva vincere con {}'.format(pk_winner)
    }
    defaults = ['Vince {} con {}, giocando completamente a caso'.format(winner_name, pk_winner),
                'Totalmente concessa a {} con {}'.format(winner_name, pk_winner),
                'Va bene, registriamo pure {} e {}'.format(pk_winner, winner_name),
                'Vincere con {} nel 2020, boh {}'.format(pk_winner, winner_name),
                'Per quanto con {} una win è sempre una win ({})'.format(pk_winner, winner_name),
                'E figurati se {} non vince con un animale come {}'.format(winner_name, pk_winner),
                'Trionfa {} con {}, impunito'.format(winner_name, pk_winner)]

    if winner_name not in specific_users:
        return random.choice(defaults)

    coinflip = random.randint(0, 6)

    if coinflip <4:
        return specific_users[winner_name]
    else:
        return random.choice(defaults)


def str_sverg(sverginatori):
    contatore = Counter(sverginatori)

    occorrenza_massima = max(contatore.values())

    elementi_massimi = [elemento for elemento, conteggio in contatore.items() if conteggio == occorrenza_massima]

    if len(elementi_massimi) > 1:
        stringa_elementi = ', '.join(elementi_massimi[:-1]) + " e " + elementi_massimi[-1]
    else:
        stringa_elementi = elementi_massimi[0]

    return f"{stringa_elementi} (<code>{occorrenza_massima}</code>)"

def commentoStagioneVittoria(category):
    comments = {
        'dominio': [
            "👑 Dominata dall'inizio alla fine",
            "👑 Stagione a senso unico",
            "👑 Zero competizione per tutta la siso",
        ],
        'furto': [
            "🥷 Rubata la siso a fine corsa",
            "🥷 Zitto zitto ruba la siso con un colpo di reni",
            "🥷 Colpo di stato nelle ultime frigo",
        ],
        'misura': [
            "📏 Staccato il secondo per un pelo",
            "📏 Vittoria di misura dopo un brivido",
            "📏 Si separa per un nonnulla",
        ],
        'schiacciante': [
            "🪨 Distrutti tutti i contendenti",
            "🪨 Vittoria schiacciante",
            "🪨 Margine imbarazzante sul secondo",
        ],
        'normale': [
            "📈 Vittoria solida e di sostanza",
            "📈 Ordinaria amministrazione nella disciplina del frigo",
            "📈 Nulla di eclatante, ma porta a casa il risultato",
        ],
    }
    return random.choice(comments.get(category, comments['normale']))


def commentoMedia(f_per_day):
    if f_per_day<1:
        return 'francamente sconfortante'
    if f_per_day<2:
        return 'miserabile'
    if f_per_day<3:
        return 'in fin dei conti accettabile'
    if f_per_day<5:
        return 'niente male'
    return 'fuori di testa'