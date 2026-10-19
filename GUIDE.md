# 📘 ContainerWatch Pro: Step-by-Step Guide

**Rules that avoid 90% of problems**
1. Docker Desktop must show **"Engine running"** before you type any `docker` command.
2. Run **one command at a time**. Press Enter, wait for the prompt to come back, then paste the next.
3. Commands starting with `docker` or `.\scripts` go in **PowerShell**. Queries like `cw_container_cpu_percent` go in the **Prometheus website**, not PowerShell.
4. Run PowerShell commands from the folder that contains `docker-compose.yml`.

---
## PART 1: Start the platform
1. Open Docker Desktop and wait for "Engine running".
2. Open PowerShell in the project folder, then run:
```
copy .env.example .env
notepad .env
```
Set `GRAFANA_ADMIN_PASSWORD`, save, close. (Ports default to 3001 and 5001; change them in `.env` only if something else uses them.)
```
docker compose up -d --build
```
First run takes 3 to 5 minutes. Then:
```
docker compose ps
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\verify.ps1
```
Wait about 1 minute after startup if a check fails, then run `verify.ps1` again. **Goal: ALL CHECKS PASSED.**

Open: Status page http://localhost:8000, Grafana http://localhost:3001 (Dashboards, ContainerWatch Overview).
📸 Screenshot 1: status page all green. Screenshot 2: Grafana dashboard.

## PART 2: Chaos tests (one at a time, wait for green between tests)
Keep the status page open. Before each test confirm: `demo-app` is green and the pill says **Auto-healing: ON**.

| # | Command | Wait | Expected result |
|---|---|---|---|
| 1 | `.\scripts\chaos.ps1 unhealthy` | 30 to 60 s | Card turns red, then healer restarts it. Timeline: `Self-healed (reason: unhealthy)`. About 1 min later red `ContainerSelfHealed` alert |
| 2 | `.\scripts\chaos.ps1 crash` | 30 s | Container exits, healer restarts it (`reason: exited`) |
| 3 | `.\scripts\chaos.ps1 cpu` | **3 minutes. Do nothing else** | Grafana CPU hits 100%. Prometheus Alerts: `HighContainerCPU` FIRING. Burn stops itself after 5 min |
| 4 | `.\scripts\chaos.ps1 memory` | **3 minutes. Do nothing else** | Memory about 88%. `HighContainerMemory` FIRING |
| 5 | `.\scripts\chaos.ps1 recover` | 1 to 3 min | Run it **only after** the alert fired and you took screenshots. Alerts resolve (blue entries) |

⚠️ Running `recover` too early cancels the test, because alerts need the problem to last a full minute.
⏱️ **Recovery time:** run test 1 three times (about a minute apart) with a stopwatch from pressing Enter to the green card. Write the three times down for your resume.
📸 Screenshots: red card, timeline with heal event, Prometheus Alerts page (http://localhost:9090/alerts) with a firing alert, Grafana during CPU spike.

## PART 3: Real notifications (Discord)
Discord: Server Settings, Integrations, Webhooks, New Webhook, Copy URL. In `alertmanager/alertmanager.yml` uncomment `discord_configs`, paste the URL, then:
```
docker compose restart alertmanager
```
Run a chaos test and screenshot the Discord message. (Email works the same way with a Google App Password.)

## PART 4: GitHub
```
git init
git add .
git commit -m "ContainerWatch Pro"
git branch -M main
git remote add origin https://github.com/<you>/containerwatch-pro.git
git push -u origin main
```
`.env` is git-ignored, so your password stays private. Check the Actions tab for the CI run.

## PART 5: AWS with Terraform
Setup: AWS account with MFA, IAM user, AWS CLI and Terraform installed, `aws configure` (region ap-south-1), EC2 key pair (for example `cw-key`), your IP from https://checkip.amazonaws.com.
```
cd terraform
terraform init
terraform apply -var="key_name=cw-key" -var="my_ip_cidr=YOUR.IP.HERE/32" -var="budget_email=you@gmail.com"
```
Type `yes`, wait 3 minutes. Then from the project folder (Git Bash or WSL):
```
./scripts/deploy-ec2.sh <public_ip> /path/to/cw-key.pem <grafana_password>
```
Open `http://<public_ip>:8000` and `:3001`, run the chaos tests on AWS, screenshot them.
⚠️ **Cost:** about 2 US cents per hour. When done: `terraform destroy` with the same `-var` values.

## PART 6: Auto deploy (optional)
GitHub, Settings, Secrets and variables, Actions: add `EC2_HOST`, `EC2_SSH_KEY` (full .pem text), `GRAFANA_ADMIN_PASSWORD`. GitHub runner IPs change, so if SSH is blocked use `deploy-ec2.sh` instead.

## PART 7: Resume
Use `docs/RESUME.md`. Replace every [X] with your measured numbers. Only claim Discord/email, AWS or CI/CD if you actually did and tested them.

## 🧯 Troubleshooting
| Problem | Fix |
|---|---|
| "failed to connect to the docker API" | Docker Desktop is not running. Start it, wait for Engine running |
| `.env.example` not found | You are in the wrong folder. `cd` into the one containing `docker-compose.yml` |
| "port is already allocated" | Another program uses it. Set `GRAFANA_PORT` or `APP_PORT` in `.env`, then `docker compose up -d` |
| `GRAFANA_ADMIN_PASSWORD` error | `.env` is missing or empty |
| Script blocked by PowerShell | `Set-ExecutionPolicy -Scope Process Bypass` |
| Card stays red | Pill says PAUSED? Click Resume healing. Else `docker compose logs healer --tail 20` |
| Alert never fires | Wait the full 3 minutes and do not run `recover` early. Check `cw_container_cpu_percent{name="demo-app"}` in Prometheus |
| `verify.ps1` fails right after start | Wait 1 minute and rerun |
| Status page shows other projects | Fixed: it shows only this project (set `SHOW_ALL_CONTAINERS=1` on the healer to see everything) |
