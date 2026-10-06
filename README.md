# Speed Zone Witness

## Français

Outil hors ligne en lecture seule qui compare la **limite de vitesse attendue** à la limite appliquée et à la vitesse mesurée. Il recalcule la position sur le chemin à chaque mesure, y compris après un recul. Un chemin trop ancien ou trop éloigné est ignoré ; la zone à la position actuelle reste vérifiée. Sans exposition à une zone, le verdict est `inconclusive`.

```sh
python3 -m venv .venv
.venv/bin/pip install -e .
.venv/bin/python -m unittest discover -s tests
.venv/bin/speed-zone-witness fixtures/safe.jsonl fixtures/config.json --locale=fr
.venv/bin/speed-zone-witness fixtures/reverse.jsonl fixtures/config.json --locale=fr
```

Le JSONL contient des événements `path` avec `points` `[x,y]` en mètres et des événements `sample` avec position, `applied_limit_mps` et `velocity_mps`. Le fichier de configuration définit des zones rectangulaires, l’horizon de chemin, son âge maximal, la distance maximale au chemin et la tolérance. Une intégration Nav2 doit convertir le masque de vitesse et l’unité de limite en m/s avant l’analyse. Les exemples sont synthétiques ; ce rapport ne remplace pas la validation du système de sûreté et n’envoie aucune commande.

Codes de sortie : 0 `pass`, 1 `fail`, 2 entrée invalide, 3 `inconclusive`.

## English

Read-only offline tool that compares the **expected speed limit** with the applied limit and measured velocity. It recomputes position on the path at each sample, including after reverse motion. An old or distant path is ignored; the zone at the current pose is still checked. Without zone exposure, the verdict is `inconclusive`.

```sh
python3 -m venv .venv
.venv/bin/pip install -e .
.venv/bin/python -m unittest discover -s tests
.venv/bin/speed-zone-witness fixtures/safe.jsonl fixtures/config.json --locale=en
.venv/bin/speed-zone-witness fixtures/reverse.jsonl fixtures/config.json --locale=en
```

JSONL contains `path` events with `[x,y]` points in meters and `sample` events with pose, `applied_limit_mps` and `velocity_mps`. The config defines rectangular zones, path lookahead, maximum path age, maximum distance from the path and tolerance. A Nav2 integration must convert the speed mask and limit unit to m/s before analysis. Samples are synthetic; this report does not replace safety-system validation and sends no commands.

Exit codes: 0 `pass`, 1 `fail`, 2 invalid input, 3 `inconclusive`.

## Español

Herramienta de solo lectura que compara el **límite de velocidad esperado** con el aplicado y la velocidad medida. Recalcula la posición en el camino en cada medición, incluso después de retroceder. Ignora un camino antiguo o lejano; sigue comprobando la zona en la posición actual. Sin exposición a una zona, el resultado es `inconclusive`.

```sh
python3 -m venv .venv
.venv/bin/pip install -e .
.venv/bin/python -m unittest discover -s tests
.venv/bin/speed-zone-witness fixtures/safe.jsonl fixtures/config.json --locale=es
.venv/bin/speed-zone-witness fixtures/reverse.jsonl fixtures/config.json --locale=es
```

El JSONL contiene eventos `path` con puntos `[x,y]` en metros y eventos `sample` con posición, `applied_limit_mps` y `velocity_mps`. La configuración define zonas rectangulares, horizonte del camino, antigüedad máxima, distancia máxima al camino y tolerancia. Una integración Nav2 debe convertir la máscara y la unidad del límite a m/s antes del análisis. Los ejemplos son sintéticos; este informe no sustituye la validación del sistema de seguridad y no envía órdenes.

Códigos de salida: 0 `pass`, 1 `fail`, 2 entrada no válida, 3 `inconclusive`.

MIT — [LICENSE](LICENSE).
