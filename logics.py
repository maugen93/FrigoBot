import math


def calcMarvWr(giocate, vinte, totali, base=10000):
    if giocate == 0:
        return 0
    original_pond_wr = vinte * math.log(giocate) / giocate
    marvWr = original_pond_wr / math.log(totali - giocate)
    to_base = int(marvWr * base)
    return to_base
