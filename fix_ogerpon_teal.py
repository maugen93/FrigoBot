"""Normalize historical Ogerpon-Teal records to Ogerpon.

Usage:
    uv run python fix_ogerpon_teal.py --db /path/to/frigo.db --dry-run
    uv run python fix_ogerpon_teal.py --db /path/to/frigo.db
"""
import argparse

import db


def fix_ogerpon_teal(conn, dry_run=False):
    aliases = conn.execute(
        "SELECT frigo, player, winconato FROM spawns "
        "WHERE lower(spawn)='ogerpon-teal' ORDER BY frigo, player"
    ).fetchall()
    pokewinners = conn.execute(
        "SELECT progr FROM frigos WHERE lower(pokewinner)='ogerpon-teal' ORDER BY progr"
    ).fetchall()

    merged = 0
    renamed = 0
    for frigo, player, winconato in aliases:
        base = conn.execute(
            "SELECT winconato FROM spawns WHERE frigo=? AND player=? AND lower(spawn)='ogerpon'",
            (frigo, player),
        ).fetchone()
        if dry_run:
            if base:
                merged += 1
            else:
                renamed += 1
            continue

        if base:
            conn.execute(
                "UPDATE spawns SET winconato=max(winconato, ?) "
                "WHERE frigo=? AND player=? AND lower(spawn)='ogerpon'",
                (winconato or 0, frigo, player),
            )
            conn.execute(
                "DELETE FROM spawns WHERE frigo=? AND player=? AND lower(spawn)='ogerpon-teal'",
                (frigo, player),
            )
            merged += 1
        else:
            conn.execute(
                "UPDATE spawns SET spawn='Ogerpon' "
                "WHERE frigo=? AND player=? AND lower(spawn)='ogerpon-teal'",
                (frigo, player),
            )
            renamed += 1

    if not dry_run:
        conn.execute(
            "UPDATE frigos SET pokewinner='Ogerpon' WHERE lower(pokewinner)='ogerpon-teal'"
        )
        conn.commit()
        if aliases or pokewinners:
            # Correct the incremental caches, which may have counted the alias
            # as a separate species / first win.
            db.rebuildStatsCache(conn)

    return len(aliases), merged, renamed, len(pokewinners)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--db', default='frigo.db', help='path to the SQLite database')
    parser.add_argument('--dry-run', action='store_true', help='report changes without writing')
    args = parser.parse_args()

    conn = db.openDbConn(args.db)
    try:
        aliases, merged, renamed, pokewinners = fix_ogerpon_teal(conn, args.dry_run)
        mode = 'Would fix' if args.dry_run else 'Fixed'
        print('{} {} spawn rows ({} merged, {} renamed) and {} pokewinner rows.'.format(
            mode, aliases, merged, renamed, pokewinners
        ))
    finally:
        db.closeDbConn(conn)


if __name__ == '__main__':
    main()
