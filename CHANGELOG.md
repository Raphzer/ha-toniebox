# Changelog

All notable changes to this project will be documented in this file.

## [0.1.1] - 2026-03-18

### Fixed
- Sorted `manifest.json` keys per hassfest requirements (`domain`, `name`, then alphabetical)
- Applied ruff formatting to all integration files

## [0.1.0] - 2026-03-18

### Added

#### Plateformes
- **Media Player** par Toniebox — volume, état (playing/idle/off), turn off via sleep (Gen 2), image du Tonie actif
- **Sensor batterie** — niveau batterie en temps réel via WebSocket (Gen 2)
- **Sensor Tonie actif** — nom et image URL du Tonie posé (Gen 2)
- **Sensor connexion** — état online/offline en temps réel (Gen 2)
- **Switch Sleep** — extinction immédiate par commande WebSocket (Gen 2)
- **Select LED** — luminosité on/dimmed/off (Gen 1)
- **Number volume enceinte** — 25–100% par pas de 1% (Gen 2) ; snappé à 25/50/75/100% (Gen 1, via media player)
- **Number volume casque** — 25–100% par pas de 1% (Gen 2) ; snappé à 25/50/75/100% (Gen 1)
- **Number luminosité LED** — 0–100% par pas de 1% via light ring (Gen 2)
- **Number volume mode sommeil** — 25–100% par pas de 1% (Gen 2)
- **Number volume casque mode sommeil** — 25–100% par pas de 1% (Gen 2)
- **Number luminosité LED mode sommeil** — 0–100% par pas de 1% (Gen 2)

#### Appareil Tonies Library
- Appareil virtuel regroupant toutes les entités liées aux Tonies possédés
- Sensor de comptage (contenu + créatifs)
- Un sensor par Tonie contenu (titre, image, série, cover URL)
- Un sensor par Tonie créatif (nom, image, chapitres, live)

#### Blueprints
- `volume_bedtime.yaml` — Réduction du volume la nuit, restauration le matin
- `low_battery_sleep.yaml` — Extinction automatique sur batterie faible (Gen 2)
- `notify_tonie_change.yaml` — Notification lors du changement de Tonie (Gen 2)
- `sleep_schedule.yaml` — Plage horaire de silence configurable avec extinction immédiate si rallumée (Gen 2)

#### Service
- `tonies.get_tonies_list` — émet l'événement `tonies_list_result` avec la liste complète des Tonies (contournement de la limite 16 KB des attributs HA)

#### Général
- Config flow email + mot de passe avec gestion d'erreurs (auth vs connexion)
- Support dual-mode : Classic (polling 5 min) et TNG/Gen 2 (WebSocket temps réel)
- Traductions français et anglais
- CI : lint Ruff + validation Hassfest/HACS
