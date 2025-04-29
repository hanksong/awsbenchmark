#!/usr/bin/env python3
# collect_results.py
# collect and整理iperf3测试结果

import json
import argparse
import os
import sys
import re


def parse_iperf3_result(result_file):
    """parse the iperf3 json result file"""
    try:
        with open(result_file, 'r') as f:
            data = json.load(f)

        # extract the key performance metrics
        if 'end' in data:
            if data.get('error'):
                return {
                    'status': 'error',
                    'error_msg': data.get('error'),
                    'file': result_file
                }

            # TCP test results
            if 'sum_received' in data['end']:
                return {
                    'status': 'success',
                    'protocol': 'TCP',
                    'bits_per_second': data['end']['sum_received']['bits_per_second'],
                    'bytes': data['end']['sum_received']['bytes'],
                    'seconds': data['end']['sum_received']['seconds'],
                    'retransmits': data['end'].get('sum_sent', {}).get('retransmits', 0),
                    'file': result_file
                }
            # UDP test results
            elif 'sum' in data['end']:
                return {
                    'status': 'success',
                    'protocol': 'UDP',
                    'bits_per_second': data['end']['sum']['bits_per_second'],
                    'bytes': data['end']['sum']['bytes'],
                    'seconds': data['end']['sum']['seconds'],
                    'jitter_ms': data['end']['sum'].get('jitter_ms', 0),
                    'lost_packets': data['end']['sum'].get('lost_packets', 0),
                    'packets': data['end']['sum'].get('packets', 0),
                    'lost_percent': data['end']['sum'].get('lost_percent', 0),
                    'file': result_file
                }

        return {
            'status': 'unknown',
            'file': result_file
        }
    except Exception as e:
        print(f"error: failed to parse the file {result_file}: {e}")
        return {
            'status': 'error',
            'error_msg': str(e),
            'file': result_file
        }


def extract_region_info(filename):
    """extract the region info from the filename"""
    try:
        # for the p2p test files: p2p_<server_ip>_to_<client_ip>_<timestamp>.json
        if filename.startswith('p2p_'):
            return None  # the p2p test files do not contain region info directly

        # for the udp test files: udp_multicast_<server_ip>_to_<client_ip>_<timestamp>.json
        elif filename.startswith('udp_multicast_'):
            return None  # the udp test files do not contain region info directly

        return None
    except:
        return None


def extract_ip_info(filename):
    """extract the ip info from the filename"""
    # for example: udp_multicast_18.170.227.74_to_34.239.172.73_20250419_224615.json
    match = re.search(r'udp_multicast_([\d\.]+)_to_([\d\.]+)_', filename)
    if match:
        return {
            'server_ip': match.group(1),
            'client_ip': match.group(2)
        }
    return None


def main():
    parser = argparse.ArgumentParser(
        description="collect and format the iperf3 test results")
    parser.add_argument("--data-dir", default="../data",
                        help="the data directory for the test results")
    parser.add_argument("--output", help="the output file path")

    args = parser.parse_args()

    # ensure the data directory exists
    if not os.path.isdir(args.data_dir):
        print(f"error: the data directory {args.data_dir} does not exist")
        sys.exit(1)

    collect_results(args.data_dir, args.output)


def collect_results(instance_info_path, ssh_key_path, remote_dir, local_dir, file_pattern):
    """Collects benchmark result files from EC2 instances."""
    try:
        with open(instance_info_path, 'r') as f:
            instance_info = json.load(f)
    except FileNotFoundError:
        print(f"Error: Instance info file not found at {instance_info_path}")
        return 1
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from {instance_info_path}")
        return 1

    # Use public IPs for SCP/SSH access
    ip_key = 'public_ips'
    print(f"Using {ip_key} for collecting results.")

    regions = list(instance_info['instances'].keys())
    collected_files = []

    # Ensure local directory exists
    os.makedirs(local_dir, exist_ok=True)

    print(
        f"Collecting files matching '{file_pattern}' from '{remote_dir}' on all instances...")

    for region in regions:
        instance_ips = get_ips(instance_info, ip_key, [region])
        if not instance_ips:
            print(
                f"Warning: No {ip_key} found for region {region}, skipping collection.")
            continue

        for ip_address in instance_ips:
            print(f"  Connecting to {ip_address} ({region})...")
            # Use scp to copy files
            # Construct the source path carefully
            remote_path = f"ubuntu@{ip_address}:{os.path.join(remote_dir, file_pattern)}"
            scp_command = f"scp -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -i {ssh_key_path} {remote_path} {local_dir}/"

            print(f"    Executing: {scp_command}")
            try:
                # Use subprocess.run for better control and error handling than run_remote_command
                result = subprocess.run(
                    scp_command, shell=True, check=True, capture_output=True, text=True)
                print(f"    SCP stdout:\n{result.stdout}")
                # Note: SCP might not list files transferred on stdout unless verbose.
                # We might need to list the local_dir afterwards to confirm.
                print(f"    Successfully collected files from {ip_address}")
                # Add logic here to list collected files if needed
            except subprocess.CalledProcessError as e:
                print(f"    Error collecting files from {ip_address}:")
                print(f"    Command: {e.cmd}")
                print(f"    Return code: {e.returncode}")
                print(f"    Stderr: {e.stderr}")
            except Exception as e:
                print(f"    An unexpected error occurred during SCP: {e}")

    # Optional: Verify files were collected by listing local_dir
    print(f"\nFiles collected in {local_dir}:")
    try:
        files_in_local_dir = os.listdir(local_dir)
        if files_in_local_dir:
            for f in files_in_local_dir:
                # Potentially filter for expected patterns if needed
                print(f"  - {f}")
                collected_files.append(os.path.join(local_dir, f))
        else:
            print("  No files found in local directory after collection.")
    except Exception as e:
        print(f"  Error listing local directory: {e}")

    print("\nFile collection finished.")
    # Return the list of collected file paths (or just indicate success/failure)
    # For now, just return success code
    return 0  # Indicate success


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Collect benchmark result files from EC2 instances.")
    parser.add_argument("--instance-info", required=True,
                        help="Path to the instance info JSON file.")
    parser.add_argument("--ssh-key", required=True,
                        help="Path to the SSH private key.")
    parser.add_argument("--remote-dir", default="/tmp/benchmark_results",
                        help="Directory on remote instances containing results.")
    parser.add_argument("--local-dir", required=True,
                        help="Local directory to save collected results.")
    parser.add_argument("--file-pattern", default="*.json",
                        help="Pattern of result files to collect (e.g., '*.json', 'results_*.csv').")

    args = parser.parse_args()

    exit_code = collect_results(
        instance_info_path=args.instance_info,
        ssh_key_path=args.ssh_key,
        remote_dir=args.remote_dir,
        local_dir=args.local_dir,
        file_pattern=args.file_pattern
    )
    sys.exit(exit_code)
