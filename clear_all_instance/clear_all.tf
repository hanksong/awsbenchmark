terraform {
  required_version = ">= 0.14.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 4.0"
    }
  }
}

# Configure providers
provider "aws" {
  alias  = "ap-northeast-1"
  region = "ap-northeast-1"
}

provider "aws" {
  alias  = "ap-southeast-2"
  region = "ap-southeast-2"
}

provider "aws" {
  alias  = "eu-west-2"
  region = "eu-west-2"
}

# Use data source to get all instances
data "aws_instances" "tokyo" {
  provider = aws.ap-northeast-1
  instance_tags = {
    Project = "aws-network-benchmark"
  }
}

data "aws_instances" "sydney" {
  provider = aws.ap-southeast-2
  instance_tags = {
    Project = "aws-network-benchmark"
  }
}

data "aws_instances" "london" {
  provider = aws.eu-west-2
  instance_tags = {
    Project = "aws-network-benchmark"
  }
}

# Reboot Tokyo region instances
resource "null_resource" "reboot_tokyo" {
  count = length(data.aws_instances.tokyo.ids)

  provisioner "local-exec" {
    command = "aws ec2 reboot-instances --instance-ids ${data.aws_instances.tokyo.ids[count.index]} --region ap-northeast-1"
  }
}

# Reboot Sydney region instances
resource "null_resource" "reboot_sydney" {
  count = length(data.aws_instances.sydney.ids)

  provisioner "local-exec" {
    command = "aws ec2 reboot-instances --instance-ids ${data.aws_instances.sydney.ids[count.index]} --region ap-southeast-2"
  }
}

# Reboot London region instances
resource "null_resource" "reboot_london" {
  count = length(data.aws_instances.london.ids)

  provisioner "local-exec" {
    command = "aws ec2 reboot-instances --instance-ids ${data.aws_instances.london.ids[count.index]} --region eu-west-2"
  }
}

# Output all rebooted instance IDs
output "rebooted_instances" {
  value = {
    tokyo  = data.aws_instances.tokyo.ids
    sydney = data.aws_instances.sydney.ids
    london = data.aws_instances.london.ids
  }
}
