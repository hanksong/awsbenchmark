#!/usr/bin/env python3
# collect_results.py
# collect and整理iperf3测试结果

import json
import argparse
import os
import sys
import re
import shutil


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


def collect_results(source_dir, target_dir, file_pattern="*.json"):
    """Collects result files from a source directory to a target directory."""
    # Ensure target directory exists
    os.makedirs(target_dir, exist_ok=True)

    print(f"Collecting files matching '{file_pattern}' from {source_dir} to {target_dir}...")
    collected_count = 0
    try:
        for filename in os.listdir(source_dir):
            # Simple pattern matching (can be enhanced with glob or regex if needed)
            if filename.endswith(".json") or filename.endswith(".csv") or filename.endswith(".txt"):
                source_path = os.path.join(source_dir, filename)
                target_path = os.path.join(target_dir, filename)
                if os.path.isfile(source_path):
                    try:
                        shutil.copy2(source_path, target_path)  # copy2 preserves metadata
                        print(f"  Copied: {filename}")
                        collected_count += 1
                    except Exception as copy_e:
                        print(f"  Error copying {filename}: {copy_e}")

        print(f"Collected {collected_count} result files.")
        return 0  # Indicate success
    except FileNotFoundError:
        print(f"Error: Source directory not found: {source_dir}")
        return 1  # Indicate failure
    except Exception as e:
        print(f"An unexpected error occurred during collection: {e}")
        return 1  # Indicate failure


def main():
    parser = argparse.ArgumentParser(description="Collect benchmark result files.")
    parser.add_argument("--source-dir", required=True, help="Directory containing raw result files.")
    parser.add_argument("--target-dir", required=True, help="Directory to copy result files into.")

    args = parser.parse_args()

    if collect_results(args.source_dir, args.target_dir) != 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
