# The `.fm` save format (FM20 and FM24)

Reverse engineering notes. All integers are little-endian.

## Container

- 26-byte header: `02 01 'fmf.' [version] 00 00 [u64 = index_position - 9] [9 bytes] [compression]`;
  compression `1` = zlib (FM20), `3` = zstd (FM24).
- Each internal file is compressed at `26 + offset`.
- Index at the end: `[02 01 'fmf.'][ver][00 00][compressed index]`. The index holds the save name, the file list
  (`name`, `extension`, `offset u64`, `compressed u64`, `raw u64`, two timestamps) and one or more subfolders
  (`rgman`: competition files `comp_N.dat`, `fix_man.dat`, `comp_history_ls.dat`, `player_stats_hist_ls.dat`...).
- `fmsave.py` reads both formats; `fmcontenedor.py` rebuilds an FM24 container keeping the physical order.

## `game_db.dat`

- Records start with `[id][uid][uid][type]`: the `uid` (unique id) is mostly stable between FM20 and FM24, the ids are not.
  A few clubs changed uid between the two databases (e.g. Celtic 1568 -> 1567, Rennes 883 -> 881), so a uid match is not
  a proof of identity.
  References from other structures usually store `id + 1`.
  - person: type `0x02` player, `0x01` retired / non-player, `0x10`, `0x13` others.
  - team: `[team-1][uid][uid] 0a [flag]` (first team, B teams and youth teams).
  - national team: `[team-1][uid][uid] 0b [date]`, in the same area as the clubs (France: FM20 675, FM24 651, uid 768).
    The records `[id][uid][uid] 00 01 01 01 01` at the beginning of the file are cities (they carry coordinates);
    their ids overlap the team ids.
  - competition: `[comp-1][uid][uid] 00 [u8][u8] 01 ...` followed by a run of `06` bytes.
  - club: `[club id][uid][uid] 00` + four u32 that are the nation or `ffffffff` (FM24 `[nation][ff][nation][nation]`,
    FM20 also `[nation][ff][ff][nation]` and `[ff][nation][ff][nation]`); the names come later in the record, after up
    to several KB for big clubs, usually after `00 01 01 [u8 in FM20]`: `[len u32][full name][len u32][short name]`.
    The team record of the first team carries the club uid. Reserve and youth teams are clubs too.
  - award ids are mostly the same in both versions (team of the week of La Liga = 158 in both); some moved by one or
    two (405 -> 403, 608 -> 606).
  - stadium: `[stadium-1][uid][uid] 00 [capacity u32]...`, stored consecutively with increasing ids.
- Player attribute block: 15 positions (1–20) + 54 attributes (1–100, the game shows `round(v/5)`).
- Dates: `u16` (day of the year in the low 9 bits, time slot in the high 7 bits) + `u16` year; null date `01 00 6c 07`.
- Money is stored in pounds.
- Contracts, loans (type 1) and B-team registrations (0xff), squad lists `[ff ff ff ff][n u16][n ids]`.

## `tad` tables (`*_ls.dat` + `*_dt.cmt`)

Histories stored as lists of fixed-size rows. `_dt.cmt` holds the rows one after another; `_ls.dat` holds, for
every list, the offsets of its rows.

```
v3 (FM20): 02 01 'tad.' 03 00 00 | free u32 | free x u32 | n u32 | n x [c u32][c x u32 offset] | tail
v4 (FM24): 03 01 'tad.' 04 00    | free u32 | free x u32 | n u32 | n x [c u32][c x u32 encoded] | tail
tail = [u32 0][u32 row size][u16 version]
_dt.cmt header: 9 bytes (v3), 8 bytes (v4)
```

**v4 encoding:** `S0 = T0`, `Sk = Tk − S(k−1)`; to decode, `Tk = Sk + S(k−1)` (mod 2^32).
`free` are reusable rows of `_dt`. Implemented in `fm_tad.py` (reading and writing reproduce the original bytes).

The lists do not say who they belong to:

- `tc_league_history` (24 bytes: year, competition, position, teams, stats): one list per team in team id order, only
  for teams with history. Identified through historical seasons (signature) and through the order.
- `comp_history` (FM20 54 / FM24 55 bytes): one list per competition, one row per season:
  `[comp u32][year u16][..][9 x u32][00][04][start year][end year][date]`; slots 0–3 are teams (1st–4th), slot 7 is
  the stadium of the final, slot 8 is copied as is.
- `award_year_hist` (82 bytes): one list per award; 3 entries `[person = pid+1][club = uid+1][age]...[nation]`.
- `player_stats_hist` (FM20 96 / FM24 152 bytes: `[00][team u32][comp u16][u32][year u16][stats...]`): one list
  per player. The list index of every player is a `u32` stored **21 bytes before the player's name record** in
  `game_db.dat` (`ffffffff` = no list), in FM20 and FM24. Lists are allocated on demand (new lists are appended),
  so the index is not related to the player id. Found by comparing an FM24 save before and after the first match
  day of a season.
- `injury_histories` (FM20 18 / FM24 16 bytes): one list per person. Its index is stored inside the person record,
  between the attribute block and the name record, as `[ffffffff][date][date][00 00][list u32][03 00 00 00]`.
  Rows: FM20 `[type u32][u32][u8][u8][date][days u16][2 bytes]`, FM24 `[type u16][u32][00][u8][date][days u32]`;
  both versions share the same 114 injury types.
- International caps (person record, both versions): `[caps u8][goals u8][youth caps u8][youth goals u8][date][date]`,
  right before the milestones field `[u8][flag]([u32] if flag)[list u32][05 00]`. FM24 template, June 2023:
  Cristiano Ronaldo `c8 7b 0a 03` (200, 123, 10, 3), Messi `af 67 12 0e` (175, 103, 18, 14).
- `person_record_history` (milestones, FM20 44 / FM24 42 bytes): one list per person; its index follows the injury
  field: `[date][0a][flag]([u32] if flag = 1)[list u32][05 00]`. Rows:
  - FM20: `[00][team u32][u8][team2 u32][person u32][comp u16][award u16][date][A..E 5×u32][type u8][flag u8]`
  - FM24: `[date][A..E][type][flag][00][team u32][person u32][comp u16]` + `[00][team2 u32]`, or `[award u16][00 00 00]`
    in award rows (a row never has both).
  - `team` is the player's team, `team2` the other team (opponent, buying or selling club), `person` the player
    (pid + 1). `A..E` depend on the type (record code and value, transfer fee, position reached, year...).
  - Types seen: 0/1 competition result (`B` = position), 30–33 awards, 36/37 team of the season, 62 transfer,
    66/71 club arrivals, 94 joined club, 113 records and firsts, 122/123 debuts.
  - A team, competition or award the game cannot resolve is shown as `team#2` / `comp#1`.

## Competitions (`rgman/comp_N.dat`, `fix_man.dat`)

League tables are fixed-size rows starting with the team id; fixtures in `fix_man.dat` follow
`02 00 00 [home u32] ff 00 00 [away u32] ff 00`. The rows of the last finished season(s) of every competition (winner, runner-up, venue of the final...) are kept
**inside `game_db.dat`**, with the same layout as the `comp_history` rows (FM20 54 bytes, FM24 55 bytes), and are
only moved to `comp_history` when the next season starts.

## Loan contracts

The loan contract record has the loan end and start dates right after 8 bytes `ff`.

- The loan options are the same `u16` bit field in both versions, stored 67 bytes (FM20) or 88 bytes (FM24)
  before the loan end date: `0x0002` / `0x0004` can be recalled + can play cup games, `0x0001` can play against its
  own club, `0x1000` the loan cannot be terminated, `0x8000` can play against the parent club's B team
  (`0x0100` seen together with an optional future fee).
- The contract with the parent club of a loaned-out player has loan data in the 8 bytes before its dates
  (`ffffffff` + 4 bytes) instead of 8 bytes `ff`.
