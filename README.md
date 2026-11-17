# Conversor de partidas FM20 → FM24 (experimental)

Convierte una partida guardada de **Football Manager 2020** en una partida de **Football Manager 2024**, mediante
ingeniería inversa del formato `.fm`. Solo hace falta la partida de FM20 y una **plantilla de FM24** (una partida de
FM24 con todas las ligas cargadas); el conversor **nunca modifica** ninguna de las dos y escribe un `.fm` nuevo.

> Proyecto en desarrollo. Las partidas generadas cargan en FM24, pero no todo se traslada todavía (ver Estado).

## Requisitos

- Python 3.10 o superior
- `numpy` (`pip install -r requirements.txt`)
- `zstd` en el PATH (compresión de FM24): <https://github.com/facebook/zstd/releases>

## Uso

```
python conversor/convertir.py PASO partida_fm20.fm plantilla_fm24.fm salida.fm [carpeta_de_trabajo]
```

`PASO` es `todo` o uno de los pasos, que se pueden ejecutar por separado y en este orden:

| Paso | Qué hace |
|---|---|
| `exportar20` | exporta todos los jugadores de FM20 a `fm20.csv` (atributos, contrato, nombres, datos personales) |
| `exportar24` | lo mismo con la plantilla de FM24 (`base.csv`) |
| `planificar` | empareja clubes por id único, decide qué ficha de FM24 recibe a cada jugador de FM20, las cesiones y el desfase de años |
| `mundo` | coloca los clubes en las divisiones de FM20 (intercambios de plaza y cambios de división), copia reputación y presupuestos, cierra cesiones |
| `jugadores` | trasplanta los jugadores: atributos, posiciones, CA/PA, nombres, nacimiento, nacionalidad, personalidad, contrato, cesiones, plantillas, saldo y patrocinadores |
| `historial` | historial de liga de cada club, campeones de cada competición (palmarés) y premios por temporada |

La carpeta de trabajo (por defecto `trabajo/`) guarda los resultados intermedios de cada paso.

## Estado

**Se traslada:** jugadores (atributos, posiciones, CA/PA, reputación, altura/peso, nombres, nacimiento, nacionalidad,
personalidad), contratos (sueldo, fechas, cláusulas), cesiones (club dueño / club de cesión y fechas), plantillas,
divisiones de los clubes, reputación de equipos, presupuestos, saldo y patrocinadores, historial de ligas de los
clubes, historial de competiciones (palmarés) y premios por temporada.

**Pendiente:** historial de temporadas de cada jugador, hitos y lesiones (falta saber a qué persona pertenece cada
lista), deudas por traspasos, leyendas e iconos de los clubes, manager, competiciones nuevas sin historial anterior a
2019, nombres cortos, internacionalidades.

**Fechas:** si la plantilla de FM24 está en la misma fecha que la partida de FM20 no se desplaza nada (plan A).
Si no, todos los años se desplazan la diferencia entre ambas (plan B).

## Estructura

- `conversor/` código del conversor (módulos `fm_*.py` y `convertir.py`)
- `docs/FORMATO.md` lo descubierto del formato de las partidas
- `investigacion/` scripts de búsqueda usados durante la ingeniería inversa
