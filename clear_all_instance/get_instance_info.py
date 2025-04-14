#!/usr/bin/env python3
# 从AWS获取实例信息并生成instance_info.json文件

import os
import json
import subprocess
import sys
import boto3
from botocore.exceptions import ClientError

# 项目根目录
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 区域列表
REGIONS = ["ap-northeast-1", "ap-southeast-2", "eu-west-2"]
REGION_NAMES = {"ap-northeast-1": "东京", "ap-southeast-2": "悉尼", "eu-west-2": "伦敦"}

def print_color(text, color):
    """打印彩色文本"""
    colors = {
        "green": "\033[0;32m",
        "yellow": "\033[1;33m",
        "red": "\033[0;31m",
        "reset": "\033[0m"
    }
    print(f"{colors.get(color, colors['reset'])}{text}{colors['reset']}")

def get_instance_info():
    """从AWS获取实例信息"""
    instance_info = {"instances": {}}
    
    for region in REGIONS:
        region_name = REGION_NAMES.get(region, region)
        print_color(f"\n获取{region_name}区域 ({region}) 的实例信息...", "yellow")
        
        try:
            # 创建EC2客户端
            ec2 = boto3.client('ec2', region_name=region)
            
            # 获取有Project=aws-network-benchmark标签的实例
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
            
            # 提取实例信息
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
                print_color(f"在{region_name}区域没有找到实例", "yellow")
                continue
                
            print_color(f"在{region_name}区域找到 {len(instance_ids)} 个实例:", "green")
            for i, instance_id in enumerate(instance_ids):
                public_ip = public_ips[i] if i < len(public_ips) else "无公网IP"
                print(f" - {instance_id} ({public_ip})")
            
            # 添加到实例信息
            instance_info["instances"][region] = {
                "public_ips": public_ips,
                "private_ips": private_ips,
                "instance_ids": instance_ids
            }
            
        except ClientError as e:
            print_color(f"获取{region_name}区域实例时出错: {e}", "red")
    
    return instance_info

def save_instance_info(instance_info):
    """保存实例信息到文件"""
    # 确保data目录存在
    data_dir = os.path.join(PROJECT_ROOT, "data")
    os.makedirs(data_dir, exist_ok=True)
    
    # 保存到文件
    instance_info_path = os.path.join(data_dir, "instance_info.json")
    with open(instance_info_path, 'w') as f:
        json.dump(instance_info, f, indent=2)
    
    print_color(f"\n实例信息已保存到: {instance_info_path}", "green")
    return instance_info_path

def main():
    """主函数"""
    print_color("开始获取实例信息...", "yellow")
    
    # 检查AWS凭证
    try:
        boto3.client('sts').get_caller_identity()
    except Exception as e:
        print_color(f"AWS凭证无效: {e}", "red")
        print("请运行 'aws configure' 配置您的AWS凭证")
        return 1
    
    # 获取实例信息
    instance_info = get_instance_info()
    
    # 检查是否获取到任何实例
    any_instances = False
    for region, info in instance_info["instances"].items():
        if info.get("instance_ids"):
            any_instances = True
            break
    
    if not any_instances:
        print_color("错误: 未在任何区域找到实例", "red")
        return 1
    
    # 保存实例信息
    save_instance_info(instance_info)
    
    print_color("实例信息获取完成!", "green")
    return 0

if __name__ == "__main__":
    sys.exit(main()) 