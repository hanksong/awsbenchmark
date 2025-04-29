#!/usr/bin/env python3
# format_data.py
# Format parsed benchmark data into a Markdown report.

import json
import argparse
import os
import sys
import pandas as pd
import numpy as np
from datetime import datetime


def load_parsed_data(json_file):
    """Load parsed test result data from a JSON file."""
    try:
        with open(json_file, 'r') as f:
            data = json.load(f)
        # Convert lists of records back to DataFrames
        dfs = {}
        if 'latency' in data and data['latency']:
            dfs['latency'] = pd.DataFrame(data['latency'])
        if 'p2p' in data and data['p2p']:
            dfs['p2p'] = pd.DataFrame(data['p2p'])
        if 'udp' in data and data['udp']:
            dfs['udp'] = pd.DataFrame(data['udp'])
        return dfs
    except FileNotFoundError:
        print(f"Error: Parsed data file not found: {json_file}")
        return None
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON in parsed data file: {json_file}")
        return None
    except Exception as e:
        print(f"Error: Cannot load parsed data file {json_file}: {e}")
        return None


def create_latency_matrix(latency_df):
    """Generate inter-region latency matrix from DataFrame"""
    if latency_df is None or latency_df.empty:
        print("Info: No latency data found for matrix generation.")
        return None

    # Check required columns
    if not all(col in latency_df.columns for col in ['source_region', 'target_region', 'avg_latency_ms']):
        print("Error: Latency DataFrame missing required columns (source_region, target_region, avg_latency_ms).")
        return None

    # Get all unique regions involved
    source_regions = latency_df['source_region'].unique()
    target_regions = latency_df['target_region'].unique()
    all_regions = sorted(list(np.unique(np.concatenate(
        [source_regions, target_regions]))))  # Sort for consistent order

    # Create an empty matrix initialized with NaN
    latency_matrix = pd.DataFrame(
        index=all_regions, columns=all_regions, dtype=float)

    # Fill the matrix with average latency values
    for _, row in latency_df.iterrows():
        source = row['source_region']
        target = row['target_region']
        latency = row['avg_latency_ms']
        if pd.notna(latency):
            # Handle potential duplicates (e.g., multiple runs): average them
            if pd.notna(latency_matrix.loc[source, target]):
                latency_matrix.loc[source, target] = (
                    latency_matrix.loc[source, target] + latency) / 2
            else:
                latency_matrix.loc[source, target] = latency

    # Intra-region latency (source == target) is typically not measured or meaningful in this context
    # The diagonal is already NaN, which is appropriate.

    return latency_matrix


def create_p2p_bandwidth_matrix(p2p_df):
    """Generate inter-region P2P bandwidth matrix from DataFrame"""
    if p2p_df is None or p2p_df.empty:
        print("Info: No P2P data found for matrix generation.")
        return None

    if not all(col in p2p_df.columns for col in ['source_region', 'target_region', 'bandwidth_mbps']):
        print("Error: P2P DataFrame missing required columns (source_region, target_region, bandwidth_mbps).")
        return None

    source_regions = p2p_df['source_region'].unique()
    target_regions = p2p_df['target_region'].unique()
    all_regions = sorted(
        list(np.unique(np.concatenate([source_regions, target_regions]))))

    bandwidth_matrix = pd.DataFrame(
        index=all_regions, columns=all_regions, dtype=float)

    for _, row in p2p_df.iterrows():
        source = row['source_region']
        target = row['target_region']
        bandwidth = row['bandwidth_mbps']
        if pd.notna(bandwidth):
            if pd.notna(bandwidth_matrix.loc[source, target]):
                bandwidth_matrix.loc[source, target] = (
                    bandwidth_matrix.loc[source, target] + bandwidth) / 2
            else:
                bandwidth_matrix.loc[source, target] = bandwidth

    return bandwidth_matrix


def create_udp_matrices(udp_df):
    """Generate inter-region UDP bandwidth and loss matrices from DataFrame"""
    if udp_df is None or udp_df.empty:
        print("Info: No UDP data found for matrix generation.")
        return None, None

    if not all(col in udp_df.columns for col in ['server_region', 'client_region', 'bandwidth_mbps', 'lost_percent']):
        print("Error: UDP DataFrame missing required columns (server_region, client_region, bandwidth_mbps, lost_percent).")
        return None, None

    # Ensure client_region is present and handle potential NaNs if necessary
    udp_df = udp_df.dropna(subset=['client_region'])
    if udp_df.empty:
        print("Info: No UDP data with valid client regions found.")
        return None, None

    server_regions = udp_df['server_region'].unique()
    client_regions = udp_df['client_region'].unique()
    all_regions = sorted(
        list(np.unique(np.concatenate([server_regions, client_regions]))))

    bandwidth_matrix = pd.DataFrame(
        index=all_regions, columns=all_regions, dtype=float)
    loss_matrix = pd.DataFrame(
        index=all_regions, columns=all_regions, dtype=float)

    # Group by server/client pair and average results if duplicates exist
    grouped = udp_df.groupby(['server_region', 'client_region'])
    avg_results = grouped[['bandwidth_mbps',
                           'lost_percent']].mean().reset_index()

    for _, row in avg_results.iterrows():
        server = row['server_region']
        client = row['client_region']
        bandwidth = row['bandwidth_mbps']
        loss = row['lost_percent']

        if pd.notna(bandwidth):
            bandwidth_matrix.loc[server, client] = bandwidth
        if pd.notna(loss):
            loss_matrix.loc[server, client] = loss

    return bandwidth_matrix, loss_matrix


def format_matrix_markdown(matrix, title, unit):
    """Formats a pandas DataFrame matrix into a Markdown table."""
    if matrix is None:
        return f"### {title}\n\nNo data available.\n"
    # Format numbers to 2 decimal places, replace NaN with '-'
    formatted_matrix = matrix.round(2).fillna('-')
    markdown = f"### {title} ({unit})\n\n"
    markdown += formatted_matrix.to_markdown()
    markdown += "\n"
    return markdown

# This is the core function that generates the report content


def _generate_markdown_report(parsed_data_dfs):
    """Generates the Markdown report content from parsed data DataFrames."""
    report_content = f"# AWS Network Benchmark Report\n\n"
    report_content += f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"

    # --- Latency ---
    report_content += "## Latency Test Results\n\n"
    latency_df = parsed_data_dfs.get('latency')
    if latency_df is not None and not latency_df.empty:
        latency_matrix = create_latency_matrix(latency_df)
        report_content += format_matrix_markdown(
            latency_matrix, "Average Latency Matrix", "ms")
        # Add summary stats if desired
        report_content += f"\n**Latency Summary Statistics:**\n"
        report_content += latency_df['avg_latency_ms'].describe().to_markdown() + "\n"
    else:
        report_content += "No latency data available.\n"

    # --- Point-to-Point (TCP) ---
    report_content += "\n## Point-to-Point (TCP) Test Results\n\n"
    p2p_df = parsed_data_dfs.get('p2p')
    if p2p_df is not None and not p2p_df.empty:
        p2p_bw_matrix = create_p2p_bandwidth_matrix(p2p_df)
        report_content += format_matrix_markdown(
            p2p_bw_matrix, "Average TCP Bandwidth Matrix", "Mbps")
        report_content += f"\n**P2P Bandwidth Summary Statistics:**\n"
        report_content += p2p_df['bandwidth_mbps'].describe().to_markdown() + "\n"
    else:
        report_content += "No Point-to-Point (TCP) data available.\n"

    # --- UDP ---
    report_content += "\n## UDP Test Results\n\n"
    udp_df = parsed_data_dfs.get('udp')
    if udp_df is not None and not udp_df.empty:
        udp_bw_matrix, udp_loss_matrix = create_udp_matrices(udp_df)
        report_content += format_matrix_markdown(
            udp_bw_matrix, "Average UDP Bandwidth Matrix", "Mbps")
        report_content += format_matrix_markdown(
            udp_loss_matrix, "Average UDP Packet Loss Matrix", "%")

        # Add summary stats
        report_content += f"\n**UDP Bandwidth Summary Statistics:**\n"
        report_content += udp_df['bandwidth_mbps'].describe().to_markdown() + "\n"
        report_content += f"\n**UDP Packet Loss Summary Statistics:**\n"
        report_content += udp_df['lost_percent'].describe().to_markdown() + "\n"
        if 'jitter_ms' in udp_df.columns:
            report_content += f"\n**UDP Jitter Summary Statistics:**\n"
            report_content += udp_df['jitter_ms'].describe().to_markdown() + "\n"
    else:
        report_content += "No UDP data available.\n"

    return report_content


# This is the main function callable from other scripts
def format_data(input_json_path, output_md_path):
    """
    Loads parsed data from JSON, formats it into a Markdown report,
    and saves it to the specified file.

    Args:
        input_json_path (str): Path to the input JSON file (parsed_results.json).
        output_md_path (str): Path to save the output Markdown report.

    Returns:
        int: 0 on success, 1 on failure.
    """
    print(f"Formatting data from {input_json_path} into {output_md_path}")

    # Create output directory if it doesn't exist
    output_dir = os.path.dirname(output_md_path)
    # Ensure output_dir is not empty (e.g., if path is just filename)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    # Load data
    parsed_data_dfs = load_parsed_data(input_json_path)
    if parsed_data_dfs is None:
        return 1  # Error loading data

    if not parsed_data_dfs:
        print("Warning: No valid data found in the parsed JSON file.")
        # Create an empty/minimal report? Or return error? Let's create minimal.
        report_content = f"# AWS Network Benchmark Report\n\nGenerated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\nNo data found in {input_json_path}.\n"
    else:
        # Generate report content
        try:
            report_content = _generate_markdown_report(parsed_data_dfs)
        except Exception as e:
            print(f"Error generating markdown report content: {e}")
            # Optionally print traceback
            # import traceback
            # traceback.print_exc()
            return 1

    # Save the report
    try:
        with open(output_md_path, 'w') as f:
            f.write(report_content)
        print(f"Formatted report saved successfully to {output_md_path}")
        return 0  # Success
    except IOError as e:
        print(
            f"Error: Could not write formatted report to {output_md_path}: {e}")
        return 1  # Failure


def main():
    parser = argparse.ArgumentParser(
        description="Format parsed benchmark data into a Markdown report.")
    parser.add_argument("--input-json", required=True,
                        help="Path to the parsed results JSON file (e.g., parsed_results.json)")
    parser.add_argument("--output-md", required=True,
                        help="Path to save the output Markdown report file (e.g., formatted_results.md)")

    args = parser.parse_args()

    # Call the main logic function
    exit_code = format_data(args.input_json, args.output_md)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
