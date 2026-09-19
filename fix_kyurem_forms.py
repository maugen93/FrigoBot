"""Corregge le frigo caricate quando Kyurem-White (e Kyurem-Black) venivano
erroneamente collassati su "Kyurem" da replay_reader.get_clean_mon_name (la
regola ALT_FORMS per il -White cosmetico di Squawkabilly stripava per errore
anche il -White di Kyurem, che e' invece una forma con stats/moveset diversi
e va trattata come spawn distinto).

Per ogni frigo che ha uno spawn "Kyurem" o pokewinner "Kyurem" rilegge il
replay (con la get_clean_mon_name corretta) e confronta gli animali Kyurem/
Kyurem-White/Kyurem-Black ottenuti con quanto salvato a db:
    - se un giocatore risulta aver spawnato una forma diversa da "Kyurem"
      (es. Kyurem-White), la riga spawns esistente viene aggiornata
    - se un giocatore ha spawnato sia Kyurem che una forma alternativa nella
      stessa frigo (collassati in una sola riga dal bug), viene aggiunta la
      riga mancante
    - se pokewinner era "Kyurem" ma il wincon effettivo era una forma
      alternativa, frigos.pokewinner viene corretto

Uso:
    uv run --with rich python fix_kyurem_forms.py [--db PATH] [--dry-run]
"""
import argparse

from rich.progress import Progress

import db
import replay_reader

DEFAULT_DB_PATH = 'frigo.db'
KYUREM_FORMS = ('Kyurem', 'Kyurem-White', 'Kyurem-Black')


def fix_frigo(conn, progr, replay_link, dry_run=False):
    players, _, pokewinner = replay_reader.elab_sd_replay(replay_link)

    esiti = []

    for p in players.values():
        collo = p['collo']
        if not collo:
            continue
        player = db.getPlayerFromSDName(conn, collo)
        if not player:
            continue

        corretti = [a for a in p['animali'] if a in KYUREM_FORMS]
        if not corretti:
            continue

        esistenti = {spawn for spawn, _ in db.getSpawnsForFrigoPlayer(conn, progr, player)
                     if spawn in KYUREM_FORMS}
        corretti_set = set(corretti)

        da_rimuovere = esistenti - corretti_set
        da_aggiungere = corretti_set - esistenti
        if not da_rimuovere and not da_aggiungere:
            continue

        for mon in corretti:
            winconato = (mon == p['ultimo_in_campo'])
            if mon in da_aggiungere:
                esiti.append((player, mon, 'da aggiungere' if dry_run else 'aggiunto'))
                if not dry_run:
                    db.insertSpawn(conn, progr, player, mon, winconato=winconato)

        for mon in da_rimuovere:
            esiti.append((player, mon, 'da rimuovere' if dry_run else 'rimosso'))
            if not dry_run:
                db.deleteSpawn(conn, progr, player, mon)

    frigo = db.getFrigoInfoFromNumber(conn, progr)
    if frigo['pokewinner'] == 'Kyurem' and pokewinner != 'Kyurem':
        esiti.append(('pokewinner', pokewinner, 'da correggere' if dry_run else 'corretto'))
        if not dry_run:
            db.updatePokewinner(conn, progr, pokewinner)

    return esiti


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--db', default=DEFAULT_DB_PATH, help='path al file frigo.db')
    parser.add_argument('--dry-run', action='store_true',
                         help='non scrive sul db, stampa solo cosa farebbe')
    args = parser.parse_args()

    conn = db.openDbConn(args.db)
    da_fare = db.getFrigosByMon(conn, 'Kyurem')

    n_errori = 0
    n_corrette = 0
    with Progress() as progress:
        task = progress.add_task('Fix Kyurem/Kyurem-White...', total=len(da_fare))
        for progr, replay_link in da_fare:
            try:
                esiti = fix_frigo(conn, progr, replay_link, dry_run=args.dry_run)
            except Exception as e:
                print('Frigo {}: ERRORE ({})'.format(progr, e))
                n_errori += 1
                progress.advance(task)
                continue
            if esiti:
                n_corrette += 1
                print('Frigo {}:'.format(progr))
                for player, mon, esito in esiti:
                    print('    {} -> {} [{}]'.format(player, mon, esito))
            progress.advance(task)

    if not args.dry_run and n_corrette > 0:
        print('\nRicostruzione cache statistiche (svergiconverters/svergitryers/swingscore)...')
        db.rebuildStatsCache(conn)

    db.closeDbConn(conn)
    print('\nCandidate: {}, corrette: {}, errori: {}'.format(len(da_fare), n_corrette, n_errori))


if __name__ == '__main__':
    main()
