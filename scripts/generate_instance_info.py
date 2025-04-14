#!/usr/bin/env python3
# generate_instance_info.py
# 从terraform_output.json生成instance_info.json文件

import json
import os
import sys
import argparse

def main():
    parser = argparse.ArgumentParser(description="从Terraform输出生成实例信息文件")
    parser.add_argument("--terraform-output", default="../terraform_output.json", help="Terraform输出JSON文件路径")
    parser.add_argument("--output", default="../data/instance_info.json", help="输出的实例信息JSON文件路径")
    
    args = parser.parse_args()
    
    # 确保输出目录存在
    output_dir = os.path.dirname(args.output)
    os.makedirs(output_dir, exist_ok=True)
    
    try:
        # 读取Terraform输出
        with open(args.terraform_output, 'r') as f:
            terraform_data = json.load(f)
        
        # 构造实例信息数据结构
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
            
            # 检查是否有非空公网IP
            for ip in public_ips:
                if ip and ip != "":
                    public_ips_empty = False
                    break
            
            instance_info["instances"][aws_region] = {
                "public_ips": public_ips,
                "private_ips": private_ips
            }
        
        # 保存实例信息到JSON文件
        with open(args.output, 'w') as f:
            json.dump(instance_info, f, indent=2)
        
        print(f"实例信息已保存到: {args.output}")
        
        if public_ips_empty:
            print("\n警告: 所有公网IP都为空！请检查Terraform配置确保已分配公网IP。")
            print("您可能需要执行以下步骤:")
            print("1. 确认VPC和子网配置中已启用自动分配公网IP")
            print("2. 确认EC2实例配置中的associate_public_ip_address=true")
            print("3. 重新应用Terraform配置: cd terraform && terraform apply")
            
    except Exception as e:
        print(f"错误: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 