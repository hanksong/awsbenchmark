#!/usr/bin/env python3
# collect_results.py
# collect and整理iperf3测试结果

import json
import argparse
import os
import sys
import glob
from datetime import datetime
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


def collect_results(data_dir, output_file=None):
    """collect and format the test results"""
    # find all the test result files
    p2p_files = glob.glob(os.path.join(data_dir, 'p2p_*.json'))
    udp_files = glob.glob(os.path.join(data_dir, 'udp_multicast_*.json'))

    # first find and parse the summary files to get the region info
    p2p_summary_files = glob.glob(os.path.join(
        data_dir, 'p2p_test_summary_*.json'))
    udp_summary_files = glob.glob(os.path.join(
        data_dir, 'udp_multicast_summary_*.json'))

    # create the ip to region map
    ip_to_region_map = {}
    # first get the region info from the udp summary files
    for summary_file in udp_summary_files:
        try:
            with open(summary_file, 'r') as f:
                summary = json.load(f)
                if 'ip_to_region_map' in summary:
                    ip_to_region_map.update(summary['ip_to_region_map'])
                else:
                    # compatible with the old version summary files
                    server_region = summary.get('server_region')
                    server_ip = summary.get('server_ip')
                    if server_ip and server_region:
                        ip_to_region_map[server_ip] = server_region

                    for i, result in enumerate(summary.get('results', [])):
                        client_ip = result.get('client_ip')
                        if client_ip and i < len(summary.get('client_regions', [])):
                            ip_to_region_map[client_ip] = summary['client_regions'][i]
        except Exception as e:
            print(
                f"warning: failed to parse the udp summary file {summary_file}: {e}")

    p2p_region_map = {}
    for summary_file in p2p_summary_files:
        try:
            with open(summary_file, 'r') as f:
                summary = json.load(f)
                for test in summary:
                    result_file = os.path.basename(test['result_file'])
                    p2p_region_map[result_file] = {
                        'source_region': test['source_region'],
                        'target_region': test['target_region']
                    }
        except Exception as e:
            print(
                f"warning: failed to parse the p2p summary file {summary_file}: {e}")

    # parse the p2p test results
    p2p_results = []
    for file in p2p_files:
        if 'summary' not in file:  # skip the summary files
            result = parse_iperf3_result(file)
            filename = os.path.basename(file)
            region_info = extract_region_info(filename)

            if region_info:
                result.update(region_info)

            # get the region info from the region map
            if filename in p2p_region_map:
                result.update(p2p_region_map[filename])

            p2p_results.append(result)

    # parse the udp test results
    udp_results = []
    for file in udp_files:
        if 'summary' not in file:  # skip the summary files
            result = parse_iperf3_result(file)
            filename = os.path.basename(file)

            # try to get the region info from the file
            try:
                with open(file, 'r') as f:
                    file_data = json.load(f)
                    if 'server_region' in file_data:
                        result['server_region'] = file_data['server_region']
                    if 'client_region' in file_data:
                        result['client_region'] = file_data['client_region']
            except Exception:
                pass

            # if there is no region info, try to get the region info from the filename
            if 'server_region' not in result or 'client_region' not in result:
                ip_info = extract_ip_info(filename)
                if ip_info:
                    server_ip = ip_info.get('server_ip')
                    client_ip = ip_info.get('client_ip')

                    if server_ip and server_ip in ip_to_region_map:
                        result['server_region'] = ip_to_region_map[server_ip]

                    if client_ip and client_ip in ip_to_region_map:
                        result['client_region'] = ip_to_region_map[client_ip]

            udp_results.append(result)

    # integrate all the results
    all_results = {
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'point_to_point_tests': p2p_results,
        'udp_multicast_tests': udp_results
    }

    # save the results
    if output_file:
        output_path = output_file
    else:
        output_path = os.path.join(
            data_dir, f'collected_results_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json')

    with open(output_path, 'w') as f:
        json.dump(all_results, f, indent=2)

    print(f"test results collected and saved to: {output_path}")
    print(f"total {len(p2p_results)} p2p tests and {len(udp_results)} udp tests")

    return output_path


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


if __name__ == "__main__":
    main()
