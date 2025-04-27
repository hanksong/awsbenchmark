#!/usr/bin/env python3
# generate_histograms.py
# Generate histograms for network performance test results

import json
import argparse
import os
import sys
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
from datetime import datetime

def load_csv_data(csv_file):
    """Load test result data in CSV format"""
    try:
        return pd.read_csv(csv_file)
    except Exception as e:
        print(f"Error: Cannot load CSV file {csv_file}: {e}")
        sys.exit(1)

def load_formatted_data(json_file):
    """Load formatted JSON data"""
    try:
        with open(json_file, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error: Cannot load JSON file {json_file}: {e}")
        sys.exit(1)

def generate_bandwidth_histogram(df, output_dir, prefix="", bins=20):
    """Generate bandwidth histogram"""
    if df is None or df.empty or 'bandwidth_mbps' not in df.columns:
        print(f"Warning: Cannot generate bandwidth histogram for {prefix}, data incomplete")
        return None
    
    plt.figure(figsize=(10, 6))
    sns.histplot(df['bandwidth_mbps'], bins=bins, kde=True)
    plt.title(f'{prefix}Bandwidth Distribution')
    plt.xlabel('Bandwidth (Mbps)')
    plt.ylabel('Frequency')
    plt.grid(True, linestyle='--', alpha=0.7)
    
    # Add statistics
    mean_bw = df['bandwidth_mbps'].mean()
    median_bw = df['bandwidth_mbps'].median()
    min_bw = df['bandwidth_mbps'].min()
    max_bw = df['bandwidth_mbps'].max()
    
    stats_text = f"Mean: {mean_bw:.2f} Mbps\nMedian: {median_bw:.2f} Mbps\nMin: {min_bw:.2f} Mbps\nMax: {max_bw:.2f} Mbps"
    plt.annotate(stats_text, xy=(0.95, 0.95), xycoords='axes fraction', 
                 ha='right', va='top', bbox=dict(boxstyle='round,pad=0.5', fc='white', alpha=0.8))
    
    # Save chart
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = os.path.join(output_dir, f"{prefix}bandwidth_histogram_{timestamp}.png")
    plt.tight_layout()
    plt.savefig(output_file, dpi=300)
    plt.close()
    
    print(f"Bandwidth histogram saved to {output_file}")
    return output_file

def generate_loss_histogram(df, output_dir, prefix="", bins=10):
    """Generate packet loss histogram"""
    if df is None or df.empty or 'lost_percent' not in df.columns:
        print(f"Warning: Cannot generate packet loss histogram for {prefix}, data incomplete")
        return None
    
    plt.figure(figsize=(10, 6))
    sns.histplot(df['lost_percent'], bins=bins, kde=True)
    plt.title(f'{prefix}Packet Loss Distribution')
    plt.xlabel('Packet Loss (%)')
    plt.ylabel('Frequency')
    plt.grid(True, linestyle='--', alpha=0.7)
    
    # Add statistics
    mean_loss = df['lost_percent'].mean()
    median_loss = df['lost_percent'].median()
    min_loss = df['lost_percent'].min()
    max_loss = df['lost_percent'].max()
    
    stats_text = f"Mean: {mean_loss:.2f}%\nMedian: {median_loss:.2f}%\nMin: {min_loss:.2f}%\nMax: {max_loss:.2f}%"
    plt.annotate(stats_text, xy=(0.95, 0.95), xycoords='axes fraction', 
                 ha='right', va='top', bbox=dict(boxstyle='round,pad=0.5', fc='white', alpha=0.8))
    
    # Save chart
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = os.path.join(output_dir, f"{prefix}loss_histogram_{timestamp}.png")
    plt.tight_layout()
    plt.savefig(output_file, dpi=300)
    plt.close()
    
    print(f"Packet loss histogram saved to {output_file}")
    return output_file

def generate_jitter_histogram(df, output_dir, prefix="", bins=10):
    """Generate jitter histogram"""
    if df is None or df.empty or 'jitter_ms' not in df.columns:
        print(f"Warning: Cannot generate jitter histogram for {prefix}, data incomplete")
        return None
    
    plt.figure(figsize=(10, 6))
    sns.histplot(df['jitter_ms'], bins=bins, kde=True)
    plt.title(f'{prefix}Jitter Distribution')
    plt.xlabel('Jitter (ms)')
    plt.ylabel('Frequency')
    plt.grid(True, linestyle='--', alpha=0.7)
    
    # Add statistics
    mean_jitter = df['jitter_ms'].mean()
    median_jitter = df['jitter_ms'].median()
    min_jitter = df['jitter_ms'].min()
    max_jitter = df['jitter_ms'].max()
    
    stats_text = f"Mean: {mean_jitter:.2f} ms\nMedian: {median_jitter:.2f} ms\nMin: {min_jitter:.2f} ms\nMax: {max_jitter:.2f} ms"
    plt.annotate(stats_text, xy=(0.95, 0.95), xycoords='axes fraction', 
                 ha='right', va='top', bbox=dict(boxstyle='round,pad=0.5', fc='white', alpha=0.8))
    
    # Save chart
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = os.path.join(output_dir, f"{prefix}jitter_histogram_{timestamp}.png")
    plt.tight_layout()
    plt.savefig(output_file, dpi=300)
    plt.close()
    
    print(f"Jitter histogram saved to {output_file}")
    return output_file

def generate_heatmap(matrix_df, output_dir, title, filename_prefix, cmap="YlGnBu", fmt=".1f"):
    """Generate heatmap"""
    if matrix_df is None or matrix_df.empty:
        print(f"Warning: Cannot generate {title} heatmap, data incomplete")
        return None
    
    plt.figure(figsize=(12, 10))
    mask = np.isnan(matrix_df)
    sns.heatmap(matrix_df, annot=True, cmap=cmap, fmt=fmt, mask=mask, cbar_kws={'label': 'Mbps' if 'bandwidth' in filename_prefix else '%'})
    plt.title(title)
    plt.tight_layout()
    
    # Save chart
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = os.path.join(output_dir, f"{filename_prefix}_heatmap_{timestamp}.png")
    plt.savefig(output_file, dpi=300)
    plt.close()
    
    print(f"{title} heatmap saved to {output_file}")
    return output_file

def generate_interval_histograms(data_dir, output_dir):
    """
    Generate detailed performance distribution charts for each time interval
    of each client-server connection to show performance variation over time
    """
    print("\nGenerating detailed interval performance charts...")
    
    # Find all UDP and P2P test result files
    udp_files = [f for f in os.listdir(data_dir) if f.startswith('udp_multicast_') and f.endswith('.json') and 'summary' not in f]
    p2p_files = [f for f in os.listdir(data_dir) if f.startswith('p2p_') and f.endswith('.json') and 'summary' not in f]
    
    generated_files = []
    
    # Process UDP test results
    for udp_file in udp_files:
        file_path = os.path.join(data_dir, udp_file)
        
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
                
            # Extract server and client information
            server_ip = udp_file.split('_to_')[0].split('udp_multicast_')[1]
            client_ip = udp_file.split('_to_')[1].split('_')[0]
            
            # Try to get region information
            server_region = data.get('server_region', 'unknown')
            client_region = data.get('client_region', 'unknown')
            connection_name = f"UDP: {server_region}({server_ip}) → {client_region}({client_ip})"
            
            # Check if intervals data exists
            if 'intervals' in data and len(data['intervals']) > 0:
                # Extract data for each interval
                intervals = []
                bandwidth_values = []
                jitter_values = []
                loss_values = []
                
                for interval in data['intervals']:
                    if 'sum' in interval:
                        interval_sec = interval.get('sum', {}).get('end', 0)
                        bw_mbps = interval.get('sum', {}).get('bits_per_second', 0) / 1000000
                        jitter_ms = interval.get('sum', {}).get('jitter_ms', 0)
                        lost_percent = interval.get('sum', {}).get('lost_percent', 0)
                        
                        intervals.append(interval_sec)
                        bandwidth_values.append(bw_mbps)
                        jitter_values.append(jitter_ms)
                        loss_values.append(lost_percent)
                
                if bandwidth_values:
                    # Create bandwidth over time chart
                    plt.figure(figsize=(12, 6))
                    plt.plot(intervals, bandwidth_values, 'o-', linewidth=2, markersize=8)
                    plt.title(f'{connection_name} - Bandwidth Over Time')
                    plt.xlabel('Time (seconds)')
                    plt.ylabel('Bandwidth (Mbps)')
                    plt.grid(True)
                    
                    # Add statistics
                    avg_bw = sum(bandwidth_values) / len(bandwidth_values)
                    max_bw = max(bandwidth_values)
                    min_bw = min(bandwidth_values)
                    
                    stats_text = f"Avg: {avg_bw:.2f} Mbps\nMax: {max_bw:.2f} Mbps\nMin: {min_bw:.2f} Mbps"
                    plt.annotate(stats_text, xy=(0.95, 0.95), xycoords='axes fraction', 
                                 ha='right', va='top', bbox=dict(boxstyle='round,pad=0.5', fc='white', alpha=0.8))
                    
                    # Save chart
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"udp_{server_region}_to_{client_region}_bandwidth_intervals_{timestamp}.png"
                    output_file = os.path.join(output_dir, filename)
                    plt.tight_layout()
                    plt.savefig(output_file, dpi=300)
                    plt.close()
                    
                    generated_files.append(output_file)
                    print(f"UDP bandwidth intervals chart saved to: {output_file}")
                
                if loss_values:
                    # Create packet loss over time chart
                    plt.figure(figsize=(12, 6))
                    plt.plot(intervals, loss_values, 'o-', color='red', linewidth=2, markersize=8)
                    plt.title(f'{connection_name} - Packet Loss Over Time')
                    plt.xlabel('Time (seconds)')
                    plt.ylabel('Packet Loss (%)')
                    plt.grid(True)
                    
                    # Add statistics
                    avg_loss = sum(loss_values) / len(loss_values)
                    max_loss = max(loss_values)
                    min_loss = min(loss_values)
                    
                    stats_text = f"Avg: {avg_loss:.2f}%\nMax: {max_loss:.2f}%\nMin: {min_loss:.2f}%"
                    plt.annotate(stats_text, xy=(0.95, 0.95), xycoords='axes fraction', 
                                 ha='right', va='top', bbox=dict(boxstyle='round,pad=0.5', fc='white', alpha=0.8))
                    
                    # Save chart
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"udp_{server_region}_to_{client_region}_loss_intervals_{timestamp}.png"
                    output_file = os.path.join(output_dir, filename)
                    plt.tight_layout()
                    plt.savefig(output_file, dpi=300)
                    plt.close()
                    
                    generated_files.append(output_file)
                    print(f"UDP packet loss intervals chart saved to: {output_file}")
                
                if jitter_values:
                    # Create jitter over time chart
                    plt.figure(figsize=(12, 6))
                    plt.plot(intervals, jitter_values, 'o-', color='green', linewidth=2, markersize=8)
                    plt.title(f'{connection_name} - Jitter Over Time')
                    plt.xlabel('Time (seconds)')
                    plt.ylabel('Jitter (ms)')
                    plt.grid(True)
                    
                    # Add statistics
                    avg_jitter = sum(jitter_values) / len(jitter_values)
                    max_jitter = max(jitter_values)
                    min_jitter = min(jitter_values)
                    
                    stats_text = f"Avg: {avg_jitter:.2f} ms\nMax: {max_jitter:.2f} ms\nMin: {min_jitter:.2f} ms"
                    plt.annotate(stats_text, xy=(0.95, 0.95), xycoords='axes fraction', 
                                 ha='right', va='top', bbox=dict(boxstyle='round,pad=0.5', fc='white', alpha=0.8))
                    
                    # Save chart
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"udp_{server_region}_to_{client_region}_jitter_intervals_{timestamp}.png"
                    output_file = os.path.join(output_dir, filename)
                    plt.tight_layout()
                    plt.savefig(output_file, dpi=300)
                    plt.close()
                    
                    generated_files.append(output_file)
                    print(f"UDP jitter intervals chart saved to: {output_file}")
                    
                # Generate bandwidth distribution histogram
                if bandwidth_values:
                    plt.figure(figsize=(10, 6))
                    sns.histplot(bandwidth_values, bins=min(10, len(bandwidth_values)), kde=True)
                    plt.title(f'{connection_name} - Bandwidth Distribution')
                    plt.xlabel('Bandwidth (Mbps)')
                    plt.ylabel('Frequency')
                    plt.grid(True)
                    
                    # Add statistics
                    avg_bw = sum(bandwidth_values) / len(bandwidth_values)
                    max_bw = max(bandwidth_values)
                    min_bw = min(bandwidth_values)
                    
                    stats_text = f"Avg: {avg_bw:.2f} Mbps\nMax: {max_bw:.2f} Mbps\nMin: {min_bw:.2f} Mbps"
                    plt.annotate(stats_text, xy=(0.95, 0.95), xycoords='axes fraction', 
                                 ha='right', va='top', bbox=dict(boxstyle='round,pad=0.5', fc='white', alpha=0.8))
                    
                    # Save chart
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"udp_{server_region}_to_{client_region}_bandwidth_histogram_{timestamp}.png"
                    output_file = os.path.join(output_dir, filename)
                    plt.tight_layout()
                    plt.savefig(output_file, dpi=300)
                    plt.close()
                    
                    generated_files.append(output_file)
                    print(f"UDP bandwidth distribution histogram saved to: {output_file}")
            else:
                print(f"Warning: No intervals data found in {udp_file}")
        except Exception as e:
            print(f"Error processing UDP file {udp_file}: {str(e)}")
    
    # Process P2P test results 
    for p2p_file in p2p_files:
        file_path = os.path.join(data_dir, p2p_file)
        
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
                
            # Extract source and target information
            source_ip = p2p_file.split('_to_')[0].split('p2p_')[1]
            target_ip = p2p_file.split('_to_')[1].split('_')[0]
            
            # Try to get region information
            source_region = data.get('source_region', 'unknown')
            target_region = data.get('target_region', 'unknown')
            connection_name = f"P2P: {source_region}({source_ip}) → {target_region}({target_ip})"
            
            # Check if intervals data exists
            if 'intervals' in data and len(data['intervals']) > 0:
                # Extract data for each interval
                intervals = []
                bandwidth_values = []
                retransmit_values = [] 
                
                for interval in data['intervals']:
                    if 'sum' in interval:
                        interval_sec = interval.get('sum', {}).get('end', 0)
                        bw_mbps = interval.get('sum', {}).get('bits_per_second', 0) / 1000000
                        retransmits = interval.get('sum', {}).get('retransmits', 0)
                        
                        intervals.append(interval_sec)
                        bandwidth_values.append(bw_mbps)
                        retransmit_values.append(retransmits)
                
                if bandwidth_values:
                    # Create bandwidth over time chart
                    plt.figure(figsize=(12, 6))
                    plt.plot(intervals, bandwidth_values, 'o-', linewidth=2, markersize=8)
                    plt.title(f'{connection_name} - Bandwidth Over Time')
                    plt.xlabel('Time (seconds)')
                    plt.ylabel('Bandwidth (Mbps)')
                    plt.grid(True)
                    
                    # Add statistics
                    avg_bw = sum(bandwidth_values) / len(bandwidth_values)
                    max_bw = max(bandwidth_values)
                    min_bw = min(bandwidth_values)
                    
                    stats_text = f"Avg: {avg_bw:.2f} Mbps\nMax: {max_bw:.2f} Mbps\nMin: {min_bw:.2f} Mbps"
                    plt.annotate(stats_text, xy=(0.95, 0.95), xycoords='axes fraction', 
                                 ha='right', va='top', bbox=dict(boxstyle='round,pad=0.5', fc='white', alpha=0.8))
                    
                    # Save chart
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"p2p_{source_region}_to_{target_region}_bandwidth_intervals_{timestamp}.png"
                    output_file = os.path.join(output_dir, filename)
                    plt.tight_layout()
                    plt.savefig(output_file, dpi=300)
                    plt.close()
                    
                    generated_files.append(output_file)
                    print(f"P2P bandwidth intervals chart saved to: {output_file}")
                
                if retransmit_values:
                    # Only create retransmits chart if there are actual retransmits
                    if sum(retransmit_values) > 0:
                        # Create retransmits over time chart
                        plt.figure(figsize=(12, 6))
                        plt.plot(intervals, retransmit_values, 'o-', color='orange', linewidth=2, markersize=8)
                        plt.title(f'{connection_name} - Retransmits Over Time')
                        plt.xlabel('Time (seconds)')
                        plt.ylabel('Retransmits')
                        plt.grid(True)
                        
                        # Save chart
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        filename = f"p2p_{source_region}_to_{target_region}_retransmits_intervals_{timestamp}.png"
                        output_file = os.path.join(output_dir, filename)
                        plt.tight_layout()
                        plt.savefig(output_file, dpi=300)
                        plt.close()
                        
                        generated_files.append(output_file)
                        print(f"P2P retransmits intervals chart saved to: {output_file}")
                
                # Generate bandwidth distribution histogram
                if bandwidth_values:
                    plt.figure(figsize=(10, 6))
                    sns.histplot(bandwidth_values, bins=min(10, len(bandwidth_values)), kde=True)
                    plt.title(f'{connection_name} - Bandwidth Distribution')
                    plt.xlabel('Bandwidth (Mbps)')
                    plt.ylabel('Frequency')
                    plt.grid(True)
                    
                    # Add statistics
                    avg_bw = sum(bandwidth_values) / len(bandwidth_values)
                    max_bw = max(bandwidth_values)
                    min_bw = min(bandwidth_values)
                    
                    stats_text = f"Avg: {avg_bw:.2f} Mbps\nMax: {max_bw:.2f} Mbps\nMin: {min_bw:.2f} Mbps"
                    plt.annotate(stats_text, xy=(0.95, 0.95), xycoords='axes fraction', 
                                 ha='right', va='top', bbox=dict(boxstyle='round,pad=0.5', fc='white', alpha=0.8))
                    
                    # Save chart
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"p2p_{source_region}_to_{target_region}_bandwidth_histogram_{timestamp}.png"
                    output_file = os.path.join(output_dir, filename)
                    plt.tight_layout()
                    plt.savefig(output_file, dpi=300)
                    plt.close()
                    
                    generated_files.append(output_file)
                    print(f"P2P bandwidth distribution histogram saved to: {output_file}")
            else:
                print(f"Warning: No intervals data found in {p2p_file}")
        except Exception as e:
            print(f"Error processing P2P file {p2p_file}: {str(e)}")
    
    return generated_files

def generate_latency_histogram(df, output_dir, bins=15):
    """Generate latency histogram"""
    if df is None or df.empty or 'avg_latency_ms' not in df.columns:
        print(f"Warning: Cannot generate latency histogram, data incomplete")
        return None
    
    plt.figure(figsize=(10, 6))
    sns.histplot(df['avg_latency_ms'], bins=bins, kde=True)
    plt.title('Network Latency Distribution')
    plt.xlabel('Round-Trip Time (ms)')
    plt.ylabel('Frequency')
    plt.grid(True, linestyle='--', alpha=0.7)
    
    # Add statistics
    mean_latency = df['avg_latency_ms'].mean()
    median_latency = df['avg_latency_ms'].median()
    min_latency = df['avg_latency_ms'].min()
    max_latency = df['avg_latency_ms'].max()
    
    stats_text = f"Mean: {mean_latency:.2f} ms\nMedian: {median_latency:.2f} ms\nMin: {min_latency:.2f} ms\nMax: {max_latency:.2f} ms"
    plt.annotate(stats_text, xy=(0.95, 0.95), xycoords='axes fraction', 
                 ha='right', va='top', bbox=dict(boxstyle='round,pad=0.5', fc='white', alpha=0.8))
    
    # Save chart
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = os.path.join(output_dir, f"latency_histogram_{timestamp}.png")
    plt.tight_layout()
    plt.savefig(output_file, dpi=300)
    plt.close()
    
    print(f"Latency histogram saved to {output_file}")
    return output_file

def main():
    parser = argparse.ArgumentParser(description="Generate histograms for network performance test results")
    parser.add_argument("--p2p-csv", help="Point-to-point test results CSV file")
    parser.add_argument("--udp-csv", help="UDP test results CSV file")
    parser.add_argument("--latency-csv", help="Latency test results CSV file")
    parser.add_argument("--p2p-matrix", help="Point-to-point bandwidth matrix CSV file")
    parser.add_argument("--udp-bandwidth-matrix", help="UDP bandwidth matrix CSV file")
    parser.add_argument("--udp-loss-matrix", help="UDP packet loss matrix CSV file")
    parser.add_argument("--latency-matrix", help="Latency matrix CSV file")
    parser.add_argument("--formatted-json", help="Formatted JSON data file")
    parser.add_argument("--output-dir", default="visualization", help="Output directory")
    parser.add_argument("--generate-intervals", action="store_true", help="Generate detailed interval histograms for each connection")
    parser.add_argument("--log-subdir", default="", help="Optional subdirectory name for logging visualizations")
    
    args = parser.parse_args()
    
    # If output_dir starts with "../", fix it to the correct project directory
    if args.output_dir.startswith("../"):
        args.output_dir = args.output_dir[3:]  # Remove "../" prefix
    
    # Get absolute path to output directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    output_dir = os.path.join(project_root, args.output_dir)
    data_dir = os.path.join(project_root, 'data')
    
    # Create a timestamped log directory for this visualization run
    if not args.log_subdir:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_dir_name = f"vis_log_{timestamp}"
    else:
        log_dir_name = args.log_subdir
    
    log_dir = os.path.join(output_dir, log_dir_name)
    os.makedirs(log_dir, exist_ok=True)
    
    # Update output directory to the log directory
    output_dir = log_dir
    
    # Create a symlink to the latest visualization log directory
    latest_link = os.path.join(os.path.dirname(log_dir), "latest")
    try:
        # Remove existing link if it exists
        if os.path.islink(latest_link):
            os.unlink(latest_link)
        # Create new symlink
        os.symlink(log_dir, latest_link, target_is_directory=True)
        print(f"Created symlink: {latest_link} -> {log_dir}")
    except Exception as e:
        print(f"Warning: Could not create symlink: {e}")
    
    print(f"Output directory: {output_dir}")
    
    # Look for CSV files if not specified
    if not args.p2p_csv and not args.udp_csv and not args.latency_csv:
        # Find latest CSV files
        p2p_files = [f for f in os.listdir(data_dir) if f.startswith('p2p_results_') and f.endswith('.csv')]
        udp_files = [f for f in os.listdir(data_dir) if f.startswith('udp_results_') and f.endswith('.csv')]
        latency_files = [f for f in os.listdir(data_dir) if f.startswith('latency_results_') and f.endswith('.csv')]
        
        if p2p_files:
            latest_p2p = sorted(p2p_files)[-1]
            args.p2p_csv = os.path.join(data_dir, latest_p2p)
            print(f"Using latest p2p CSV file: {args.p2p_csv}")
        
        if udp_files:
            latest_udp = sorted(udp_files)[-1]
            args.udp_csv = os.path.join(data_dir, latest_udp)
            print(f"Using latest UDP CSV file: {args.udp_csv}")
            
        if latency_files:
            latest_latency = sorted(latency_files)[-1]
            args.latency_csv = os.path.join(data_dir, latest_latency)
            print(f"Using latest latency CSV file: {args.latency_csv}")
    
    generated_files = []
    
    # 生成每个client-server对的详细间隔分布图
    if args.generate_intervals:
        interval_files = generate_interval_histograms(data_dir, output_dir)
        if interval_files:
            generated_files.extend(interval_files)
    
    # Load point-to-point test data
    p2p_df = None
    if args.p2p_csv:
        p2p_df = load_csv_data(args.p2p_csv)
        print(f"Loaded {len(p2p_df)} point-to-point test data entries")
        
        # Generate point-to-point bandwidth histogram
        p2p_bw_hist = generate_bandwidth_histogram(p2p_df, output_dir, prefix="p2p_")
        if p2p_bw_hist:
            generated_files.append(p2p_bw_hist)
    
    # Load UDP test data
    udp_df = None
    if args.udp_csv:
        udp_df = load_csv_data(args.udp_csv)
        print(f"Loaded {len(udp_df)} UDP test data entries")
        
        # Generate UDP bandwidth histogram
        udp_bw_hist = generate_bandwidth_histogram(udp_df, output_dir, prefix="udp_")
        if udp_bw_hist:
            generated_files.append(udp_bw_hist)
        
        # Generate UDP packet loss histogram
        udp_loss_hist = generate_loss_histogram(udp_df, output_dir, prefix="udp_")
        if udp_loss_hist:
            generated_files.append(udp_loss_hist)
        
        # Generate UDP jitter histogram
        udp_jitter_hist = generate_jitter_histogram(udp_df, output_dir, prefix="udp_")
        if udp_jitter_hist:
            generated_files.append(udp_jitter_hist)
    
    # Load latency test data
    latency_df = None
    if args.latency_csv:
        latency_df = load_csv_data(args.latency_csv)
        print(f"Loaded {len(latency_df)} latency test data entries")
        
        # Generate latency histogram
        latency_hist = generate_latency_histogram(latency_df, output_dir)
        if latency_hist:
            generated_files.append(latency_hist)
    
    # Look for matrix files if not specified
    if not args.p2p_matrix and not args.udp_bandwidth_matrix and not args.udp_loss_matrix and not args.latency_matrix:
        data_dir = os.path.join(project_root, 'data')
        # Find latest matrix files
        p2p_matrix_files = [f for f in os.listdir(data_dir) if f.startswith('p2p_bandwidth_matrix_') and f.endswith('.csv')]
        udp_bw_matrix_files = [f for f in os.listdir(data_dir) if f.startswith('udp_bandwidth_matrix_') and f.endswith('.csv')]
        udp_loss_matrix_files = [f for f in os.listdir(data_dir) if f.startswith('udp_loss_matrix_') and f.endswith('.csv')]
        latency_matrix_files = [f for f in os.listdir(data_dir) if f.startswith('latency_matrix_') and f.endswith('.csv')]
        
        if p2p_matrix_files:
            latest_p2p_matrix = sorted(p2p_matrix_files)[-1]
            args.p2p_matrix = os.path.join(data_dir, latest_p2p_matrix)
            print(f"Using latest p2p bandwidth matrix file: {args.p2p_matrix}")
        
        if udp_bw_matrix_files:
            latest_udp_bw_matrix = sorted(udp_bw_matrix_files)[-1]
            args.udp_bandwidth_matrix = os.path.join(data_dir, latest_udp_bw_matrix)
            print(f"Using latest UDP bandwidth matrix file: {args.udp_bandwidth_matrix}")
        
        if udp_loss_matrix_files:
            latest_udp_loss_matrix = sorted(udp_loss_matrix_files)[-1]
            args.udp_loss_matrix = os.path.join(data_dir, latest_udp_loss_matrix)
            print(f"Using latest UDP loss matrix file: {args.udp_loss_matrix}")
            
        if latency_matrix_files:
            latest_latency_matrix = sorted(latency_matrix_files)[-1]
            args.latency_matrix = os.path.join(data_dir, latest_latency_matrix)
            print(f"Using latest latency matrix file: {args.latency_matrix}")
    
    # Load point-to-point bandwidth matrix
    if args.p2p_matrix:
        p2p_matrix_df = load_csv_data(args.p2p_matrix)
        p2p_matrix_df = p2p_matrix_df.set_index(p2p_matrix_df.columns[0])
        
        # Generate point-to-point bandwidth heatmap
        p2p_heatmap = generate_heatmap(
            p2p_matrix_df, 
            output_dir, 
            "Inter-region Point-to-Point Bandwidth (Mbps)", 
            "p2p_bandwidth"
        )
        if p2p_heatmap:
            generated_files.append(p2p_heatmap)
    
    # Load UDP bandwidth matrix
    if args.udp_bandwidth_matrix:
        udp_bw_matrix_df = load_csv_data(args.udp_bandwidth_matrix)
        udp_bw_matrix_df = udp_bw_matrix_df.set_index(udp_bw_matrix_df.columns[0])
        
        # Generate UDP bandwidth heatmap
        udp_bw_heatmap = generate_heatmap(
            udp_bw_matrix_df, 
            output_dir, 
            "Inter-region UDP Bandwidth (Mbps)", 
            "udp_bandwidth"
        )
        if udp_bw_heatmap:
            generated_files.append(udp_bw_heatmap)
    
    # Load UDP packet loss matrix
    if args.udp_loss_matrix:
        udp_loss_matrix_df = load_csv_data(args.udp_loss_matrix)
        udp_loss_matrix_df = udp_loss_matrix_df.set_index(udp_loss_matrix_df.columns[0])
        
        # Generate UDP packet loss heatmap
        udp_loss_heatmap = generate_heatmap(
            udp_loss_matrix_df, 
            output_dir, 
            "Inter-region UDP Packet Loss (%)", 
            "udp_loss",
            cmap="Reds"
        )
        if udp_loss_heatmap:
            generated_files.append(udp_loss_heatmap)
            
    # Load latency matrix
    if args.latency_matrix:
        latency_matrix_df = load_csv_data(args.latency_matrix)
        latency_matrix_df = latency_matrix_df.set_index(latency_matrix_df.columns[0])
        
        # Generate latency heatmap
        latency_heatmap = generate_heatmap(
            latency_matrix_df, 
            output_dir, 
            "Inter-region Network Latency (ms)", 
            "latency",
            cmap="viridis_r",
            fmt=".1f"
        )
        if latency_heatmap:
            generated_files.append(latency_heatmap)
    
    # If formatted JSON data is provided, can generate charts directly from it
    if args.formatted_json:
        formatted_data = load_formatted_data(args.formatted_json)
        print("Loaded formatted data")
        
        # Can generate other charts from formatted data as needed
    
    print(f"\nGenerated {len(generated_files)} visualization files:")
    for file in generated_files:
        print(f"- {file}")
    
    # Return list of generated files to make it easier for the report generator
    return generated_files

if __name__ == "__main__":
    main()
