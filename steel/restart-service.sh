#!/usr/bin/env bash
set -euo pipefail

# ========== Configuration ==========
# Name of the systemd service (arbitrary)
SERVICE_NAME="steel-service"

# Directory of your project (where exec.sh is located)
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Path where the restart helper script will be installed
RESTART_SCRIPT="/usr/local/bin/${SERVICE_NAME}.sh"

# Paths for the systemd unit files
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"
TIMER_FILE="/etc/systemd/system/${SERVICE_NAME}.timer"

RESTART_TIME=120

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
Description=Restart Docker Compose project in ${PROJECT_DIR}

[Service]
Type=oneshot
ExecStart=${RESTART_SCRIPT}
WorkingDirectory=${PROJECT_DIR}
EOF

echo "✔️  Created systemd service unit at ${SERVICE_FILE}"

# ========== 3. Create the systemd Timer unit ==========
cat <<EOF | sudo tee "${TIMER_FILE}" > /dev/null
[Unit]
Description=Run ${SERVICE_NAME}.service every ${RESTART_TIME} minutes

[Timer]
OnCalendar=*:0/${RESTART_TIME}
# If the system was down during a scheduled run, run it once at boot
Persistent=true

[Install]
WantedBy=timers.target
EOF

echo "✔️  Created systemd timer unit at ${TIMER_FILE}"

# ========== 4. Reload systemd and enable the timer ==========
sudo systemctl daemon-reload
sudo systemctl enable --now "${SERVICE_NAME}.timer"
echo "✔️  Enabled and started ${SERVICE_NAME}.timer"

# ========== Complete ==========
echo -e "\n✅  Installation and activation complete!"
echo "Your Docker Compose project in ${PROJECT_DIR} will now restart every ${RESTART_TIME} minutes."
