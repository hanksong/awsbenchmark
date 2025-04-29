#!/usr/bin/env python3
# generate_terraform.py
# Generate Terraform configuration files from config.json

from Constants import AWS_FALLBACK_AMI_IDS, AWS_REGION_NAMES
import json
import os
import sys
import argparse
import re
import subprocess
import boto3
from botocore.exceptions import ClientError


def get_latest_ami_ids(regions):
    """get the latest amazon linux 2 ami id for the specified regions"""
    print("getting the latest amazon linux 2 ami id...")
    ami_ids = {}

    for region in regions:
        try:
            # try to get the latest ami id using aws cli
            cmd = f"aws ec2 describe-images --region {region} --owners amazon " + \
                  "--filters \"Name=name,Values=amzn2-ami-hvm-2.*-x86_64-gp2\" \"Name=state,Values=available\" " + \
                  "--query \"sort_by(Images, &CreationDate)[-1].ImageId\" --output text"

            result = subprocess.run(
                cmd, shell=True, check=True, capture_output=True, text=True)
            ami_id = result.stdout.strip()

            if ami_id:
                ami_ids[region] = ami_id
                print(f"region {region}: found the latest ami id - {ami_id}")
            else:
                ami_ids[region] = AWS_FALLBACK_AMI_IDS.get(
                    region, "ami-0000000000000000")
                print(
                    f"region {region}: not found the latest ami id, using the fallback value - {ami_ids[region]}")

        except subprocess.CalledProcessError:
            # if the aws cli call fails, try to get the latest ami id using boto3
            try:
                print(
                    f"aws cli call failed, trying to get the latest ami id using boto3 for region {region}...")
                ec2 = boto3.client('ec2', region_name=region)
                response = ec2.describe_images(
                    Owners=['amazon'],
                    Filters=[
                        {'Name': 'name', 'Values': [
                            'amzn2-ami-hvm-2.*-x86_64-gp2']},
                        {'Name': 'state', 'Values': ['available']}
                    ]
                )

                # 按创建日期排序并获取最新的
                images = sorted(
                    response['Images'], key=lambda x: x['CreationDate'], reverse=True)
                if images:
                    ami_ids[region] = images[0]['ImageId']
                    print(
                        f"region {region}: found the latest ami id using boto3 - {ami_ids[region]}")
                else:
                    ami_ids[region] = AWS_FALLBACK_AMI_IDS.get(
                        region, "ami-0000000000000000")
                    print(
                        f"region {region}: not found the latest ami id, using the fallback value - {ami_ids[region]}")

            except (ClientError, Exception) as e:
                # if both methods fail, use the fallback ami id
                ami_ids[region] = AWS_FALLBACK_AMI_IDS.get(
                    region, "ami-0000000000000000")
                print(
                    f"region {region}: failed to get the latest ami id ({str(e)}), using the fallback value - {ami_ids[region]}")

    return ami_ids


def get_region_name(region_code):
    """Get a human-readable name for a region code"""
    return AWS_REGION_NAMES.get(region_code, region_code.replace("-", "_"))


def generate_main_tf(regions, output_file, region_instance_counts):
    """Generate main.tf file with resources for specified regions"""
    template = """# Auto-generated main.tf from config.json
# DO NOT EDIT MANUALLY

{resources}
"""

    resources = []

    # Generate resources for each region
    for i, region in enumerate(regions):
        region_name = get_region_name(region)
        # 处理重复区域，为资源名添加索引
        region_count = regions[:i + 1].count(region)
        resource_suffix = "" if region_count == 1 else f"_{region_count}"

        vpc_module = f"""# Create resources for {region_name} region{f" #{region_count}" if region_count > 1 else ""}
module "vpc_{region_name}{resource_suffix}" {{
  source = "./modules/vpc"
  
  providers = {{
    aws = aws.{region}
  }}
  
  region            = "{region}"
  vpc_cidr_block    = var.vpc_cidr_blocks["{region}"]
  subnet_cidr_block = var.subnet_cidr_blocks["{region}"]
  project_tags      = var.project_tags
}}

module "security_group_{region_name}{resource_suffix}" {{
  source = "./modules/security_group"
  
  providers = {{
    aws = aws.{region}
  }}
  
  vpc_id       = module.vpc_{region_name}{resource_suffix}.vpc_id
  project_tags = var.project_tags
}}

module "ec2_instance_{region_name}{resource_suffix}" {{
  source = "./modules/ec2"
  
  providers = {{
    aws = aws.{region}
  }}
  
  region            = "{region}"
  instance_type     = var.instance_type
  ami_id            = var.ami_ids["{region}"]
  key_name          = var.key_name
  subnet_id         = module.vpc_{region_name}{resource_suffix}.subnet_id
  security_group_id = module.security_group_{region_name}{resource_suffix}.security_group_id
  instance_count    = {region_instance_counts.get(region, "var.instance_count")}
  project_tags      = var.project_tags
}}
"""
        resources.append(vpc_module)

    with open(output_file, 'w') as f:
        f.write(template.format(resources="\n".join(resources)))

    print(f"Generated {output_file} with {len(regions)} regions")


def generate_provider_tf(regions, output_file):
    """Generate provider.tf file with provider configurations for specified regions"""
    template = """# Auto-generated provider.tf from config.json
# DO NOT EDIT MANUALLY

terraform {{
  required_version = ">= 0.14.0"
  required_providers {{
    aws = {{
      source  = "hashicorp/aws"
      version = "~> 4.0"
    }}
  }}
}}

{providers}
"""

    providers = []

    # Generate provider blocks for each region
    for region in regions:
        provider_block = f"""provider "aws" {{
  alias  = "{region}"
  region = "{region}"
}}
"""
        providers.append(provider_block)

    with open(output_file, 'w') as f:
        f.write(template.format(providers="\n".join(providers)))

    print(f"Generated {output_file} with {len(regions)} providers")


def generate_outputs_tf(regions, output_file):
    """Generate outputs.tf file with output configurations for specified regions"""
    template = """# Auto-generated outputs.tf from config.json
# DO NOT EDIT MANUALLY

output "vpc_ids" {{
  description = "IDs of the created VPCs"
  value = {{
{vpc_ids}
  }}
}}

output "subnet_ids" {{
  description = "IDs of the created subnets"
  value = {{
{subnet_ids}
  }}
}}

output "instance_public_ips" {{
  description = "Public IPs of the created EC2 instances"
  value = {{
{public_ips}
  }}
}}

output "instance_private_ips" {{
  description = "Private IPs of the created EC2 instances"
  value = {{
{private_ips}
  }}
}}
"""

    vpc_ids = []
    subnet_ids = []
    public_ips = []
    private_ips = []

    # Generate outputs for each region
    unique_regions = []
    for i, region in enumerate(regions):
        region_name = get_region_name(region)
        # 处理重复区域
        region_count = regions[:i + 1].count(region)
        resource_suffix = "" if region_count == 1 else f"_{region_count}"

        if region not in unique_regions:
            unique_regions.append(region)

        vpc_ids.append(
            f'    "{region_name}{f"_{region_count}" if region_count > 1 else ""}" = module.vpc_{region_name}{resource_suffix}.vpc_id')
        subnet_ids.append(
            f'    "{region_name}{f"_{region_count}" if region_count > 1 else ""}" = module.vpc_{region_name}{resource_suffix}.subnet_id')
        public_ips.append(
            f'    "{region_name}{f"_{region_count}" if region_count > 1 else ""}" = module.ec2_instance_{region_name}{resource_suffix}.public_ips')
        private_ips.append(
            f'    "{region_name}{f"_{region_count}" if region_count > 1 else ""}" = module.ec2_instance_{region_name}{resource_suffix}.private_ips')

    with open(output_file, 'w') as f:
        f.write(template.format(
            vpc_ids="\n".join(vpc_ids),
            subnet_ids="\n".join(subnet_ids),
            public_ips="\n".join(public_ips),
            private_ips="\n".join(private_ips)
        ))

    print(f"Generated {output_file} with {len(regions)} regions")


def update_variables_tf(regions, output_file, ami_ids):
    """Update variables.tf file to include all required regions"""
    try:
        with open(output_file, 'r') as f:
            content = f.read()

        # Update aws_regions variable default value
        regions_str = '", "'.join(regions)
        regions_list = f'["{regions_str}"]'
        content = re.sub(r'variable "aws_regions".*?default\s*=\s*\[(.*?)\]',
                         f'variable "aws_regions" {{\n  description = "AWS regions where EC2 instances will be deployed"\n  type        = list(string)\n  default     = {regions_list}',
                         content, flags=re.DOTALL)

        # Ensure ami_ids includes all regions
        ami_ids_entries = []
        for region in regions:
            ami_ids_entries.append(
                f'    "{region}" = "{ami_ids.get(region, AWS_FALLBACK_AMI_IDS.get(region, "ami-0000000000000000"))}" # {get_region_name(region)}')

        ami_ids_block = '{\n' + '\n'.join(ami_ids_entries) + '\n  }'
        content = re.sub(r'variable "ami_ids".*?default\s*=\s*\{(.*?)\}',
                         f'variable "ami_ids" {{\n  description = "AMI IDs for each region (Amazon Linux 2)"\n  type        = map(string)\n  default     = {ami_ids_block}',
                         content, flags=re.DOTALL)

        # Ensure vpc_cidr_blocks includes all regions
        vpc_cidr_entries = []
        for i, region in enumerate(regions):
            vpc_cidr_entries.append(f'    "{region}" = "10.{i}.0.0/16"')

        vpc_cidr_block = '{\n' + '\n'.join(vpc_cidr_entries) + '\n  }'
        content = re.sub(r'variable "vpc_cidr_blocks".*?default\s*=\s*\{(.*?)\}',
                         f'variable "vpc_cidr_blocks" {{\n  description = "CIDR blocks for VPCs in each region"\n  type        = map(string)\n  default     = {vpc_cidr_block}',
                         content, flags=re.DOTALL)

        # Ensure subnet_cidr_blocks includes all regions
        subnet_cidr_entries = []
        for i, region in enumerate(regions):
            subnet_cidr_entries.append(f'    "{region}" = "10.{i}.1.0/24"')

        subnet_cidr_block = '{\n' + '\n'.join(subnet_cidr_entries) + '\n  }'
        content = re.sub(r'variable "subnet_cidr_blocks".*?default\s*=\s*\{(.*?)\}',
                         f'variable "subnet_cidr_blocks" {{\n  description = "CIDR blocks for subnets in each region"\n  type        = map(string)\n  default     = {subnet_cidr_block}',
                         content, flags=re.DOTALL)

        with open(output_file, 'w') as f:
            f.write(content)

        print(f"Updated {output_file} with {len(regions)} regions")
    except Exception as e:
        print(f"Error updating variables.tf: {e}")
        # If update fails, generate a new file
        generate_variables_tf(regions, output_file, ami_ids)


def generate_variables_tf(regions, output_file, ami_ids):
    """Generate variables.tf file with variables for specified regions"""

    # Generate AMI IDs block
    ami_ids_entries = []
    for region in regions:
        ami_ids_entries.append(
            f'    "{region}" = "{ami_ids.get(region, AWS_FALLBACK_AMI_IDS.get(region, "ami-0000000000000000"))}" # {get_region_name(region)}')

    ami_ids_block = '{\n' + '\n'.join(ami_ids_entries) + '\n  }'

    # Generate VPC CIDR blocks
    vpc_cidr_entries = []
    for i, region in enumerate(regions):
        vpc_cidr_entries.append(f'    "{region}" = "10.{i}.0.0/16"')

    vpc_cidr_block = '{\n' + '\n'.join(vpc_cidr_entries) + '\n  }'

    # Generate subnet CIDR blocks
    subnet_cidr_entries = []
    for i, region in enumerate(regions):
        subnet_cidr_entries.append(f'    "{region}" = "10.{i}.1.0/24"')

    subnet_cidr_block = '{\n' + '\n'.join(subnet_cidr_entries) + '\n  }'

    # Construct entire variables.tf content
    template = f"""# Auto-generated variables.tf from config.json
# DO NOT EDIT MANUALLY

variable "aws_regions" {{
  description = "AWS regions where EC2 instances will be deployed"
  type        = list(string)
  default     = ["{'", "'.join(regions)}"]
}}

variable "instance_type" {{
  description = "EC2 instance type"
  type        = string
  default     = "t2.micro"
}}

variable "ami_ids" {{
  description = "AMI IDs for each region (Amazon Linux 2)"
  type        = map(string)
  default     = {ami_ids_block}
}}

variable "key_name" {{
  description = "SSH key name for EC2 instances"
  type        = string
  default     = "aws-network-benchmark"
}}

variable "vpc_cidr_blocks" {{
  description = "CIDR blocks for VPCs in each region"
  type        = map(string)
  default     = {vpc_cidr_block}
}}

variable "subnet_cidr_blocks" {{
  description = "CIDR blocks for subnets in each region"
  type        = map(string)
  default     = {subnet_cidr_block}
}}

variable "instance_count" {{
  description = "Number of EC2 instances to create in each region"
  type        = number
  default     = 1
}}

variable "project_tags" {{
  description = "Tags for resources"
  type        = map(string)
  default     = {{
    Project = "aws-network-benchmark"
    Owner   = "DevOps"
  }}
}}
"""

    with open(output_file, 'w') as f:
        f.write(template)

    print(f"Generated {output_file} with {len(regions)} regions")


def modify_run_benchmark_py(config_hook_file):
    """Modify run_benchmark.py to add a hook for generating Terraform files"""
    try:
        with open(config_hook_file, 'r') as f:
            content = f.read()

        # Check if the hook is already added
        if "generate_terraform.py" in content:
            print(f"Hook already exists in {config_hook_file}")
            return

        # Find the setup_terraform function and add the hook
        setup_terraform_func = re.search(
            r'def setup_terraform\(config\):(.*?)return True', content, re.DOTALL)
        if setup_terraform_func:
            # Add hook after the data directory creation
            hook_code = """
    # Generate Terraform files from config.json
    print("Generating Terraform configuration files from config.json...")
    gen_terraform_cmd = f"python3 {os.path.join(PROJECT_ROOT, 'scripts/generate_terraform.py')} --config {os.path.join(PROJECT_ROOT, 'terraform/config.json')} --terraform-dir {terraform_dir}"
    run_command(gen_terraform_cmd)
    
"""
            new_function = setup_terraform_func.group(0).replace(
                'os.makedirs(data_dir, exist_ok=True)', 'os.makedirs(data_dir, exist_ok=True)' + hook_code)
            content = content.replace(
                setup_terraform_func.group(0), new_function)

            with open(config_hook_file, 'w') as f:
                f.write(content)

            print(f"Added Terraform generation hook to {config_hook_file}")
        else:
            print(
                f"Could not find setup_terraform function in {config_hook_file}")
    except Exception as e:
        print(f"Error modifying run_benchmark.py: {e}")

# Modify main to accept arguments directly


def generate_terraform(config_path, terraform_dir):
    """Generates Terraform configuration files."""
    print(f"Generating Terraform configuration from: {config_path}")
    print(f"Output directory: {terraform_dir}")

    # Ensure terraform directory exists
    os.makedirs(terraform_dir, exist_ok=True)

    try:
        # Load configuration
        with open(config_path, 'r') as f:
            config = json.load(f)

        aws_regions = config.get('aws_regions', [])
        if not aws_regions:
            print("Error: 'aws_regions' not found or empty in config file.")
            return 1

        instance_type = config.get('instance_type', 't2.micro')
        key_name = config.get('ssh_key_name', 'aws-network-benchmark')
        # Use region_instance_counts if available, otherwise default instance_count
        default_instance_count = config.get('instance_count', 1)
        region_instance_counts = config.get('region_instance_counts', {})

        # Get AMI IDs
        ami_ids = get_latest_ami_ids(aws_regions)

        # Generate provider.tf
        generate_provider_tf(aws_regions, terraform_dir)

        # Generate variables.tf
        generate_variables_tf(config, ami_ids, terraform_dir)

        # Generate main.tf
        generate_main_tf(config, terraform_dir)

        # Generate outputs.tf
        generate_outputs_tf(config, terraform_dir)

        print("Terraform configuration files generated successfully.")
        return 0

    except FileNotFoundError:
        print(f"Error: Config file not found at {config_path}")
        return 1
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from {config_path}")
        return 1
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Generate Terraform configuration files from config.json")
    # Make config path relative to project root for consistency
    parser.add_argument("--config", default="config.json",
                        help="Path to the configuration JSON file (relative to project root)")
    parser.add_argument("--terraform-dir", default="terraform",
                        help="Directory to output Terraform files (relative to project root)")
    args = parser.parse_args()

    # Construct absolute paths based on project root
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    abs_config_path = os.path.join(project_root, args.config)
    abs_terraform_dir = os.path.join(project_root, args.terraform_dir)

    sys.exit(generate_terraform(config_path=abs_config_path, terraform_dir=abs_terraform_dir))
