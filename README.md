# ha-toniebox

Intégration Home Assistant pour les **Toniebox** via [HACS](https://hacs.xyz/), basée sur la librairie [`tonies-api`](https://github.com/Raphzer/tonies-api).

## Fonctionnalités

- Découverte automatique de toutes vos Tonieboxes et Tonies
- **Media Player** par Toniebox (volume, état lecture, Tonie actif)
- **Sensor batterie** en temps réel (Toniebox Gen 2 uniquement)
- **Sensor Tonie actif** (nom + image URL) (Toniebox Gen 2 uniquement)
- **Sensor connexion** online / offline (Toniebox Gen 2 uniquement)
- **Sensor bibliothèque** : nombre total de Tonies possédés
- **Switch Sleep** — extinction immédiate (Toniebox Gen 2 uniquement)
- **Sélecteur LED** — luminosité on / dimmed / off (toutes boxes)
- **Volume casque** — réglage du volume max casque (toutes boxes)
- **3 Blueprints** d'automations prêts à l'emploi
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

| Entité | Type | Classic | Gen 2 | Description |
|--------|------|:-------:|:-----:|-------------|
| `media_player.toniebox_*` | Media Player | ✓ | ✓ | Volume, état, turn off |
| `sensor.toniebox_*_battery` | Sensor | — | ✓ | Niveau batterie (%) |
| `sensor.toniebox_*_active_tonie` | Sensor | — | ✓ | Tonie actuellement posé |
| `sensor.toniebox_*_connection` | Sensor | — | ✓ | online / offline |
| `switch.toniebox_*_sleep` | Switch | — | ✓ | Extinction immédiate |
| `select.toniebox_*_led` | Select | ✓ | ✓ | Luminosité LED (on/dimmed/off) |
| `number.toniebox_*_headphone_volume` | Number | ✓ | ✓ | Volume max casque (%) |

### Globale (par compte)

| Entité | Type | Description |
|--------|------|-------------|
| `sensor.tonies_library` | Sensor | Nombre total de Tonies possédés (contenu + créatifs) |

> **Note :** pour récupérer la liste complète des Tonies, utilisez le service `tonies.get_tonies_list` qui émet un événement `tonies_list_result` (contournement de la limite 16 KB des attributs HA).

## Blueprints

Importez les blueprints depuis `blueprints/automation/tonies/` :

| Blueprint | Description | Prérequis |
|-----------|-------------|-----------|
| `volume_bedtime.yaml` | Réduit le volume la nuit, le restaure le matin | Toutes boxes |
| `low_battery_sleep.yaml` | Éteint la box quand la batterie est faible | Gen 2 uniquement |
| `notify_tonie_change.yaml` | Notification quand un Tonie est changé | Gen 2 uniquement |

## Développement

Ce projet utilise un **Dev Container VSCode** avec Home Assistant préconfiguré.

```bash
git clone https://github.com/Raphzer/ha-toniebox
code ha-toniebox
# VSCode propose d'ouvrir dans le container → Accepter
# HA démarre sur http://localhost:8123
```

### Scripts

```bash
scripts/setup    # Installe les dépendances Python
scripts/lint     # Ruff format + check avec autofix
scripts/develop  # Démarre HA local en mode debug sur le port 8123
```

### Structure

```
custom_components/tonies/
├── __init__.py          # Setup / unload + service get_tonies_list
├── manifest.json        # Métadonnées HACS
├── const.py             # Constantes
├── config_flow.py       # UI de configuration (email + mot de passe)
├── coordinator.py       # DataUpdateCoordinator + WebSocket TNG
├── entity.py            # Classe de base partagée (ToniesBaseEntity)
├── media_player.py      # Plateforme Media Player
├── sensor.py            # Batterie, Tonie actif, connexion, bibliothèque
├── switch.py            # Switch Sleep (Gen 2 uniquement)
├── select.py            # Sélecteur LED (toutes boxes)
├── number.py            # Volume casque (toutes boxes)
├── services.yaml        # Déclaration du service get_tonies_list
└── translations/
    ├── en.json          # Traduction anglaise
    └── fr.json          # Traduction française
```

## Licence

Apache 2.0
