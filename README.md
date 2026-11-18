# FM20 → FM24 save converter (experimental)

Converts a **Football Manager 2020** save game into a **Football Manager 2024** save game, based on reverse
engineering of the `.fm` format. It only needs the FM20 save and an **FM24 template** (an FM24 save with all the
leagues loaded); the converter **never modifies** either of them and writes a new `.fm` file.

> Work in progress. The generated saves load in FM24, but not everything is carried over yet (see Status).

## Requirements

- Python 3.10 or newer
- `numpy` (`pip install -r requirements.txt`)
- `zstd` in the PATH (FM24 compression): <https://github.com/facebook/zstd/releases>

## Usage

```
python conversor/convertir.py STEP fm20_save.fm fm24_template.fm output.fm [work_folder]
```

`STEP` is `todo` (all) or one of the steps below, which can also be run one by one in this order:

| Step | What it does |
|---|---|
| `exportar20` | exports every FM20 player to `fm20.csv` (attributes, contract, names, personal data) |
| `exportar24` | same for the FM24 template (`base.csv`) |
| `planificar` | matches clubs (by unique id, or by nation + name when a club got another unique id in FM24), decides which FM24 player record receives each FM20 player, loans and the year offset |
| `mundo` | places the clubs in their FM20 divisions (place swaps and division changes), copies reputation and budgets, ends loans |
| `jugadores` | transplants the players: attributes, positions, CA/PA, names, birth date, nationality, personality, appearance (ethnicity, hair, skin tone), birthplace, international caps and debut, contract, loans, squads, balance and sponsors, club legends / icons / favoured personnel |
| `historial` | career history of every player, league history of every club, winners of every competition (honours, with the venue of each final) and yearly awards |
| `temporada` | results of the last finished season (for example the last Champions League final), which the database keeps until the next season starts, and the milestones of every player (records, debuts, transfers, team of the week and other awards) |

The work folder (`trabajo/` by default) keeps the intermediate results of every step.

## Status

**Carried over:** players (attributes, positions, CA/PA, reputation, height/weight, names, birth date, nationality,
personality), contracts (wage, dates, clauses), loans (parent club / loan club and dates), squads, club divisions,
team reputation, budgets, balance and sponsors, club league history, competition history (honours, including the
venue of each final and the last finished season), yearly awards, loan options and the career history (season
stats, including the season in progress) of every player, injury history, milestones and international caps and
goals (senior and youth).

**Pending:** transfer history with fees, transfer debts, the manager, competitions with no
history before 2019, short names.

**Club matching:** most clubs keep their unique id between FM20 and FM24, but some got another one and their old id
may belong to a different club in FM24 (Rennes 883 -> 881, while 881 was Poitiers in FM20). Clubs are matched by unique
id when the names agree, otherwise by nation + name; a club whose id now belongs to another club and has no match by
name is left out instead of being mapped to the wrong club.

`conversor/data/fm24_awards.json` lists how every FM24 award id is used (type of milestone, competition). It was built
with `fm24_tabla_premios.py` from a long FM24 career and is used to match the awards that have no yearly history.

**Dates:** if the FM24 template has the same date as the FM20 save nothing is shifted (plan A). Otherwise every year
is shifted by the difference between both saves (plan B).

## Layout

- `conversor/` converter code (`fm_*.py` modules and `convertir.py`)
- `docs/FORMAT.md` what is known about the save format
- `investigacion/` search scripts used during the reverse engineering
