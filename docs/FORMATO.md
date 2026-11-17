# Formato de las partidas `.fm` (FM20 y FM24)

Notas de la ingeniería inversa. Todos los enteros son little-endian.

## Contenedor

- Cabecera de 26 bytes: `02 01 'fmf.' [version] 00 00 [u64 = posicion_indice - 9] [9 bytes] [compresion]`;
  compresion `1` = zlib (FM20), `3` = zstd (FM24).
- Cada fichero interno está comprimido en `26 + offset`.
- Índice al final: `[02 01 'fmf.'][ver][00 00][indice comprimido]`. El índice tiene el nombre de la partida, la lista de
  ficheros (`nombre`, `extension`, `offset u64`, `comprimido u64`, `sin comprimir u64`, dos marcas de tiempo) y una o
  más subcarpetas (`rgman`: ficheros de competición `comp_N.dat`, `fix_man.dat`, `comp_history_ls.dat`,
  `player_stats_hist_ls.dat`...).
- `fmsave.py` lee ambos formatos; `fmcontenedor.py` reconstruye un contenedor FM24 conservando el orden físico.

## `game_db.dat`

- Fichas con cabecera `[id][uid][uid][tipo]`: el `uid` (id único) es estable entre FM20 y FM24; los ids no.
  - jugador/persona: tipo `0x02` jugador, `0x01` retirado/no jugador, `0x10`, `0x13` otros.
  - equipo: `[equipo-1][uid][uid] 0a [indicador]` (primer equipo, filiales y juveniles).
  - selección: `[equipo-1][uid][uid] 00 01 01 01 01` al principio del fichero.
- Bloque de atributos del jugador: 15 posiciones (1–20) + 54 atributos (1–100, el juego muestra `round(v/5)`).
- Fechas: `u16` (día del año en los 9 bits bajos, franja horaria en los 7 altos) + `u16` año; fecha nula `01 00 6c 07`.
- Dinero en libras.
- Contratos, cesiones (tipo 1) y fichas de filial (0xff), listas de plantilla `[ff ff ff ff][n u16][n ids]`.

## Tablas `tad` (`*_ls.dat` + `*_dt.cmt`)

Historiales guardados como listas de filas de tamaño fijo. `_dt.cmt` contiene las filas una tras otra; `_ls.dat`
contiene, por lista, los offsets de sus filas.

```
v3 (FM20): 02 01 'tad.' 03 00 00 | libres u32 | libres x u32 | n u32 | n x [c u32][c x u32 offset] | cola
v4 (FM24): 03 01 'tad.' 04 00    | libres u32 | libres x u32 | n u32 | n x [c u32][c x u32 codificado] | cola
cola = [u32 0][u32 tamaño de fila][u16 version]
cabecera de _dt.cmt: 9 bytes (v3), 8 bytes (v4)
```

**Codificación v4:** `S0 = T0`, `Sk = Tk − S(k−1)`; para decodificar, `Tk = Sk + S(k−1)` (mod 2^32).
`libres` son filas del `_dt` reutilizables. Implementado en `fm_tad.py` (lectura y escritura idénticas al original).

Las listas no dicen a quién pertenecen:

- `tc_league_history` (24 bytes: año, competición, posición, equipos, estadísticas): una lista por equipo en orden de
  id de equipo, solo para equipos con historial. Se identifica por firma de temporadas históricas y por orden.
- `comp_history` (FM20 54 / FM24 55 bytes): una lista por competición, una fila por temporada con 9 clasificados
  (ids de equipo).
- `award_year_hist` (82 bytes): una lista por premio; 3 clasificados `[persona = pid+1][club = uid+1][edad]...[nación]`.
- `player_stats_hist`, `person_record_history`, `injury_histories`: una lista por persona, **sin índice conocido**.

## Competiciones (`rgman/comp_N.dat`, `fix_man.dat`)

Tablas de clasificación con filas de tamaño fijo que empiezan por el id de equipo; partidos en `fix_man.dat` con
`02 00 00 [local u32] ff 00 00 [visitante u32] ff 00`.
