#!/usr/bin/env bash
# Usage: ./scripts/deploy-ec2.sh <public_ip> <path-to-key.pem> <grafana_password>
set -e
IP=$1; KEY=$2; PASS=$3
rsync -az -e "ssh -i $KEY -o StrictHostKeyChecking=accept-new" \
  --exclude .git --exclude terraform --exclude .env ./ ec2-user@$IP:/opt/containerwatch/
ssh -i "$KEY" ec2-user@$IP "cd /opt/containerwatch && echo GRAFANA_ADMIN_PASSWORD='$PASS' > .env && docker compose up -d --build"
echo "Grafana:     http://$IP:3001"
echo "Status page: http://$IP:8000"
