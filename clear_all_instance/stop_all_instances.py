#!/usr/bin/env python3
# 停止所有区域的EC2实例

import os
import json
import sys
import time
import boto3
from botocore.exceptions import ClientError

# 项目根目录
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 区域列表 通过读取terraform/config.json获取    
with open(os.path.join(PROJECT_ROOT, 'terraform', 'config.json'), 'r') as f:
    config = json.load(f)

REGIONS = config.get('aws_regions', [])
REGION_NAMES = {
    "ap-northeast-1": "东京",
    "us-east-1": "弗吉尼亚",
    "eu-west-2": "伦敦",
    "ap-southeast-2": "悉尼",
    "me-south-1": "巴林",
    "sa-east-1": "圣保罗",
    "ca-central-1": "蒙特利尔",
    "eu-west-3": "巴黎",
    "eu-north-1": "法兰克福",
    "eu-west-1": "爱尔兰",
    "eu-central-1": "米兰",
    "eu-south-1": "马德里"
}

def print_color(text, color):
    """打印彩色文本"""
    colors = {
        "green": "\033[0;32m",
        "yellow": "\033[1;33m",
        "red": "\033[0;31m",
        "blue": "\033[0;34m",
        "reset": "\033[0m"
    }
    print(f"{colors.get(color, colors['reset'])}{text}{colors['reset']}")

def get_running_instances():
    """获取所有区域中正在运行的EC2实例"""
    instances_by_region = {}
    total_instances = 0
    
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
            instance_list = []
            
            for reservation in response['Reservations']:
                for instance in reservation['Instances']:
                    instance_id = instance['InstanceId']
                    instance_state = instance['State']['Name']
                    instance_name = "未命名"
                    
                    # 查找名称标签
                    for tag in instance.get('Tags', []):
                        if tag['Key'] == 'Name':
                            instance_name = tag['Value']
                            break
                    
                    # 获取公网IP（如果有）
                    public_ip = instance.get('PublicIpAddress', '无公网IP')
                    
                    instance_list.append({
                        'id': instance_id,
                        'state': instance_state,
                        'name': instance_name,
                        'public_ip': public_ip
                    })
            
            if not instance_list:
                print_color(f"在{region_name}区域没有找到运行中的实例", "yellow")
                continue
                
            print_color(f"在{region_name}区域找到 {len(instance_list)} 个运行中的实例:", "green")
            for instance in instance_list:
                print(f" - {instance['id']} ({instance['name']}) [{instance['public_ip']}] - {instance['state']}")
            
            instances_by_region[region] = instance_list
            total_instances += len(instance_list)
            
        except ClientError as e:
            print_color(f"获取{region_name}区域实例时出错: {e}", "red")
    
    return instances_by_region, total_instances

def stop_instances(instances_by_region):
    """停止所有区域中的实例"""
    stopped_count = 0
    
    for region, instances in instances_by_region.items():
        region_name = REGION_NAMES.get(region, region)
        
        if not instances:
            continue
        
        print_color(f"\n正在停止{region_name}区域的 {len(instances)} 个实例...", "blue")
        
        # 提取实例ID
        instance_ids = [instance['id'] for instance in instances]
        
        try:
            # 创建EC2客户端
            ec2 = boto3.client('ec2', region_name=region)
            
            # 停止实例
            response = ec2.stop_instances(InstanceIds=instance_ids)
            
            # 处理结果
            stopping_instances = response.get('StoppingInstances', [])
            if stopping_instances:
                print_color(f"成功发送停止命令到 {len(stopping_instances)} 个实例", "green")
                stopped_count += len(stopping_instances)
                
                for instance in stopping_instances:
                    instance_id = instance['InstanceId']
                    prev_state = instance['PreviousState']['Name']
                    current_state = instance['CurrentState']['Name']
                    print(f" - {instance_id}: {prev_state} -> {current_state}")
            else:
                print_color("没有实例被停止", "yellow")
                
        except ClientError as e:
            print_color(f"停止{region_name}区域实例时出错: {e}", "red")
    
    return stopped_count

def confirm_action():
    """确认用户操作"""
    print_color("\n警告: 此操作将停止所有区域中的EC2实例！", "red")
    print_color("请确认您要继续 (y/n): ", "yellow")
    
    response = input().strip().lower()
    return response == 'y' or response == 'yes'

def watch_instances(instances_by_region):
    """监控实例停止状态"""
    print_color("\n监控实例停止状态...", "blue")
    
    all_stopped = False
    attempt = 0
    max_attempts = 10
    
    while not all_stopped and attempt < max_attempts:
        attempt += 1
        all_stopped = True
        still_running = 0
        
        print_color(f"\n检查状态 (尝试 {attempt}/{max_attempts})...", "yellow")
        
        for region, instances in instances_by_region.items():
            if not instances:
                continue
                
            region_name = REGION_NAMES.get(region, region)
            ec2 = boto3.client('ec2', region_name=region)
            
            # 提取实例ID
            instance_ids = [instance['id'] for instance in instances]
            
            try:
                # 获取当前状态
                response = ec2.describe_instances(InstanceIds=instance_ids)
                
                # 检查状态
                for reservation in response['Reservations']:
                    for instance in reservation['Instances']:
                        instance_id = instance['InstanceId']
                        state = instance['State']['Name']
                        
                        if state not in ['stopped', 'terminated']:
                            all_stopped = False
                            still_running += 1
                            print(f" - {region_name}: {instance_id} 仍在 {state} 状态")
                
            except ClientError as e:
                print_color(f"获取{region_name}区域实例状态时出错: {e}", "red")
                all_stopped = False
        
        if not all_stopped:
            if still_running > 0:
                print_color(f"还有 {still_running} 个实例正在停止中，等待30秒...", "yellow")
                time.sleep(30)
            else:
                print_color("无法获取某些实例的状态，等待30秒...", "yellow")
                time.sleep(30)
        else:
            print_color("所有实例已停止！", "green")
    
    if attempt >= max_attempts and not all_stopped:
        print_color("已达到最大尝试次数，但仍有一些实例可能未完全停止", "yellow")
        print_color("请登录AWS控制台检查实例状态", "yellow")
    
    return all_stopped

def main():
    """主函数"""
    print_color("开始停止EC2实例...", "yellow")
    
    # 检查AWS凭证
    try:
        boto3.client('sts').get_caller_identity()
    except Exception as e:
        print_color(f"AWS凭证无效: {e}", "red")
        print("请运行 'aws configure' 配置您的AWS凭证")
        return 1
    
    # 获取运行中的实例
    instances_by_region, total_instances = get_running_instances()
    
    if total_instances == 0:
        print_color("\n没有找到运行中的实例", "green")
        return 0
    
    # 确认操作
    if not confirm_action():
        print_color("操作已取消", "yellow")
        return 0
    
    # 停止实例
    stopped_count = stop_instances(instances_by_region)
    
    if stopped_count == 0:
        print_color("\n没有实例被停止", "yellow")
        return 0
    
    print_color(f"\n已发送停止命令到 {stopped_count} 个实例", "green")
    
    # 监控停止状态
    watch_instances(instances_by_region)
    
    print_color("\n实例停止操作完成!", "green")
    print_color("提示: 请记得检查AWS控制台确认所有实例已停止，以避免不必要的费用", "yellow")
    return 0

if __name__ == "__main__":
    sys.exit(main()) 