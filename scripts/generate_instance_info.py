#!/usr/bin/env python3
# generate_instance_info.py
# generate instance info from terraform output

import json
import os
# import argparse # No longer needed here

# Modified function to accept paths as arguments


def generate_instance_info(terraform_output_path, output_path):

    # make sure the output directory exists
    output_dir = os.path.dirname(output_path)  # Use output_path
    os.makedirs(output_dir, exist_ok=True)

    try:
        # read terraform output
        with open(terraform_output_path, 'r') as f:  # Use terraform_output_path
            terraform_data = json.load(f)

        # construct instance info data structure
        instance_info = {
            "instances": {}
        }

        # Dynamically get regions from terraform output keys if possible
        # Assuming output keys like 'london', 'tokyo', 'virginia' exist under 'value'
        # This makes it more robust than the hardcoded list.
        if "instance_public_ips" in terraform_data and "value" in terraform_data["instance_public_ips"]:
            regions_from_tf = list(
                terraform_data["instance_public_ips"]["value"].keys())
            print(f"Regions detected from Terraform output: {regions_from_tf}")
        else:
            print(
                "Warning: Could not detect regions from Terraform output keys. Falling back to default.")
            # Fallback or error handling needed if dynamic detection fails and is required
            # For now, let's assume the structure is consistent or handle potential KeyError below
            regions_from_tf = []  # Or raise an error

        # Map short names (like 'tokyo') to AWS region codes (like 'ap-northeast-1')
        # This mapping might need adjustment based on your actual Terraform output keys
        # and the desired keys in instance_info.json
        # A more robust approach might involve getting region directly from TF output if available
        region_map = {
            "tokyo": "ap-northeast-1",
            "sydney": "ap-southeast-2",
            "london": "eu-west-2",
            "virginia": "us-east-1",  # Added virginia based on TF output example
            # Add other potential mappings as needed
        }

        public_ips_empty = True

        # Iterate through regions found in Terraform output
        for region_key in regions_from_tf:
            # Use the map to get the standard AWS region code, default to the key itself if not found
            aws_region = region_map.get(region_key, region_key)

            # Check if keys exist before accessing
            if region_key not in terraform_data.get("instance_public_ips", {}).get("value", {}):
                print(
                    f"Warning: Public IPs for region key '{region_key}' not found in Terraform output. Skipping.")
                continue
            if region_key not in terraform_data.get("instance_private_ips", {}).get("value", {}):
                print(
                    f"Warning: Private IPs for region key '{region_key}' not found in Terraform output. Skipping.")
                continue

            public_ips = terraform_data["instance_public_ips"]["value"][region_key]
            private_ips = terraform_data["instance_private_ips"]["value"][region_key]

            # check if there is any non-empty public ip
            if isinstance(public_ips, list):
                for ip in public_ips:
                    if ip and ip != "":
                        public_ips_empty = False
                        break
            elif public_ips and public_ips != "":  # Handle case where it might not be a list
                public_ips_empty = False

            instance_info["instances"][aws_region] = {
                "public_ips": public_ips,
                "private_ips": private_ips
            }

        # save instance info to json file
        with open(output_path, 'w') as f:  # Use output_path
            json.dump(instance_info, f, indent=2)

        print(f"instance info saved to: {output_path}")  # Use output_path

        if public_ips_empty:
            print("\nwarning: all public ips are empty! please check the terraform config to ensure public ips are assigned.")
            print("you may need to do the following steps:")
            print(
                "1. check if the vpc and subnet config has enabled auto assign public ip")
            print(
                "2. check if the ec2 instance config has associate_public_ip_address=true")
            print("3. reapply the terraform config: cd terraform && terraform apply")

    except FileNotFoundError:
        print(
            f"error: Terraform output file not found at {terraform_output_path}")
        return 1
    except KeyError as e:
        print(
            f"error: Missing expected key {e} in Terraform output file {terraform_output_path}. Check terraform/outputs.tf.")
        return 1
    except Exception as e:
        print(f"error generating instance info: {e}")
        return 1

    return 0


# Removed the __main__ block as this script is now primarily called as a function
# if __name__ == "__main__":
#     sys.exit(generate_instance_info())
