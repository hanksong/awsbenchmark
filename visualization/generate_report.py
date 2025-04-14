#!/usr/bin/env python3
# generate_report.py
# Generate comprehensive report for network performance test results

import json
import argparse
import os
import sys
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
import base64
from jinja2 import Template
import glob

def load_csv_data(csv_file):
    """Load test result data in CSV format"""
    try:
        return pd.read_csv(csv_file)
    except Exception as e:
        print(f"Error: Cannot load CSV file {csv_file}: {e}")
        sys.exit(1)

def load_json_data(json_file):
    """Load data in JSON format"""
    try:
        with open(json_file, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error: Cannot load JSON file {json_file}: {e}")
        sys.exit(1)

def image_to_base64(image_path):
    """Convert image to base64 encoding for embedding in HTML"""
    try:
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
    except Exception as e:
        print(f"Warning: Cannot convert image {image_path} to base64: {e}")
        return ""

def find_latest_images(output_dir):
    """Find the latest version of each type of visualization image"""
    image_files = {}
    
    # Look for histogram images
    for prefix in ['p2p_bandwidth', 'udp_bandwidth', 'udp_loss', 'udp_jitter']:
        pattern = os.path.join(output_dir, f"{prefix}_histogram_*.png")
        matching_files = glob.glob(pattern)
        if matching_files:
            latest_file = sorted(matching_files)[-1]
            image_files[f"{prefix}_histogram"] = latest_file
    
    # Look for heatmap images
    for prefix in ['p2p_bandwidth', 'udp_bandwidth', 'udp_loss']:
        pattern = os.path.join(output_dir, f"{prefix}_heatmap_*.png")
        matching_files = glob.glob(pattern)
        if matching_files:
            latest_file = sorted(matching_files)[-1]
            image_files[f"{prefix}_heatmap"] = latest_file
    
    return image_files

def generate_html_report(summary_data, p2p_df, udp_df, image_files, output_dir):
    """Generate comprehensive report in HTML format"""
    
    # Prepare report data
    report_data = {
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'summary': summary_data,
        'images': {}
    }
    
    # Add images
    for img_key, img_path in image_files.items():
        if os.path.exists(img_path):
            report_data['images'][img_key] = image_to_base64(img_path)
    
    # Add point-to-point test statistics
    if p2p_df is not None and not p2p_df.empty:
        report_data['p2p_stats'] = {
            'count': len(p2p_df),
            'avg_bandwidth': p2p_df['bandwidth_mbps'].mean(),
            'min_bandwidth': p2p_df['bandwidth_mbps'].min(),
            'max_bandwidth': p2p_df['bandwidth_mbps'].max(),
            'median_bandwidth': p2p_df['bandwidth_mbps'].median()
        }
        
        # Region pair statistics
        region_stats = p2p_df.groupby(['source_region', 'target_region'])['bandwidth_mbps'].agg(['mean', 'min', 'max']).reset_index()
        report_data['p2p_region_stats'] = region_stats.to_dict('records')
    
    # Add UDP test statistics
    if udp_df is not None and not udp_df.empty:
        report_data['udp_stats'] = {
            'count': len(udp_df),
            'avg_bandwidth': udp_df['bandwidth_mbps'].mean(),
            'min_bandwidth': udp_df['bandwidth_mbps'].min(),
            'max_bandwidth': udp_df['bandwidth_mbps'].max(),
            'median_bandwidth': udp_df['bandwidth_mbps'].median(),
            'avg_loss': udp_df['lost_percent'].mean(),
            'avg_jitter': udp_df['jitter_ms'].mean()
        }
        
        # Region pair statistics
        region_stats = udp_df.groupby(['server_region', 'client_region'])[['bandwidth_mbps', 'lost_percent', 'jitter_ms']].agg(['mean']).reset_index()
        report_data['udp_region_stats'] = region_stats.to_dict('records')
    
    # HTML template
    html_template = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>AWS Network Benchmark Report</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                line-height: 1.6;
                margin: 0;
                padding: 20px;
                color: #333;
            }
            .container {
                max-width: 1200px;
                margin: 0 auto;
            }
            h1, h2, h3 {
                color: #0066cc;
            }
            .summary-box {
                background-color: #f5f5f5;
                border-left: 4px solid #0066cc;
                padding: 15px;
                margin-bottom: 20px;
            }
            table {
                border-collapse: collapse;
                width: 100%;
                margin-bottom: 20px;
            }
            th, td {
                border: 1px solid #ddd;
                padding: 8px;
                text-align: left;
            }
            th {
                background-color: #f2f2f2;
            }
            tr:nth-child(even) {
                background-color: #f9f9f9;
            }
            .image-container {
                margin: 20px 0;
            }
            .image-container img {
                max-width: 100%;
                height: auto;
                border: 1px solid #ddd;
            }
            .footer {
                margin-top: 30px;
                padding-top: 10px;
                border-top: 1px solid #ddd;
                font-size: 0.8em;
                color: #666;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>AWS Network Benchmark Report</h1>
            <p>Generated at: {{ timestamp }}</p>
            
            <div class="summary-box">
                <h2>Test Summary</h2>
                <p>Point-to-point tests: {{ summary.p2p_test_count }} (Successful: {{ summary.p2p_success_count }})</p>
                <p>UDP tests: {{ summary.udp_test_count }} (Successful: {{ summary.udp_success_count }})</p>
            </div>
            
            {% if p2p_stats %}
            <h2>Point-to-Point Test Results</h2>
            <div class="summary-box">
                <p>Average Bandwidth: {{ "%.2f"|format(p2p_stats.avg_bandwidth) }} Mbps</p>
                <p>Minimum Bandwidth: {{ "%.2f"|format(p2p_stats.min_bandwidth) }} Mbps</p>
                <p>Maximum Bandwidth: {{ "%.2f"|format(p2p_stats.max_bandwidth) }} Mbps</p>
                <p>Median Bandwidth: {{ "%.2f"|format(p2p_stats.median_bandwidth) }} Mbps</p>
            </div>
            
            <h3>Inter-Region Bandwidth Statistics</h3>
            <table>
                <tr>
                    <th>Source Region</th>
                    <th>Target Region</th>
                    <th>Average Bandwidth (Mbps)</th>
                    <th>Minimum Bandwidth (Mbps)</th>
                    <th>Maximum Bandwidth (Mbps)</th>
                </tr>
                {% for stat in p2p_region_stats %}
                <tr>
                    <td>{{ stat.source_region }}</td>
                    <td>{{ stat.target_region }}</td>
                    <td>{{ "%.2f"|format(stat.mean) }}</td>
                    <td>{{ "%.2f"|format(stat.min) }}</td>
                    <td>{{ "%.2f"|format(stat.max) }}</td>
                </tr>
                {% endfor %}
            </table>
            
            {% if images.p2p_bandwidth_histogram %}
            <div class="image-container">
                <h3>Point-to-Point Bandwidth Distribution</h3>
                <img src="data:image/png;base64,{{ images.p2p_bandwidth_histogram }}" alt="Point-to-Point Bandwidth Histogram">
            </div>
            {% endif %}
            
            {% if images.p2p_bandwidth_heatmap %}
            <div class="image-container">
                <h3>Inter-Region Bandwidth Heatmap</h3>
                <img src="data:image/png;base64,{{ images.p2p_bandwidth_heatmap }}" alt="Point-to-Point Bandwidth Heatmap">
            </div>
            {% endif %}
            {% endif %}
            
            {% if udp_stats %}
            <h2>UDP Test Results</h2>
            <div class="summary-box">
                <p>Average Bandwidth: {{ "%.2f"|format(udp_stats.avg_bandwidth) }} Mbps</p>
                <p>Minimum Bandwidth: {{ "%.2f"|format(udp_stats.min_bandwidth) }} Mbps</p>
                <p>Maximum Bandwidth: {{ "%.2f"|format(udp_stats.max_bandwidth) }} Mbps</p>
                <p>Median Bandwidth: {{ "%.2f"|format(udp_stats.median_bandwidth) }} Mbps</p>
                <p>Average Packet Loss: {{ "%.2f"|format(udp_stats.avg_loss) }}%</p>
                <p>Average Jitter: {{ "%.2f"|format(udp_stats.avg_jitter) }} ms</p>
            </div>
            
            <h3>Inter-Region UDP Statistics</h3>
            <table>
                <tr>
                    <th>Server Region</th>
                    <th>Client Region</th>
                    <th>Average Bandwidth (Mbps)</th>
                    <th>Average Packet Loss (%)</th>
                    <th>Average Jitter (ms)</th>
                </tr>
                {% for stat in udp_region_stats %}
                <tr>
                    <td>{{ stat.server_region }}</td>
                    <td>{{ stat.client_region }}</td>
                    <td>{{ "%.2f"|format(stat['bandwidth_mbps']['mean']) }}</td>
                    <td>{{ "%.2f"|format(stat['lost_percent']['mean']) }}</td>
                    <td>{{ "%.2f"|format(stat['jitter_ms']['mean']) }}</td>
                </tr>
                {% endfor %}
            </table>
            
            {% if images.udp_bandwidth_histogram %}
            <div class="image-container">
                <h3>UDP Bandwidth Distribution</h3>
                <img src="data:image/png;base64,{{ images.udp_bandwidth_histogram }}" alt="UDP Bandwidth Histogram">
            </div>
            {% endif %}
            
            {% if images.udp_loss_histogram %}
            <div class="image-container">
                <h3>UDP Packet Loss Distribution</h3>
                <img src="data:image/png;base64,{{ images.udp_loss_histogram }}" alt="UDP Packet Loss Histogram">
            </div>
            {% endif %}
            
            {% if images.udp_jitter_histogram %}
            <div class="image-container">
                <h3>UDP Jitter Distribution</h3>
                <img src="data:image/png;base64,{{ images.udp_jitter_histogram }}" alt="UDP Jitter Histogram">
            </div>
            {% endif %}
            
            {% if images.udp_bandwidth_heatmap %}
            <div class="image-container">
                <h3>Inter-Region UDP Bandwidth Heatmap</h3>
                <img src="data:image/png;base64,{{ images.udp_bandwidth_heatmap }}" alt="UDP Bandwidth Heatmap">
            </div>
            {% endif %}
            
            {% if images.udp_loss_heatmap %}
            <div class="image-container">
                <h3>Inter-Region UDP Packet Loss Heatmap</h3>
                <img src="data:image/png;base64,{{ images.udp_loss_heatmap }}" alt="UDP Packet Loss Heatmap">
            </div>
            {% endif %}
            {% endif %}
            
            <div class="footer">
                <p>Report generated by AWS Network Benchmark Tool | {{ timestamp }}</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    # Render HTML
    template = Template(html_template)
    html_content = template.render(**report_data)
    
    # Save HTML report
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = os.path.join(output_dir, f"network_benchmark_report_{timestamp}.html")
    
    with open(output_file, 'w') as f:
        f.write(html_content)
    
    print(f"HTML report generated: {output_file}")
    return output_file

def main():
    parser = argparse.ArgumentParser(description="Generate comprehensive report for network performance test results")
    parser.add_argument("--summary-json", help="Summary JSON file of test results")
    parser.add_argument("--p2p-csv", help="Point-to-point test results CSV file")
    parser.add_argument("--udp-csv", help="UDP test results CSV file")
    parser.add_argument("--images", nargs='+', help="List of visualization image files")
    parser.add_argument("--output-dir", default="visualization", help="Output directory")
    
    args = parser.parse_args()
    
    # Get absolute path to directories
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    
    # If output_dir starts with "../", fix it to the correct project directory
    if args.output_dir.startswith("../"):
        args.output_dir = args.output_dir[3:]  # Remove "../" prefix
    
    output_dir = os.path.join(project_root, args.output_dir)
    data_dir = os.path.join(project_root, 'data')
    
    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)
    
    print(f"Output directory: {output_dir}")
    
    # Look for summary file if not specified
    if not args.summary_json:
        summary_files = [f for f in os.listdir(data_dir) if f.startswith('results_summary_') and f.endswith('.json')]
        if summary_files:
            latest_summary = sorted(summary_files)[-1]
            args.summary_json = os.path.join(data_dir, latest_summary)
            print(f"Using latest summary file: {args.summary_json}")
    
    # Load summary data
    if not args.summary_json or not os.path.exists(args.summary_json):
        print("Error: No summary JSON file specified or found")
        sys.exit(1)
    
    summary_data = load_json_data(args.summary_json)
    
    # Look for CSV files if not specified
    if not args.p2p_csv:
        p2p_files = [f for f in os.listdir(data_dir) if f.startswith('p2p_results_') and f.endswith('.csv')]
        if p2p_files:
            latest_p2p = sorted(p2p_files)[-1]
            args.p2p_csv = os.path.join(data_dir, latest_p2p)
            print(f"Using latest p2p CSV file: {args.p2p_csv}")
    
    if not args.udp_csv:
        udp_files = [f for f in os.listdir(data_dir) if f.startswith('udp_results_') and f.endswith('.csv')]
        if udp_files:
            latest_udp = sorted(udp_files)[-1]
            args.udp_csv = os.path.join(data_dir, latest_udp)
            print(f"Using latest UDP CSV file: {args.udp_csv}")
    
    # Load test data
    p2p_df = None
    if args.p2p_csv and os.path.exists(args.p2p_csv):
        p2p_df = load_csv_data(args.p2p_csv)
        print(f"Loaded {len(p2p_df)} point-to-point test records")
    
    udp_df = None
    if args.udp_csv and os.path.exists(args.udp_csv):
        udp_df = load_csv_data(args.udp_csv)
        print(f"Loaded {len(udp_df)} UDP test records")
    
    # Image files list
    image_files = {}
    
    if args.images:
        # If specific images are provided
        for img_path in args.images:
            if os.path.exists(img_path):
                img_name = os.path.basename(img_path).split('_')[0]
                if 'histogram' in img_path:
                    img_name += '_histogram'
                elif 'heatmap' in img_path:
                    img_name += '_heatmap'
                image_files[img_name] = img_path
    else:
        # Auto-discover images
        image_files = find_latest_images(output_dir)
        if not image_files:
            print("Warning: No visualization images found in output directory")
    
    # Generate HTML report
    html_report = generate_html_report(summary_data, p2p_df, udp_df, image_files, output_dir)
    
    print(f"\nReport generation completed: {html_report}")
    return html_report

if __name__ == "__main__":
    main()
