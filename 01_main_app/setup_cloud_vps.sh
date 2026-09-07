#!/usr/bin/env bash
# ==============================================================================
# MAESTRO 24/7 Autonomous Cloud Deployment Script (Ubuntu / Debian / AWS EC2)
# ==============================================================================
# This script sets up MAESTRO to run 24/7 in the cloud so your YouTube channel
# continues producing, rendering, analyzing comments, and publishing videos
# EVEN WHEN YOUR PERSONAL LAPTOP IS COMPLETELY POWERED OFF.
# ==============================================================================

set -e

echo "========================================================="
echo "   MAESTRO - 24/7 Autonomous Cloud Daemon Setup"
echo "========================================================="

# 1. Update system packages
sudo apt-get update -y
sudo apt-get install -y curl git ffmpeg libcairo2-dev libpango1.0-dev python3 python3-pip python3-venv

# 2. Check for Docker
if ! command -v docker &> /dev/null; then
    echo "[+] Installing Docker..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    sudo usermod -aG docker $USER
fi

# 3. Create persistent directories
mkdir -p data outputs logs

echo "[+] Directory structure verified."

# 4. Instructions for YouTube Auth in Cloud
echo "---------------------------------------------------------"
echo " IMPORTANT: To connect your YouTube Channel in the Cloud:"
echo " 1. Copy your 'client_secret.json' and 'token.json' to this directory:"
echo "    scp client_secret.json token.json user@your-cloud-ip:$(pwd)/"
echo " 2. Start the 24/7 Autonomous Suite:"
echo "    docker compose up -d --build"
echo " 3. View live 24/7 Autonomous Director logs anytime:"
echo "    docker logs -f maestro-daemon"
echo "---------------------------------------------------------"
echo "✅ Setup script completed. MAESTRO is ready for 24/7 cloud execution!"
