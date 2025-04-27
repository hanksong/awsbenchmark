# AWS Network Benchmark Tool

This project provides an automated tool for network performance benchmarking between EC2 instances in different AWS regions. The tool uses Terraform to automatically deploy EC2 instances, performs network tests using iperf3, and generates visualization reports.

# Team Members

- Hanliang Song (hs67)
  - MS in Financial Engineering 2025' | Quant Developer | Seeking for full-time position starting Dec 2025.
- Tim Rolsh (rolshud2)
- Austin Belman (abelma2)
- David Mun (davidm16)

# Features

- **Multi-region Deployment**: Automatically deploy EC2 instances in multiple AWS regions using Terraform
- **Network Performance Testing**: Conduct point-to-point and one-to-many UDP tests using iperf3
- **Data Collection and Processing**: Automatically collect test results and process data
- **Visualization Reports**: Generate histograms and heatmaps for bandwidth, packet loss, and jitter
- **Complete Automation**: One-click execution of the entire process from deployment to testing, data collection, and report generation

## Project Structure

```
aws-network-benchmark/
├── terraform/             # Terraform configuration files
│   ├── variables.tf       # Variable definitions
│   ├── provider.tf        # AWS provider configuration
│   ├── main.tf            # Main configuration file
│   ├── outputs.tf         # Output definitions
│   └── modules/           # Modules directory
│       ├── vpc/           # VPC module
│       ├── security_group/ # Security group module
│       └── ec2/           # EC2 instance module
├── scripts/               # Testing and data processing scripts
│   ├── install_iperf3.sh  # iperf3 installation script
│   ├── point_to_point_test.py # Point-to-point test script
│   ├── udp_multicast_test.py  # One-to-many UDP test script
│   ├── collect_results.py     # Results collection script
│   ├── parse_data.py          # Data parsing script
│   ├── format_data.py         # Data formatting script
│   └── run_benchmark.py       # Main execution script
├── visualization/         # Visualization scripts
│   ├── generate_histograms.py # Histogram generation script
│   └── generate_report.py     # Report generation script
├── data/                  # Data storage directory
├── docs/                  # Documentation directory
│   ├── installation.md    # Installation guide
│   └── usage.md           # Usage instructions
├── config.json            # Configuration file
└── README.md              # Project description
```

## Prerequisites

- AWS account and configured AWS CLI credentials
- Python 3.6+
- Terraform 0.14+
- The following Python packages:
  - pandas
  - matplotlib
  - seaborn
  - jinja2
  - numpy

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

   * Set `use_private_ip` to `true` to use private IPs for testing (when using VPC Peering or other connection methods within the same region)
   * Set `use_private_ip` to `false` (default) to use public IPs for testing (for general cross-region scenarios)
5. Run the benchmark:

```bash
python3 scripts/run_benchmark.py [options]
```

| Option                                                                                        | Description                                                                       |
| --------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------- |
| `--config PATH`                                                                             | Specify the path to the configuration file (default:`../terraform/config.json`) |
| `--skip-terraform`                                                                          | Skip the Terraform deployment step                                                |
| `--skip-install`                                                                            | Skip the iperf3 installation step                                                 |
| `--skip-tests`                                                                              | Skip the network test step                                                        |
| `--cleanup`                                                                                 | Clean up AWS resources after testing                                              |
| 6. View the generated reports (located in the project root and `visualization/` directory). |                                                                                   |

## Detailed Documentation

- [Installation Guide](docs/installation.md)
- [Usage Instructions](docs/usage.md)

## License

MIT

## Contribution

Issues and pull requests are welcome.

## Troubleshooting

### cannot automatically import ssh key to aws, please run the following command to import manually:

```
aws ec2 import-key-pair --region us-east-1 --key-name aws-network-benchmark --public-key-material fileb://$HOME/.ssh/aws-network-benchmark.pub
```
