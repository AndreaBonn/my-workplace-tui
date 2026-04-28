#!/usr/bin/env bash
set -euo pipefail

INSTALL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN_LINK="/usr/local/bin/workspace-tui"
REQUIRED_PYTHON_MINOR=11

echo "=== Workspace TUI — Installazione ==="
echo ""

# Check Python version
if ! command -v python3 &> /dev/null; then
    echo "Errore: python3 non trovato. Installa Python 3.${REQUIRED_PYTHON_MINOR}+."
    exit 1
fi

PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
PYTHON_MINOR=$(python3 -c "import sys; print(sys.version_info.minor)")

if [ "$PYTHON_MINOR" -lt "$REQUIRED_PYTHON_MINOR" ]; then
    echo "Errore: Python ${PYTHON_VERSION} trovato, richiesto 3.${REQUIRED_PYTHON_MINOR}+."
    exit 1
fi
echo "[OK] Python ${PYTHON_VERSION}"

# Check uv
if ! command -v uv &> /dev/null; then
    echo "Errore: uv non trovato."
    echo "Installa uv prima di procedere: https://docs.astral.sh/uv/getting-started/installation/"
    exit 1
fi
echo "[OK] uv $(uv --version)"

# Install dependencies
echo "Installazione dipendenze..."
cd "$INSTALL_DIR"
uv sync --all-extras
echo "[OK] Dipendenze installate"

# Create credentials directory
mkdir -p "$INSTALL_DIR/credentials"
echo "[OK] Directory credentials/ pronta"

# Copy .env.example to .env if not exists
if [ ! -f "$INSTALL_DIR/.env" ]; then
    cp "$INSTALL_DIR/.env.example" "$INSTALL_DIR/.env"
    echo "[OK] .env creato da .env.example — configuralo prima di avviare"
else
    echo "[OK] .env già presente"
fi

# Create log directory
mkdir -p "$HOME/.local/share/workspace-tui/logs"
echo "[OK] Directory log pronta"

# Create launcher script
LAUNCHER_CONTENT="#!/usr/bin/env bash
cd \"${INSTALL_DIR}\"
exec uv run python -m workspace_tui \"\$@\"
"

echo "Creazione launcher in ${BIN_LINK} (richiede sudo)..."
echo "$LAUNCHER_CONTENT" | sudo tee "$BIN_LINK" > /dev/null
sudo chmod +x "$BIN_LINK"
echo "[OK] Comando 'workspace-tui' disponibile globalmente"

echo ""
echo "=== Installazione completata ==="
echo ""
echo "Prossimi passi:"
echo "  1. Configura le credenziali Google in credentials/client_secret.json"
echo "  2. Modifica .env con i tuoi dati (Jira opzionale)"
echo "  3. Avvia con: workspace-tui"
