variable "aws_regions" {
  description = "AWS regions where EC2 instances will be deployed"
  type        = list(string)
  default     = ["ap-northeast-1", "us-east-1", "eu-west-2"]
}

variable "instance_type" {
  description = "EC2 instance type"
  type        = string
  default     = "t2.micro"
}

variable "ami_ids" {
  description = "AMI IDs for each region (Amazon Linux 2)"
  type        = map(string)
  default     = {
    "ap-northeast-1" = "ami-0f6963e3a0e928610" # tokyo
    "us-east-1" = "ami-065aeacd44e98d9ac" # virginia
    "eu-west-2" = "ami-0ad4d44e1fe45a341" # london
  }
}

variable "key_name" {
  description = "SSH key name for EC2 instances"
  type        = string
  default     = "aws-network-benchmark"
}

variable "vpc_cidr_blocks" {
  description = "CIDR blocks for VPCs in each region"
  type        = map(string)
  default     = {
    "ap-northeast-1" = "10.0.0.0/16"
    "us-east-1" = "10.1.0.0/16"
    "eu-west-2" = "10.2.0.0/16"
  }
}

variable "subnet_cidr_blocks" {
  description = "CIDR blocks for subnets in each region"
  type        = map(string)
  default     = {
    "ap-northeast-1" = "10.0.1.0/24"
    "us-east-1" = "10.1.1.0/24"
    "eu-west-2" = "10.2.1.0/24"
  }
}

variable "instance_count" {
  description = "Number of EC2 instances to create in each region"
  type        = number
  default     = 1
}

variable "project_tags" {
  description = "Tags for resources"
  type        = map(string)
  default     = {
    Project = "aws-network-benchmark"
    Owner   = "DevOps"
  }
}
