#!/usr/bin/env bash
# ==============================================================================
# Comic Strip Animator (CSA) - Automated Setup & Environment Installer
# ==============================================================================

set -e

# HOOK_COLOR_FORMATTING: Visual indicators for terminal logs
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# HOOK_GIT_UPDATE_CHECK: Detect Git repo and offer updates
if [ -f ".git/config" ]; then
    echo -e "${BLUE}[Git] Cloned repository detected. Checking for remote updates...${NC}"
    git fetch origin
    
    LOCAL_HASH=$(git rev-parse HEAD)
    REMOTE_HASH=$(git rev-parse @{u} 2>/dev/null || echo "$LOCAL_HASH")
    
    if [ "$LOCAL_HASH" != "$REMOTE_HASH" ]; then
        echo -e "${YELLOW}[Git] A new update is available on remote repository.${NC}"
        read -p "Would you like to pull the latest changes? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            git pull
            echo -e "${GREEN}[Git] Successfully updated repository code!${NC}"
        fi
    else
        echo -e "${GREEN}[Git] Repository is up-to-date.${NC}"
    fi
fi

echo -e "${BLUE}[1/6] Checking System Packages...${NC}"

# HOOK_SYSTEM_APT_INSTALL: Install system binaries if apt-get is available
if command -v apt-get &> /dev/null; then
    echo -e "${GREEN}Detected apt-get. Updating package lists and installing dependencies...${NC}"
    sudo apt-get update -y
    sudo apt-get install -y \
        python3 \
        python3-pip \
        python3-venv \
        ffmpeg \
        tesseract-ocr \
        tesseract-ocr-eng \
        tesseract-ocr-fra \
        poppler-utils \
        git \
        curl \
        wget \
        libgl1 \
        libglx-mesa0 \
        libglib2.0-0
else
    echo -e "${YELLOW}Notice: apt-get not found. Ensuring essential binaries exist...${NC}"
    
    # HOOK_BINARY_FALLBACK_CHECK: Fallback verification for non-apt systems
    for tool in ffmpeg tesseract git curl; do
        if ! command -v $tool &> /dev/null; then
            echo -e "${RED}Error: Required tool '$tool' is missing. Please install it manually.${NC}"
            exit 1
        fi
    done
fi

echo -e "${BLUE}[Checking External Tools & Services]${NC}"

# Check for local ComfyUI
if curl -s http://localhost:8188/system_stats &>/dev/null; then
    echo -e "${GREEN}[✓] Local ComfyUI server detected at http://localhost:8188${NC}"
else
    echo -e "${YELLOW}[!] ComfyUI is not running on port 8188. (Image-to-Video generation will use API fallbacks or default profiles)${NC}"
fi

# Check for Tesseract OCR
if command -v tesseract &> /dev/null; then
    echo -e "${GREEN}[✓] Tesseract OCR installed.${NC}"
else
    echo -e "${RED}[✗] Tesseract OCR missing.${NC}"
fi

# Check for FFmpeg
if command -v ffmpeg &> /dev/null; then
    echo -e "${GREEN}[✓] FFmpeg installed.${NC}"
else
    echo -e "${RED}[✗] FFmpeg missing.${NC}"
fi

echo -e "${BLUE}[2/6] Ensuring 'uv' Is Installed...${NC}"

# HOOK_INSTALL_UV: Install uv standalone if missing for ultra-fast venv/pip operations
if ! command -v uv &> /dev/null; then
    echo -e "${GREEN}Installing 'uv' package manager...${NC}"
    curl -LsSf https://astral.sh/uv/install.sh | sh
    # Source uv binary path for current session
    export PATH="$HOME/.local/bin:$PATH"
fi

echo -e "${BLUE}[3/6] Creating Virtual Environment with 'uv'...${NC}"

# HOOK_CREATE_VENV_UV: Fast environment creation
if [ ! -d "venv" ]; then
    uv venv venv --python 3.13 --seed
    echo -e "${GREEN}Virtual environment 'venv' created.${NC}"
fi

# Activate virtual environment
source venv/bin/activate

echo -e "${BLUE}[4/6] Installing PyTorch with CUDA Support...${NC}"

# HOOK_UV_NETWORK_TWEAKS: Increase timeout and limit concurrency to prevent timeouts & extraction errors
export UV_HTTP_TIMEOUT=300
export UV_CONCURRENT_DOWNLOADS=2

# HOOK_PYTORCH_INSTALL: Install PyTorch for AI/ML features (SAM 2, LaMa, Paddle)
uv pip install torch torchvision \
    --index-url https://download.pytorch.org/whl/cu121

echo -e "${BLUE}[5/6] Installing Dependencies from requirements.txt...${NC}"

if [ -f "requirements.txt" ]; then
    # Ensure overrides.txt exists to patch simple-lama-inpainting's Pillow constraint
    echo "pillow>=10.2.0" > overrides.txt

    uv pip install -r requirements.txt --override overrides.txt

    # Explicitly install OCR engines (PaddleOCR & EasyOCR)
    uv pip install paddlepaddle paddleocr easyocr
else
    echo -e "${RED}Error: requirements.txt not found!${NC}"
fi

echo -e "${BLUE}[6/6] Preparing Directory Structure & Permissions...${NC}"

# HOOK_CREATE_RUNTIME_FOLDERS: Prepare initial asset folders
mkdir -p projects/project_001/assets/raw
mkdir -p projects/project_001/assets/panels
mkdir -p projects/project_001/assets/inpainted
mkdir -p projects/project_001/assets/elements
mkdir -p projects/project_001/assets/audio
mkdir -p projects/project_001/renders/plans
mkdir -p projects/project_001/renders/sequences

chmod +x start.sh

# HOOK_DEACTIVATE_VENV: Deactivate virtualenv before exiting setup
deactivate 2>/dev/null || true

echo -e "${GREEN}======================================================================${NC}"
echo -e "${GREEN}  Comic Strip Animator (CSA) Workbench Setup Complete!               ${NC}"
echo -e "${GREEN}======================================================================${NC}"

