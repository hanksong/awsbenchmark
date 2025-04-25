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
    for prefix in ['p2p_bandwidth', 'udp_bandwidth', 'udp_loss', 'udp_jitter', 'latency']:
        pattern = os.path.join(output_dir, f"{prefix}_histogram_*.png")
        matching_files = glob.glob(pattern)
        if matching_files:
            latest_file = sorted(matching_files)[-1]
            image_files[f"{prefix}_histogram"] = latest_file
    
    # Look for heatmap images
    for prefix in ['p2p_bandwidth', 'udp_bandwidth', 'udp_loss', 'latency']:
        pattern = os.path.join(output_dir, f"{prefix}_heatmap_*.png")
        matching_files = glob.glob(pattern)
        if matching_files:
            latest_file = sorted(matching_files)[-1]
            image_files[f"{prefix}_heatmap"] = latest_file
    
    # Look for detailed interval analysis images
    # Pattern: p2p_<region>_to_<region>_bandwidth_intervals_*.png
    # and: udp_<region>_to_<region>_bandwidth_intervals_*.png
    p2p_interval_files = {}
    udp_interval_files = {}
    
    # P2P bandwidth intervals
    pattern = os.path.join(output_dir, "p2p_*_to_*_bandwidth_intervals_*.png")
    matching_files = glob.glob(pattern)
    for file in matching_files:
        basename = os.path.basename(file)
        parts = basename.split('_')
        if len(parts) >= 5:
            source_region = parts[1]
            target_region = parts[3]
            key = f"p2p_{source_region}_to_{target_region}_bandwidth_intervals"
            p2p_interval_files[key] = file
    
    # P2P retransmits intervals
    pattern = os.path.join(output_dir, "p2p_*_to_*_retransmits_intervals_*.png")
    matching_files = glob.glob(pattern)
    for file in matching_files:
        basename = os.path.basename(file)
        parts = basename.split('_')
        if len(parts) >= 5:
            source_region = parts[1]
            target_region = parts[3]
            key = f"p2p_{source_region}_to_{target_region}_retransmits_intervals"
            p2p_interval_files[key] = file
    
    # P2P bandwidth histogram by connection
    pattern = os.path.join(output_dir, "p2p_*_to_*_bandwidth_histogram_*.png")
    matching_files = glob.glob(pattern)
    for file in matching_files:
        basename = os.path.basename(file)
        parts = basename.split('_')
        if len(parts) >= 5:
            source_region = parts[1]
            target_region = parts[3]
            key = f"p2p_{source_region}_to_{target_region}_bandwidth_histogram"
            p2p_interval_files[key] = file
    
    # UDP bandwidth intervals
    pattern = os.path.join(output_dir, "udp_*_to_*_bandwidth_intervals_*.png")
    matching_files = glob.glob(pattern)
    for file in matching_files:
        basename = os.path.basename(file)
        parts = basename.split('_')
        if len(parts) >= 5:
            server_region = parts[1]
            client_region = parts[3]
            key = f"udp_{server_region}_to_{client_region}_bandwidth_intervals"
            udp_interval_files[key] = file
    
    # UDP loss intervals
    pattern = os.path.join(output_dir, "udp_*_to_*_loss_intervals_*.png")
    matching_files = glob.glob(pattern)
    for file in matching_files:
        basename = os.path.basename(file)
        parts = basename.split('_')
        if len(parts) >= 5:
            server_region = parts[1]
            client_region = parts[3]
            key = f"udp_{server_region}_to_{client_region}_loss_intervals"
            udp_interval_files[key] = file
    
    # UDP jitter intervals
    pattern = os.path.join(output_dir, "udp_*_to_*_jitter_intervals_*.png")
    matching_files = glob.glob(pattern)
    for file in matching_files:
        basename = os.path.basename(file)
        parts = basename.split('_')
        if len(parts) >= 5:
            server_region = parts[1]
            client_region = parts[3]
            key = f"udp_{server_region}_to_{client_region}_jitter_intervals"
            udp_interval_files[key] = file
    
    # UDP bandwidth histogram by connection
    pattern = os.path.join(output_dir, "udp_*_to_*_bandwidth_histogram_*.png")
    matching_files = glob.glob(pattern)
    for file in matching_files:
        basename = os.path.basename(file)
        parts = basename.split('_')
        if len(parts) >= 5:
            server_region = parts[1]
            client_region = parts[3]
            key = f"udp_{server_region}_to_{client_region}_bandwidth_histogram"
            udp_interval_files[key] = file
    
    # Add the interval files to the image_files
    image_files["p2p_interval_files"] = p2p_interval_files
    image_files["udp_interval_files"] = udp_interval_files
    
    return image_files

def generate_html_report(summary_data, p2p_df, udp_df, latency_df, image_files, output_dir):
    """Generate comprehensive report in HTML format"""
    
    # Prepare report data
    report_data = {
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'summary': summary_data,
        'images': {}
    }
    
    # Add images
    for img_key, img_path in image_files.items():
        if img_key not in ["p2p_interval_files", "udp_interval_files"]:
            if os.path.exists(img_path):
                report_data['images'][img_key] = image_to_base64(img_path)
    
    # Add interval images
    report_data['p2p_interval_images'] = {}
    for img_key, img_path in image_files.get("p2p_interval_files", {}).items():
        if os.path.exists(img_path):
            report_data['p2p_interval_images'][img_key] = image_to_base64(img_path)
    
    report_data['udp_interval_images'] = {}
    for img_key, img_path in image_files.get("udp_interval_files", {}).items():
        if os.path.exists(img_path):
            report_data['udp_interval_images'][img_key] = image_to_base64(img_path)
    
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
        
        # Use summary data for UDP region stats if available
        if 'udp_region_stats' in summary_data:
            report_data['udp_region_stats'] = summary_data['udp_region_stats']
        else:
            # Fallback to generating from DataFrame
            try:
                region_stats = udp_df.groupby(['server_region', 'client_region'])[['bandwidth_mbps', 'lost_percent', 'jitter_ms']].agg(['mean']).reset_index()
                report_data['udp_region_stats'] = region_stats.to_dict('records')
            except Exception as e:
                print(f"Warning: Could not generate UDP region stats: {e}")
                report_data['udp_region_stats'] = []
    
    # Add latency test statistics
    if latency_df is not None and not latency_df.empty:
        report_data['latency_stats'] = {
            'count': len(latency_df),
            'avg_latency': latency_df['avg_latency_ms'].mean(),
            'min_latency': latency_df['avg_latency_ms'].min(),
            'max_latency': latency_df['avg_latency_ms'].max(),
            'median_latency': latency_df['avg_latency_ms'].median()
        }
        
        # Region pair statistics
        try:
            region_stats = latency_df.groupby(['source_region', 'target_region'])[['avg_latency_ms', 'min_latency_ms', 'max_latency_ms']].agg('first').reset_index()
            report_data['latency_region_stats'] = region_stats.to_dict('records')
        except Exception as e:
            print(f"Warning: Could not generate latency region stats: {e}")
            report_data['latency_region_stats'] = []
    
    # HTML template (updated to include interval analysis)
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
            h1, h2, h3, h4 {
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
            .interval-container {
                margin-top: 30px;
                padding: 20px;
                background-color: #f9f9f9;
                border-radius: 5px;
            }
            .connection {
                margin-bottom: 30px;
                border-bottom: 1px solid #ddd;
                padding-bottom: 20px;
            }
            .toggle-button {
                background-color: #0066cc;
                color: white;
                border: none;
                padding: 10px 15px;
                margin-bottom: 10px;
                cursor: pointer;
                border-radius: 4px;
            }
            .toggle-content {
                display: none;
            }
            .show {
                display: block;
            }
        </style>
        <script>
            function toggleContent(id) {
                var content = document.getElementById(id);
                if (content.style.display === "none" || content.style.display === "") {
                    content.style.display = "block";
                } else {
                    content.style.display = "none";
                }
            }
        </script>
    </head>
    <body>
        <div class="container">
            <h1>AWS Network Benchmark Report</h1>
            <p>Generated at: {{ timestamp }}</p>
            
            <div class="summary-box">
                <h2>Test Summary</h2>
                <p>Point-to-point tests: {{ summary.p2p_test_count }} (Successful: {{ summary.p2p_success_count }})</p>
                <p>UDP tests: {{ summary.udp_test_count }} (Successful: {{ summary.udp_success_count }})</p>
                {% if latency_stats %}
                <p>Latency tests: {{ latency_stats.count }}</p>
                {% endif %}
            </div>
            
            {% if latency_stats %}
            <h2>Network Latency Test Results</h2>
            <div class="summary-box">
                <p>Average Latency: {{ "%.2f"|format(latency_stats.avg_latency) }} ms</p>
                <p>Minimum Latency: {{ "%.2f"|format(latency_stats.min_latency) }} ms</p>
                <p>Maximum Latency: {{ "%.2f"|format(latency_stats.max_latency) }} ms</p>
                <p>Median Latency: {{ "%.2f"|format(latency_stats.median_latency) }} ms</p>
            </div>
            
            <h3>Inter-Region Latency Statistics</h3>
            <table>
                <tr>
                    <th>Source Region</th>
                    <th>Target Region</th>
                    <th>Average Latency (ms)</th>
                    <th>Minimum Latency (ms)</th>
                    <th>Maximum Latency (ms)</th>
                </tr>
                {% for stat in latency_region_stats %}
                <tr>
                    <td>{{ stat.source_region }}</td>
                    <td>{{ stat.target_region }}</td>
                    <td>{{ "%.2f"|format(stat.avg_latency_ms) }}</td>
                    <td>{{ "%.2f"|format(stat.min_latency_ms) }}</td>
                    <td>{{ "%.2f"|format(stat.max_latency_ms) }}</td>
                </tr>
                {% endfor %}
            </table>
            
            {% if images.latency_histogram %}
            <div class="image-container">
                <h3>Network Latency Distribution</h3>
                <img src="data:image/png;base64,{{ images.latency_histogram }}" alt="Network Latency Histogram">
            </div>
            {% endif %}
            
            {% if images.latency_heatmap %}
            <div class="image-container">
                <h3>Inter-Region Latency Heatmap</h3>
                <img src="data:image/png;base64,{{ images.latency_heatmap }}" alt="Latency Heatmap">
            </div>
            {% endif %}
            {% endif %}
            
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
            
            {% if p2p_interval_images and p2p_interval_images|length > 0 %}
            <div class="interval-container">
                <h3>Detailed Point-to-Point Connection Analysis</h3>
                <p>Click on each connection to see detailed interval performance data.</p>
                
                {% set connections = {} %}
                {% for key, image in p2p_interval_images.items() %}
                    {% set parts = key.split('_') %}
                    {% if parts|length >= 5 %}
                        {% set source = parts[1] %}
                        {% set target = parts[3] %}
                        {% set connection_key = source + "_to_" + target %}
                        {% if connection_key not in connections %}
                            {% set _ = connections.update({connection_key: {"source": source, "target": target, "images": {}}}) %}
                        {% endif %}
                        {% set _ = connections[connection_key]["images"].update({key: image}) %}
                    {% endif %}
                {% endfor %}
                
                {% for conn_key, conn_info in connections.items() %}
                <div class="connection">
                    <button class="toggle-button" onclick="toggleContent('p2p_{{ conn_key }}')">
                        {{ conn_info.source }} → {{ conn_info.target }}
                    </button>
                    <div id="p2p_{{ conn_key }}" class="toggle-content">
                        {% set bandwidth_interval_key = "p2p_" + conn_info.source + "_to_" + conn_info.target + "_bandwidth_intervals" %}
                        {% if bandwidth_interval_key in conn_info.images %}
                        <div class="image-container">
                            <h4>Bandwidth Over Time</h4>
                            <img src="data:image/png;base64,{{ conn_info.images[bandwidth_interval_key] }}" alt="Bandwidth over time">
                        </div>
                        {% endif %}
                        
                        {% set retransmits_interval_key = "p2p_" + conn_info.source + "_to_" + conn_info.target + "_retransmits_intervals" %}
                        {% if retransmits_interval_key in conn_info.images %}
                        <div class="image-container">
                            <h4>Retransmits Over Time</h4>
                            <img src="data:image/png;base64,{{ conn_info.images[retransmits_interval_key] }}" alt="Retransmits over time">
                        </div>
                        {% endif %}
                        
                        {% set bandwidth_histogram_key = "p2p_" + conn_info.source + "_to_" + conn_info.target + "_bandwidth_histogram" %}
                        {% if bandwidth_histogram_key in conn_info.images %}
                        <div class="image-container">
                            <h4>Bandwidth Distribution</h4>
                            <img src="data:image/png;base64,{{ conn_info.images[bandwidth_histogram_key] }}" alt="Bandwidth histogram">
                        </div>
                        {% endif %}
                    </div>
                </div>
                {% endfor %}
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
                    <td>{{ "%.2f"|format(stat.avg_bandwidth_mbps) }}</td>
                    <td>{{ "%.2f"|format(stat.avg_packet_loss_percent) }}</td>
                    <td>{{ "%.2f"|format(stat.avg_jitter_ms if 'avg_jitter_ms' in stat else 0) }}</td>
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
            
            {% if udp_interval_images and udp_interval_images|length > 0 %}
            <div class="interval-container">
                <h3>Detailed UDP Connection Analysis</h3>
                <p>Click on each connection to see detailed interval performance data.</p>
                
                {% set connections = {} %}
                {% for key, image in udp_interval_images.items() %}
                    {% set parts = key.split('_') %}
                    {% if parts|length >= 5 %}
                        {% set server = parts[1] %}
                        {% set client = parts[3] %}
                        {% set connection_key = server + "_to_" + client %}
                        {% if connection_key not in connections %}
                            {% set _ = connections.update({connection_key: {"server": server, "client": client, "images": {}}}) %}
                        {% endif %}
                        {% set _ = connections[connection_key]["images"].update({key: image}) %}
                    {% endif %}
                {% endfor %}
                
                {% for conn_key, conn_info in connections.items() %}
                <div class="connection">
                    <button class="toggle-button" onclick="toggleContent('udp_{{ conn_key }}')">
                        {{ conn_info.server }} → {{ conn_info.client }}
                    </button>
                    <div id="udp_{{ conn_key }}" class="toggle-content">
                        {% set bandwidth_interval_key = "udp_" + conn_info.server + "_to_" + conn_info.client + "_bandwidth_intervals" %}
                        {% if bandwidth_interval_key in conn_info.images %}
                        <div class="image-container">
                            <h4>Bandwidth Over Time</h4>
                            <img src="data:image/png;base64,{{ conn_info.images[bandwidth_interval_key] }}" alt="Bandwidth over time">
                        </div>
                        {% endif %}
                        
                        {% set loss_interval_key = "udp_" + conn_info.server + "_to_" + conn_info.client + "_loss_intervals" %}
                        {% if loss_interval_key in conn_info.images %}
                        <div class="image-container">
                            <h4>Packet Loss Over Time</h4>
                            <img src="data:image/png;base64,{{ conn_info.images[loss_interval_key] }}" alt="Packet loss over time">
                        </div>
                        {% endif %}
                        
                        {% set jitter_interval_key = "udp_" + conn_info.server + "_to_" + conn_info.client + "_jitter_intervals" %}
                        {% if jitter_interval_key in conn_info.images %}
                        <div class="image-container">
                            <h4>Jitter Over Time</h4>
                            <img src="data:image/png;base64,{{ conn_info.images[jitter_interval_key] }}" alt="Jitter over time">
                        </div>
                        {% endif %}
                        
                        {% set bandwidth_histogram_key = "udp_" + conn_info.server + "_to_" + conn_info.client + "_bandwidth_histogram" %}
                        {% if bandwidth_histogram_key in conn_info.images %}
                        <div class="image-container">
                            <h4>Bandwidth Distribution</h4>
                            <img src="data:image/png;base64,{{ conn_info.images[bandwidth_histogram_key] }}" alt="Bandwidth histogram">
                        </div>
                        {% endif %}
                    </div>
                </div>
                {% endfor %}
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
    parser.add_argument("--latency-csv", help="Latency test results CSV file")
    parser.add_argument("--images", nargs='+', help="List of visualization image files")
    parser.add_argument("--output-dir", default="visualization", help="Output directory")
    parser.add_argument("--log-subdir", default="", help="Use specific log subdirectory for output")
    
    args = parser.parse_args()
    
    # Get absolute path to directories
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    
    # If output_dir starts with "../", fix it to the correct project directory
    if args.output_dir.startswith("../"):
        args.output_dir = args.output_dir[3:]  # Remove "../" prefix
    
    output_dir = os.path.join(project_root, args.output_dir)
    data_dir = os.path.join(project_root, 'data')
    
    # Use the specified log subdirectory or try to use "latest" symlink
    if args.log_subdir:
        output_dir = os.path.join(output_dir, args.log_subdir)
    else:
        latest_link = os.path.join(output_dir, "latest")
        if os.path.exists(latest_link) and os.path.isdir(latest_link):
            output_dir = latest_link
            print(f"Using latest visualization log directory: {output_dir}")
        else:
            # Create a timestamped log directory if not using an existing one
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            log_dir_name = f"vis_log_{timestamp}"
            output_dir = os.path.join(output_dir, log_dir_name)
            
            # Create symlink to latest
            try:
                latest_link = os.path.join(os.path.dirname(output_dir), "latest")
                if os.path.islink(latest_link):
                    os.unlink(latest_link)
                os.symlink(output_dir, latest_link, target_is_directory=True)
                print(f"Created symlink: {latest_link} -> {output_dir}")
            except Exception as e:
                print(f"Warning: Could not create symlink: {e}")
    
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
            
    if not args.latency_csv:
        latency_files = [f for f in os.listdir(data_dir) if f.startswith('latency_results_') and f.endswith('.csv')]
        if latency_files:
            latest_latency = sorted(latency_files)[-1]
            args.latency_csv = os.path.join(data_dir, latest_latency)
            print(f"Using latest latency CSV file: {args.latency_csv}")
    
    # Load test data
    p2p_df = None
    if args.p2p_csv and os.path.exists(args.p2p_csv):
        p2p_df = load_csv_data(args.p2p_csv)
        print(f"Loaded {len(p2p_df)} point-to-point test records")
    
    udp_df = None
    if args.udp_csv and os.path.exists(args.udp_csv):
        udp_df = load_csv_data(args.udp_csv)
        print(f"Loaded {len(udp_df)} UDP test records")
        
    latency_df = None
    if args.latency_csv and os.path.exists(args.latency_csv):
        latency_df = load_csv_data(args.latency_csv)
        print(f"Loaded {len(latency_df)} latency test records")
    
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
    html_report = generate_html_report(summary_data, p2p_df, udp_df, latency_df, image_files, output_dir)
    
    print(f"\nReport generation completed: {html_report}")
    return html_report

if __name__ == "__main__":
    main()
