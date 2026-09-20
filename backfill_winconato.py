"""Backfill di spawns.winconato per le frigo già presenti nel db.

Le insert nuove (worker.insertResult) marcano già, per ogni giocatore, quale
animale fosse il suo ultimo mandato in campo (il tentativo di wincon). Le
frigo caricate prima di questa modifica hanno invece tutte winconato=0. Per
ognuna di queste rilegge il replay, individua l'ultimo animale in campo di
ogni giocatore e aggiorna la riga spawns corrispondente.

Le frigo che hanno già almeno uno spawn con winconato=1 vengono saltate senza
richiamare la rete (non serve rileggere un replay già elaborato).

Uso:
    uv run --with rich python backfill_winconato.py [--db PATH] [--limit N] [--frigo PROGR [PROGR ...]] [--dry-run]

    --limit N          elabora solo le prime N frigo da fare (per un test rapido)
    --frigo PROGR ...  elabora solo queste frigo (per numero progr); ignora --limit
                        e rilegge il replay anche se già marcata (utile per un test
                        puntuale su una o due frigo)
    --dry-run          non scrive sul db, stampa solo cosa farebbe

Richiede il pacchetto "rich" (solo per la progress bar): passato al volo con
--with, così non serve aggiungerlo alle dipendenze del progetto.
"""
import argparse

from rich.progress import Progress

import db
import replay_reader

DEFAULT_DB_PATH = 'frigo.db'


def backfill_frigo(conn, progr, replay_link, dry_run=False):
    players, _, _ = replay_reader.elab_sd_replay(replay_link)

    esiti = []
    for p in players.values():
        collo = p['collo']
        ultimo = p['ultimo_in_campo']
        if not collo or not ultimo:
            esiti.append((collo, ultimo, 'saltato (dati mancanti nel replay)'))
            continue

        player = db.getPlayerFromSDName(conn, collo)
        if not player:
            esiti.append((collo, ultimo, 'saltato (collo non registrato)'))
            continue

        if dry_run:
            esiti.append((player, ultimo, 'da aggiornare'))
            continue

        rowcount = db.setWinconato(conn, progr, player, ultimo)
        esito = 'aggiornato' if rowcount else 'ATTENZIONE: nessuna riga spawns corrispondente'
        esiti.append((player, ultimo, esito))

    return esiti


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--db', default=DEFAULT_DB_PATH, help='path al file frigo.db')
    parser.add_argument('--limit', type=int, default=None,
                         help='elabora solo le prime N frigo da fare (per un test rapido)')
    parser.add_argument('--frigo', type=int, nargs='+', default=None,
                         help='elabora solo queste frigo (per numero progr), anche se già marcate')
    parser.add_argument('--dry-run', action='store_true',
                         help='non scrive sul db, stampa solo cosa farebbe')
    args = parser.parse_args()

    conn = db.openDbConn(args.db)
    da_fare = db.getFrigosToBackfillWinconato(conn, args.frigo)
    if args.limit and not args.frigo:
        da_fare = da_fare[:args.limit]

    n_errori = 0
    with Progress() as progress:
        task = progress.add_task('Backfill winconato...', total=len(da_fare))
        for progr, replay_link in da_fare:
            try:
                esiti = backfill_frigo(conn, progr, replay_link, dry_run=args.dry_run)
            except Exception as e:
                print('Frigo {}: ERRORE ({})'.format(progr, e))
                n_errori += 1
                progress.advance(task)
                continue
            print('Frigo {}:'.format(progr))
            for player, spawn, esito in esiti:
                print('    {} -> {} [{}]'.format(player, spawn, esito))
            progress.advance(task)

    if not args.dry_run and len(da_fare) - n_errori > 0:
        print('\nRicostruzione cache statistiche (svergiconverters/svergitryers/swingscore)...')
        db.rebuildStatsCache(conn)

    db.closeDbConn(conn)
    print('\nCompletate: {}/{} (errori: {})'.format(len(da_fare) - n_errori, len(da_fare), n_errori))


if __name__ == '__main__':
    main()

# 486 ogerpon-gate
# 916 oinkologne-gate
# 1334 tutti
# Frigo 1532:
# fraraga -> Magearna-Original-Mega [ATTENZIONE: nessuna riga spawns corrispondente]
# Frigo 1759:
# sergio -> Veluza [ATTENZIONE: nessuna riga spawns corrispondente]