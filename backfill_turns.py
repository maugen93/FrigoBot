"""Backfill di frigos.turns per le frigo già presenti nel db.

La colonna turns viene popolata solo dalle insert nuove (worker.insertResult),
leggendo il numero di turni dal replay (replay_reader.get_num_turns). Le frigo
caricate prima di questa modifica hanno turns=NULL. Per ognuna di queste
rilegge il replay e aggiorna frigos.turns.

Le frigo che hanno già un turns non-NULL vengono saltate senza richiamare la
rete (non serve rileggere un replay già elaborato).

Uso:
    uv run --with rich python backfill_turns.py [--db PATH] [--limit N] [--frigo PROGR [PROGR ...]] [--dry-run]

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
    _, _, _, num_turns = replay_reader.elab_sd_replay(replay_link)

    if dry_run:
        return num_turns, 'da aggiornare'

    rowcount = db.setTurns(conn, progr, num_turns)
    esito = 'aggiornato' if rowcount else 'ATTENZIONE: nessuna riga frigos corrispondente'
    return num_turns, esito


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
    da_fare = db.getFrigosToBackfillTurns(conn, args.frigo)
    if args.limit and not args.frigo:
        da_fare = da_fare[:args.limit]

    n_errori = 0
    with Progress() as progress:
        task = progress.add_task('Backfill turns...', total=len(da_fare))
        for progr, replay_link in da_fare:
            try:
                num_turns, esito = backfill_frigo(conn, progr, replay_link, dry_run=args.dry_run)
            except Exception as e:
                print('Frigo {}: ERRORE ({})'.format(progr, e))
                n_errori += 1
                progress.advance(task)
                continue
            print('Frigo {}: {} turni [{}]'.format(progr, num_turns, esito))
            progress.advance(task)

    db.closeDbConn(conn)
    print('\nCompletate: {}/{} (errori: {})'.format(len(da_fare) - n_errori, len(da_fare), n_errori))


if __name__ == '__main__':
    main()
