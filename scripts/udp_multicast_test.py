#!/usr/bin/env python3
# udp_multicast_test.py
# 执行一对多UDP网络性能测试

import json
import argparse
import subprocess
import time
import os
import sys
from datetime import datetime

def load_instance_info(json_file):
    """加载EC2实例信息"""
    try:
        with open(json_file, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"错误：无法加载实例信息文件 {json_file}: {e}")
        sys.exit(1)

def run_udp_test(server_ip, client_ips, ssh_key, bandwidth="1G", duration=10, output_dir="../data"):
    """执行iperf3一对多UDP测试"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results = []
    
    # 确保输出目录存在
    os.makedirs(output_dir, exist_ok=True)
    
    # 在服务器端启动iperf3服务器
    server_cmd = f"ssh -i {ssh_key} -o StrictHostKeyChecking=no ec2-user@{server_ip} 'systemctl stop iperf3 && iperf3 -s -D'"
    try:
        subprocess.run(server_cmd, shell=True, check=True)
        print(f"iperf3服务器在 {server_ip} 上启动")
    except subprocess.CalledProcessError as e:
        print(f"警告：无法在 {server_ip} 上启动iperf3服务器: {e}")
    
    # 给服务器一点时间启动
    time.sleep(2)
    
    # 在每个客户端运行iperf3 UDP测试
    for i, client_ip in enumerate(client_ips):
        output_file = f"{output_dir}/udp_multicast_{server_ip}_to_{client_ip}_{timestamp}.json"
        
        # 在客户端运行iperf3测试
        client_cmd = (
            f"ssh -i {ssh_key} -o StrictHostKeyChecking=no ec2-user@{client_ip} "
            f"'iperf3 -c {server_ip} -u -b {bandwidth} -t {duration} -J > /tmp/iperf3_udp_result.json'"
        )
        
        try:
            print(f"开始UDP测试 ({i+1}/{len(client_ips)}): {client_ip} -> {server_ip}")
            subprocess.run(client_cmd, shell=True, check=True)
            
            # 获取测试结果
            get_result_cmd = f"scp -i {ssh_key} -o StrictHostKeyChecking=no ec2-user@{client_ip}:/tmp/iperf3_udp_result.json {output_file}"
            subprocess.run(get_result_cmd, shell=True, check=True)
            
            print(f"测试完成，结果保存到 {output_file}")
            results.append({
                "client_ip": client_ip,
                "server_ip": server_ip,
                "result_file": output_file
            })
        except subprocess.CalledProcessError as e:
            print(f"错误：UDP测试失败 {client_ip} -> {server_ip}: {e}")
    
    # 停止服务器上的iperf3
    stop_cmd = f"ssh -i {ssh_key} -o StrictHostKeyChecking=no ec2-user@{server_ip} 'pkill iperf3 && systemctl start iperf3'"
    try:
        subprocess.run(stop_cmd, shell=True, check=True)
    except subprocess.CalledProcessError:
        pass
    
    return results

def main():
    parser = argparse.ArgumentParser(description="执行EC2实例间的一对多UDP网络性能测试")
    parser.add_argument("--instance-info", required=True, help="包含EC2实例信息的JSON文件路径")
    parser.add_argument("--ssh-key", required=True, help="SSH密钥文件路径")
    parser.add_argument("--bandwidth", default="1G", help="UDP带宽限制，例如'100M'或'1G'")
    parser.add_argument("--duration", type=int, default=10, help="每次测试持续时间（秒）")
    parser.add_argument("--output-dir", default="../data", help="测试结果输出目录")
    parser.add_argument("--server-region", required=True, help="服务器所在区域")
    parser.add_argument("--use-private-ip", action="store_true", help="使用私有IP而非公网IP进行测试")
    
    args = parser.parse_args()
    
    # 加载实例信息
    instance_data = load_instance_info(args.instance_info)
    
    # 创建测试结果目录
    os.makedirs(args.output_dir, exist_ok=True)
    
    # 验证服务器区域存在
    if args.server_region not in instance_data["instances"]:
        print(f"错误：服务器区域 {args.server_region} 不存在")
        sys.exit(1)
    
    # 根据参数选择使用公网IP还是私有IP
    ip_type = "private_ips" if args.use_private_ip else "public_ips"
    
    # 获取服务器IP
    server_ip = instance_data["instances"][args.server_region][ip_type][0]
    
    # 获取所有其他区域的客户端IP
    client_ips = []
    client_regions = []
    for region, info in instance_data["instances"].items():
        if region != args.server_region:
            client_ips.append(info[ip_type][0])
            client_regions.append(region)
    
    if not client_ips:
        print("错误：没有找到客户端实例")
        sys.exit(1)
    
    print(f"\n开始一对多UDP测试，服务器区域: {args.server_region}")
    print(f"服务器IP: {server_ip} (使用{('私有' if args.use_private_ip else '公网')}IP)")
    print(f"客户端区域: {', '.join(client_regions)}")
    print(f"客户端IP: {', '.join(client_ips)}")
    
    # 运行UDP测试
    results = run_udp_test(
        server_ip, client_ips, args.ssh_key, 
        args.bandwidth, args.duration, args.output_dir
    )
    
    # 保存测试摘要
    summary_file = f"{args.output_dir}/udp_multicast_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    summary = {
        "server_region": args.server_region,
        "server_ip": server_ip,
        "client_regions": client_regions,
        "ip_type": "private" if args.use_private_ip else "public",
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "results": results
    }
    
    with open(summary_file, 'w') as f:
        json.dump(summary, f, indent=2)
    
    print(f"\n测试摘要已保存到 {summary_file}")
    print(f"共完成 {len(results)} 次UDP测试")

if __name__ == "__main__":
    main()
