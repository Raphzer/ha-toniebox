#!/bin/bash
# Post-create script for the devcontainer
set -e

echo "📦 Installing tonies-api from GitHub..."
pip install --quiet git+https://github.com/Raphzer/tonies-api.git

echo "📦 Installing dev dependencies..."
pip install --quiet homeassistant colorlog

# ── Symlink du custom_component dans /config ─────────────────────────────────
# /config est le volume partagé avec le container homeassistant
echo "⏳ Waiting for /config to be available (shared volume)..."
timeout=30
while [ ! -d /config ] && [ $timeout -gt 0 ]; do
  sleep 1
  timeout=$((timeout - 1))
done

if [ ! -d /config ]; then
  echo "⚠️  /config not yet available — skipping symlink (run manually later)"
else
  echo "🔗 Symlinking custom_components into HA config..."
  mkdir -p /config/custom_components
  # Supprime un éventuel lien cassé avant de recréer
  rm -f /config/custom_components/tonies
  ln -sf /workspaces/ha-toniebox/custom_components/tonies /config/custom_components/tonies
  echo "   ✅ /config/custom_components/tonies → symlinked"

  echo "📋 Copying blueprints..."
  mkdir -p /config/blueprints/automation/tonies
  cp -rf /workspaces/ha-toniebox/blueprints/automation/tonies/* \
         /config/blueprints/automation/tonies/

  echo "⚙️  Writing configuration.yaml (if absent)..."
  if [ ! -f /config/configuration.yaml ]; then
    cp /workspaces/ha-toniebox/.devcontainer/configuration.yaml /config/configuration.yaml
    echo "   ✅ configuration.yaml copied"
  else
    echo "   ℹ️  configuration.yaml already exists, skipping"
  fi
fi

echo ""
echo "✅ Dev environment ready!"
echo ""
echo "   Home Assistant is starting at → http://localhost:8123"
echo "   Logs HA : docker compose logs -f homeassistant"
echo "   Restart HA : docker compose restart homeassistant"
echo ""