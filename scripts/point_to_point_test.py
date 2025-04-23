#!/usr/bin/env python3
# point_to_point_test.py
# Execute point-to-point network performance tests

import json
import argparse
import subprocess
import time
import os
import sys
from datetime import datetime

def load_instance_info(json_file):
    """Load EC2 instance information"""
    try:
        with open(json_file, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error: Unable to load instance info file {json_file}: {e}")
        sys.exit(1)

def run_test(server_ip, client_ip, ssh_key, duration=10, parallel=1, output_dir="../data"):
    """Execute iperf3 point-to-point test"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"{output_dir}/p2p_{server_ip}_to_{client_ip}_{timestamp}.json"
    
    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)
    
    # Start iperf3 server on server side (if not already running)
    server_cmd = f"ssh -i {ssh_key} -o StrictHostKeyChecking=no ec2-user@{server_ip} 'systemctl is-active iperf3 || systemctl start iperf3'"
    try:
        subprocess.run(server_cmd, shell=True, check=True)
        print(f"iperf3 server started on {server_ip}")
    except subprocess.CalledProcessError as e:
        print(f"Warning: Unable to start iperf3 server on {server_ip}: {e}")
    
    # Run iperf3 test on client
    client_cmd = (
        f"ssh -i {ssh_key} -o StrictHostKeyChecking=no ec2-user@{client_ip} "
        f"'iperf3 -c {server_ip} -t {duration} -P {parallel} -J > /tmp/iperf3_result.json'"
    )
    
    try:
        print(f"Starting test: {client_ip} -> {server_ip}")
        subprocess.run(client_cmd, shell=True, check=True)
        
        # Get test results
        get_result_cmd = f"scp -i {ssh_key} -o StrictHostKeyChecking=no ec2-user@{client_ip}:/tmp/iperf3_result.json {output_file}"
        subprocess.run(get_result_cmd, shell=True, check=True)
        
        print(f"Test completed, results saved to {output_file}")
        return output_file
    except subprocess.CalledProcessError as e:
        print(f"Error: Test failed {client_ip} -> {server_ip}: {e}")
        return None

def main():
    parser = argparse.ArgumentParser(description="Execute point-to-point network performance tests between EC2 instances")
    parser.add_argument("--instance-info", required=True, help="Path to JSON file containing EC2 instance information")
    parser.add_argument("--ssh-key", required=True, help="Path to SSH key file")
    parser.add_argument("--duration", type=int, default=10, help="Duration of each test in seconds")
    parser.add_argument("--parallel", type=int, default=1, help="Number of parallel streams")
    parser.add_argument("--output-dir", default="../data", help="Output directory for test results")
    parser.add_argument("--all-regions", action="store_true", help="Test all region combinations")
    parser.add_argument("--source-region", help="Source region")
    parser.add_argument("--target-region", help="Target region")
    parser.add_argument("--use-private-ip", action="store_true", help="Use private IPs instead of public IPs for testing")
    parser.add_argument("--intra-region", action="store_true", help="Also test between instances in the same region")
    
    args = parser.parse_args()
    
    # Load instance information
    instance_data = load_instance_info(args.instance_info)
    
    # Create results directory
    os.makedirs(args.output_dir, exist_ok=True)
    
    results = []
    
    if args.all_regions:
        # Test all region combinations
        regions = list(instance_data["instances"].keys())
        for source_region in regions:
            for target_region in regions:
                # 选择IP类型
                ip_type = "private_ips" if args.use_private_ip else "public_ips"
                
                # 获取区域中的所有IP
                source_ips = instance_data["instances"][source_region][ip_type]
                target_ips = instance_data["instances"][target_region][ip_type]
                
                # 如果是不同区域，或者是相同区域并且启用了intra-region选项
                if source_region != target_region or args.intra_region:
                    # 如果是相同区域，测试所有实例对之间的连接
                    if source_region == target_region and len(source_ips) > 1:
                        for i, s_ip in enumerate(source_ips):
                            for j, t_ip in enumerate(target_ips):
                                # 避免自己测自己
                                if i != j:
                                    print(f"\nTesting P2P within {source_region}: Instance {i+1} -> Instance {j+1} (using {('private' if args.use_private_ip else 'public')} IPs)")
                                    result_file = run_test(
                                        t_ip, s_ip, args.ssh_key, 
                                        args.duration, args.parallel, args.output_dir
                                    )
                                    if result_file:
                                        results.append({
                                            "source_region": f"{source_region}_instance{i+1}",
                                            "target_region": f"{target_region}_instance{j+1}",
                                            "result_file": result_file
                                        })
                    # 如果是不同区域，测试第一个实例之间的连接
                    else:
                        source_ip = source_ips[0]
                        target_ip = target_ips[0]
                        
                        print(f"\nTesting regions: {source_region} -> {target_region} (using {('private' if args.use_private_ip else 'public')} IPs)")
                        result_file = run_test(
                            target_ip, source_ip, args.ssh_key, 
                            args.duration, args.parallel, args.output_dir
                        )
                        if result_file:
                            results.append({
                                "source_region": source_region,
                                "target_region": target_region,
                                "result_file": result_file
                            })
    elif args.source_region and args.target_region:
        # Test specific region combination
        if args.source_region not in instance_data["instances"]:
            print(f"Error: Source region {args.source_region} does not exist")
            sys.exit(1)
        if args.target_region not in instance_data["instances"]:
            print(f"Error: Target region {args.target_region} does not exist")
            sys.exit(1)
            
        # Choose IP type based on args
        ip_type = "private_ips" if args.use_private_ip else "public_ips"
        
        # 如果是相同区域，并且有多个实例
        if args.source_region == args.target_region and len(instance_data["instances"][args.source_region][ip_type]) > 1 and args.intra_region:
            source_ips = instance_data["instances"][args.source_region][ip_type]
            target_ips = instance_data["instances"][args.target_region][ip_type]
            
            for i, s_ip in enumerate(source_ips):
                for j, t_ip in enumerate(target_ips):
                    # 避免自己测自己
                    if i != j:
                        print(f"\nTesting P2P within {args.source_region}: Instance {i+1} -> Instance {j+1} (using {('private' if args.use_private_ip else 'public')} IPs)")
                        result_file = run_test(
                            t_ip, s_ip, args.ssh_key, 
                            args.duration, args.parallel, args.output_dir
                        )
                        if result_file:
                            results.append({
                                "source_region": f"{args.source_region}_instance{i+1}",
                                "target_region": f"{args.target_region}_instance{j+1}",
                                "result_file": result_file
                            })
        else:
            source_ip = instance_data["instances"][args.source_region][ip_type][0]
            target_ip = instance_data["instances"][args.target_region][ip_type][0]
            
            print(f"\nTesting regions: {args.source_region} -> {args.target_region} (using {('private' if args.use_private_ip else 'public')} IPs)")
            result_file = run_test(
                target_ip, source_ip, args.ssh_key, 
                args.duration, args.parallel, args.output_dir
            )
            if result_file:
                results.append({
                    "source_region": args.source_region,
                    "target_region": args.target_region,
                    "result_file": result_file
                })
    else:
        print("Error: Must specify either --all-regions or both --source-region and --target-region")
        sys.exit(1)
    
    # Save test summary
    summary_file = f"{args.output_dir}/p2p_test_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(summary_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\nTest summary saved to {summary_file}")
    print(f"Completed {len(results)} tests")

if __name__ == "__main__":
    main()
