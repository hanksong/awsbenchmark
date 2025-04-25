#!/usr/bin/env python3
# format_data.py
# Format iperf3 test result data for visualization

import json
import argparse
import os
import sys
import pandas as pd
import numpy as np
from datetime import datetime
import re
import glob

def load_csv_data(csv_file):
    """Load test result data in CSV format"""
    try:
        return pd.read_csv(csv_file)
    except Exception as e:
        print(f"Error: Cannot load CSV file {csv_file}: {e}")
        sys.exit(1)

def format_p2p_data(p2p_df):
    """Format point-to-point test data, generate inter-region bandwidth matrix"""
    if p2p_df is None or p2p_df.empty:
        print("Warning: No point-to-point test data to format")
        return None
    
    # Get all regions
    source_regions = p2p_df['source_region'].unique()
    target_regions = p2p_df['target_region'].unique()
    all_regions = np.unique(np.concatenate([source_regions, target_regions]))
    
    # Create inter-region bandwidth matrix
    bandwidth_matrix = pd.DataFrame(index=all_regions, columns=all_regions)
    
    # Fill the matrix
    for _, row in p2p_df.iterrows():
        source = row['source_region']
        target = row['target_region']
        bandwidth = row['bandwidth_mbps']
        bandwidth_matrix.loc[source, target] = bandwidth
    
    # Set diagonal to NaN (tests within the same region)
    for region in all_regions:
        bandwidth_matrix.loc[region, region] = np.nan
    
    return bandwidth_matrix

def format_udp_data(udp_df):
    """Format UDP test data, generate inter-region bandwidth and packet loss data"""
    if udp_df is None or udp_df.empty:
        print("Warning: No UDP test data to format")
        return None, None
    
    # Try to load the most recent UDP summary file to get IP-to-region mapping
    data_dir = os.path.dirname(udp_df.iloc[0]['file'])
    summary_files = glob.glob(os.path.join(data_dir, 'udp_multicast_summary_*.json'))
    ip_to_region_map = {}
    
    if summary_files:
        # Sort by name to get the most recent
        latest_summary = sorted(summary_files)[-1]
        try:
            with open(latest_summary, 'r') as f:
                summary = json.load(f)
                # Create mapping of IP to region
                if 'client_regions' in summary and len(summary['client_regions']) > 0:
                    for i, result in enumerate(summary.get('results', [])):
                        if i < len(summary.get('client_regions', [])):
                            ip_to_region_map[result['client_ip']] = summary['client_regions'][i]
        except Exception as e:
            print(f"Warning: Error loading UDP summary file: {e}")
    
    # Fix null client_region values by extracting from file path
    for idx, row in udp_df.iterrows():
        if pd.isnull(row['client_region']) or row['client_region'] == 'unknown':
            file_path = row['file']
            # Extract client IP from filename
            match = re.search(r'udp_multicast_.*?_to_([\d\.]+)_', file_path)
            if match:
                client_ip = match.group(1)
                # First try to use our IP-to-region map
                if client_ip in ip_to_region_map:
                    udp_df.at[idx, 'client_region'] = ip_to_region_map[client_ip]
                # Fall back to hardcoded mappings if needed
                elif '18.170.227.74' in client_ip:
                    udp_df.at[idx, 'client_region'] = 'eu-west-2'
                elif '52.195.188.216' in client_ip:
                    udp_df.at[idx, 'client_region'] = 'ap-northeast-1'
                elif '34.239.172.73' in client_ip:
                    udp_df.at[idx, 'client_region'] = 'us-east-1'
                else:
                    # Default fallback - use a descriptive name
                    udp_df.at[idx, 'client_region'] = 'unknown-region'
    
    # Get all regions
    server_regions = udp_df['server_region'].unique()
    client_regions = [r for r in udp_df['client_region'].unique() if pd.notna(r)]
    all_regions = np.unique(np.concatenate([server_regions, client_regions]))
    
    # Create inter-region bandwidth matrix
    bandwidth_matrix = pd.DataFrame(index=all_regions, columns=all_regions)
    
    # Create inter-region packet loss matrix
    loss_matrix = pd.DataFrame(index=all_regions, columns=all_regions)
    
    # Fill the matrix
    for _, row in udp_df.iterrows():
        server = row['server_region']
        client = row['client_region']
        if pd.notna(client):  # Ensure client region is not null
            bandwidth = row['bandwidth_mbps']
            loss = row['lost_percent']
            
            bandwidth_matrix.loc[server, client] = bandwidth
            loss_matrix.loc[server, client] = loss
    
    # Set diagonal to NaN (tests within the same region)
    for region in all_regions:
        bandwidth_matrix.loc[region, region] = np.nan
        loss_matrix.loc[region, region] = np.nan
    
    return bandwidth_matrix, loss_matrix

def prepare_histogram_data(df, column, bins=10):
    """Prepare histogram data"""
    if df is None or df.empty:
        return None
    
    hist, bin_edges = np.histogram(df[column], bins=bins)
    bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2
    
    return {
        'counts': hist.tolist(),
        'bin_centers': bin_centers.tolist(),
        'bin_edges': bin_edges.tolist()
    }

def main():
    parser = argparse.ArgumentParser(description="Format iperf3 test result data for visualization")
    parser.add_argument("--p2p-csv", help="Point-to-point test results CSV file")
    parser.add_argument("--udp-csv", help="UDP test results CSV file")
    parser.add_argument("--latency-csv", help="Latency test results CSV file")
    parser.add_argument("--output-dir", default="../data", help="Output directory")
    
    args = parser.parse_args()
    
    # Ensure output directory exists
    os.makedirs(args.output_dir, exist_ok=True)
    
    # Load point-to-point test data
    p2p_df = None
    if args.p2p_csv:
        p2p_df = load_csv_data(args.p2p_csv)
        print(f"Loaded {len(p2p_df)} point-to-point test data entries")
    
    # Load UDP test data
    udp_df = None
    if args.udp_csv:
        udp_df = load_csv_data(args.udp_csv)
        print(f"Loaded {len(udp_df)} UDP test data entries")
    
    # Load latency test data
    latency_df = None
    if args.latency_csv:
        latency_df = load_csv_data(args.latency_csv)
        print(f"Loaded {len(latency_df)} latency test data entries")
    
    # Format point-to-point test data
    formatted_data = {
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    
    if p2p_df is not None and not p2p_df.empty:
        # Inter-region bandwidth matrix
        bandwidth_matrix = format_p2p_data(p2p_df)
        if bandwidth_matrix is not None:
            formatted_data['p2p_bandwidth_matrix'] = bandwidth_matrix.to_dict()
            
            # Save as CSV for visualization
            matrix_csv = os.path.join(args.output_dir, f"p2p_bandwidth_matrix_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
            bandwidth_matrix.to_csv(matrix_csv)
            print(f"Point-to-point bandwidth matrix saved to {matrix_csv}")
        
        # Bandwidth histogram data
        bandwidth_hist = prepare_histogram_data(p2p_df, 'bandwidth_mbps', bins=20)
        if bandwidth_hist:
            formatted_data['p2p_bandwidth_histogram'] = bandwidth_hist
    
    # Format UDP test data
    if udp_df is not None and not udp_df.empty:
        # Inter-region bandwidth and packet loss matrix
        udp_bandwidth_matrix, udp_loss_matrix = format_udp_data(udp_df)
        
        if udp_bandwidth_matrix is not None:
            formatted_data['udp_bandwidth_matrix'] = udp_bandwidth_matrix.to_dict()
            
            # Save as CSV for visualization
            matrix_csv = os.path.join(args.output_dir, f"udp_bandwidth_matrix_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
            udp_bandwidth_matrix.to_csv(matrix_csv)
            print(f"UDP bandwidth matrix saved to {matrix_csv}")
        
        if udp_loss_matrix is not None:
            formatted_data['udp_loss_matrix'] = udp_loss_matrix.to_dict()
            
            # Save as CSV for visualization
            matrix_csv = os.path.join(args.output_dir, f"udp_loss_matrix_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
            udp_loss_matrix.to_csv(matrix_csv)
            print(f"UDP packet loss matrix saved to {matrix_csv}")
        
        # Bandwidth and packet loss histogram data
        udp_bandwidth_hist = prepare_histogram_data(udp_df, 'bandwidth_mbps', bins=20)
        if udp_bandwidth_hist:
            formatted_data['udp_bandwidth_histogram'] = udp_bandwidth_hist
        
        udp_loss_hist = prepare_histogram_data(udp_df, 'lost_percent', bins=10)
        if udp_loss_hist:
            formatted_data['udp_loss_histogram'] = udp_loss_hist
        
        udp_jitter_hist = prepare_histogram_data(udp_df, 'jitter_ms', bins=10)
        if udp_jitter_hist:
            formatted_data['udp_jitter_histogram'] = udp_jitter_hist
    
    # Format latency test data
    if latency_df is not None and not latency_df.empty:
        # Create latency matrix
        latency_matrix = format_latency_data(latency_df)
        if latency_matrix is not None:
            formatted_data['latency_matrix'] = latency_matrix.to_dict()
            
            # Save as CSV for visualization
            matrix_csv = os.path.join(args.output_dir, f"latency_matrix_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
            latency_matrix.to_csv(matrix_csv)
            print(f"Latency matrix saved to {matrix_csv}")
        
        # Latency histogram data
        latency_hist = prepare_histogram_data(latency_df, 'avg_latency_ms', bins=15)
        if latency_hist:
            formatted_data['latency_histogram'] = latency_hist
    
    # Save formatted data
    formatted_file = os.path.join(args.output_dir, f"formatted_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    with open(formatted_file, 'w') as f:
        json.dump(formatted_data, f, indent=2)
    
    print(f"Formatted data saved to {formatted_file}")

def format_latency_data(latency_df):
    """Format latency test data, generate inter-region latency matrix"""
    if latency_df is None or latency_df.empty:
        print("Warning: No latency test data to format")
        return None
    
    # Get all regions
    source_regions = latency_df['source_region'].unique()
    target_regions = latency_df['target_region'].unique()
    all_regions = np.unique(np.concatenate([source_regions, target_regions]))
    
    # Create inter-region latency matrix
    latency_matrix = pd.DataFrame(index=all_regions, columns=all_regions)
    
    # Fill the matrix
    for _, row in latency_df.iterrows():
        source = row['source_region']
        target = row['target_region']
        latency = row['avg_latency_ms']
        latency_matrix.loc[source, target] = latency
    
    # Set diagonal to NaN (tests within the same region)
    for region in all_regions:
        latency_matrix.loc[region, region] = np.nan
    
    return latency_matrix

if __name__ == "__main__":
    main()
