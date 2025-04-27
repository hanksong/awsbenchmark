#!/usr/bin/env python3
# Stop all EC2 instances in all regions

import os
import json
import sys
import time
import boto3
from botocore.exceptions import ClientError

# Project root directory
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Region list from terraform/config.json
with open(os.path.join(PROJECT_ROOT, 'terraform', 'config.json'), 'r') as f:
    config = json.load(f)

REGIONS = config.get('aws_regions', [])
REGION_NAMES = {
    "ap-northeast-1": "Tokyo",
    "us-east-1": "Virginia", 
    "eu-west-2": "London",
    "ap-southeast-2": "Sydney",
    "me-south-1": "Bahrain",
    "sa-east-1": "Sao Paulo",
    "ca-central-1": "Montreal",
    "eu-west-3": "Paris",
    "eu-north-1": "Frankfurt",
    "eu-west-1": "Ireland",
    "eu-central-1": "Milan",
    "eu-south-1": "Madrid"
}

def print_color(text, color):
    colors = {
        "green": "\033[0;32m",
        "yellow": "\033[1;33m", 
        "red": "\033[0;31m",
        "blue": "\033[0;34m",
        "reset": "\033[0m"
    }
    print(f"{colors.get(color, colors['reset'])}{text}{colors['reset']}")

def get_running_instances():
    """Get all running EC2 instances in all regions"""
    instances_by_region = {}
    total_instances = 0
    
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
            instance_list = []
            
            for reservation in response['Reservations']:
                for instance in reservation['Instances']:
                    instance_id = instance['InstanceId']
                    instance_state = instance['State']['Name']
                    instance_name = "Unnamed"
                    
                    # Find name tag
                    for tag in instance.get('Tags', []):
                        if tag['Key'] == 'Name':
                            instance_name = tag['Value']
                            break
                    
                    # Get public IP (if exists)
                    public_ip = instance.get('PublicIpAddress', 'No public IP')
                    
                    instance_list.append({
                        'id': instance_id,
                        'state': instance_state,
                        'name': instance_name,
                        'public_ip': public_ip
                    })
            
            if not instance_list:
                print_color(f"No running instances found in {region_name} region", "yellow")
                continue
                
            print_color(f"Found {len(instance_list)} running instances in {region_name} region:", "green")
            for instance in instance_list:
                print(f" - {instance['id']} ({instance['name']}) [{instance['public_ip']}] - {instance['state']}")
            
            instances_by_region[region] = instance_list
            total_instances += len(instance_list)
            
        except ClientError as e:
            print_color(f"Error getting instances in {region_name} region: {e}", "red")
    
    return instances_by_region, total_instances

def stop_instances(instances_by_region):
    """Stop all instances in all regions"""
    stopped_count = 0
    
    for region, instances in instances_by_region.items():
        region_name = REGION_NAMES.get(region, region)
        
        if not instances:
            continue
        
        print_color(f"\nStopping {len(instances)} instances in {region_name} region...", "blue")
        
        # Extract instance IDs
        instance_ids = [instance['id'] for instance in instances]
        
        try:
            # Create EC2 client
            ec2 = boto3.client('ec2', region_name=region)
            
            # Stop instances
            response = ec2.stop_instances(InstanceIds=instance_ids)
            
            # Process results
            stopping_instances = response.get('StoppingInstances', [])
            if stopping_instances:
                print_color(f"Successfully sent stop command to {len(stopping_instances)} instances", "green")
                stopped_count += len(stopping_instances)
                
                for instance in stopping_instances:
                    instance_id = instance['InstanceId']
                    prev_state = instance['PreviousState']['Name']
                    current_state = instance['CurrentState']['Name']
                    print(f" - {instance_id}: {prev_state} -> {current_state}")
            else:
                print_color("No instances were stopped", "yellow")
                
        except ClientError as e:
            print_color(f"Error stopping instances in {region_name} region: {e}", "red")
    
    return stopped_count

def confirm_action():
    """Confirm user action"""
    print_color("\nWarning: This will stop all EC2 instances in all regions!", "red")
    print_color("Please confirm you want to continue (y/n): ", "yellow")
    
    response = input().strip().lower()
    return response == 'y' or response == 'yes'

def watch_instances(instances_by_region):
    """Monitor instance stop status"""
    print_color("\nMonitoring instance stop status...", "blue")
    
    all_stopped = False
    attempt = 0
    max_attempts = 10
    
    while not all_stopped and attempt < max_attempts:
        attempt += 1
        all_stopped = True
        still_running = 0
        
        print_color(f"\nChecking status (attempt {attempt}/{max_attempts})...", "yellow")
        
        for region, instances in instances_by_region.items():
            if not instances:
                continue
                
            region_name = REGION_NAMES.get(region, region)
            ec2 = boto3.client('ec2', region_name=region)
            
            # Extract instance IDs
            instance_ids = [instance['id'] for instance in instances]
            
            try:
                # Get current status
                response = ec2.describe_instances(InstanceIds=instance_ids)
                
                # Check status
                for reservation in response['Reservations']:
                    for instance in reservation['Instances']:
                        instance_id = instance['InstanceId']
                        state = instance['State']['Name']
                        
                        if state not in ['stopped', 'terminated']:
                            all_stopped = False
                            still_running += 1
                            print(f" - {region_name}: {instance_id} still in {state} state")
                
            except ClientError as e:
                print_color(f"Error getting instance status in {region_name} region: {e}", "red")
                all_stopped = False
        
        if not all_stopped:
            if still_running > 0:
                print_color(f"{still_running} instances still stopping, waiting 30 seconds...", "yellow")
                time.sleep(30)
            else:
                print_color("Unable to get status for some instances, waiting 30 seconds...", "yellow")
                time.sleep(30)
        else:
            print_color("All instances have stopped!", "green")
    
    if attempt >= max_attempts and not all_stopped:
        print_color("Maximum attempts reached but some instances may not be fully stopped", "yellow")
        print_color("Please check AWS Console for instance status", "yellow")
    
    return all_stopped

def main():
    """Main function"""
    print_color("Starting EC2 instance shutdown...", "yellow")
    
    # Check AWS credentials
    try:
        boto3.client('sts').get_caller_identity()
    except Exception as e:
        print_color(f"Invalid AWS credentials: {e}", "red")
        print("Please run 'aws configure' to configure your AWS credentials")
        return 1
    
    # Get running instances
    instances_by_region, total_instances = get_running_instances()
    
    if total_instances == 0:
        print_color("\nNo running instances found", "green")
        return 0
    
    # Confirm action
    if not confirm_action():
        print_color("Operation cancelled", "yellow")
        return 0
    
    # Stop instances
    stopped_count = stop_instances(instances_by_region)
    
    if stopped_count == 0:
        print_color("\nNo instances were stopped", "yellow")
        return 0
    
    print_color(f"\nSent stop command to {stopped_count} instances", "green")
    
    # Monitor stop status
    watch_instances(instances_by_region)
    
    print_color("\nInstance stop operation complete!", "green")
    print_color("Note: Please check AWS Console to confirm all instances have stopped to avoid unnecessary charges", "yellow")
    return 0

if __name__ == "__main__":
    sys.exit(main())