# AWS EC2 Network Benchmark Suite

A comprehensive suite for benchmarking network performance between Amazon EC2 instances.

# Team Members

---

### Hanliang Song (hs67)

- MS in Financial Engineering 2025' | Quant Developer | Seeking for full-time position starting Dec 2025.

---

### Tim Rolsh (rolshud2)

<img src="imgs/rolshud2.jpg" alt="Tim Rolsh" width="300"/>

- Undergraduate student at the University of Illinois Urbana-Champaign pursuing a BSLAS in Statistics and Computer Science, expected graduation May 2027. Full-stack software engineer and clean code practitioner. Open to internship opportunities and part-time roles during studies, seeking full-time positions starting May 2027.
- LinkedIn: [https://www.linkedin.com/in/tim-rolsh-492088261/](https://www.linkedin.com/in/tim-rolsh-492088261/)
- GitHub: [https://github.com/timrolsh](https://github.com/timrolsh)

---

### Austin Belman (abelma2)

- add here

---

### David Mun (davidm16)

<img src="imgs/davidm16.jpeg" alt="David Mun" width="300"/>

I am currently a junior studying Computer Engineering at UIUC graduating in Spring 2026. I have previous experience working with low-latency C++ embedded systems at Rivian and I am currently working at DRW as a software engineering intern. I am interested in intersecting my understanding of computer systems with trading, and I am motivated by solving hard problems.

Email: [davidm16@illinois.edu](mailto:davidm16@illinois.edu)
LinkedIn: <https://www.linkedin.com/in/davidmun910/>

---

# Features

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
- Terraform 0.14+
- The following Python packages:

  - pandas
  - matplotlib
  - seaborn
  - jinja2
  - numpy
- iperf3

## Quick Start

1. Clone the repository:

   ```
   git clone https://github.com/yourusername/aws-network-benchmark.git
   cd aws-network-benchmark
   ```

2. Install dependencies:

   ```
   pip install -r requirements.txt
   ```

3. Configure AWS credentials:

   ```
   aws configure
   ```

4. Modify the `config.json` configuration file (optional):

   ```json
   {
     "aws_regions": ["us-east-1", "us-west-2", "eu-west-1", "ap-northeast-1", "sa-east-1"],
     "instance_type": "t2.micro",
     "ssh_key_name": "aws-network-benchmark",
     "create_ssh_key": true,
     "use_private_ip": false,
     ...
   }
   ```

   - Set `use_private_ip` to `true` to use private IPs for testing (when using VPC Peering or other connection methods within the same region)
   - Set `use_private_ip` to `false` (default) to use public IPs for testing (for general cross-region scenarios)
5. Run the benchmark:

```bash
python3 scripts/run_benchmark.py [options]
```

| Option               | Description                                                                       |
| -------------------- | --------------------------------------------------------------------------------- |
| `--config PATH`    | Specify the path to the configuration file (default:`../terraform/config.json`) |
| `--skip-terraform` | Skip the Terraform deployment step                                                |
| `--skip-install`   | Skip the iperf3 installation step                                                 |
| `--skip-tests`     | Skip the network test step                                                        |
| `--cleanup`        | Clean up AWS resources after testing                                              |

## Detailed Documentation

- [Installation Guide](docs/installation.md)
- [Usage Instructions](docs/usage.md)

## License

MIT

## Contribution

Issues and pull requests are welcome.

## Troubleshooting

### cannot automatically import ssh key to aws, please run the following command to import manually

```
aws ec2 import-key-pair --region us-east-1 --key-name aws-network-benchmark --public-key-material fileb://$HOME/.ssh/aws-network-benchmark.pub
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.
