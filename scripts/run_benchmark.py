#!/usr/bin/env python3
# run_benchmark.py
# AWS Network Benchmark Automation Script

import argparse
import os
import sys
import json
import subprocess
import time
from datetime import datetime
import shutil
import glob

# Define project root directory
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def run_command(command, cwd=None):
    """Execute command and return output"""
    try:
        if cwd is None:
            cwd = PROJECT_ROOT

        print(f"Executing command: {command}")
        result = subprocess.run(command, shell=True, check=True, cwd=cwd,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                text=True)
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"Command execution failed: {e}")
        print(f"Error output: {e.stderr}")
        return None


def setup_terraform(config):
    """Setup and apply Terraform configuration"""
    terraform_dir = os.path.join(PROJECT_ROOT, "terraform")
    data_dir = os.path.join(PROJECT_ROOT, "data")

    # Ensure data directory exists
    os.makedirs(data_dir, exist_ok=True)

    # Generate Terraform files from config.json
    print("Generating Terraform configuration files from config.json...")
    gen_terraform_cmd = f"python3 {os.path.join(PROJECT_ROOT, 'scripts/generate_terraform.py')} --config {os.path.join(PROJECT_ROOT, 'terraform/config.json')} --terraform-dir {terraform_dir}"
    run_command(gen_terraform_cmd)

    # Handle SSH key across all regions
    key_name = config.get('ssh_key_name', 'aws-network-benchmark')
    key_path = os.path.expanduser(f"~/.ssh/{key_name}")
    pub_key_path = f"{key_path}.pub"

    # Create local SSH key if it doesn't exist
    if not os.path.exists(key_path) and config.get('create_ssh_key', True):
        print(f"Creating SSH key: {key_path}")
        run_command(f"ssh-keygen -t rsa -b 2048 -f {key_path} -N ''")

    # Import SSH key to AWS for each region
    aws_regions = config.get('aws_regions', [])

    # Read public key content
    if os.path.exists(pub_key_path):
        try:
            with open(pub_key_path, 'r') as key_file:
                public_key_material = key_file.read().strip()

            if not public_key_material:
                print("Error: Public key file exists but is empty")
                return False

            # Create a temporary file with the correct format for AWS
            temp_key_file = os.path.join(
                "/tmp", f"{key_name}_{int(time.time())}.pub")
            with open(temp_key_file, 'w') as f:
                f.write(public_key_material)

            print(f"Created temporary key file: {temp_key_file}")

            # Process each region with more robust error handling
            for region in aws_regions:
                print(f"\n*** Processing SSH key for region {region} ***")

                # Delete any existing key with same name (force clean slate)
                print(f"Deleting any existing key in {region}...")
                delete_cmd = f"aws ec2 delete-key-pair --region {region} --key-name {key_name}"
                try:
                    run_command(delete_cmd)
                    print(
                        f"Successfully deleted old key in {region} (if it existed)")
                except:
                    print(f"No existing key in {region} or failed to delete")

                # Import the key using fileb:// method
                print(f"Importing SSH key to {region} using fileb://...")
                import_cmd = f"aws ec2 import-key-pair --region {region} --key-name {key_name} --public-key-material fileb://{temp_key_file}"
                result = run_command(import_cmd)

                if result and "KeyPairId" in result:
                    print(f"Successfully imported key to {region}!")
                else:
                    print(
                        f"First import method failed for {region}, trying alternative method...")

                    # Try alternative method with public-key-material as string
                    try:
                        # Format key correctly for direct input
                        formatted_key = public_key_material
                        if "ssh-rsa" not in formatted_key:
                            formatted_key = f"ssh-rsa {formatted_key}"

                        print(
                            f"Importing with alternative method to {region}...")
                        temp_key_json = os.path.join(
                            "/tmp", f"{key_name}_{region}_key.json")
                        with open(temp_key_json, 'w') as f:
                            f.write(formatted_key)

                        # Use base64 encoding
                        base64_cmd = f"cat {temp_key_json} | base64"
                        base64_result = run_command(base64_cmd)

                        if base64_result:
                            base64_key = base64_result.strip()
                            import_cmd2 = f"aws ec2 import-key-pair --region {region} --key-name {key_name} --public-key-material {base64_key}"
                            result2 = run_command(import_cmd2)

                            if result2 and "KeyPairId" in result2:
                                print(
                                    f"Alternative method succeeded for {region}!")
                            else:
                                # Last resort - try using AWS CLI with stdin
                                print(f"Trying final method for {region}...")
                                import_cmd3 = f"aws ec2 import-key-pair --region {region} --key-name {key_name} --public-key-material file://{temp_key_json}"
                                result3 = run_command(import_cmd3)

                                if not result3 or "Error" in str(result3):
                                    print(
                                        f"WARNING: Failed to import key to {region} after multiple attempts!")
                                    print(f"Last error: {result3}")
                                    # Don't return False here, still try to continue with other regions

                        # Clean up temporary json file
                        try:
                            os.remove(temp_key_json)
                        except:
                            pass
                    except Exception as e:
                        print(
                            f"Error during alternative key import for {region}: {str(e)}")

                # Verify key was actually imported
                print(f"Verifying key exists in {region}...")
                verify_cmd = f"aws ec2 describe-key-pairs --region {region} --key-names {key_name}"
                verify_result = run_command(verify_cmd)

                if verify_result and "KeyPairs" in verify_result and key_name in verify_result:
                    print(f"✅ Key verification successful for {region}")
                else:
                    print(
                        f"❌ CRITICAL: Key verification failed for {region}! This will cause deployment to fail.")
                    print(f"Verification result: {verify_result}")

            # Clean up temporary key file
            try:
                os.remove(temp_key_file)
            except:
                pass

        except Exception as e:
            print(f"Error processing SSH key: {str(e)}")
            return False
    else:
        print(f"Error: Public key file {pub_key_path} not found")
        return False

    # Initialize Terraform
    print("\nInitializing Terraform...")
    run_command("terraform init", cwd=terraform_dir)

    # Apply Terraform configuration
    print("\nApplying Terraform configuration...")
    run_command("terraform apply -auto-approve", cwd=terraform_dir)

    # Wait for instances to start
    print("Waiting for EC2 instances to start and initialize...")
    time.sleep(60)

    # Get Terraform output and generate instance info file
    print("Getting instance information...")
    terraform_output = run_command("terraform output -json", cwd=terraform_dir)

    if not terraform_output:
        print("Error: Unable to get Terraform output")
        return False

    try:
        terraform_data = json.loads(terraform_output)

        # Construct instance info data structure
        instance_info = {
            "instances": {}
        }

        # Get region information from config.json
        aws_regions = config.get('aws_regions', [])
        region_friendly_names = {
            "ap-northeast-1": "tokyo",
            "ap-southeast-2": "sydney",
            "eu-west-2": "london",
            "us-east-1": "virginia",
            "us-west-1": "california",
            "us-west-2": "oregon",
            "eu-central-1": "frankfurt"
            # Add more region mappings if necessary
        }

        # Use region names parsed from Terraform output
        for region_name, values in terraform_data["instance_public_ips"]["value"].items():
            # Check if this is a region with suffix (for multiple resources)
            base_region_name = region_name
            if "_" in region_name:
                # 例如: tokyo_2 -> tokyo
                base_region_name = region_name.split("_")[0]

            # Find corresponding AWS region code
            aws_region = None
            for code, name in region_friendly_names.items():
                if name == base_region_name:
                    aws_region = code
                    break

            if not aws_region:
                print(
                    f"Warning: Could not map region name {region_name} to AWS region code")
                continue

            public_ips = values
            private_ips = terraform_data["instance_private_ips"]["value"][region_name]

            # 如果是当前区域的第一个资源，初始化该区域的IP列表
            if aws_region not in instance_info["instances"]:
                instance_info["instances"][aws_region] = {
                    "public_ips": [],
                    "private_ips": []
                }

            # 将当前资源的IP添加到对应区域
            instance_info["instances"][aws_region]["public_ips"].extend(
                public_ips)
            instance_info["instances"][aws_region]["private_ips"].extend(
                private_ips)

        # Save instance info to JSON file
        instance_info_path = os.path.join(
            PROJECT_ROOT, "data/instance_info.json")
        with open(instance_info_path, 'w') as f:
            json.dump(instance_info, f, indent=2)

    except Exception as e:
        print(f"Error: Failed to process Terraform output: {e}")
        return False

    # Get instance info
    instance_info_path = os.path.join(PROJECT_ROOT, "data/instance_info.json")

    if not os.path.exists(instance_info_path):
        print("Error: Unable to find instance info file")
        return False

    print(
        f"Terraform configuration applied, instance info saved to: {instance_info_path}")
    return True


def install_iperf3(config):
    """Install iperf3 on all EC2 instances"""
    instance_info_path = os.path.join(PROJECT_ROOT, "data/instance_info.json")
    ssh_key_path = os.path.expanduser(
        f"~/.ssh/{config.get('ssh_key_name', 'aws-network-benchmark')}")

    try:
        with open(instance_info_path, 'r') as f:
            instance_data = json.load(f)

        install_script_path = os.path.join(
            PROJECT_ROOT, "scripts/install_iperf3.sh")

        # Ensure install script has execute permission
        run_command(f"chmod +x {install_script_path}")

        # Install iperf3 on instances in each region
        for region, info in instance_data['instances'].items():
            for ip in info['public_ips']:
                # Skip empty IP addresses
                if not ip or ip == "":
                    print(
                        f"Warning: Instance in {region} region has no public IP, skipping installation")
                    continue

                print(
                    f"Installing iperf3 on instance {ip} in {region} region...")

                # Copy install script to instance
                scp_cmd = f"scp -i {ssh_key_path} -o StrictHostKeyChecking=no {install_script_path} ec2-user@{ip}:/tmp/"
                run_command(scp_cmd)

                # Execute install script
                ssh_cmd = f"ssh -i {ssh_key_path} -o StrictHostKeyChecking=no ec2-user@{ip} 'chmod +x /tmp/install_iperf3.sh && sudo /tmp/install_iperf3.sh'"
                run_command(ssh_cmd)

        print("iperf3 installation completed on all instances")
        return True
    except Exception as e:
        print(f"Error installing iperf3: {e}")
        return False


def run_network_tests(config):
    """Run network performance tests"""
    instance_info_path = os.path.join(PROJECT_ROOT, "data/instance_info.json")
    ssh_key_path = os.path.expanduser(
        f"~/.ssh/{config.get('ssh_key_name', 'aws-network-benchmark')}")
    scripts_dir = os.path.join(PROJECT_ROOT, "scripts")
    data_dir = os.path.join(PROJECT_ROOT, "data")

    # Ensure data directory exists
    os.makedirs(data_dir, exist_ok=True)

    # Control whether to use private IPs for testing
    use_private_ip = config.get('use_private_ip', False)
    ip_type_flag = "--use-private-ip" if use_private_ip else ""
    ip_type_desc = "private IPs" if use_private_ip else "public IPs"
    print(f"\nUsing {ip_type_desc} for network tests")

    # Determine if we should test within regions
    intra_region_flag = "--intra-region" if config.get(
        'test_intra_region', True) else ""

    # Run latency (ping) tests
    if config.get('run_latency_tests', True):
        print("\nStarting latency tests...")
        latency_cmd = (
            f"python3 {scripts_dir}/latency_test.py "
            f"--instance-info {instance_info_path} "
            f"--ssh-key {ssh_key_path} "
            f"--ping-count {config.get('ping_count', 20)} "
            f"--output-dir {data_dir} "
            f"--all-regions {ip_type_flag} {intra_region_flag}"
        )
        run_command(latency_cmd)

    # Run point-to-point tests
    if config.get('run_p2p_tests', True):
        print("\nStarting point-to-point network tests...")
        p2p_cmd = (
            f"python3 {scripts_dir}/point_to_point_test.py "
            f"--instance-info {instance_info_path} "
            f"--ssh-key {ssh_key_path} "
            f"--duration {config.get('p2p_duration', 10)} "
            f"--parallel {config.get('p2p_parallel', 1)} "
            f"--output-dir {data_dir} "
            f"--all-regions {ip_type_flag} {intra_region_flag}"
        )
        run_command(p2p_cmd)

    # Run UDP tests
    if config.get('run_udp_tests', True):
        print("\nStarting UDP network tests...")

        # Get server region from config, use first region if not specified
        with open(instance_info_path, 'r') as f:
            instance_data = json.load(f)

        server_region = config.get('udp_server_region')
        if not server_region:
            server_region = list(instance_data['instances'].keys())[0]

        udp_cmd = (
            f"python3 {scripts_dir}/udp_multicast_test.py "
            f"--instance-info {instance_info_path} "
            f"--ssh-key {ssh_key_path} "
            f"--bandwidth {config.get('udp_bandwidth', '1G')} "
            f"--duration {config.get('udp_duration', 10)} "
            f"--output-dir {data_dir} "
            f"--server-region {server_region} {ip_type_flag} {intra_region_flag}"
        )
        run_command(udp_cmd)

    print("Network tests completed")
    return True


def process_test_results(config):
    """Process test result data"""
    scripts_dir = os.path.join(PROJECT_ROOT, "scripts")
    data_dir = os.path.join(PROJECT_ROOT, "data")

    # Collect test results
    print("\nCollecting test results...")
    collect_cmd = f"python3 {scripts_dir}/collect_results.py --data-dir {data_dir}"
    output = run_command(collect_cmd)

    # Extract collected result file path from output
    collected_file = None
    if output:
        for line in output.splitlines():
            if "Results collected and saved to" in line:
                collected_file = line.split("saved to")[-1].strip()
                break

    if not collected_file or not os.path.exists(collected_file):
        print("Warning: Unable to determine collected results file path")
        # Try to find the latest collected results file
        result_files = [f for f in os.listdir(
            data_dir) if f.startswith("collected_results_")]
        if result_files:
            result_files.sort(reverse=True)
            collected_file = os.path.join(data_dir, result_files[0])
            print(f"Using latest results file: {collected_file}")
        else:
            print("Error: Cannot find collected results file")
            return False

    # Parse test results
    print("\nParsing test results...")
    parse_cmd = f"python3 {scripts_dir}/parse_data.py --input {collected_file} --output-dir {data_dir}"
    output = run_command(parse_cmd)

    # Extract CSV file paths
    p2p_csv = None
    udp_csv = None
    summary_json = None

    if output:
        for line in output.splitlines():
            if "Point-to-point test results saved to" in line:
                p2p_csv = line.split("saved to")[-1].strip()
            elif "UDP test results saved to" in line:
                udp_csv = line.split("saved to")[-1].strip()
            elif "Results summary statistics saved to" in line:
                summary_json = line.split("saved to")[-1].strip()

    # Format data
    print("\nFormatting test data...")
    format_cmd = f"python3 {scripts_dir}/format_data.py"

    if p2p_csv:
        format_cmd += f" --p2p-csv {p2p_csv}"

    if udp_csv:
        format_cmd += f" --udp-csv {udp_csv}"

    format_cmd += f" --output-dir {data_dir}"
    run_command(format_cmd)

    return {
        'collected_file': collected_file,
        'p2p_csv': p2p_csv,
        'udp_csv': udp_csv,
        'summary_json': summary_json
    }


def generate_visualizations(result_files, config):
    """Generate visualizations and report from test results"""
    print("\nGenerating visualization charts...")
    visualization_dir = os.path.join(PROJECT_ROOT, "visualization")

    # Current timestamp for log directory
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    vis_log_dir = f"vis_log_{timestamp}"

    # Ensure we have the latest results file references
    data_dir = os.path.join(PROJECT_ROOT, "data")

    # Find latest summary file if not explicitly provided
    if not result_files.get('summary_json'):
        summary_files = [f for f in os.listdir(data_dir) if f.startswith(
            'results_summary_') and f.endswith('.json')]
        if summary_files:
            latest_summary = sorted(summary_files)[-1]
            result_files['summary_json'] = os.path.join(
                data_dir, latest_summary)
            print(f"Using latest summary file: {result_files['summary_json']}")

    # Find latest results CSV files if not explicitly provided
    if not result_files.get('p2p_csv'):
        p2p_files = [f for f in os.listdir(data_dir) if f.startswith(
            'p2p_results_') and f.endswith('.csv')]
        if p2p_files:
            latest_p2p = sorted(p2p_files)[-1]
            result_files['p2p_csv'] = os.path.join(data_dir, latest_p2p)
            print(f"Using latest p2p results file: {result_files['p2p_csv']}")

    if not result_files.get('udp_csv'):
        udp_files = [f for f in os.listdir(data_dir) if f.startswith(
            'udp_results_') and f.endswith('.csv')]
        if udp_files:
            latest_udp = sorted(udp_files)[-1]
            result_files['udp_csv'] = os.path.join(data_dir, latest_udp)
            print(f"Using latest UDP results file: {result_files['udp_csv']}")

    if not result_files.get('latency_csv'):
        latency_files = [f for f in os.listdir(data_dir) if f.startswith(
            'latency_results_') and f.endswith('.csv')]
        if latency_files:
            latest_latency = sorted(latency_files)[-1]
            result_files['latency_csv'] = os.path.join(
                data_dir, latest_latency)
            print(
                f"Using latest latency results file: {result_files['latency_csv']}")

    # Find latest matrix files
    p2p_matrix_files = [f for f in os.listdir(data_dir) if f.startswith(
        'p2p_bandwidth_matrix_') and f.endswith('.csv')]
    p2p_matrix = None
    if p2p_matrix_files:
        p2p_matrix = os.path.join(data_dir, sorted(p2p_matrix_files)[-1])
        print(f"Using point-to-point bandwidth matrix: {p2p_matrix}")

    udp_bw_matrix_files = [f for f in os.listdir(data_dir) if f.startswith(
        'udp_bandwidth_matrix_') and f.endswith('.csv')]
    udp_bw_matrix = None
    if udp_bw_matrix_files:
        udp_bw_matrix = os.path.join(data_dir, sorted(udp_bw_matrix_files)[-1])
        print(f"Using UDP bandwidth matrix: {udp_bw_matrix}")

    udp_loss_matrix_files = [f for f in os.listdir(
        data_dir) if f.startswith('udp_loss_matrix_') and f.endswith('.csv')]
    udp_loss_matrix = None
    if udp_loss_matrix_files:
        udp_loss_matrix = os.path.join(
            data_dir, sorted(udp_loss_matrix_files)[-1])
        print(f"Using UDP loss matrix: {udp_loss_matrix}")

    latency_matrix_files = [f for f in os.listdir(
        data_dir) if f.startswith('latency_matrix_') and f.endswith('.csv')]
    latency_matrix = None
    if latency_matrix_files:
        latency_matrix = os.path.join(
            data_dir, sorted(latency_matrix_files)[-1])
        print(f"Using latency matrix: {latency_matrix}")

    # Generate histograms and heatmaps
    hist_cmd = f"python3 {visualization_dir}/generate_histograms.py"

    if result_files.get('p2p_csv'):
        hist_cmd += f" --p2p-csv {result_files['p2p_csv']}"

    if result_files.get('udp_csv'):
        hist_cmd += f" --udp-csv {result_files['udp_csv']}"

    if result_files.get('latency_csv'):
        hist_cmd += f" --latency-csv {result_files['latency_csv']}"

    if p2p_matrix:
        hist_cmd += f" --p2p-matrix {p2p_matrix}"

    if udp_bw_matrix:
        hist_cmd += f" --udp-bandwidth-matrix {udp_bw_matrix}"

    if udp_loss_matrix:
        hist_cmd += f" --udp-loss-matrix {udp_loss_matrix}"

    if latency_matrix:
        hist_cmd += f" --latency-matrix {latency_matrix}"

    # Add generate interval analysis parameter
    hist_cmd += " --generate-intervals"

    # Add log subdirectory parameter
    hist_cmd += f" --log-subdir {vis_log_dir}"

    hist_cmd += f" --output-dir {os.path.join(PROJECT_ROOT, 'visualization')}"

    print(f"Executing visualization command: {hist_cmd}")
    output = run_command(hist_cmd)

    # Extract generated image files
    image_files = []
    if output:
        for line in output.splitlines():
            if line.startswith("- ") and (".png" in line or ".jpg" in line):
                image_file = line[2:].strip()
                if os.path.exists(image_file):
                    image_files.append(image_file)
                    print(f"Found visualization file: {image_file}")
                else:
                    print(
                        f"Warning: Generated image file not found: {image_file}")

    # If no image files were found via output parsing, try to find them directly
    if not image_files:
        print("Searching for visualization files in log directory...")
        vis_files = glob.glob(os.path.join(
            visualization_dir, vis_log_dir, '*.png'))
        # Sort by timestamp to get the latest ones
        vis_files.sort(key=lambda f: os.path.getmtime(f), reverse=True)
        for file in vis_files:
            image_files.append(file)
            print(f"Found visualization file: {file}")

    # Generate HTML report
    print("\nGenerating test report...")
    if result_files.get('summary_json') and os.path.exists(result_files['summary_json']):
        report_cmd = (
            f"python3 {visualization_dir}/generate_report.py "
            f"--summary-json {result_files['summary_json']}"
        )

        if result_files.get('p2p_csv') and os.path.exists(result_files['p2p_csv']):
            report_cmd += f" --p2p-csv {result_files['p2p_csv']}"

        if result_files.get('udp_csv') and os.path.exists(result_files['udp_csv']):
            report_cmd += f" --udp-csv {result_files['udp_csv']}"

        if result_files.get('latency_csv') and os.path.exists(result_files['latency_csv']):
            report_cmd += f" --latency-csv {result_files['latency_csv']}"

        if image_files:
            report_cmd += f" --images {' '.join(image_files)}"

        # Add log subdirectory parameter
        report_cmd += f" --log-subdir {vis_log_dir}"

        report_cmd += f" --output-dir {os.path.join(PROJECT_ROOT, 'visualization')}"

        print(f"Executing report command: {report_cmd}")
        output = run_command(report_cmd)

        # Extract report file path
        report_file = None
        if output:
            for line in output.splitlines():
                if "Report generation completed:" in line:
                    report_file = line.split(
                        "Report generation completed:")[-1].strip()
                    break
                elif "HTML report generated:" in line:
                    report_file = line.split(
                        "HTML report generated:")[-1].strip()
                    break

        if report_file and os.path.exists(report_file):
            # Create a link to the report in the project root for easy access
            root_report = os.path.join(
                PROJECT_ROOT, f"network_benchmark_report_latest.html")
            try:
                # If it's a symlink, remove it first
                if os.path.islink(root_report):
                    os.unlink(root_report)
                # Create a symbolic link
                os.symlink(report_file, root_report)
                print(f"Created link to report at: {root_report}")
            except Exception as e:
                # If symlink fails, just copy the file
                shutil.copy2(report_file, root_report)
                print(f"Report copied to: {root_report}")

            return report_file
        else:
            print(
                f"Warning: Could not find generated report file in output: {output}")
    else:
        if not result_files.get('summary_json'):
            print("Warning: No summary JSON file found for report generation")
        else:
            print(
                f"Warning: Summary file does not exist: {result_files['summary_json']}")

    print("Warning: Unable to generate complete report")
    return None


def cleanup_resources(config):
    """Clean up AWS resources"""
    if not config.get('cleanup_resources', False):
        print("\nSkipping resource cleanup (not enabled)")
        return

    terraform_dir = os.path.join(PROJECT_ROOT, "terraform")

    print("\nCleaning up AWS resources...")
    run_command("terraform destroy -auto-approve", cwd=terraform_dir)
    print("AWS resources cleaned up")


def main():
    parser = argparse.ArgumentParser(
        description="AWS Network Benchmark Automation Script")
    parser.add_argument("--config", default="../config.json",
                        help="Configuration file path")
    parser.add_argument("--skip-terraform", action="store_true",
                        help="Skip Terraform deployment step")
    parser.add_argument("--skip-install", action="store_true",
                        help="Skip iperf3 installation step")
    parser.add_argument("--skip-tests", action="store_true",
                        help="Skip network tests step")
    parser.add_argument("--cleanup", action="store_true",
                        help="Clean up AWS resources after testing")

    args = parser.parse_args()

    # Load configuration
    config_path = args.config
    if not os.path.isabs(config_path):
        config_path = os.path.join(PROJECT_ROOT, config_path)

    config = {}
    if os.path.exists(config_path):
        with open(config_path, 'r') as f:
            config = json.load(f)

    # Command line arguments override config file
    if args.cleanup:
        config['cleanup_resources'] = True

    # Create timestamp directory for this test run
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = os.path.join(PROJECT_ROOT, f"runs/{timestamp}")
    os.makedirs(run_dir, exist_ok=True)

    print(
        f"AWS Network Benchmark starting, results will be saved to: {run_dir}")

    # Deploy EC2 instances
    if not args.skip_terraform:
        if not setup_terraform(config):
            print("Terraform configuration failed, exiting")
            return 1
    else:
        print("Skipping Terraform deployment step")

    # Install iperf3
    if not args.skip_install:
        if not install_iperf3(config):
            print("iperf3 installation failed, exiting")
            return 1
    else:
        print("Skipping iperf3 installation step")

    # Run network tests
    if not args.skip_tests:
        if not run_network_tests(config):
            print("Network tests failed, exiting")
            return 1
    else:
        print("Skipping network tests step")

    # Process test results
    result_files = process_test_results(config)
    if not result_files:
        print("Processing test results failed, exiting")
        return 1

    # Generate visualizations and report
    report_file = generate_visualizations(result_files, config)

    # Copy important results to run directory
    for key, file_path in result_files.items():
        if file_path and os.path.exists(file_path):
            dest_path = os.path.join(run_dir, os.path.basename(file_path))
            shutil.copy2(file_path, dest_path)

    if report_file and os.path.exists(report_file):
        dest_report = os.path.join(run_dir, os.path.basename(report_file))
        shutil.copy2(report_file, dest_report)

    # Clean up resources
    cleanup_resources(config)

    print(f"\nAWS Network Benchmark completed, results saved to: {run_dir}")
    if report_file:
        print(f"Test report: {report_file}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
