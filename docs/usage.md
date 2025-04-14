# AWS Network Benchmark Tool Usage Guide

This document provides detailed usage instructions for the AWS Network Benchmark Tool, including configuration, running tests, and analyzing results.

## Configuring the Tool

### Configuration File Description

The main configuration file for the tool is `config.json` in the project root directory. Below is a detailed description of the configuration options:

```json
{
  "aws_regions": ["us-east-1", "us-west-2", "eu-west-1", "ap-northeast-1", "sa-east-1"],
  "instance_type": "t2.micro",
  "ssh_key_name": "aws-network-benchmark",
  "create_ssh_key": true,
  "instance_count": 1,
  
  "run_p2p_tests": true,
  "p2p_duration": 10,
  "p2p_parallel": 1,
  
  "run_udp_tests": true,
  "udp_server_region": "us-east-1",
  "udp_bandwidth": "1G",
  "udp_duration": 10,
  
  "cleanup_resources": false
}
```

| Configuration Item | Description | Default Value |
|--------|------|--------|
| `aws_regions` | List of AWS regions to deploy EC2 instances | `["us-east-1", "us-west-2", "eu-west-1", "ap-northeast-1", "sa-east-1"]` |
| `instance_type` | EC2 instance type | `"t2.micro"` |
| `ssh_key_name` | SSH key name | `"aws-network-benchmark"` |
| `create_ssh_key` | Whether to automatically create SSH key | `true` |
| `instance_count` | Number of instances to create in each region | `1` |
| `run_p2p_tests` | Whether to run point-to-point tests | `true` |
| `p2p_duration` | Duration of point-to-point tests (seconds) | `10` |
| `p2p_parallel` | Number of parallel streams for point-to-point tests | `1` |
| `run_udp_tests` | Whether to run UDP tests | `true` |
| `udp_server_region` | Region where the UDP test server is located | `"us-east-1"` |
| `udp_bandwidth` | UDP test bandwidth limit | `"1G"` |
| `udp_duration` | UDP test duration (seconds) | `10` |
| `cleanup_resources` | Whether to clean up AWS resources after testing | `false` |

### Modifying Configuration

You can modify the configuration options in the `config.json` file:

1. **Adjusting Test Regions**：Modify the `aws_regions` array to add or remove AWS regions.
   ```json
   "aws_regions": ["us-east-1", "us-west-2", "ap-southeast-1", "eu-central-1"]
   ```

2. **Changing Instance Type**：For higher performance tests, you can choose a more powerful instance type.
   ```json
   "instance_type": "t3.medium"
   ```

3. **Adjusting Test Parameters**：Adjust the test duration and parallelism as needed.
   ```json
   "p2p_duration": 30,
   "p2p_parallel": 4
   ```

4. **Enabling Resource Cleanup**：Clean up AWS resources automatically after testing.
   ```json
   "cleanup_resources": true
   ```

## Running Tests

### Basic Usage

Run the following command in the project root directory to start the tests:

```bash
python3 scripts/run_benchmark.py
```

This will execute the complete test process, including:
1. Using Terraform to deploy EC2 instances
2. Installing iperf3 on the instances
3. Executing network performance tests
4. Collecting and processing test results
5. Generating visual reports

### Command Line Options

The `run_benchmark.py` script supports the following command line options:

```bash
python3 scripts/run_benchmark.py [options]
```

| Option | Description |
|------|------|
| `--config PATH` | Specify the path to the configuration file (default: `../config.json`) |
| `--skip-terraform` | Skip the Terraform deployment step |
| `--skip-install` | Skip the iperf3 installation step |
| `--skip-tests` | Skip the network test step |
| `--cleanup` | Clean up AWS resources after testing |

### Example Usage

1. **Using Custom Configuration File**：
   ```bash
   python3 scripts/run_benchmark.py --config my_config.json
   ```

2. **Run Tests Without Deployment**（Assuming instances are already deployed）：
   ```bash
   python3 scripts/run_benchmark.py --skip-terraform
   ```

3. **Run Tests and Clean Up Resources**：
   ```bash
   python3 scripts/run_benchmark.py --cleanup
   ```

4. **Process Existing Test Results**（Skip Deployment and Tests）：
   ```bash
   python3 scripts/run_benchmark.py --skip-terraform --skip-install --skip-tests
   ```

## Test Results Analysis

### Result Files

Test results will be saved in the following locations:

- **Raw Test Data**：`data/` directory
- **Visualization Charts**：`visualization/` directory
- **HTML Report**：Project root directory and `visualization/` directory
- **Results for Each Run**：`runs/TIMESTAMP/` directory

### HTML Report Interpretation

The HTML report contains the following main sections:

1. **Test Summary**：Display test count and success rate
2. **Point-to-Point Test Results**：
   - Bandwidth Statistics (Average, Minimum, Maximum, Median)
   - Inter-Region Bandwidth Table
   - Bandwidth Distribution Histogram
   - Inter-Region Bandwidth Heatmap
3. **UDP Test Results**：
   - Bandwidth, Packet Loss, and Jitter Statistics
   - Inter-Region UDP Performance Table
   - Bandwidth, Packet Loss, and Jitter Distribution Histogram
   - Inter-Region UDP Bandwidth and Packet Loss Rate Heatmap

### Key Indicators Interpretation

1. **Bandwidth**：
   - Unit: Mbps (Megabits per second)
   - Higher is better
   - Reflects network throughput capability

2. **Packet Loss**：
   - Unit: % (Percentage)
   - Lower is better
   - Reflects network reliability

3. **Jitter**：
   - Unit: ms (Milliseconds)
   - Lower is better
   - Reflects the degree of network latency variation, which is important for real-time applications

4. **Inter-Region Performance Differences**：
   - The heatmap can visually show the network performance differences between different regions
   - Helps choose the best multi-region deployment strategy

## Advanced Usage

### Running Individual Components Separately

You can run individual components of the tool:

1. **Deploy Infrastructure Only**：
   ```bash
   cd terraform
   terraform init
   terraform apply
   ```

2. **Run Point-to-Point Tests Only**：
   ```bash
   python3 scripts/point_to_point_test.py --instance-info data/instance_info.json --ssh-key ~/.ssh/aws-network-benchmark --all-regions
   ```

3. **Run UDP Tests Only**：
   ```bash
   python3 scripts/udp_multicast_test.py --instance-info data/instance_info.json --ssh-key ~/.ssh/aws-network-benchmark --server-region us-east-1
   ```

4. **Collect and Process Results Only**：
   ```bash
   python3 scripts/collect_results.py --data-dir data
   python3 scripts/parse_data.py --input data/collected_results_*.json
   python3 scripts/format_data.py --p2p-csv data/p2p_results_*.csv --udp-csv data/udp_results_*.csv
   ```

5. **Generate Visualization Only**：
   ```bash
   python3 visualization/generate_histograms.py --p2p-csv data/p2p_results_*.csv --udp-csv data/udp_results_*.csv
   python3 visualization/generate_report.py --summary-json data/results_summary_*.json --p2p-csv data/p2p_results_*.csv --udp-csv data/udp_results_*.csv
   ```

### Custom Test

1. **Test Specific Region Pair**：
   ```bash
   python3 scripts/point_to_point_test.py --instance-info data/instance_info.json --ssh-key ~/.ssh/aws-network-benchmark --source-region us-east-1 --target-region ap-northeast-1
   ```

2. **Adjust UDP Test Bandwidth**：
   ```bash
   python3 scripts/udp_multicast_test.py --instance-info data/instance_info.json --ssh-key ~/.ssh/aws-network-benchmark --server-region us-east-1 --bandwidth 500M
   ```

## Troubleshooting

### Common Issues

1. **Terraform Deployment Failure**：
   - Check if AWS credentials are valid
   - Confirm you have sufficient permissions to create required resources
   - Check Terraform error messages, which may be due to resource limits or configuration issues

2. **SSH Connection Failure**：
   - Confirm the correct SSH key path
   - Check if the security group allows SSH connections
   - Wait for the instance to fully start (usually takes 1-2 minutes)

3. **iperf3 Test Failure**：
   - Confirm iperf3 is installed correctly
   - Check if the security group allows iperf3 port (5201)
   - Check if instances can communicate with each other

4. **Result Processing or Visualization Failure**：
   - Confirm that required Python packages are installed
   - Check if test result files exist
   - Check error messages for specific issues

### Logging and Debugging

- The output of the main execution script will display progress and errors for each step
- Terraform logs are located in the `terraform/` directory
- Results for each run are saved in the `runs/TIMESTAMP/` directory, for later analysis

## Best Practices

1. **Choosing Appropriate Instance Type**：
   - For network performance tests, it's recommended to use an instance type that supports enhanced networking
   - t3.medium or higher specifications can yield more accurate results

2. **Adjusting Test Duration**：
   - Short test duration (10 seconds) is suitable for quick assessment
   - Longer test duration (60 seconds or more) can yield more stable results

3. **Multiple Tests for Average**：
   - Network performance can be affected by various factors
   - It's recommended to perform multiple tests and analyze average results

4. **Testing Different Time Points**：
   - Network performance can vary with time
   - Testing at different time points can yield a more comprehensive performance picture

5. **Resource Management**：
   - Clean up resources after testing to avoid unnecessary costs
   - Use `--cleanup` option or set `"cleanup_resources": true`
