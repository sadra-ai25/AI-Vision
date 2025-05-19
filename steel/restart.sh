#!/usr/bin/env bash
set -euo pipefail

# ========== Configuration ==========
# Name of the systemd service (arbitrary)
SERVICE_NAME="steel-service"

# Directory of your project (where docker-compose.yml is located)
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Path where the restart helper script will be installed
RESTART_SCRIPT="/usr/local/bin/${SERVICE_NAME}.sh"

# Path for the systemd unit file
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"

# ========== 1. Create the restart helper script ==========
cat <<EOF | sudo tee "${RESTART_SCRIPT}" > /dev/null
#!/usr/bin/env bash

# Move into the project directory
cd "${PROJECT_DIR}"

# If you use a .env file, uncomment the following line to export its variables:
# export \$(grep -v '^#' .env | xargs)

# Bring the compose stack down and then back up in detached mode
docker compose down
docker compose up -d
EOF

# Make the helper script executable
sudo chmod +x "${RESTART_SCRIPT}"
echo "✔️  Created restart helper script at ${RESTART_SCRIPT}"

# ========== 2. Create the systemd Service unit ==========
cat <<EOF | sudo tee "${SERVICE_FILE}" > /dev/null
[Unit]
Description=Docker Compose project in ${PROJECT_DIR}
After=docker.service
Requires=docker.service

[Service]
Type=simple
ExecStart=/usr/bin/docker compose -f ${PROJECT_DIR}/docker-compose.yml up
ExecStop=/usr/bin/docker compose -f ${PROJECT_DIR}/docker-compose.yml down
WorkingDirectory=${PROJECT_DIR}
Restart=always
RestartSec=10
EnvironmentFile=${PROJECT_DIR}/.env

[Install]
WantedBy=multi-user.target
EOF

echo "✔️  Created systemd service unit at ${SERVICE_FILE}"

# ========== 3. Remove any existing timer (if present) ==========
TIMER_FILE="/etc/systemd/system/${SERVICE_NAME}.timer"
if [ -f "${TIMER_FILE}" ]; then
    sudo systemctl disable "${SERVICE_NAME}.timer" || true
    sudo rm "${TIMER_FILE}"
    echo "✔️  Removed existing timer unit at ${TIMER_FILE}"
fi

# ========== 4. Reload systemd and enable the service ==========
sudo systemctl daemon-reload
sudo systemctl enable --now "${SERVICE_NAME}.service"
echo "✔️  Enabled and started ${SERVICE_NAME}.service"

# ========== Complete ==========
echo -e "\n✅  Installation and activation complete!"
echo "Your Docker Compose project in ${PROJECT_DIR} will now run continuously and restart automatically if it fails."
