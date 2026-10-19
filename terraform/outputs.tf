output "public_ip" {
  value = aws_eip.containerwatch.public_ip
}

output "grafana_url" {
  value = "http://${aws_eip.containerwatch.public_ip}:3001"
}

output "status_page_url" {
  value = "http://${aws_eip.containerwatch.public_ip}:8000"
}

output "ssh_command" {
  value = "ssh -i <your-key>.pem ec2-user@${aws_eip.containerwatch.public_ip}"
}
