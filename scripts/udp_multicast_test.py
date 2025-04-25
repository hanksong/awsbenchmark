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
    """load the ec2 instance info"""
    try:
        with open(json_file, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"error: unable to load the instance info file {json_file}: {e}")
        sys.exit(1)

def run_udp_test(server_ip, client_ips, ssh_key, bandwidth="1G", duration=10, output_dir="../data"):
    """execute the iperf3 udp multicast test"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results = []
    
    # make sure the output directory exists
    os.makedirs(output_dir, exist_ok=True)
    
    # start the iperf3 server on the server
    server_cmd = f"ssh -i {ssh_key} -o StrictHostKeyChecking=no ec2-user@{server_ip} 'systemctl stop iperf3 && iperf3 -s -D'"
    try:
        subprocess.run(server_cmd, shell=True, check=True)
        print(f"iperf3 server started on {server_ip}")
    except subprocess.CalledProcessError as e:
        print(f"warning: unable to start the iperf3 server on {server_ip}: {e}")
    
    # give the server some time to start
    time.sleep(2)
    
    # run the iperf3 udp test on each client
    for i, client_ip in enumerate(client_ips):
        output_file = f"{output_dir}/udp_multicast_{server_ip}_to_{client_ip}_{timestamp}.json"
        
        # run the iperf3 test on the client
        client_cmd = (
            f"ssh -i {ssh_key} -o StrictHostKeyChecking=no ec2-user@{client_ip} "
            f"'iperf3 -c {server_ip} -u -b {bandwidth} -t {duration} -J > /tmp/iperf3_udp_result.json'"
        )
        
        try:
            print(f"starting udp test ({i+1}/{len(client_ips)}): {client_ip} -> {server_ip}")
            subprocess.run(client_cmd, shell=True, check=True)
            
            # get the test results
            get_result_cmd = f"scp -i {ssh_key} -o StrictHostKeyChecking=no ec2-user@{client_ip}:/tmp/iperf3_udp_result.json {output_file}"
            subprocess.run(get_result_cmd, shell=True, check=True)
            
            print(f"test completed, results saved to {output_file}")
            results.append({
                "client_ip": client_ip,
                "server_ip": server_ip,
                "result_file": output_file
            })
        except subprocess.CalledProcessError as e:
            print(f"error: udp test failed {client_ip} -> {server_ip}: {e}")
    
    # stop the iperf3 server
    stop_cmd = f"ssh -i {ssh_key} -o StrictHostKeyChecking=no ec2-user@{server_ip} 'pkill iperf3 && systemctl start iperf3'"
    try:
        subprocess.run(stop_cmd, shell=True, check=True)
    except subprocess.CalledProcessError:
        pass
    
    return results

def main():
    parser = argparse.ArgumentParser(description="execute the udp multicast test between ec2 instances")
    parser.add_argument("--instance-info", required=True, help="the json file containing the ec2 instance info")
    parser.add_argument("--ssh-key", required=True, help="the ssh key file path")
    parser.add_argument("--bandwidth", default="1G", help="the udp bandwidth limit, e.g. '100M' or '1G'")
    parser.add_argument("--duration", type=int, default=10, help="the duration of each test (seconds)")
    parser.add_argument("--output-dir", default="../data", help="the output directory for the test results")
    parser.add_argument("--server-region", required=True, help="the region of the server")
    parser.add_argument("--use-private-ip", action="store_true", help="use the private ip instead of the public ip for the test")
    parser.add_argument("--intra-region", action="store_true", help="also test between instances in the same region")
    
    args = parser.parse_args()
    
    # load the instance info
    instance_data = load_instance_info(args.instance_info)
    
    # create the test results directory
    os.makedirs(args.output_dir, exist_ok=True)
    
    # verify the server region exists
    if args.server_region not in instance_data["instances"]:
        print(f"error: the server region {args.server_region} does not exist")
        sys.exit(1)
    
    # select the ip type based on the use_private_ip flag
    ip_type = "private_ips" if args.use_private_ip else "public_ips"
    
    # get all the server ips
    server_ips = instance_data["instances"][args.server_region][ip_type]
    all_results = []
    
    # 如果服务器区域有多个实例且启用了intra-region选项，则每个实例轮流作为服务器
    if len(server_ips) > 1 and args.intra_region:
        for server_idx, server_ip in enumerate(server_ips):
            print(f"\nstarting the udp multicast test, server: {args.server_region} instance {server_idx+1}")
            print(f"server ip: {server_ip} (using {('private' if args.use_private_ip else 'public')})")
            
            # 收集其他区域的客户端IP
            client_ips = []
            client_regions = []
            for region, info in instance_data["instances"].items():
                # 如果是不同区域，添加第一个IP作为客户端
                if region != args.server_region:
                    client_ips.append(info[ip_type][0])
                    client_regions.append(region)
                # 如果是同一区域，添加除当前服务器外的所有实例作为客户端
                elif region == args.server_region:
                    for i, ip in enumerate(info[ip_type]):
                        if ip != server_ip:  # 排除当前服务器IP
                            client_ips.append(ip)
                            client_regions.append(f"{region}_instance{i+1}")
            
            if not client_ips:
                print("error: no client instances found")
                continue
                
            print(f"client regions/instances: {', '.join(client_regions)}")
            print(f"client ips: {', '.join(client_ips)}")
            
            # run the udp test
            results = run_udp_test(
                server_ip, client_ips, args.ssh_key, 
                args.bandwidth, args.duration, args.output_dir
            )
            
            all_results.extend(results)
    else:
        # 传统的多区域测试方式，服务器区域只使用第一个实例
        server_ip = server_ips[0]
        
        # 获取所有其他区域的客户端IP（每个区域的第一个实例）
        client_ips = []
        client_regions = []
        for region, info in instance_data["instances"].items():
            if region != args.server_region:
                client_ips.append(info[ip_type][0])
                client_regions.append(region)
        
        if not client_ips:
            print("error: no client instances found")
            sys.exit(1)
        
        print(f"\nstarting the udp multicast test, server region: {args.server_region}")
        print(f"server ip: {server_ip} (using {('private' if args.use_private_ip else 'public')})")
        print(f"client regions: {', '.join(client_regions)}")
        print(f"client ips: {', '.join(client_ips)}")
        
        # run the udp test
        all_results = run_udp_test(
            server_ip, client_ips, args.ssh_key, 
            args.bandwidth, args.duration, args.output_dir
        )
    
    # save the test summary
    summary_file = f"{args.output_dir}/udp_multicast_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    summary = {
        "server_region": args.server_region,
        "ip_type": "private" if args.use_private_ip else "public",
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "results": all_results
    }
    
    with open(summary_file, 'w') as f:
        json.dump(summary, f, indent=2)
    
    print(f"\ntest summary saved to {summary_file}")
    print(f"completed {len(all_results)} udp tests")

if __name__ == "__main__":
    main()
