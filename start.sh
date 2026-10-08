#!/usr/bin/env bash

# ==============================================================================
# Comic Strip Animator (CSA) - Application Launcher
# ==============================================================================

# HOOK_CLEANUP_TRAP: Runs automatically on Ctrl+C or script termination
cleanup() {
    echo -e "\n- - - STOP - - - - - - - - - - - - - - - - - - - - -"
    deactivate 2>/dev/null || true
}

# Intercept SIGINT (Ctrl+C), SIGTERM, and EXIT signals
trap cleanup SIGINT SIGTERM EXIT

# HOOK_RUN_SETUP_IF_NO_VENV: Trigger setup.sh automatically if environment doesn't exist
if [ ! -d "./venv" ]; then
    echo -e "- - - INSTALL - - - - - - - - - - - - - - - - - - - - -"
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

echo -e "- - - START - - - - - - - - - - - - - - - - - - - - - -"
#sudo fuser -k 8080/tcp

# Ensure PATH includes uv binary location
export PATH="$HOME/.local/bin:$PATH"
export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"

python3 src/csa_main.py

exit 0
