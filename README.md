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
| `planificar` | matches clubs by unique id, decides which FM24 player record receives each FM20 player, loans and the year offset |
| `mundo` | places the clubs in their FM20 divisions (place swaps and division changes), copies reputation and budgets, ends loans |
| `jugadores` | transplants the players: attributes, positions, CA/PA, names, birth date, nationality, personality, contract, loans, squads, balance and sponsors |
| `historial` | league history of every club, winners of every competition (honours) and yearly awards |

The work folder (`trabajo/` by default) keeps the intermediate results of every step.

## Status

**Carried over:** players (attributes, positions, CA/PA, reputation, height/weight, names, birth date, nationality,
personality), contracts (wage, dates, clauses), loans (parent club / loan club and dates), squads, club divisions,
team reputation, budgets, balance and sponsors, club league history, competition history (honours, including the
venue of each final) and yearly awards.

**Pending:** player career history, milestones and injuries (it is still unknown which person each list belongs to),
results of the season that has just finished (they live in the competition files until the new season starts),
transfer debts, club legends and icons, the manager, competitions with no history before 2019, short names,
international caps.

**Dates:** if the FM24 template has the same date as the FM20 save nothing is shifted (plan A). Otherwise every year
is shifted by the difference between both saves (plan B).

## Layout

- `conversor/` converter code (`fm_*.py` modules and `convertir.py`)
- `docs/FORMAT.md` what is known about the save format
- `investigacion/` search scripts used during the reverse engineering
