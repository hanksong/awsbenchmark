#!/usr/bin/env python3
# Get instance information from AWS and generate instance_info.json file

import os
import json
import subprocess
import sys
import boto3
from botocore.exceptions import ClientError

# Project root directory
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# List of regions
REGIONS = ["ap-northeast-1", "ap-southeast-2", "eu-west-2"]
REGION_NAMES = {"ap-northeast-1": "Tokyo", "ap-southeast-2": "Sydney", "eu-west-2": "London"}

def print_color(text, color):
    """Print colored text"""
    colors = {
        "green": "\033[0;32m",
        "yellow": "\033[1;33m",
        "red": "\033[0;31m",
        "reset": "\033[0m"
    }
    print(f"{colors.get(color, colors['reset'])}{text}{colors['reset']}")

def get_instance_info():
    """Get instance information from AWS"""
    instance_info = {"instances": {}}
    
    for region in REGIONS:
        region_name = REGION_NAMES.get(region, region)
        print_color(f"\nGetting instance information for {region_name} region ({region})...", "yellow")
        
        try:
            # Create EC2 client
            ec2 = boto3.client('ec2', region_name=region)
            
            # Get instances with Project=aws-network-benchmark tag
            response = ec2.describe_instances(
                Filters=[
                    {
                        'Name': 'tag:Project',
                        'Values': ['aws-network-benchmark']
                    },
                    {
                        'Name': 'instance-state-name',
                        'Values': ['running', 'pending']
                    }
                ]
            )
            
            # Extract instance information
            public_ips = []
            private_ips = []
            instance_ids = []
            
            for reservation in response['Reservations']:
                for instance in reservation['Instances']:
                    instance_id = instance['InstanceId']
                    instance_ids.append(instance_id)
                    
                    if 'PublicIpAddress' in instance:
                        public_ips.append(instance['PublicIpAddress'])
                    
                    if 'PrivateIpAddress' in instance:
                        private_ips.append(instance['PrivateIpAddress'])
            
            if not instance_ids:
                print_color(f"No instances found in {region_name} region", "yellow")
                continue
                
            print_color(f"Found {len(instance_ids)} instances in {region_name} region:", "green")
            for i, instance_id in enumerate(instance_ids):
                public_ip = public_ips[i] if i < len(public_ips) else "No public IP"
                print(f" - {instance_id} ({public_ip})")
            
            # Add to instance information
            instance_info["instances"][region] = {
                "public_ips": public_ips,
                "private_ips": private_ips,
                "instance_ids": instance_ids
            }
            
        except ClientError as e:
            print_color(f"Error getting instances in {region_name} region: {e}", "red")
    
    return instance_info

def save_instance_info(instance_info):
    """Save instance information to file"""
    # Ensure data directory exists
    data_dir = os.path.join(PROJECT_ROOT, "data")
    os.makedirs(data_dir, exist_ok=True)
    
    # Save to file
    instance_info_path = os.path.join(data_dir, "instance_info.json")
    with open(instance_info_path, 'w') as f:
        json.dump(instance_info, f, indent=2)
    
    print_color(f"\nInstance information saved to: {instance_info_path}", "green")
    return instance_info_path

def main():
    """Main function"""
    print_color("Starting to get instance information...", "yellow")
    
    # Check AWS credentials
    try:
        boto3.client('sts').get_caller_identity()
    except Exception as e:
        print_color(f"Invalid AWS credentials: {e}", "red")
        print("Please run 'aws configure' to set up your AWS credentials")
        return 1
    
    # Get instance information
    instance_info = get_instance_info()
    
    # Check if any instances were found
    any_instances = False
    for region, info in instance_info["instances"].items():
        if info.get("instance_ids"):
            any_instances = True
            break
    
    if not any_instances:
        print_color("Error: No instances found in any region", "red")
        return 1
    
    # Save instance information
    save_instance_info(instance_info)
    
    print_color("Instance information retrieval complete!", "green")
    return 0

if __name__ == "__main__":
    sys.exit(main()) 