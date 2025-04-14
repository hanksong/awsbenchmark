# Auto-generated main.tf from config.json
# DO NOT EDIT MANUALLY

# Create resources for tokyo region
module "vpc_tokyo" {
  source = "./modules/vpc"
  
  providers = {
    aws = aws.ap-northeast-1
  }
  
  region            = "ap-northeast-1"
  vpc_cidr_block    = var.vpc_cidr_blocks["ap-northeast-1"]
  subnet_cidr_block = var.subnet_cidr_blocks["ap-northeast-1"]
  project_tags      = var.project_tags
}

module "security_group_tokyo" {
  source = "./modules/security_group"
  
  providers = {
    aws = aws.ap-northeast-1
  }
  
  vpc_id       = module.vpc_tokyo.vpc_id
  project_tags = var.project_tags
}

module "ec2_instance_tokyo" {
  source = "./modules/ec2"
  
  providers = {
    aws = aws.ap-northeast-1
  }
  
  region            = "ap-northeast-1"
  instance_type     = var.instance_type
  ami_id            = var.ami_ids["ap-northeast-1"]
  key_name          = var.key_name
  subnet_id         = module.vpc_tokyo.subnet_id
  security_group_id = module.security_group_tokyo.security_group_id
  instance_count    = var.instance_count
  project_tags      = var.project_tags
}

# Create resources for virginia region
module "vpc_virginia" {
  source = "./modules/vpc"
  
  providers = {
    aws = aws.us-east-1
  }
  
  region            = "us-east-1"
  vpc_cidr_block    = var.vpc_cidr_blocks["us-east-1"]
  subnet_cidr_block = var.subnet_cidr_blocks["us-east-1"]
  project_tags      = var.project_tags
}

module "security_group_virginia" {
  source = "./modules/security_group"
  
  providers = {
    aws = aws.us-east-1
  }
  
  vpc_id       = module.vpc_virginia.vpc_id
  project_tags = var.project_tags
}

module "ec2_instance_virginia" {
  source = "./modules/ec2"
  
  providers = {
    aws = aws.us-east-1
  }
  
  region            = "us-east-1"
  instance_type     = var.instance_type
  ami_id            = var.ami_ids["us-east-1"]
  key_name          = var.key_name
  subnet_id         = module.vpc_virginia.subnet_id
  security_group_id = module.security_group_virginia.security_group_id
  instance_count    = var.instance_count
  project_tags      = var.project_tags
}

# Create resources for london region
module "vpc_london" {
  source = "./modules/vpc"
  
  providers = {
    aws = aws.eu-west-2
  }
  
  region            = "eu-west-2"
  vpc_cidr_block    = var.vpc_cidr_blocks["eu-west-2"]
  subnet_cidr_block = var.subnet_cidr_blocks["eu-west-2"]
  project_tags      = var.project_tags
}

module "security_group_london" {
  source = "./modules/security_group"
  
  providers = {
    aws = aws.eu-west-2
  }
  
  vpc_id       = module.vpc_london.vpc_id
  project_tags = var.project_tags
}

module "ec2_instance_london" {
  source = "./modules/ec2"
  
  providers = {
    aws = aws.eu-west-2
  }
  
  region            = "eu-west-2"
  instance_type     = var.instance_type
  ami_id            = var.ami_ids["eu-west-2"]
  key_name          = var.key_name
  subnet_id         = module.vpc_london.subnet_id
  security_group_id = module.security_group_london.security_group_id
  instance_count    = var.instance_count
  project_tags      = var.project_tags
}

