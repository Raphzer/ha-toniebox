# Documentation — Intégration Tonies pour Home Assistant

## Sommaire

1. [Vue d'ensemble](#1-vue-densemble)
2. [Architecture](#2-architecture)
3. [Support matériel](#3-support-matériel)
4. [Flux de données](#4-flux-de-données)
5. [Entités](#5-entités)
6. [Appareil Tonies Library](#6-appareil-tonies-library)
7. [Services](#7-services)
8. [Blueprints](#8-blueprints)
9. [Installation et configuration](#9-installation-et-configuration)
10. [Développement](#10-développement)

---

## 1. Vue d'ensemble

L'intégration `tonies` connecte Home Assistant à votre compte [mytonies.com](https://mytonies.com). Elle découvre automatiquement vos Tonieboxes, les Tonies figurines de votre bibliothèque et expose des entités pour les piloter.

**Caractéristiques principales :**

- Découverte automatique des Tonieboxes et des Tonies
- Contrôle du volume, de la LED et du mode sommeil
- Données temps réel pour la Gen 2 (WebSocket)
- Bibliothèque complète : une entité par Tonie possédé
- 4 blueprints d'automations prêts à l'emploi

---

## 2. Architecture

### Patron d'intégration

| Propriété | Valeur |
|---|---|
| Domaine | `tonies` |
| Classe IoT | `cloud_push` |
| Authentification | Email + mot de passe (mytonies.com) |
| Identifiant unique | Email en minuscules |
| Version HA minimum | 2026.1.0 |
| Dépendance | `tonies-api>=0.1.4` |

### Fichiers principaux

```
custom_components/tonies/
├── __init__.py        # Setup/unload de l'entrée, service get_tonies_list
├── manifest.json      # Métadonnées HACS
├── const.py           # Toutes les constantes
├── config_flow.py     # Flux de configuration (UI email + mot de passe)
├── coordinator.py     # ToniesCoordinator — polling + WebSocket
├── entity.py          # ToniesBaseEntity — base partagée
├── media_player.py    # Plateforme Media Player (une entité par box)
├── sensor.py          # Capteurs batterie, tonie actif, connexion, chapitre, bibliothèque
├── button.py          # Bouton Sleep Now (Gen 2 uniquement)
├── select.py          # Sélecteur LED (Gen 1 uniquement)
├── number.py          # Sliders volume et LED
├── services.yaml      # Déclaration du service get_tonies_list
└── translations/
    ├── en.json
    └── fr.json
```

---

## 3. Support matériel

L'intégration gère deux générations de Tonieboxes avec des capacités différentes :

| Fonctionnalité | Gen 1 (Classic) | Gen 2 |
|---|:---:|:---:|
| Méthode de mise à jour | Polling REST (5 min) | WebSocket temps réel |
| Capteur batterie | — | ✓ |
| Capteur Tonie actif | — | ✓ |
| Capteur connexion | — | ✓ |
| Capteur chapitre | — | ✓ |
| Bouton Sleep Now | — | ✓ |
| Volume enceinte | 25/50/75/100% (snappé) | 25–100% (pas 1%) |
| LED | Sélecteur (on/dimmed/off) | Slider 0–100% |
| Volume casque | 25/50/75/100% (snappé) | 25–100% (pas 1%) |
| Volume mode sommeil | — | 25–100% (pas 1%) |
| Volume casque mode sommeil | — | 25–100% (pas 1%) |
| Luminosité LED mode sommeil | — | 0–100% (pas 1%) |

La distinction Gen 1 / Gen 2 est gérée par la propriété `is_tng` sur le modèle `Toniebox` de la librairie (détectée via la présence de `"tngSettings"` dans la liste `features` retournée par l'API).

---

## 4. Flux de données

```
┌─────────────────────────────────────────────────────┐
│                 mytonies.com Cloud                  │
│                                                     │
│   REST API (GraphQL)        WebSocket (MQTT/WSS)    │
└────────────┬────────────────────────┬───────────────┘
             │                        │
             ▼                        ▼
┌─────────────────────────────────────────────────────┐
│              ToniesCoordinator                      │
│                                                     │
│  _async_update_data()         _on_ws_event()        │
│  → boxes (REST, 5 min)        → ws_state par box    │
│  → households_with_tonies     online / battery /    │
│                               tonie_id / chapter…   │
│                                                     │
│  ToniesData                                         │
│  ├── boxes: list[Toniebox]                          │
│  ├── households_with_tonies: dict[id, HWT]          │
│  └── ws_state: dict[box_id, dict]                   │
└──────────────┬──────────────────────────────────────┘
               │ async_set_updated_data()
               ▼
┌─────────────────────────────────────────────────────┐
│         Entités HA (state machine)                  │
│  MediaPlayer / Sensor / Button / Select / Number    │
└─────────────────────────────────────────────────────┘
```

### Connexion WebSocket

Pour les Tonieboxes Gen 2, le coordinateur maintient une connexion WebSocket persistante via la librairie `tonies-api`. Les événements MQTT reçus sont parsés par `_on_ws_event()` selon leur topic :

| Topic (suffix) | Données mises à jour |
|---|---|
| `online-state` | `ws_state["online"]` — `connected` ou `online` → True |
| `metrics/battery` | `ws_state["battery"]`, `ws_state["charging"]` |
| `playback/state` | `ws_state["tonie_id"]`, `tonie_name`, `tonie_image`, `chapter`, `chapter_until_ms`, `chapter_duration` |
| `metrics/headphones` | `ws_state["headphones"]` |

Le champ `tonie` dans `playback/state` peut être :
- Un **dict** `{id, name, imageUrl}` — format complet
- Une **string** — l'UID NFC du chip (format compact Gen 2) → lookup dans la bibliothèque locale
- `null` — plus de Tonie posé

---

## 5. Entités

### 5.1 Media Player (`media_player.*`)

Une entité par Toniebox. C'est l'entité principale visible dans le tableau de bord.

| Propriété | Gen 1 | Gen 2 |
|---|---|---|
| État | Toujours `idle` | `off` (hors ligne), `idle`, `playing` |
| Volume | Slider snappé 25/50/75/100% | Slider libre 25–100% |
| Turn off | — | Commande sleep WebSocket |
| Image | Image de la box | Image du Tonie actif (si lecture) |
| `media_title` | — | Nom du Tonie actif |

**Attributs :**

| Attribut | Description |
|---|---|
| `tng` | `true` si Gen 2 |
| `household_id` | Identifiant du foyer |
| `mac_address` | Adresse MAC de la box |
| `tonie_id` | UID du Tonie actif (Gen 2) |
| `tonie_name` | Nom du Tonie actif (Gen 2) |
| `tonie_image` | URL de l'image du Tonie (Gen 2) |
| `headphones_connected` | Casque branché (Gen 2) |

---

### 5.2 Capteur Tonie actif (`sensor.*_active_tonie`) — Gen 2

Affiche le **nom du Tonie** actuellement posé sur la box. L'**icône de l'entité** est remplacée par l'image du Tonie en cours de lecture.

**Attributs :**

| Attribut | Description |
|---|---|
| `tonie_id` | UID NFC du chip |
| `tonie_image_url` | URL de l'image |
| `chapter` | Numéro du chapitre en cours |
| `chapter_remaining_s` | Secondes restantes sur le chapitre (calculé depuis `chapterUntilMs`) |
| `chapter_duration_s` | Durée totale du chapitre (secondes) |

---

### 5.3 Capteur batterie (`sensor.*_battery`) — Gen 2

Affiche le niveau de batterie en % (mis à jour en temps réel via WebSocket).

**Attributs :**

| Attribut | Description |
|---|---|
| `charging` | `true` si en charge |

---

### 5.4 Capteur connexion (`sensor.*_connection`) — Gen 2

Affiche l'état de connexion de la box : `online` ou `offline`.

Les valeurs WebSocket `online` et `connected` sont toutes deux traitées comme `online`.

---

### 5.5 Capteur chapitre (`sensor.*_chapter`) — Gen 2

Affiche le **numéro du chapitre** en cours de lecture.

**Attributs :**

| Attribut | Description |
|---|---|
| `chapter_duration_s` | Durée du chapitre en secondes |
| `chapter_remaining_s` | Secondes restantes (snapshot au moment de l'événement WebSocket) |

> **Note :** `chapter_remaining_s` est calculé à partir du timestamp absolu `chapterUntilMs` reçu par WebSocket. La valeur est juste au moment où l'entité est lue, mais elle n'est pas mise à jour en continu — elle reflète la valeur au dernier événement WebSocket reçu.

---

### 5.6 Bouton Sleep Now (`button.*_sleep_now`) — Gen 2

Appuyer sur ce bouton envoie immédiatement une commande d'extinction à la Toniebox via WebSocket.

---

### 5.7 Sélecteur LED (`select.*_led`) — Gen 1 uniquement

Contrôle la luminosité de la LED de la Toniebox Gen 1.

**Options :** `on` · `dimmed` · `off`

> Pour les Tonieboxes Gen 2, le contrôle LED se fait via le slider **LED Brightness**.

---

### 5.8 Sliders de volume et luminosité (`number.*`)

| Entité | Box | Plage | Pas | Commande API |
|---|---|---|---|---|
| Max Volume | Gen 2 | 25–100% | 1% | `set_max_volume` |
| Max Headphone Volume | Toutes | 25–100% | 1% (Gen 2) / 25% (Gen 1) | `set_max_headphone_volume` |
| LED Brightness | Gen 2 | 0–100% | 1% | `set_lightring_brightness` |
| Bedtime Max Volume | Gen 2 | 25–100% | 1% | `set_bedtime_max_volume` |
| Bedtime Max Headphone Volume | Gen 2 | 25–100% | 1% | `set_bedtime_headphone_max_volume` |
| Bedtime LED Brightness | Gen 2 | 0–100% | 1% | `set_bedtime_lightring_brightness` |

> **Gen 1 — volume snappé :** pour les Tonieboxes Gen 1, toute valeur de volume est arrondie au palier le plus proche parmi `[25, 50, 75, 100]` avant envoi à l'API.

---

## 6. Appareil Tonies Library

Un appareil virtuel **Tonies Library** est créé par compte (config entry). Il regroupe :

- **`sensor.tonies_library_count`** : nombre total de Tonies possédés avec attributs `content_count` et `creative_count`
- **Un sensor par Tonie contenu** (figurine du catalogue officiel)
- **Un sensor par Tonie créatif** (figurine enregistrable)

### Sensor Tonie contenu

| Propriété | Valeur |
|---|---|
| État | Titre du Tonie |
| Image | Artwork du Tonie (`image_url`) |
| `tonie_id` | Identifiant API |
| `cover_url` | URL de la pochette |
| `series` | Nom de la série |

### Sensor Tonie créatif

| Propriété | Valeur |
|---|---|
| État | Nom du Tonie créatif |
| Image | Image du Tonie |
| `tonie_id` | Identifiant API |
| `live` | `true` si le mode live est activé |
| `chapters` | Nombre de chapitres enregistrés |

---

## 7. Services

### `tonies.get_tonies_list`

Émet l'événement `tonies_list_result` sur le bus d'événements HA avec la liste complète de tous les Tonies.

**Pourquoi un service plutôt que des attributs ?** Les attributs HA sont limités à 16 KB. Une bibliothèque de 50+ Tonies dépasse facilement cette limite.

**Payload de l'événement :**

```yaml
total: 47
content_count: 45
creative_count: 2
tonies:
  - id: "abc123"
    name: "Le Petit Prince"
    image_url: "https://..."
    cover_url: "https://..."
    household_id: "hh_xyz"
    type: "content"
  - id: "def456"
    name: "Mon Tonie Créatif"
    image_url: "https://..."
    household_id: "hh_xyz"
    type: "creative"
    live: false
```

**Utilisation en automation :**

```yaml
action:
  - service: tonies.get_tonies_list

trigger:
  - platform: event
    event_type: tonies_list_result
```

---

## 8. Blueprints

### `volume_bedtime.yaml` — Volume mode nuit

Réduit le volume de la Toniebox à une heure configurable et le restaure le matin.

**Inputs :**
- `media_player` : la Toniebox concernée
- `sleep_time` : heure de réduction (défaut 21h00)
- `wake_time` : heure de restauration (défaut 7h00)
- `night_volume` : volume nocturne (défaut 25%)
- `day_volume` : volume de jour (défaut 75%)

---

### `low_battery_sleep.yaml` — Extinction batterie faible (Gen 2)

Éteint automatiquement la Toniebox lorsque la batterie descend sous un seuil.

**Inputs :**
- `battery_sensor` : capteur batterie de la box
- `sleep_button` : bouton Sleep Now de la même box
- `threshold` : seuil de déclenchement (défaut 15%)
- `notify` : activer les notifications (défaut oui)
- `notify_target` : service de notification

---

### `notify_tonie_change.yaml` — Notification changement Tonie (Gen 2)

Envoie une notification lorsque le Tonie posé sur la box change.

**Inputs :**
- `tonie_sensor` : capteur Active Tonie de la box
- `notify_target` : service de notification

---

### `sleep_schedule.yaml` — Plage horaire de silence (Gen 2)

Éteint la Toniebox en dehors d'une plage horaire autorisée. Si la box est allumée pendant la plage de silence, elle est éteinte immédiatement.

**Inputs :**
- `media_player` : le media player de la Toniebox
- `sleep_button` : le bouton Sleep Now
- `sleep_time` : début du silence (défaut 21h30)
- `wake_time` : fin du silence (défaut 7h00)

> La plage gère le **chevauchement minuit** : si `sleep_time > wake_time`, la plage s'étend de `sleep_time` à `wake_time` le lendemain.

---

## 9. Installation et configuration

### Via HACS

1. HACS → **Intégrations** → menu ⋮ → *Dépôts personnalisés*
2. URL : `https://github.com/Raphzer/ha-toniebox`, catégorie **Integration**
3. Chercher **Tonies** → Installer
4. Redémarrer Home Assistant

### Configuration

1. **Paramètres** → **Appareils & Services** → **Ajouter une intégration** → *Tonies*
2. Entrer l'**email** et le **mot de passe** mytonies.com
3. Les appareils et entités sont créés automatiquement

### Erreurs de configuration

| Erreur | Cause | Solution |
|---|---|---|
| `invalid_auth` | Identifiants incorrects | Vérifier email/mot de passe |
| `cannot_connect` | API inaccessible | Vérifier la connexion internet |

Si la configuration échoue pour cause réseau, HA relance automatiquement l'initialisation (`ConfigEntryNotReady`).

---

## 10. Développement

### Prérequis

- Python 3.14
- Home Assistant 2026.1+
- `tonies-api>=0.1.4`

### Scripts

```bash
scripts/setup    # pip install -r requirements.txt
scripts/lint     # ruff format + ruff check --fix
scripts/develop  # Lance HA local sur http://localhost:8123 avec debug logging
```

### Ajouter une nouvelle plateforme

1. Créer `custom_components/tonies/<platform>.py` héritant de `ToniesBaseEntity`
2. Ajouter le nom de la plateforme dans `PLATFORMS` (`const.py`)
3. Conditionner les fonctionnalités Gen 2 avec `self.is_tng`
4. Implémenter `async_setup_entry` (pattern standard HA)
5. Ajouter les clés de traduction dans `strings.json`, `translations/en.json`, `translations/fr.json`

### Ajouter une commande au coordinateur

1. Ajouter une méthode `async` dans `ToniesCoordinator` (`coordinator.py`)
2. Appeler la méthode correspondante du client `tonies-api`
3. Appeler `self.async_request_refresh()` si une mise à jour du state est nécessaire

### Contraintes importantes

- **SSL en thread pool** : la création du contexte SSL et la lecture des certificats certifi doivent se faire via `hass.async_add_executor_job` pour ne pas bloquer la boucle asyncio
- **Volume Gen 1 snappé** : toujours arrondir aux paliers `[25, 50, 75, 100]` avant d'appeler l'API
- **Bouton Sleep momentané** : utiliser la plateforme `button` (pas `switch`) — l'action est instantanée, pas d'état persistant
- **`strings.json` est en français** (langue par défaut) — garder `en.json` et `fr.json` synchronisés
- **Erreurs config_flow** : `TonieAuthError` (singular) → `InvalidAuth` · tout autre → `CannotConnect`
- **`ToniesLibrarySensor`** n'étend pas `CoordinatorEntity` — c'est un `SensorEntity` plain qui s'abonne manuellement dans `async_added_to_hass`
- **`chapter_remaining_s`** est un snapshot calculé au moment de la lecture de l'attribut — pas mis à jour en continu

### CI / Validation

| Workflow | Déclencheur | Jobs |
|---|---|---|
| `lint.yml` | push main, PRs | Ruff format + check |
| `validate.yml` | quotidien, dispatch, changements main | Hassfest + HACS validation |
