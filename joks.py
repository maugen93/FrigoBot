import random
from collections import Counter

def messForWinnerOnReg(winner_name, pk_winner):
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

    # Trova il massimo numero di occorrenze
    occorrenza_massima = max(contatore.values())

    # Trova tutti gli elementi che hanno l'occorrenza massima
    elementi_massimi = [elemento for elemento, conteggio in contatore.items() if conteggio == occorrenza_massima]

    # Crea la stringa separata da virgole e con "e" tra gli ultimi due elementi
    if len(elementi_massimi) > 1:
        stringa_elementi = ', '.join(elementi_massimi[:-1]) + " e " + elementi_massimi[-1]
    else:
        stringa_elementi = elementi_massimi[0]

    # Restituisci la stringa con il numero di occorrenze tra parentesi
    return f"{stringa_elementi} (`{occorrenza_massima}`)"

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