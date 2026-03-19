# ha-toniebox

Intégration Home Assistant pour les **Toniebox** via [HACS](https://hacs.xyz/), basée sur la librairie [`tonies-api`](https://github.com/Raphzer/tonies-api).

## Fonctionnalités

- Découverte automatique de toutes vos Tonieboxes et Tonies
- **Media Player** par Toniebox (volume, état lecture, artwork du Tonie actif)
- **Capteur Tonie actif** — nom + image en temps réel (Gen 2)
- **Capteur chapitre** — numéro et durée du chapitre en cours (Gen 2)
- **Capteur batterie** en temps réel (Gen 2)
- **Capteur connexion** online / offline (Gen 2)
- **Appareil Tonies Library** — une entité sensor par Tonie possédé
- **Bouton Sleep Now** — extinction immédiate (Gen 2)
- **Sélecteur LED** — on / dimmed / off (Gen 1)
- **Contrôles avancés Gen 2** — volume enceinte, casque, LED, et leurs équivalents mode sommeil
- **4 Blueprints** d'automations prêts à l'emploi
- Interface bilingue français / anglais

## Prérequis

- Home Assistant **2026.1+**
- [HACS](https://hacs.xyz/) installé
- Un compte [mytonies.com](https://mytonies.com)
- Données temps réel (batterie, Tonie actif, connexion, sleep) : **Toniebox Gen 2** uniquement

## Installation via HACS

1. HACS → **Intégrations** → menu ⋮ → *Dépôts personnalisés*
2. Ajouter l'URL de ce dépôt, catégorie **Integration**
3. Chercher **Tonies** et installer
4. Redémarrer Home Assistant

## Configuration

1. **Paramètres** → **Appareils & Services** → **Ajouter une intégration** → *Tonies*
2. Entrer votre **email** et **mot de passe** mytonies.com
3. Les Tonieboxes et entités sont créées automatiquement

## Entités créées

### Par Toniebox

| Entité | Type | Gen 1 | Gen 2 | Description |
|--------|------|:-----:|:-----:|-------------|
| `media_player.toniebox_*` | Media Player | ✓ | ✓ | Volume, état lecture, artwork |
| `sensor.*_battery` | Sensor | — | ✓ | Niveau batterie (%) |
| `sensor.*_active_tonie` | Sensor | — | ✓ | Tonie actif — nom + image |
| `sensor.*_connection` | Sensor | — | ✓ | online / offline |
| `sensor.*_chapter` | Sensor | — | ✓ | Numéro et durée du chapitre |
| `button.*_sleep_now` | Button | — | ✓ | Extinction immédiate |
| `select.*_led` | Select | ✓ | — | LED on / dimmed / off |
| `number.*_headphone_volume` | Number | ✓ | ✓ | Volume casque (25–100%) |
| `number.*_volume` | Number | — | ✓ | Volume enceinte (25–100%, pas 1%) |
| `number.*_led_brightness` | Number | — | ✓ | Luminosité LED (0–100%, pas 1%) |
| `number.*_bedtime_volume` | Number | — | ✓ | Volume mode sommeil (25–100%) |
| `number.*_bedtime_headphone_volume` | Number | — | ✓ | Volume casque mode sommeil (25–100%) |
| `number.*_bedtime_led_brightness` | Number | — | ✓ | Luminosité LED mode sommeil (0–100%) |

### Appareil Tonies Library (par compte)

| Entité | Description |
|--------|-------------|
| `sensor.tonies_library_count` | Nombre total de Tonies (contenu + créatifs) |
| `sensor.<titre>` | Un sensor par Tonie contenu (image, série, cover) |
| `sensor.<nom>` | Un sensor par Tonie créatif (chapitres, live) |

> Pour récupérer la liste complète en automation, utilisez le service `tonies.get_tonies_list` qui émet l'événement `tonies_list_result` (contournement de la limite 16 KB des attributs HA).

## Blueprints

| Blueprint | Description | Prérequis |
|-----------|-------------|-----------|
| `volume_bedtime.yaml` | Réduit le volume la nuit, restaure le matin | Toutes boxes |
| `low_battery_sleep.yaml` | Extinction sur batterie faible | Gen 2 |
| `notify_tonie_change.yaml` | Notification au changement de Tonie | Gen 2 |
| `sleep_schedule.yaml` | Plage horaire de silence (extinction + blocage) | Gen 2 |

## Documentation

La documentation complète (architecture, entités, services, développement) est disponible dans [DOCUMENTATION.md](DOCUMENTATION.md).

## Développement

```bash
scripts/setup    # Installe les dépendances Python
scripts/develop  # Démarre HA local en mode debug sur http://localhost:8123
scripts/lint     # Ruff format + check avec autofix
```

## Licence

Apache 2.0
