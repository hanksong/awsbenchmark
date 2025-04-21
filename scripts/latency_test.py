#!/usr/bin/env python3
# latency_test.py
# Execute ping latency tests between EC2 instances

import json
import argparse
import subprocess
import time
import os
import sys
import re
from datetime import datetime
import csv

def load_instance_info(json_file):
    """Load EC2 instance information"""
    try:
        with open(json_file, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error: Unable to load instance info file {json_file}: {e}")
        sys.exit(1)

def run_ping_test(server_ip, client_ip, ssh_key, count=10, output_dir="../data"):
    """Execute ping latency test"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"{output_dir}/latency_{server_ip}_to_{client_ip}_{timestamp}.json"
    
    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)
    
    # Run ping test from client to server
    ping_cmd = (
        f"ssh -i {ssh_key} -o StrictHostKeyChecking=no ec2-user@{client_ip} "
        f"'ping -c {count} -i 0.2 {server_ip} > /tmp/ping_result.txt'"
    )
    
    try:
        print(f"Starting latency test: {client_ip} -> {server_ip}")
        subprocess.run(ping_cmd, shell=True, check=True)
        
        # Get ping results
        get_result_cmd = f"scp -i {ssh_key} -o StrictHostKeyChecking=no ec2-user@{client_ip}:/tmp/ping_result.txt /tmp/ping_result.txt"
        subprocess.run(get_result_cmd, shell=True, check=True)
        
        # Parse ping results
        ping_stats = parse_ping_results("/tmp/ping_result.txt")
        
        # Add test metadata
        ping_stats["source_ip"] = client_ip
        ping_stats["target_ip"] = server_ip
        ping_stats["timestamp"] = timestamp
        ping_stats["ping_count"] = count
        
        # Save results as JSON
        with open(output_file, 'w') as f:
            json.dump(ping_stats, f, indent=2)
        
        print(f"Latency test completed, results saved to {output_file}")
        return output_file, ping_stats
    except subprocess.CalledProcessError as e:
        print(f"Error: Latency test failed {client_ip} -> {server_ip}: {e}")
        return None, None

def parse_ping_results(result_file):
    """Parse ping results from output file"""
    stats = {
        "min_ms": None,
        "avg_ms": None,
        "max_ms": None,
        "mdev_ms": None,
        "packet_loss_percent": None,
        "packets_transmitted": None,
        "packets_received": None
    }
    
    try:
        with open(result_file, 'r') as f:
            content = f.read()
            
            # Extract packet stats
            packet_match = re.search(r'(\d+) packets transmitted, (\d+) received, (\d+)% packet loss', content)
            if packet_match:
                stats["packets_transmitted"] = int(packet_match.group(1))
                stats["packets_received"] = int(packet_match.group(2))
                stats["packet_loss_percent"] = float(packet_match.group(3))
            
            # Extract timing stats
            time_match = re.search(r'min/avg/max/mdev = ([\d\.]+)/([\d\.]+)/([\d\.]+)/([\d\.]+) ms', content)
            if time_match:
                stats["min_ms"] = float(time_match.group(1))
                stats["avg_ms"] = float(time_match.group(2))
                stats["max_ms"] = float(time_match.group(3))
                stats["mdev_ms"] = float(time_match.group(4))
        
        return stats
    except Exception as e:
        print(f"Error parsing ping results: {e}")
        return stats

def write_csv_summary(results, output_dir):
    """Write summary of latency tests to CSV file"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_file = f"{output_dir}/latency_results_{timestamp}.csv"
    
    try:
        with open(csv_file, 'w', newline='') as f:
            writer = csv.writer(f)
            # Write header
            writer.writerow([
                'source_region', 'target_region', 'min_latency_ms', 'avg_latency_ms',
                'max_latency_ms', 'mdev_ms', 'packet_loss_percent', 'file'
            ])
            
            # Write data rows
            for result in results:
                writer.writerow([
                    result['source_region'],
                    result['target_region'],
                    result['ping_stats']['min_ms'],
                    result['ping_stats']['avg_ms'],
                    result['ping_stats']['max_ms'],
                    result['ping_stats']['mdev_ms'],
                    result['ping_stats']['packet_loss_percent'],
                    result['result_file']
                ])
        
        print(f"Latency summary saved to {csv_file}")
        return csv_file
    except Exception as e:
        print(f"Error creating CSV summary: {e}")
        return None

def main():
    parser = argparse.ArgumentParser(description="Execute ping latency tests between EC2 instances")
    parser.add_argument("--instance-info", required=True, help="Path to JSON file containing EC2 instance information")
    parser.add_argument("--ssh-key", required=True, help="Path to SSH key file")
    parser.add_argument("--ping-count", type=int, default=20, help="Number of ping packets to send")
    parser.add_argument("--output-dir", default="../data", help="Output directory for test results")
    parser.add_argument("--all-regions", action="store_true", help="Test all region combinations")
    parser.add_argument("--source-region", help="Source region")
    parser.add_argument("--target-region", help="Target region")
    parser.add_argument("--use-private-ip", action="store_true", help="Use private IPs instead of public IPs for testing")
    
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
                if source_region != target_region:  # Avoid self-testing
                    # Choose IP type based on args
                    ip_type = "private_ips" if args.use_private_ip else "public_ips"
                    source_ip = instance_data["instances"][source_region][ip_type][0]
                    target_ip = instance_data["instances"][target_region][ip_type][0]
                    
                    print(f"\nTesting latency: {source_region} -> {target_region} (using {('private' if args.use_private_ip else 'public')} IPs)")
                    result_file, ping_stats = run_ping_test(
                        target_ip, source_ip, args.ssh_key, 
                        args.ping_count, args.output_dir
                    )
                    if result_file and ping_stats:
                        results.append({
                            "source_region": source_region,
                            "target_region": target_region,
                            "result_file": result_file,
                            "ping_stats": ping_stats
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
        source_ip = instance_data["instances"][args.source_region][ip_type][0]
        target_ip = instance_data["instances"][args.target_region][ip_type][0]
        
        print(f"\nTesting latency: {args.source_region} -> {args.target_region} (using {('private' if args.use_private_ip else 'public')} IPs)")
        result_file, ping_stats = run_ping_test(
            target_ip, source_ip, args.ssh_key, 
            args.ping_count, args.output_dir
        )
        if result_file and ping_stats:
            results.append({
                "source_region": args.source_region,
                "target_region": args.target_region,
                "result_file": result_file,
                "ping_stats": ping_stats
            })
    else:
        print("Error: Must specify either --all-regions or both --source-region and --target-region")
        sys.exit(1)
    
    # Save test summary
    summary_file = f"{args.output_dir}/latency_test_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(summary_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    # Create CSV summary
    if results:
        csv_file = write_csv_summary(results, args.output_dir)
        print(f"CSV summary saved to {csv_file}")
    
    print(f"\nTest summary saved to {summary_file}")
    print(f"Completed {len(results)} latency tests")
    
    # Print latency matrix
    print("\nLatency Matrix (Average RTT in ms):")
    regions = list(set([r["source_region"] for r in results]))
    regions.sort()
    
    # Print header
    header = "From\\To"
    for target in regions:
        header += f"\t{target}"
    print(header)
    
    # Print rows
    for source in regions:
        row = f"{source}"
        for target in regions:
            if source == target:
                row += "\t-"
            else:
                found = False
                for r in results:
                    if r["source_region"] == source and r["target_region"] == target:
                        row += f"\t{r['ping_stats']['avg_ms']:.2f}"
                        found = True
                        break
                if not found:
                    row += "\tN/A"
        print(row)

if __name__ == "__main__":
    main() 