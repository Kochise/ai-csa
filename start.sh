#!/usr/bin/env bash
# ==============================================================================
# Comic Strip Animator (CSA) - Application Launcher
# ==============================================================================

# HOOK_CLEANUP_TRAP: Runs automatically on Ctrl+C or script termination
cleanup() {
    echo -e "\n- - - STOPPING SERVER & DEACTIVATING VENV - - - - - - -"
    deactivate 2>/dev/null || true
    echo "Done. Goodbye!"
    exit 0
}

# Intercept SIGINT (Ctrl+C), SIGTERM, and EXIT signals
trap cleanup SIGINT SIGTERM EXIT

# HOOK_RUN_SETUP_IF_NO_VENV: Trigger setup.sh automatically if environment doesn't exist
if [ ! -d "./venv" ]; then
    echo -e "- - - VENV MISSING: RUNNING SETUP.SH FIRST - - - - - - -"
    if [ -f "./setup.sh" ]; then
        chmod +x ./setup.sh
        ./setup.sh
    else
        echo "Error: setup.sh not found!"
        exit 1
    fi
fi

echo -e "- - - ACTIVATE - - - - - - - - - - - - - - - - - - - - -"
source venv/bin/activate

# Optional: Ensure PATH includes uv binary location
export PATH="$HOME/.local/bin:$PATH"

if [ -f "./.git/config" ]; then
    echo -e "- - - FETCH & PULL - - - - - - - - - - - - - - - - - - -"
    git fetch origin
    git pull
fi

echo -e "- - - SYNC REQUIREMENTS - - - - - - - - - - - - - - - - -"
if command -v uv &> /dev/null; then
    uv pip install -r requirements.txt
else
    pip install -r requirements.txt
fi

echo -e "- - - LAUNCHING CSA WORKBENCH - - - - - - - - - - - - -"
export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"
python3 src/csa_main.py
