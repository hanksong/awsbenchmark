# AWS EC2 Network Benchmark Suite

A comprehensive suite for benchmarking network performance between Amazon EC2 instances.

## Team Members

- Hanliang Song (hs67)
- Tim Rolsh (rolshud2)
- Austin Belman (abelma2)
- David Mun (davidm16)

## Features

- **Point-to-Point TCP Bandwidth Testing** - Measures bandwidth between EC2 instances using iperf3 in TCP mode
- **UDP Performance Testing** - Measures bandwidth, packet loss, and jitter using iperf3 in UDP mode
- **Latency Testing** - Measures network latency (RTT) between EC2 instances using ping
- **Visualization** - Generates histograms, heatmaps, and detailed HTML reports
- **Organized Output** - All visualization outputs are stored in timestamped log directories

## Directory Structure

- `scripts/` - Core test scripts
  - `p2p_test.py` - Point-to-point TCP bandwidth testing script
  - `udp_test.py` - UDP testing script (bandwidth, packet loss, jitter)
  - `latency_test.py` - Ping-based latency testing script
  - `run_benchmark.py` - Main script to orchestrate all tests
  - `format_data.py` - Data processing utility
- `data/` - Raw test results in CSV and JSON format
- `visualization/` - Visualization scripts and output files
  - `generate_histograms.py` - Creates histogram and heatmap visualizations
  - `generate_report.py` - Creates HTML report
  - `vis_log_*` - Timestamped directories for visualization outputs

## Recent Improvements

### Latency Testing

Added comprehensive latency testing capabilities that measure Round Trip Time (RTT) between EC2 instances:

- Implemented ping-based testing with customizable packet count and interval settings
- Added latency matrix generation for visualizing the RTT patterns between instances
- Integrated latency data into the HTML report generation

### File Organization

Improved organization of visualization outputs:

- All generated visualizations and reports are now stored in timestamped directories (`vis_log_YYYYMMDD_HHMMSS`)
- A symlink to the latest report is created in the project root for easy access
- Reduced file clutter in the main visualization directory

## Setup

- Get the following info from AWS:
  - Access Key ID
  - Secret Access Key
  - Default region name
  - Default output format

- Install the AWS CLI from this page: [https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html)
- Install Terraform from this page: [https://developer.hashicorp.com/terraform/tutorials/aws-get-started/install-cli](https://developer.hashicorp.com/terraform/tutorials/aws-get-started/install-cli)
- Configure the AWS CLI with your credentials:

```bash
aws configure
```

## Usage

### Running the Full Benchmark Suite

```bash
python3 scripts/run_benchmark.py --config config/benchmark_config.json
```

### Running Individual Tests

```bash
# Run point-to-point TCP bandwidth test
python3 scripts/p2p_test.py --config config/test_config.json

# Run UDP performance test
python3 scripts/udp_test.py --config config/test_config.json

# Run latency test
python3 scripts/latency_test.py --config config/test_config.json
```

### Generating Visualizations

```bash
# Generate histograms and heatmaps
python3 visualization/generate_histograms.py --p2p-csv data/p2p_results_*.csv --udp-csv data/udp_results_*.csv --latency-csv data/latency_results_*.csv

# Generate HTML report
python3 visualization/generate_report.py --summary-json data/results_summary_*.json
```

## Configuration

The benchmark suite uses JSON configuration files to specify:

- EC2 instance details (IPs, instance types, regions)
- Test parameters (duration, parallel streams, etc.)
- Visualization options

Sample configuration files are provided in the `terraform/config.json` directory.

## Requirements

- Python 3.6+
- iperf3
- Required Python packages: matplotlib, numpy, pandas, seaborn

## License

This project is licensed under the MIT License - see the LICENSE file for details.
