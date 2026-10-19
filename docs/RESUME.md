# 🎯 Resume, LinkedIn and Interview Kit

> Replace every [X] with a number you actually measured. Do not claim anything you did not test.

## Resume bullets (pick 4-5)
**ContainerWatch Pro: Self-Healing Container Monitoring Platform** | Docker, Prometheus, Grafana, Loki, Alertmanager, Python, Terraform, AWS EC2, GitHub Actions
- Built a self-healing observability platform for Docker workloads using Prometheus, Grafana, Loki and a custom Python metrics exporter built on the Docker API; dashboards and datasources provisioned as code.
- Developed a Python healer service that detects exited/unhealthy containers and restarts them via the Docker API with cooldown and restart-loop protection, reducing recovery time to about [X] seconds with no manual action.
- Implemented chaos tests (crash, failed health check, CPU and memory pressure) to validate [N] alert rules (CPU > 80%, memory > 85%, target down, restart loop).
- Provisioned AWS infrastructure with Terraform (EC2, Elastic IP, IAM/SSM role, IP-restricted security group, IMDSv2, encrypted EBS, budget alert).
- Created a GitHub Actions pipeline running unit tests, promtool/amtool/terraform validation, Trivy image scans, and automated deployment to EC2.
- Integrated Alertmanager with Discord/email notifications for real-time incident alerts. *(only if you set it up)*

## LinkedIn project description
Self-healing container monitoring platform: detects failures, restarts containers automatically, alerts via Discord, and visualises metrics + logs in Grafana. Fully deployed on AWS with Terraform and GitHub Actions. Code: <repo link>

## Interview questions you can now answer
1. **Why Prometheus pull model?** Targets expose /metrics; Prometheus scrapes on an interval, so a dead target is detected by `up == 0`.
2. **Why a custom exporter?** cAdvisor could not label containers on Docker Desktop/WSL2, so I read per-container stats from the Docker API and exported them as Prometheus gauges. This also removed the dependency on cAdvisor labels.
3. **How does your alert flow work?** Prometheus evaluates rules, fires after the `for:` duration, sends to Alertmanager, which groups, dedupes, and routes to receivers.
4. **How does self-healing work?** Healer polls Docker every 10s for labelled containers; if exited or unhealthy it restarts them; a cooldown prevents thrashing and an alert fires if restarts loop.
5. **Why not just `restart: always`?** Docker restarts crashed containers but not *unhealthy* ones, and gives no metrics, events, or alert on restarts.
6. **Security risk of docker.sock?** It is root-equivalent. Mitigations: label-based scope, socket proxy, or move to ECS/Kubernetes with proper IAM/RBAC.
7. **Why Loki?** Lightweight log aggregation indexed by labels, so logs and metrics sit side by side in Grafana.
8. **Why Terraform?** Repeatable, reviewable infrastructure; `plan` shows changes; `destroy` removes everything to control cost.
9. **How did you secure EC2?** Security group limited to my IP, IMDSv2, encrypted volume, SSM access, no secrets in Git.
10. **How would you scale this?** ECS/EKS, Prometheus remote write / Thanos, Alertmanager HA, ALB with HTTPS, secrets in AWS Secrets Manager.
11. **What would you improve?** HTTPS + auth in front of Grafana, remote Terraform state in S3 + DynamoDB lock, socket proxy, Slack/PagerDuty on-call routing.
12. **Hardest problem you solved?** Pick a real one from your debugging (e.g. cAdvisor on WSL2, alert not firing because of `for:`).

## Demo script (2 minutes, for interviews)
1. Show status page (all green). 2. Run `chaos unhealthy`. 3. Card goes red. 4. Healer restarts, timeline updates. 5. Show the alert in Prometheus and the Grafana heal panel. 6. Show logs from the failure in Loki. 7. Show `terraform plan` and the CI run.
