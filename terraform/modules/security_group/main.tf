variable "vpc_id" {
  description = "VPC ID for the security group"
  type        = string
}

variable "project_tags" {
  description = "Tags for the project"
  type        = map(string)
}

resource "aws_security_group" "main" {
  name        = "network-benchmark-sg"
  description = "Security group for network benchmarking"
  vpc_id      = var.vpc_id

  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    from_port   = -1
    to_port     = -1
    protocol    = "icmp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  
  ingress {
    from_port   = 5201
    to_port     = 5201
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "iperf3-default-tcp-port"
  }

  ingress {
    from_port   = 5201
    to_port     = 5201
    protocol    = "udp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "iperf3-default-udp-port"
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = var.project_tags
}

output "security_group_id" {
  value = aws_security_group.main.id
} 