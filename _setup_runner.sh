#!/bin/bash
set -e
TOKEN="$1"
DIR=/opt/actions-runner-agent-pipeline-claude
NAME=nvideablackwell-agent-pipeline-claude-2404

if [ -f "$DIR/.runner" ]; then
    echo "already configured at $DIR"
    sudo systemctl restart "actions.runner.scottconverse-agent-pipeline-claude.$NAME.service" || true
    exit 0
fi

sudo mkdir -p "$DIR"
sudo chown -R scott:scott "$DIR"
cd "$DIR"
tar -xzf /tmp/actions-runner-linux-x64-2.334.0.tar.gz -C "$DIR"

# Clean PATH so the runner doesn't see /mnt/c/... Windows pollution
echo -n '/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/usr/games:/usr/local/games:/usr/lib/wsl/lib' > "$DIR/.path"

./config.sh --unattended --replace \
    --url https://github.com/scottconverse/agent-pipeline-claude \
    --token "$TOKEN" \
    --name "$NAME" \
    --labels "wsl,rtx5070,ubuntu-2404,scott-desktop" \
    --work _work 2>&1 | tail -5

sudo ./svc.sh install scott 2>&1 | tail -3
sudo ./svc.sh start 2>&1 | tail -3

echo "Runner configured + started: $NAME"
