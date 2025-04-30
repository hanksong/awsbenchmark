#!/usr/bin/env python3
# latency_test.py
# Execute ping latency tests between EC2 instances

import json
import argparse
import subprocess
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


def run_ping_test(server_ip, client_ip, ssh_key, ssh_user, count=10, output_dir="../data"):
    """Execute ping latency test"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"{output_dir}/latency_{server_ip}_to_{client_ip}_{timestamp}.json"

    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)

    # Run ping test from client to server
    ping_cmd = (
        f"ssh -i {ssh_key} -o StrictHostKeyChecking=no {ssh_user}@{client_ip} "
        f"'ping -c {count} -i 0.2 {server_ip} > /tmp/ping_result.txt'"
    )

    try:
        print(f"Starting latency test: {client_ip} -> {server_ip}")
        subprocess.run(ping_cmd, shell=True, check=True)

        # Get ping results
        get_result_cmd = f"scp -i {ssh_key} -o StrictHostKeyChecking=no {ssh_user}@{client_ip}:/tmp/ping_result.txt /tmp/ping_result.txt"
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
            packet_match = re.search(
                r'(\d+) packets transmitted, (\d+) received, (\d+)% packet loss', content)
            if packet_match:
                stats["packets_transmitted"] = int(packet_match.group(1))
                stats["packets_received"] = int(packet_match.group(2))
                stats["packet_loss_percent"] = float(packet_match.group(3))

            # Extract timing stats
            time_match = re.search(
                r'min/avg/max/mdev = ([\d\.]+)/([\d\.]+)/([\d\.]+)/([\d\.]+) ms', content)
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
        return csv_file  # Return the path to the summary file
    except Exception as e:
        print(f"Error creating CSV summary: {e}")
        return None

# Rename main and modify to accept arguments directly


def run_latency_benchmark(instance_info_path, ssh_key_path, ping_count, output_dir, all_regions, use_private_ip, intra_region, source_region=None, target_region=None):
    """Executes latency tests based on provided parameters."""
    # Load instance information
    instance_data = load_instance_info(instance_info_path)

    # Create results directory
    os.makedirs(output_dir, exist_ok=True)

    results = []

    # Determine IP type based on use_private_ip flag
    ip_type = "private_ips" if use_private_ip else "public_ips"
    ip_type_desc = "private" if use_private_ip else "public"

    if all_regions:
        # Test all region combinations
        regions = list(instance_data["instances"].keys())
        for src_region in regions:
            for dest_region in regions:
                # Skip if not testing intra-region and regions are the same
                if not intra_region and src_region == dest_region:
                    continue

                # Get IPs for the regions
                source_ips = instance_data["instances"][src_region].get(
                    ip_type, [])
                target_ips = instance_data["instances"][dest_region].get(
                    ip_type, [])

                if not source_ips or not target_ips:
                    print(
                        f"Warning: Missing IPs for {src_region} or {dest_region} using {ip_type_desc} IPs. Skipping test.")
                    continue

                # Handle intra-region multiple instances
                if src_region == dest_region and len(source_ips) > 1:
                    for i, s_ip in enumerate(source_ips):
                        for j, t_ip in enumerate(target_ips):
                            if i != j:  # Avoid self-ping
                                print(
                                    f"\nTesting latency within {src_region}: Instance {i+1} -> Instance {j+1} (using {ip_type_desc} IPs)")
                                result_file, ping_stats = run_ping_test(
                                    t_ip, s_ip, ssh_key_path, ssh_user,
                                    ping_count, output_dir
                                )
                                if result_file and ping_stats:
                                    results.append({
                                        "source_region": f"{src_region}_instance{i+1}",
                                        "target_region": f"{dest_region}_instance{j+1}",
                                        "result_file": result_file,
                                        "ping_stats": ping_stats
                                    })
                # Handle inter-region or single instance intra-region
                elif src_region != dest_region or (src_region == dest_region and len(source_ips) == 1):
                    # Test between the first instance of each region
                    source_ip = source_ips[0]
                    target_ip = target_ips[0]
                    print(
                        f"\nTesting latency: {src_region} -> {dest_region} (using {ip_type_desc} IPs)")
                    result_file, ping_stats = run_ping_test(
                        target_ip, source_ip, ssh_key_path,
                        ping_count, output_dir
                    )
                    if result_file and ping_stats:
                        results.append({
                            "source_region": src_region,
                            "target_region": dest_region,
                            "result_file": result_file,
                            "ping_stats": ping_stats
                        })

    elif source_region and target_region:
        # Test specific source and target regions (simplified, assumes first instance)
        source_ips = instance_data["instances"][source_region].get(ip_type, [])
        target_ips = instance_data["instances"][target_region].get(ip_type, [])

        if not source_ips or not target_ips:
            print(
                f"Error: Missing IPs for specified regions {source_region} or {target_region} using {ip_type_desc} IPs.")
            return None  # Indicate failure

        source_ip = source_ips[0]
        target_ip = target_ips[0]

        print(
            f"\nTesting latency: {source_region} -> {target_region} (using {ip_type_desc} IPs)")
        result_file, ping_stats = run_ping_test(
            target_ip, source_ip, ssh_key_path,
            ping_count, output_dir
        )
        if result_file and ping_stats:
            results.append({
                "source_region": source_region,
                "target_region": target_region,
                "result_file": result_file,
                "ping_stats": ping_stats
            })
    else:
        print("Error: Invalid arguments. Provide --all-regions or both --source-region and --target-region.")
        return None  # Indicate failure

    # Write summary CSV
    summary_csv_path = write_csv_summary(results, output_dir)

    print(f"\nLatency testing finished. Summary: {summary_csv_path}")
    return summary_csv_path  # Return path to summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Execute ping latency tests between EC2 instances")
    parser.add_argument("--instance-info", required=True,
                        help="Path to JSON file containing EC2 instance information")
    parser.add_argument("--ssh-key", required=True,
                        help="Path to SSH key file")
    parser.add_argument("--ping-count", type=int, default=20,
                        help="Number of ping packets to send")
    parser.add_argument("--output-dir", default="../data",
                        help="Output directory for test results")
    parser.add_argument("--all-regions", action="store_true",
                        help="Test all region combinations")
    parser.add_argument("--source-region", help="Source region")
    parser.add_argument("--target-region", help="Target region")
    parser.add_argument("--use-private-ip", action="store_true",
                        help="Use private IPs instead of public IPs for testing")
    parser.add_argument("--intra-region", action="store_true",
                        help="Also test between instances in the same region")

    args = parser.parse_args()
    run_latency_benchmark(
        args.instance_info, args.ssh_key, args.ping_count, args.output_dir,
        args.all_regions, args.use_private_ip, args.intra_region,
        args.source_region, args.target_region
    )
