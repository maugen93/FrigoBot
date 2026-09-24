"""Backfill di frigos.start_time/end_time/duration per le frigo già presenti nel db.

Le colonne vengono popolate solo dalle insert nuove (worker.insertResult),
leggendo i timestamp dal replay (replay_reader.get_first_last_timestamps). Le
frigo caricate prima di questa modifica hanno start_time=NULL. Per ognuna di
queste rilegge il replay e aggiorna frigos.start_time/end_time/duration.

Le frigo che hanno già uno start_time non-NULL vengono saltate senza
richiamare la rete (non serve rileggere un replay già elaborato).

Uso:
    uv run --with rich python backfill_start_end_time.py [--db PATH] [--limit N] [--frigo PROGR [PROGR ...]] [--dry-run]

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


def _format_duration(seconds):
    '''Durata umana in minuti e secondi, es. "12m 34s" (o "45s" se sotto il minuto).'''
    minutes, secs = divmod(int(seconds), 60)
    if minutes:
        return '{}m {}s'.format(minutes, secs)
    return '{}s'.format(secs)


def backfill_frigo(conn, progr, replay_link, dry_run=False):
    _, _, _, _, start_time, end_time = replay_reader.elab_sd_replay(replay_link)

    if start_time is None or end_time is None:
        return None, None, None, 'saltato (nessun timestamp nel replay)'

    duration = _format_duration(end_time - start_time)

    if dry_run:
        return start_time, end_time, duration, 'da aggiornare'

    rowcount = db.setTimestamps(conn, progr, start_time, end_time, duration)
    esito = 'aggiornato' if rowcount else 'ATTENZIONE: nessuna riga frigos corrispondente'
    return start_time, end_time, duration, esito


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
    da_fare = db.getFrigosToBackfillTimestamps(conn, args.frigo)
    if args.limit and not args.frigo:
        da_fare = da_fare[:args.limit]

    n_errori = 0
    with Progress() as progress:
        task = progress.add_task('Backfill start/end time...', total=len(da_fare))
        for progr, replay_link in da_fare:
            try:
                start_time, end_time, duration, esito = backfill_frigo(conn, progr, replay_link, dry_run=args.dry_run)
            except Exception as e:
                print('Frigo {}: ERRORE ({})'.format(progr, e))
                n_errori += 1
                progress.advance(task)
                continue
            print('Frigo {}: {} -> {} ({}) [{}]'.format(progr, start_time, end_time, duration, esito))
            progress.advance(task)

    db.closeDbConn(conn)
    print('\nCompletate: {}/{} (errori: {})'.format(len(da_fare) - n_errori, len(da_fare), n_errori))


if __name__ == '__main__':
    main()
