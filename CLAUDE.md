# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

FrigoBot is a Telegram bot (Italian-language) for tracking results of "Frigo" matches — 4-player free-for-all Pokémon Showdown random battles played by a private group. Players post a Pokémon Showdown replay link in the Telegram chat, the bot parses the replay, records the result, and offers various stats/leaderboard commands.

There is no test suite and no linter config. Dependencies are managed via `uv` (`pyproject.toml` / `uv.lock`): `python-telegram-bot`, `pandas`, `numpy`, `scipy`, `matplotlib`, `requests`, `fpdf2` (imported as `fpdf`).

## Running the bot

```bash
uv sync          # install/sync the venv from uv.lock
uv run python main.py
```

`uv run` executes commands inside the project's managed virtualenv (`.venv`), syncing dependencies first if needed — no manual `pip install`/`venv activate` required. Same goes for the ad-hoc scripts below, e.g. `uv run python tests.py`.

`main.py` hardcodes the Telegram bot token and the Windows filesystem path to `frigo.db` (this project was developed on Windows) — both need to be adjusted for the local environment before running. `bot.start_bot(token, db_path)` wires up all command handlers and starts polling.

There are no automated tests. `tests.py` and `summaries.py` are ad-hoc one-off scripts (module-level code that executes on import, hardcoded Windows paths, hardcoded frigo-number ranges) used manually for exploration/reporting — not a real test suite and not meant to be run as-is.

## Architecture

Layered, single-purpose modules with no classes — everything is free functions operating on a `sqlite3.Connection` or a `db_path` string:

- **`main.py`** — entry point; holds the bot token and db path, calls `bot.start_bot`.
- **`bot.py`** — Telegram handler layer. One `async def ..._command(update, context, path)` per command, each `partial`-bound to the db path and registered in `start_bot`. Handlers call into `worker.py` and reply with the returned string (or photo). A `MessageHandler` with a regex on `replay`+`pokemonshowdown`+`freeforallrandombattle` catches replay links posted as plain messages (not a slash command) and routes them to `handle_message` → `worker.insertResult`.
- **`worker.py`** — business logic / message-formatting layer. Each function opens its own db connection via `db.openDbConn`, calls one or more `db.py` query functions, formats an Italian-language string (often with emoji and in-jokes), and closes the connection. This is where new bot-facing features get added.
- **`db.py`** — the only module that touches SQLite directly. Every function takes an open `conn` (except the few that take `dbpath` to open one) and returns plain tuples/lists — no ORM. SQL is written inline, often with dynamically built `WHERE` clauses (string `.format()` of query fragments) for optional filters like `week`/`from_frigo`/`to_frigo`.
- **`replay_reader.py`** — fetches a Showdown replay's `.json` log (`link + ".json"`) and parses the `|player|`, `|switch|`/`|drag|`/`|replace|`, and `|win|` protocol lines out of the raw log text to determine each seat's Showdown nickname, which Pokémon each seat used, the winner, and the winning Pokémon. `get_clean_mon_name` strips battle-log annotations (health %, status, "(active)") and known cosmetic alternate forms so different formes of the same species collapse to one name for stats purposes.
- **`logics.py`** — small standalone scoring formulas (currently `calcMarvWr`, a participation-weighted win-rate score using `wins * log(games) / games` normalized against the rest of the field).
- **`joks.py`** — flavor-text generation (randomized snarky messages, player-specific jokes, superlative phrasing). Pure string logic, no I/O.
- **`graph.py`** — matplotlib/pandas chart and table image generation, saved to a file path that's then sent back as a Telegram photo.

### Data flow for a new replay

`bot.handle_message` → `worker.insertResult`: validates the link looks like a Showdown FFA replay → checks it isn't already recorded (`db.isSDReplayAlreadyLoaded`) → `replay_reader.elab_sd_replay` parses the replay JSON into per-seat nickname/Pokémon-used/winner → each seat's Showdown nickname is resolved to a registered player name via `db.getPlayerFromSDName` (against the `colli` table) and the insert is rejected if a nickname isn't registered → spawns are recorded per player (`spawns` table) → the frigo row itself is inserted (`frigos` table) → a flavor-text reply is generated via `joks.messForWinnerOnReg`.

### Database (SQLite, path passed around as a string)

- `frigos` — one row per match: `progr` (sequential match number, PK), `week`, `data`, `player1..player4`, `winner`, `pokewinner` (winning seat's Pokémon), `replay_link`.
- `spawns` — one row per (frigo, player, Pokémon used): `frigo`, `player`, `spawn`.
- `colli` — maps a player's Showdown nickname to their canonical player name and Telegram tag: `sd_alt`, `frigante`, `tg_tag`. This is the registration table `getPlayerFromSDName` looks up.
- `weeks` — one row per week: `week`, `startdate`, `enddate` (`enddate IS NULL` marks the current week — see `getActualWeek`).
- `califfato` — weekly "califfo" (winner of the week) history, written by `closeWeek`.
- `stagioni` — season boundaries (`from_frigo`/`to_frigo`) and season winner.

Note: `db.py` also has `getRatingPlayer`/`setRatingPlayer` (Glicko) and `getTrueskillRatingPlayer`/`setTrueskillRatingPlayer` referencing `glicko`/`trueskill` tables that do not exist in the current `frigo.db` — those functions are currently unreachable/dead against the live schema.

## Conventions to preserve when extending

- Bot-facing strings are Italian, informal, and often insulting/joking in tone — match the existing voice in `joks.py` and the message-building code in `worker.py` rather than writing neutral English strings.
- Fuzzy name matching for `/player`, `/animale`, `/secchezza`, `/unicum` uses `difflib.SequenceMatcher` with a `ratio() > 0.7` threshold against the full list of known players/Pokémon (`db.getAllPlayers`/`db.getAllMons`) — follow this pattern for any new command that takes a free-text player or Pokémon name.
- `/query` and `/tag` (and other admin actions) are gated by a hardcoded Telegram user id check (`user.id != 170532946`) directly in the handler; there's no role table.
- Pokémon names must be normalized through `replay_reader.get_clean_mon_name` before being compared/stored so cosmetic formes don't fragment stats.
