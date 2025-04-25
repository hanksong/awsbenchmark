#!/usr/bin/env python3
# generate_instance_info.py
# generate instance info from terraform output

import json
import os
import sys
import argparse

def main():
    parser = argparse.ArgumentParser(description="generate instance info from terraform output")
    parser.add_argument("--terraform-output", default="../terraform_output.json", help="Terraform output json file")
    parser.add_argument("--output", default="../data/instance_info.json", help="output instance info json file")
    
    args = parser.parse_args()
    
    # make sure the output directory exists 
    output_dir = os.path.dirname(args.output)
    os.makedirs(output_dir, exist_ok=True)
    
    try:
        # read terraform output
        with open(args.terraform_output, 'r') as f:
            terraform_data = json.load(f)
        
        # construct instance info data structure
        instance_info = {
            "instances": {}
        }
        
        regions = ["tokyo", "sydney", "london"]
        region_map = {
            "tokyo": "ap-northeast-1",
            "sydney": "ap-southeast-2",
            "london": "eu-west-2"
        }
        
        public_ips_empty = True
        
        for region in regions:
            aws_region = region_map.get(region, "")
            
            public_ips = terraform_data["instance_public_ips"]["value"][region]
            private_ips = terraform_data["instance_private_ips"]["value"][region]
            
            # check if there is any non-empty public ip
            for ip in public_ips:
                if ip and ip != "":
                    public_ips_empty = False
                    break
            
            instance_info["instances"][aws_region] = {
                "public_ips": public_ips,
                "private_ips": private_ips
            }
        
        # save instance info to json file
        with open(args.output, 'w') as f:
            json.dump(instance_info, f, indent=2)
        
        print(f"instance info saved to: {args.output}")
        
        if public_ips_empty:
            print("\nwarning: all public ips are empty! please check the terraform config to ensure public ips are assigned.")
            print("you may need to do the following steps:")
            print("1. check if the vpc and subnet config has enabled auto assign public ip")
            print("2. check if the ec2 instance config has associate_public_ip_address=true")
            print("3. reapply the terraform config: cd terraform && terraform apply")
            
    except Exception as e:
        print(f"error: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 