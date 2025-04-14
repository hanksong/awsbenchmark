# Auto-generated outputs.tf from config.json
# DO NOT EDIT MANUALLY

output "vpc_ids" {
  description = "IDs of the created VPCs"
  value = {
    "tokyo" = module.vpc_tokyo.vpc_id
    "virginia" = module.vpc_virginia.vpc_id
    "london" = module.vpc_london.vpc_id
  }
}

output "subnet_ids" {
  description = "IDs of the created subnets"
  value = {
    "tokyo" = module.vpc_tokyo.subnet_id
    "virginia" = module.vpc_virginia.subnet_id
    "london" = module.vpc_london.subnet_id
  }
}

output "instance_public_ips" {
  description = "Public IPs of the created EC2 instances"
  value = {
    "tokyo" = module.ec2_instance_tokyo.public_ips
    "virginia" = module.ec2_instance_virginia.public_ips
    "london" = module.ec2_instance_london.public_ips
  }
}

output "instance_private_ips" {
  description = "Private IPs of the created EC2 instances"
  value = {
    "tokyo" = module.ec2_instance_tokyo.private_ips
    "virginia" = module.ec2_instance_virginia.private_ips
    "london" = module.ec2_instance_london.private_ips
  }
}
