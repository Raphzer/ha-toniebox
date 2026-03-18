# ha-toniebox

Intégration Home Assistant pour les **Toniebox** via [HACS](https://hacs.xyz/), basée sur la librairie [`tonies-api`](https://github.com/Raphzer/tonies-api).

## Fonctionnalités

- Découverte automatique de toutes vos Tonieboxes et Tonies
- **Media Player** par Toniebox (volume, état lecture, Tonie actif)
- **Sensor batterie** en temps réel (Gen 2 uniquement)
- **Sensor Tonie actif** (nom + image URL) (Gen 2 uniquement)
- **Sensor connexion** online / offline (Gen 2 uniquement)
- **Appareil Tonies Library** : une entité sensor par Tonie possédé (contenu + créatif)
- **Switch Sleep** — extinction immédiate (Gen 2 uniquement)
- **Sélecteur LED** — luminosité on / dimmed / off (Gen 1)
- **Contrôles avancés Gen 2** : volume enceinte, volume casque, luminosité LED, volume mode sommeil, volume casque mode sommeil, luminosité LED mode sommeil
- **4 Blueprints** d'automations prêts à l'emploi
- Interface bilingue français / anglais

## Prérequis

- Home Assistant **2026.1+**
- [HACS](https://hacs.xyz/) installé
- Un compte [mytonies.com](https://mytonies.com)
- Pour les données temps réel (batterie, Tonie actif, connexion, sleep) : une **Toniebox Gen 2** (WebSocket)

## Installation via HACS

1. Dans HACS → **Intégrations** → menu ⋮ → *Dépôts personnalisés*
2. Ajouter l'URL de ce dépôt, catégorie **Integration**
3. Chercher **Tonies** et installer
4. Redémarrer Home Assistant

## Configuration

1. **Paramètres** → **Appareils & Services** → **Ajouter une intégration** → chercher *Tonies*
2. Entrer votre e-mail et mot de passe mytonies.com
3. Les Tonieboxes et entités sont créées automatiquement

## Entités créées

### Par Toniebox

| Entité | Type | Gen 1 | Gen 2 | Description |
|--------|------|:-----:|:-----:|-------------|
| `media_player.toniebox_*` | Media Player | ✓ | ✓ | Volume, état lecture, turn off |
| `sensor.toniebox_*_battery` | Sensor | — | ✓ | Niveau batterie (%) |
| `sensor.toniebox_*_active_tonie` | Sensor | — | ✓ | Tonie actuellement posé |
| `sensor.toniebox_*_connection` | Sensor | — | ✓ | online / offline |
| `switch.toniebox_*_sleep` | Switch | — | ✓ | Extinction immédiate |
| `select.toniebox_*_led` | Select | ✓ | — | Luminosité LED (on/dimmed/off) |
| `number.toniebox_*_headphone_volume` | Number | ✓ | ✓ | Volume max casque (25–100%) |
| `number.toniebox_*_volume` | Number | — | ✓ | Volume max enceinte (25–100%, pas 1%) |
| `number.toniebox_*_led_brightness` | Number | — | ✓ | Luminosité LED (0–100%, pas 1%) |
| `number.toniebox_*_bedtime_volume` | Number | — | ✓ | Volume max mode sommeil (25–100%) |
| `number.toniebox_*_bedtime_headphone_volume` | Number | — | ✓ | Volume casque mode sommeil (25–100%) |
| `number.toniebox_*_bedtime_led_brightness` | Number | — | ✓ | Luminosité LED mode sommeil (0–100%) |

### Appareil Tonies Library (par compte)

Un appareil virtuel **Tonies Library** regroupe toutes les entités liées à vos Tonies :

| Entité | Type | Description |
|--------|------|-------------|
| `sensor.tonies_library_count` | Sensor | Nombre total de Tonies possédés |
| `sensor.<titre_tonie>` | Sensor | Un sensor par Tonie contenu (image, série, ID) |
| `sensor.<nom_tonie_creatif>` | Sensor | Un sensor par Tonie créatif (chapitres, live) |

> **Note :** pour récupérer la liste complète des Tonies en automation, utilisez le service `tonies.get_tonies_list` qui émet un événement `tonies_list_result` (contournement de la limite 16 KB des attributs HA).

## Blueprints

Importez les blueprints depuis `blueprints/automation/tonies/` :

| Blueprint | Description | Prérequis |
|-----------|-------------|-----------|
| `volume_bedtime.yaml` | Réduit le volume la nuit, le restaure le matin | Toutes boxes |
| `low_battery_sleep.yaml` | Éteint la box quand la batterie est faible | Gen 2 |
| `notify_tonie_change.yaml` | Notification quand un Tonie est changé | Gen 2 |
| `sleep_schedule.yaml` | Plage horaire de silence : éteint la box automatiquement (défaut 21h30–7h00), extinction immédiate si rallumée | Gen 2 |

## Développement

```bash
git clone https://github.com/Raphzer/ha-toniebox
cd ha-toniebox
scripts/setup    # Installe les dépendances Python
scripts/develop  # Démarre HA local en mode debug sur le port 8123
scripts/lint     # Ruff format + check avec autofix
```

### Structure

```
custom_components/tonies/
├── __init__.py          # Setup / unload + service get_tonies_list
├── manifest.json        # Métadonnées HACS (dépendance tonies-api>=0.1.4)
├── const.py             # Constantes
├── config_flow.py       # UI de configuration (email + mot de passe)
├── coordinator.py       # DataUpdateCoordinator + WebSocket TNG
├── entity.py            # Classe de base partagée (ToniesBaseEntity)
├── media_player.py      # Plateforme Media Player
├── sensor.py            # Batterie, Tonie actif, connexion, bibliothèque + entités par Tonie
├── switch.py            # Switch Sleep (Gen 2 uniquement)
├── select.py            # Sélecteur LED (Gen 1 uniquement)
├── number.py            # Volume, casque, LED, mode sommeil
├── services.yaml        # Déclaration du service get_tonies_list
└── translations/
    ├── en.json
    └── fr.json

blueprints/automation/tonies/
├── volume_bedtime.yaml       # Volume réduit la nuit
├── low_battery_sleep.yaml    # Extinction batterie faible
├── notify_tonie_change.yaml  # Notification changement Tonie
└── sleep_schedule.yaml       # Plage horaire de silence
```

## Licence

Apache 2.0
