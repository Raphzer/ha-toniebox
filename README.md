# hacs-tonies

Intégration Home Assistant pour les **Toniebox** via [HACS](https://hacs.xyz/), basée sur la librairie [`tonies-api`](https://github.com/Raphzer/tonies-api).

## Fonctionnalités

- 📦 **Liste automatique** de toutes vos Tonieboxes et Tonies
- 🎵 **Media Player** par Toniebox (volume, état lecture, Tonie actif)
- 🔋 **Sensor batterie** (temps réel via WebSocket pour gen 2)
- 🧸 **Sensor Tonie actif** (nom + image URL)
- 🌐 **Sensor connexion** (online / offline)
- 😴 **Switch Sleep** (éteindre la box)
- 🤖 **3 Blueprints** d'automations prêts à l'emploi

## Prérequis

- Home Assistant 2026.1+
- HACS installé
- Un compte [mytonies.com](https://mytonies.com)
- Pour les events temps réel : une Toniebox **génération 2** (supportant le WebSocket)

## Installation via HACS

1. Dans HACS → **Intégrations** → menu ⋮ → *Dépôts personnalisés*
2. Ajouter l'URL de ce dépôt, catégorie **Integration**
3. Chercher **Tonies** et installer
4. Redémarrer Home Assistant

## Configuration

1. **Paramètres** → **Appareils & Services** → **Ajouter une intégration** → chercher *Tonies*
2. Entrer votre e-mail et mot de passe mytonies.com
3. Les Tonieboxes et entités sont créées automatiquement

## Entités créées par Toniebox

| Entité | Type | Description |
|--------|------|-------------|
| `media_player.toniebox_*` | Media Player | Contrôle volume, état, turn off |
| `sensor.toniebox_*_battery` | Sensor | Niveau batterie (%) |
| `sensor.toniebox_*_active_tonie` | Sensor | Tonie actuellement posé |
| `sensor.toniebox_*_connection` | Sensor | online / offline |
| `switch.toniebox_*_sleep` | Switch | Extinction immédiate |

## Blueprints

Importez les blueprints depuis `blueprints/automation/tonies/` :

- **`volume_bedtime.yaml`** — Réduit le volume la nuit, le restaure le matin
- **`low_battery_sleep.yaml`** — Éteint la box quand la batterie est faible
- **`notify_tonie_change.yaml`** — Notification quand un Tonie est changé

## Développement

Ce projet utilise un **Dev Container VSCode** avec Home Assistant préconfiguré.

```bash
git clone https://github.com/Raphzer/ha-toniebox
code ha-toniebox
# VSCode propose d'ouvrir dans le container → Accepter
# HA démarre sur http://localhost:8123
```

### Structure

```
custom_components/tonies/
├── __init__.py          # Setup / unload
├── manifest.json        # Métadonnées HACS
├── const.py             # Constantes
├── config_flow.py       # UI de configuration
├── coordinator.py       # DataUpdateCoordinator + WebSocket
├── entity.py            # Classe de base partagée
├── media_player.py      # Plateforme Media Player
├── sensor.py            # Plateformes Sensor (batterie, tonie, online)
└── switch.py            # Plateforme Switch (sleep)
```

## Licence

Apache 2.0
