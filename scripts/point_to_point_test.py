#!/usr/bin/env python3
# point_to_point_test.py

import argparse
import json
import os
import subprocess
import time
from datetime import datetime
import pandas as pd


def run_remote_command(ip, cmd, ssh_key_path):
    """Runs a command on a remote machine."""
    stdout, stderr = subprocess.Popen(
        [f"ssh -i {ssh_key_path} -o StrictHostKeyChecking=no ec2-user@{ip} {cmd}"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=True
    ).communicate()
    return stdout, stderr


def kill_iperf_servers(all_instance_ips, ssh_key_path):
    """Kills all iperf3 servers."""
    for instance_ip in all_instance_ips:
        run_remote_command(instance_ip, "iperf3 -k", ssh_key_path)


def get_ips(instance_info, ip_key, regions):
    """Gets all IPs for a list of regions."""
    all_ips = []
    for region in regions:
        all_ips.append(instance_info['instances'][region][ip_key])
    return all_ips


def point_to_point_test(instance_info_path, ssh_key_path, duration, parallel, output_dir, use_private_ip, test_intra_region, all_regions):
    """Runs point-to-point iperf3 tests between instances."""
    try:
        with open(instance_info_path, 'r') as f:
            instance_info = json.load(f)
    except FileNotFoundError:
        print(f"Error: Instance info file not found at {instance_info_path}")
        return 1
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from {instance_info_path}")
        return 1

    ip_key = 'private_ips' if use_private_ip else 'public_ips'
    print(f"Using {ip_key} for point-to-point tests.")

    regions = list(instance_info['instances'].keys())
    results = []
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = os.path.join(output_dir, f"p2p_results_{timestamp}.csv")

    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)

    all_instance_ips = get_ips(instance_info, ip_key, regions)

    # Kill any existing iperf3 servers first
    print("Attempting to kill existing iperf3 servers...")
    kill_iperf_servers(all_instance_ips, ssh_key_path)
    time.sleep(5)  # Give servers time to die

    try:
        for src_region in regions:
            src_ips = get_ips(instance_info, ip_key, [src_region])
            if not src_ips:
                print(
                    f"Warning: No {ip_key} found for source region {src_region}, skipping.")
                continue
            src_ip = src_ips[0]  # Use the first IP as the client

            target_regions = regions if all_regions else [src_region]

            for dest_region in target_regions:
                # Skip logic based on flags (same as latency_test)
                if not all_regions and src_region != dest_region:
                    continue
                if not test_intra_region and src_region == dest_region:
                    continue

                dest_ips = get_ips(instance_info, ip_key, [dest_region])
                if not dest_ips:
                    print(
                        f"Warning: No {ip_key} found for destination region {dest_region}, skipping.")
                    continue

                for dest_ip in dest_ips:
                    if src_region == dest_region and src_ip == dest_ip:
                        continue  # Don't test instance against itself

                    print(
                        f"\nTesting from {src_region} ({src_ip}) to {dest_region} ({dest_ip})...")

                    # Start iperf3 server on destination
                    print(f"  Starting iperf3 server on {dest_ip}...")
                    server_cmd = "iperf3 -s -D"  # Run in daemon mode
                    stdout_s, stderr_s = run_remote_command(
                        dest_ip, server_cmd, ssh_key_path)
                    if stderr_s and "bind failed" not in stderr_s:  # Ignore "bind failed" if server already running
                        print(
                            f"  Warning: Problem starting iperf3 server on {dest_ip}: {stderr_s}")
                        # Continue anyway, maybe server is already running
                    time.sleep(2)  # Wait for server to start

                    # Run iperf3 client on source
                    print(f"  Running iperf3 client on {src_ip}...")
                    # -J for JSON output
                    client_cmd = f"iperf3 -c {dest_ip} -t {duration} -P {parallel} -J"
                    stdout_c, stderr_c = run_remote_command(
                        src_ip, client_cmd, ssh_key_path)

                    if stderr_c:
                        print(f"  Client stderr: {stderr_c}")

                    if stdout_c:
                        try:
                            iperf_result = json.loads(stdout_c)
                            if 'error' in iperf_result:
                                print(
                                    f"  iperf3 error: {iperf_result['error']}")
                                # Record failure
                                results.append({
                                    'timestamp': datetime.now().isoformat(),
                                    'source_region': src_region, 'source_ip': src_ip,
                                    'destination_region': dest_region, 'destination_ip': dest_ip,
                                    'protocol': 'TCP', 'interval_sec': duration, 'parallel_streams': parallel,
                                    'sent_mbps': 0, 'received_mbps': 0, 'sent_retransmits': None, 'error': iperf_result['error']
                                })
                            else:
                                # Extract relevant data (handle potential missing keys)
                                end_data = iperf_result.get('end', {})
                                sum_sent = end_data.get('sum_sent', {})
                                sum_received = end_data.get('sum_received', {})

                                sent_bps = sum_sent.get('bits_per_second', 0)
                                received_bps = sum_received.get(
                                    'bits_per_second', 0)
                                retransmits = sum_sent.get(
                                    'retransmits')  # Might be None

                                sent_mbps = sent_bps / 1_000_000
                                received_mbps = received_bps / 1_000_000

                                results.append({
                                    'timestamp': datetime.now().isoformat(),
                                    'source_region': src_region,
                                    'source_ip': src_ip,
                                    'destination_region': dest_region,
                                    'destination_ip': dest_ip,
                                    'protocol': 'TCP',
                                    'interval_sec': duration,
                                    'parallel_streams': parallel,
                                    'sent_mbps': round(sent_mbps, 2),
                                    'received_mbps': round(received_mbps, 2),
                                    'sent_retransmits': retransmits,
                                    'error': None
                                })
                                print(
                                    f"  Result: Sent {sent_mbps:.2f} Mbps, Received {received_mbps:.2f} Mbps")

                        except json.JSONDecodeError:
                            print(f"  Error: Could not decode iperf3 JSON output.")
                            print(f"  Raw output: {stdout_c}")
                        except Exception as e:
                            print(f"  Error processing iperf3 result: {e}")
                    else:
                        print("  iperf3 client command failed or produced no output.")
                        # Record failure
                        results.append({
                            'timestamp': datetime.now().isoformat(),
                            'source_region': src_region, 'source_ip': src_ip,
                            'destination_region': dest_region, 'destination_ip': dest_ip,
                            'protocol': 'TCP', 'interval_sec': duration, 'parallel_streams': parallel,
                            'sent_mbps': 0, 'received_mbps': 0, 'sent_retransmits': None, 'error': 'Client execution failed'
                        })

                    # Kill the specific server instance (optional, cleanup handles it too)
                    # kill_iperf_servers([dest_ip], ssh_key_path)
                    # time.sleep(1)

    finally:
        # Final cleanup: kill all iperf3 servers
        print("\nFinal cleanup: Killing any remaining iperf3 servers...")
        kill_iperf_servers(all_instance_ips, ssh_key_path)

    # Save results to CSV
    if results:
        df = pd.DataFrame(results)
        df.to_csv(output_file, index=False)
        print(f"\nPoint-to-point test results saved to {output_file}")
        return output_file # Return the path to the results CSV
    else:
        print("\nNo point-to-point test results generated.")
        return None # Return None if no results

    # The original return 0 is removed as we return the path now

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run point-to-point iperf3 tests")
    # ... (keep argparse for potential standalone use/testing) ...
    args = parser.parse_args()
    point_to_point_test(
        args.instance_info, args.ssh_key, args.duration, args.parallel,
        args.output_dir, args.use_private_ip, args.intra_region, args.all_regions
    )
