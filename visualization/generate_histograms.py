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

def main():
    parser = argparse.ArgumentParser(description="Generate histograms for network performance test results")
    parser.add_argument("--p2p-csv", help="Point-to-point test results CSV file")
    parser.add_argument("--udp-csv", help="UDP test results CSV file")
    parser.add_argument("--p2p-matrix", help="Point-to-point bandwidth matrix CSV file")
    parser.add_argument("--udp-bandwidth-matrix", help="UDP bandwidth matrix CSV file")
    parser.add_argument("--udp-loss-matrix", help="UDP packet loss matrix CSV file")
    parser.add_argument("--formatted-json", help="Formatted JSON data file")
    parser.add_argument("--output-dir", default="visualization", help="Output directory")
    
    args = parser.parse_args()
    
    # If output_dir starts with "../", fix it to the correct project directory
    if args.output_dir.startswith("../"):
        args.output_dir = args.output_dir[3:]  # Remove "../" prefix
    
    # Get absolute path to output directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    output_dir = os.path.join(project_root, args.output_dir)
    
    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)
    
    print(f"Output directory: {output_dir}")
    
    # Look for CSV files if not specified
    if not args.p2p_csv and not args.udp_csv:
        data_dir = os.path.join(project_root, 'data')
        # Find latest CSV files
        p2p_files = [f for f in os.listdir(data_dir) if f.startswith('p2p_results_') and f.endswith('.csv')]
        udp_files = [f for f in os.listdir(data_dir) if f.startswith('udp_results_') and f.endswith('.csv')]
        
        if p2p_files:
            latest_p2p = sorted(p2p_files)[-1]
            args.p2p_csv = os.path.join(data_dir, latest_p2p)
            print(f"Using latest p2p CSV file: {args.p2p_csv}")
        
        if udp_files:
            latest_udp = sorted(udp_files)[-1]
            args.udp_csv = os.path.join(data_dir, latest_udp)
            print(f"Using latest UDP CSV file: {args.udp_csv}")
    
    generated_files = []
    
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
    
    # Look for matrix files if not specified
    if not args.p2p_matrix and not args.udp_bandwidth_matrix and not args.udp_loss_matrix:
        data_dir = os.path.join(project_root, 'data')
        # Find latest matrix files
        p2p_matrix_files = [f for f in os.listdir(data_dir) if f.startswith('p2p_bandwidth_matrix_') and f.endswith('.csv')]
        udp_bw_matrix_files = [f for f in os.listdir(data_dir) if f.startswith('udp_bandwidth_matrix_') and f.endswith('.csv')]
        udp_loss_matrix_files = [f for f in os.listdir(data_dir) if f.startswith('udp_loss_matrix_') and f.endswith('.csv')]
        
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
