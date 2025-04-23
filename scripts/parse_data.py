#!/usr/bin/env python3
# parse_data.py
# parse the collected iperf3 test results data

import json
import argparse
import os
import sys
import pandas as pd
from datetime import datetime
import re

def load_collected_results(result_file):
    """load the collected test results"""
    try:
        with open(result_file, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"error: failed to load the result file {result_file}: {e}")
        sys.exit(1)

def parse_p2p_results(p2p_tests):
    """parse the p2p test results and convert to a dataframe"""
    data = []
    
    for test in p2p_tests:
        if test['status'] == 'success':
            row = {
                'source_region': test.get('source_region', 'unknown'),
                'target_region': test.get('target_region', 'unknown'),
                'protocol': test.get('protocol', 'TCP'),
                'bandwidth_mbps': test['bits_per_second'] / 1000000,  # convert to Mbps
                'transfer_mb': test['bytes'] / 1000000,  # convert to MB
                'duration_sec': test['seconds'],
                'retransmits': test.get('retransmits', 0) if test.get('protocol') == 'TCP' else None,
                'jitter_ms': test.get('jitter_ms') if test.get('protocol') == 'UDP' else None,
                'lost_packets': test.get('lost_packets') if test.get('protocol') == 'UDP' else None,
                'lost_percent': test.get('lost_percent') if test.get('protocol') == 'UDP' else None,
                'file': test['file']
            }
            data.append(row)
    
    if not data:
        return None
    
    return pd.DataFrame(data)

def parse_udp_results(udp_tests):
    """parse the udp test results and convert to a dataframe"""
    data = []
    
    for test in udp_tests:
        if test['status'] == 'success':
            # try to extract client region from file name if not explicitly in test data
            client_region = test.get('client_region', 'unknown')
            if client_region == 'unknown' and 'file' in test:
                # example: udp_multicast_18.170.227.74_to_34.239.172.73_20250419_224615.json
                file_path = test['file']
                client_ip = None
                match = re.search(r'udp_multicast_.*?_to_([\d\.]+)_', file_path)
                if match:
                    client_ip = match.group(1)
                    # to determine region we would need to read instance info or summary file
                    # for now we'll set to empty for post-processing by format_data.py
            
            row = {
                'server_region': test.get('server_region', 'unknown'),
                'client_region': client_region,
                'protocol': 'UDP',
                'bandwidth_mbps': test['bits_per_second'] / 1000000,  # convert to Mbps
                'transfer_mb': test['bytes'] / 1000000,  # convert to MB
                'duration_sec': test['seconds'],
                'jitter_ms': test.get('jitter_ms', 0),
                'lost_packets': test.get('lost_packets', 0),
                'packets': test.get('packets', 0),
                'lost_percent': test.get('lost_percent', 0),
                'file': test['file']
            }
            data.append(row)
    
    if not data:
        return None
    
    return pd.DataFrame(data)

def main():
    parser = argparse.ArgumentParser(description="parse the iperf3 test results data")
    parser.add_argument("--input", required=True, help="collected test results json file")
    parser.add_argument("--output-dir", default="../data", help="output directory")
    
    args = parser.parse_args()
    
    # make sure the output directory exists
    os.makedirs(args.output_dir, exist_ok=True)
    
    # load the collected results
    results = load_collected_results(args.input)
    
    # parse the p2p test results
    p2p_df = parse_p2p_results(results.get('point_to_point_tests', []))
    if p2p_df is not None:
        p2p_csv = os.path.join(args.output_dir, f"p2p_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
        p2p_df.to_csv(p2p_csv, index=False)
        print(f"p2p test results saved to {p2p_csv}")
    else:
        print("no valid p2p test results")
    
    # parse the udp test results
    udp_df = parse_udp_results(results.get('udp_multicast_tests', []))
    if udp_df is not None:
        udp_csv = os.path.join(args.output_dir, f"udp_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
        udp_df.to_csv(udp_csv, index=False)
        print(f"udp test results saved to {udp_csv}")
    else:
        print("no valid udp test results")
    
    # create the summary statistics
    summary = {
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'p2p_test_count': len(results.get('point_to_point_tests', [])),
        'udp_test_count': len(results.get('udp_multicast_tests', [])),
        'p2p_success_count': len(p2p_df) if p2p_df is not None else 0,
        'udp_success_count': len(udp_df) if udp_df is not None else 0
    }
    
    # add the p2p test statistics
    if p2p_df is not None and not p2p_df.empty:
        summary['p2p_avg_bandwidth_mbps'] = p2p_df['bandwidth_mbps'].mean()
        summary['p2p_min_bandwidth_mbps'] = p2p_df['bandwidth_mbps'].min()
        summary['p2p_max_bandwidth_mbps'] = p2p_df['bandwidth_mbps'].max()
        
        # calculate the average bandwidth by region
        region_stats = p2p_df.groupby(['source_region', 'target_region'])['bandwidth_mbps'].mean().reset_index()
        region_stats.columns = ['source_region', 'target_region', 'avg_bandwidth_mbps']
        region_stats_dict = region_stats.to_dict('records')
        summary['p2p_region_stats'] = region_stats_dict
    
    # add the udp test statistics
    if udp_df is not None and not udp_df.empty:
        summary['udp_avg_bandwidth_mbps'] = udp_df['bandwidth_mbps'].mean()
        summary['udp_min_bandwidth_mbps'] = udp_df['bandwidth_mbps'].min()
        summary['udp_max_bandwidth_mbps'] = udp_df['bandwidth_mbps'].max()
        summary['udp_avg_jitter_ms'] = udp_df['jitter_ms'].mean()
        summary['udp_avg_packet_loss_percent'] = udp_df['lost_percent'].mean()
        
        # calculate the average bandwidth and packet loss rate by region
        region_stats = udp_df.groupby(['server_region', 'client_region'])[['bandwidth_mbps', 'lost_percent']].mean().reset_index()
        region_stats.columns = ['server_region', 'client_region', 'avg_bandwidth_mbps', 'avg_packet_loss_percent']
        region_stats_dict = region_stats.to_dict('records')
        summary['udp_region_stats'] = region_stats_dict
    
    # save the summary statistics
    summary_file = os.path.join(args.output_dir, f"results_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    with open(summary_file, 'w') as f:
        json.dump(summary, f, indent=2)
    
    print(f"results summary saved to {summary_file}")

if __name__ == "__main__":
    main()
