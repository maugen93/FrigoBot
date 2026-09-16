import math


def calcMarvWr(giocate, vinte, totali, base=10000):
    if giocate == 0:
        return 0
    original_pond_wr = vinte * math.log(giocate) / giocate
    marvWr = original_pond_wr / math.log(totali - giocate)
    to_base = int(marvWr * base)
    return to_base


def calcWinrateVariability(weekly_games, weekly_wins, min_games_per_week=2,
                            recent_weeks=10, min_weight=0.1, decay_per_week=0.02,
                            max_reasonable_stdev=25.0):
    """Stima la volatilità "vera" del winrate settimanale, nettata dal rumore statistico
    dovuto a poche partite giocate in una data week.

    weekly_games/weekly_wins devono essere ordinati dalla week più vecchia alla più recente
    (come restituito da db.getWeeklyGamesAndWinsByPlayer). Le ultime `recent_weeks` week pesano
    il massimo (1.0); prima di quelle il peso decresce linearmente di `decay_per_week` a settimana,
    fino a un minimo di `min_weight`.

    In una frigo (FFA a 4) il winrate medio atteso è ~25%, non 50%: una week con pochissime
    partite può facilmente mostrare un winrate a 0% o 100% per puro rumore campionario, quindi
    la varianza osservata tra week viene corretta sottraendo la varianza campionaria attesa
    (stima binomiale con smoothing di Jeffreys, per non azzerarsi quando una week è 0%/100%).

    `max_reasonable_stdev` è la deviazione standard raggiunta oscillando ogni week tra 0% e 50%
    (il tetto di "variabilità assurdamente alta ma raggiungibile" per questo gioco) e viene usata
    per normalizzare lo score risultante su una scala 0-100.

    Il rumore campionario atteso (expected_var) tende a essere sistematicamente più alto della
    varianza osservata tra week (observed_var): con pochi game a settimana e un winrate atteso
    basso (~25%, FFA a 4), la formula binomiale p(1-p)/n sovrastima il rumore reale (gli avversari
    cambiano di partita in partita, quindi il p reale non è fisso come assume il modello binomiale
    i.i.d.). Sottrarre semplicemente expected_var da observed_var e clampare a 0 (max(0, ...))
    azzererebbe true_stdev per la maggioranza dei giocatori. Per evitarlo, la varianza osservata
    viene invece "ridotta" (shrinkage) in proporzione al rapporto observed_var/expected_var, senza
    mai azzerarsi del tutto: un rapporto vicino a 0 (variabilità quasi tutta rumore) dà uno
    shrinkage vicino a 0, un rapporto alto (variabilità vera, oltre al rumore) dà uno shrinkage
    vicino a 1.

    Ritorna un dict con 'mean_wr' (winrate medio pesato), 'true_stdev' (deviazione standard del
    winrate scalata dal rumore) e 'score' (0-100, 0 = winrate stabile, 100 = variabilità estrema),
    oppure None se non ci sono almeno 2 week con dati sufficienti.
    """
    pairs = [
        (games, wins)
        for games, wins in zip(weekly_games, weekly_wins)
        if games >= min_games_per_week
    ]
    if len(pairs) < 2:
        return None

    winrates = [wins * 100 / games for games, wins in pairs]
    n = len(pairs)
    weights = []
    for i in range(n):
        dist_from_recent = n - 1 - i
        if dist_from_recent < recent_weeks:
            weights.append(1.0)
        else:
            steps_past_recent = dist_from_recent - recent_weeks + 1
            weights.append(max(min_weight, 1.0 - decay_per_week * steps_past_recent))

    total_weight = sum(weights)
    mean = sum(w * x for w, x in zip(weights, winrates)) / total_weight
    observed_var = sum(w * (x - mean) ** 2 for w, x in zip(weights, winrates)) / total_weight

    expected_var = 0.0
    for (games, wins), weight in zip(pairs, weights):
        p_smoothed = (wins + 0.5) / (games + 1)
        sampling_var = p_smoothed * (1 - p_smoothed) * 100 ** 2 / games
        expected_var += weight * sampling_var
    expected_var /= total_weight

    ratio = observed_var / expected_var if expected_var > 0 else 0.0
    shrinkage = ratio / (ratio + 1)
    true_stdev = math.sqrt(observed_var) * shrinkage
    score = min(100, round(true_stdev / max_reasonable_stdev * 100))
    return {'mean_wr': mean, 'true_stdev': true_stdev, 'score': score}
