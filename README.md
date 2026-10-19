🛡️ **ContainerWatch Pro

CI Show Image Show Image Show Image Show Image

A self-healing Docker monitoring platform with chaos testing, log search and AWS deployment.

Containers crash. This project detects it, fixes it automatically, tells you about it, and proves it with data.

✨ Features
Feature	What it does
🔧 Self-healing engine	A Python service restarts exited or unhealthy containers (with a cooldown and a restart-loop alert)
📈 Custom metrics exporter	Reads CPU and memory per container from the Docker API and exposes them to Prometheus
💥 Chaos engineering	Crash a container, fail its health check, burn CPU, fill memory, then watch the platform recover
📊 Dashboards	Auto-provisioned Grafana dashboard with metrics and live logs from Loki
🚨 Alerting	CPU > 80%, memory > 85%, target down, self-healed, restart loop. Discord and email ready
🖥️ Live status page	Container health cards and an event timeline in your local time (port 8000)
☁️ Terraform on AWS	EC2, Elastic IP, IAM/SSM, IP-restricted firewall, IMDSv2, encrypted disk, budget alert
🔁 CI/CD	GitHub Actions: tests, promtool/amtool/terraform validation, Trivy scan, deploy
🏗️ Architecture
Docker host (local PC or AWS EC2)
metrics
container CPU / memory
rules
webhook / email
container logs
restarts via Docker API
demo-appFlask + gunicorn
healerself-healing + status page
cAdvisor
node-exporter
Prometheus
Alertmanager
Loki
Promtail
Grafana
Discord / Email

How the loop works:

The healer polls the Docker API every 10 seconds.
If a labelled container is exited or unhealthy, it restarts it (45 s cooldown) and logs an event.
Prometheus scrapes metrics, evaluates alert rules and sends firing alerts to Alertmanager.
Alertmanager notifies Discord or email. Grafana shows metrics and logs side by side.
🚀 Quick start

Requirements: Docker Desktop (or Docker Engine + Compose v2) and Git.

powershell
copy .env.example .env        # Mac/Linux: cp .env.example .env
notepad .env                  # set GRAFANA_ADMIN_PASSWORD, save
docker compose up -d --build
.\scripts\verify.ps1          # Mac/Linux: ./scripts/verify.sh

If verify fails right after startup, wait one minute and run it again.

Service	URL
Status page	http://localhost:8000
Grafana (admin / your password)	http://localhost:3001
Prometheus	http://localhost:9090
Alertmanager	http://localhost:9093
Demo app	http://localhost:5001

Break it on purpose: .\scripts\chaos.ps1 unhealthy and watch the status page.

💥 Chaos tests

Run one test at a time and wait for the container card to turn green between tests.

Command	What happens	Expected result
chaos.ps1 unhealthy	Health endpoint starts failing	Card turns red, healer restarts it (reason: unhealthy)
chaos.ps1 crash	Container exits	Healer restarts it (reason: exited)
chaos.ps1 cpu	Burns CPU for 5 minutes	HighContainerCPU fires after about 1 minute above 80%
chaos.ps1 memory	Allocates memory	HighContainerMemory fires
chaos.ps1 recover	Stops all faults	Alerts resolve

On Mac/Linux or on a server use ./scripts/chaos.sh <test> instead. Run recover only after the alert has fired. Alerts need the problem to last a full minute.

📏 Measured results
Metric	Result
Time from failure to container healthy again	[X] s (average of 3 runs)
Containers monitored	9
Alert rules	5
🔔 Notifications

Discord: create a webhook (Server Settings, Integrations, Webhooks), uncomment discord_configs in alertmanager/alertmanager.yml, paste the URL, then run:

docker compose restart alertmanager

Email works the same way with a Google App Password. Never commit webhook URLs or passwords.

☁️ Deploy to AWS with Terraform

Creates an EC2 instance with an Elastic IP, an IAM role with SSM access, a security group limited to your IP, IMDSv2, an encrypted disk and an optional budget alert.

Prerequisites: AWS account with MFA, an IAM user, AWS CLI and Terraform installed, aws configure done (region ap-south-1), and an EC2 key pair.

bash
# 1. Create a key pair in the same region
aws ec2 create-key-pair --key-name cw-key --region ap-south-1 \
  --query KeyMaterial --output text > cw-key.pem

# 2. Provision the infrastructure
cd terraform
terraform init
terraform apply -var="key_name=cw-key" \
                -var="my_ip_cidr=YOUR.IP.HERE/32" \
                -var="budget_email=you@example.com"

# 3. Deploy the app (run from the project root)
./scripts/deploy-ec2.sh <public_ip> ./cw-key.pem '<grafana_password>'

On the server, Grafana runs on port 3000: http://<public_ip>:3000, status page on :8000.

Run the chaos tests on the server with bash scripts/chaos.sh unhealthy after SSH-ing in.

⚠️ Cost: about 2 US cents per hour. When you are done, destroy everything with the same -var values: terraform destroy -var="key_name=cw-key" -var="my_ip_cidr=YOUR.IP.HERE/32" -var="budget_email=you@example.com"

Windows notes
deploy-ec2.sh uses rsync, which Git Bash does not include. Run it from WSL, or replace the rsync line with tar czf - ... | ssh ... "tar xzf - -C /opt/containerwatch".
If a shell script fails with "No such file or directory", it has Windows line endings. Fix with sed -i 's/\r$//' scripts/*.sh, or commit a .gitattributes file containing *.sh text eol=lf.
If your IP changes, SSH is blocked. Re-run terraform apply with your new IP.
🔁 CI/CD

GitHub Actions runs on every push:

Python unit tests
promtool and amtool config validation
terraform validate
Trivy image scan
Optional deploy to EC2 (needs the EC2_HOST, EC2_SSH_KEY and GRAFANA_ADMIN_PASSWORD repository secrets). If SSH from GitHub runners is blocked by the IP-restricted firewall, use deploy-ec2.sh instead.
🔐 Security notes
The healer mounts /var/run/docker.sock, which is root-equivalent. It restarts only containers labelled containerwatch.autoheal=true and applies a cooldown. In production use a socket proxy or ECS/Kubernetes.
EC2: security group limited to your IP, IMDSv2 enforced, encrypted EBS volume, SSM access, secrets only in .env and GitHub Secrets.
.env and *.pem files are git-ignored. Never commit them, and rotate any key that was shared by accident.
📁 Project structure
containerwatch-pro/
├── alertmanager/     # alert routing (Discord / email)
├── demo-app/         # Flask app with chaos endpoints
├── docs/             # resume and interview kit
├── grafana/          # provisioned datasources and dashboard
├── healer/           # self-healing engine, exporter, status page
├── loki/  promtail/  # log storage and shipping
├── prometheus/       # scrape config and alert rules
├── scripts/          # verify, chaos, deploy-ec2
├── terraform/        # AWS infrastructure
├── tests/            # unit tests
├── .github/          # CI/CD workflows
└── docker-compose.yml
🧯 Troubleshooting
Problem	Fix
"failed to connect to the docker API"	Start Docker Desktop and wait for "Engine running"
GRAFANA_ADMIN_PASSWORD error	.env is missing or empty
"port is already allocated"	Set GRAFANA_PORT or APP_PORT in .env, then docker compose up -d
Script blocked by PowerShell	Set-ExecutionPolicy -Scope Process Bypass
Card stays red	Check the pill is not PAUSED, then docker compose logs healer --tail 20
Alert never fires	Wait the full 3 minutes and do not run recover early

Full beginner walkthrough: GUIDE.md · Resume and interview kit: docs/RESUME.md

📄 License

MIT. See LICENSE (add one before publishing if you want others to reuse the code).
