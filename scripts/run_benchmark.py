#!/usr/bin/env python3
# run_benchmark.py

import json
import subprocess
import os
import sys
import time
from datetime import datetime
import traceback  # Add traceback import

# Import functions from other scripts
from scripts.generate_terraform import generate_terraform
from scripts.generate_instance_info import generate_instance_info
from scripts.latency_test import run_latency_benchmark
from scripts.point_to_point_test import point_to_point_test
from scripts.udp_multicast_test import run_udp_test
from scripts.collect_results import collect_results
from scripts.format_data import format_data
from scripts.parse_data import parse_data


def load_config(config_file):
    """Load the configuration from a JSON file."""
    try:
        with open(config_file, 'r') as f:
            config = json.load(f)
        # --- Default values ---
        config.setdefault("instance_type", "t2.micro")
        config.setdefault("ssh_key_name", "aws-network-benchmark")
        config.setdefault("create_ssh_key", False)
        # Default instances per region if not specified
        config.setdefault("instance_count", 1)
        # Specific counts per region
        config.setdefault("region_instance_counts", {})
        config.setdefault("use_private_ip", False)
        # Default for latency/p2p intra-region
        config.setdefault("test_intra_region", False)

        config.setdefault("run_p2p_tests", False)
        config.setdefault("p2p_duration", 10)
        config.setdefault("p2p_parallel", 1)

        config.setdefault("run_udp_tests", False)
        # Must be specified if run_udp_tests is true
        config.setdefault("udp_server_region", None)
        config.setdefault("udp_bandwidth", "1G")
        config.setdefault("udp_duration", 10)

        config.setdefault("cleanup_resources", True)
        # --- Validation ---
        if not config.get("aws_regions"):
            print("Error: 'aws_regions' must be specified in the config file.")
            sys.exit(1)
        if config["run_udp_tests"] and not config.get("udp_server_region"):
            print(
                "Error: 'udp_server_region' must be specified in the config file when 'run_udp_tests' is true.")
            sys.exit(1)
        if config["run_udp_tests"] and config["udp_server_region"] not in config["aws_regions"]:
            print(
                f"Error: 'udp_server_region' ({config['udp_server_region']}) must be one of the regions listed in 'aws_regions'.")
            sys.exit(1)

        return config
    except FileNotFoundError:
        print(f"Error: Configuration file '{config_file}' not found.")
        sys.exit(1)
    except json.JSONDecodeError:
        print(
            f"Error: Configuration file '{config_file}' contains invalid JSON.")
        sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred loading the config: {e}")
        sys.exit(1)


def run_command(command, cwd=None, check=True):
    """Helper function to run shell commands."""
    print(f"Executing: {' '.join(command)}")
    try:
        result = subprocess.run(
            command, capture_output=True, text=True, check=check, cwd=cwd)
        print(result.stdout)
        if result.stderr:
            print("Stderr:", result.stderr)
        return result.returncode == 0
    except subprocess.CalledProcessError as e:
        print(f"Error executing command: {' '.join(command)}")
        print(f"Return code: {e.returncode}")
        print(f"Output: {e.output}")
        print(f"Stderr: {e.stderr}")
        return False
    except FileNotFoundError:
        print(f"Error: Command not found: {command[0]}")
        return False


def create_ssh_key(key_name, key_dir="../terraform"):
    """Creates an SSH key pair if it doesn't exist."""
    private_key_path = os.path.join(key_dir, key_name)
    public_key_path = f"{private_key_path}.pub"

    if not os.path.exists(private_key_path):
        print(
            f"SSH key '{key_name}' not found. Creating new key pair in {key_dir}...")
        os.makedirs(key_dir, exist_ok=True)
        # Create key without passphrase
        command = ["ssh-keygen", "-t", "rsa", "-b",
                   "2048", "-f", private_key_path, "-N", ""]
        if run_command(command):
            print(
                f"Successfully created SSH key pair: {private_key_path}, {public_key_path}")
            # Set appropriate permissions for the private key
            os.chmod(private_key_path, 0o600)
        else:
            print(f"Error: Failed to create SSH key pair.")
            sys.exit(1)
    else:
        print(f"Using existing SSH key: {private_key_path}")
    return private_key_path  # Return the path to the private key


def main():
    start_time = datetime.now()
    print(f"Benchmark started at: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    errors_occurred = False  # Initialize error tracking flag

    config_file = "../config.json"  # Relative to the script's location
    terraform_dir = "../terraform"
    data_dir = "../data"
    results_dir = "../results"
    script_dir = os.path.dirname(os.path.abspath(__file__))  # Define script_dir earlier
    instance_info_file = os.path.abspath(os.path.join(
        script_dir, "..", "data", "instance_info.json"))

    # Ensure data and results directories exist
    os.makedirs(data_dir, exist_ok=True)
    os.makedirs(results_dir, exist_ok=True)

    # --- 0. Load Configuration ---
    print("\n--- Step 0: Loading Configuration ---")
    config = load_config(config_file)  # Keep loading config here
    print("Configuration loaded successfully.")

    # --- 1. Create SSH Key (if needed) ---
    print("\n--- Step 1: Checking/Creating SSH Key ---")
    ssh_key_path = os.path.join(terraform_dir, config['ssh_key_name'])  
    if config['create_ssh_key']:
        create_ssh_key(config['ssh_key_name'], terraform_dir)
    elif not os.path.exists(ssh_key_path):
        print(
            f"Error: SSH key '{ssh_key_path}' not found and 'create_ssh_key' is false.")
        print(
            "Please create the key manually or set 'create_ssh_key' to true in the config.")
        sys.exit(1)
    else:
        print(f"Using existing SSH key: {ssh_key_path}")

    # --- 2. Generate Terraform Configuration ---
    print("\n--- Step 2: Generating Terraform Configuration ---")
    if generate_terraform(config_file, terraform_dir) != 0:
        print("Error: Failed to generate Terraform configuration.")
        sys.exit(1)
    print(f"Terraform configuration files generated in: {terraform_dir}")

    # --- 3. Apply Terraform Configuration ---
    print("\n--- Step 3: Applying Terraform Configuration (terraform init & apply) ---")
    if not run_command(["terraform", "init"], cwd=terraform_dir):
        print("Error: terraform init failed.")
        sys.exit(1)
    if not run_command(["terraform", "apply", "-auto-approve"], cwd=terraform_dir):
        print("Error: terraform apply failed.")
        if config['cleanup_resources']:
            print("\nAttempting Terraform destroy despite apply failure...")
            run_command(["terraform", "destroy", "-auto-approve"],
                        cwd=terraform_dir, check=False)
        sys.exit(1)
    print("Terraform apply completed successfully.")

    # --- 4. Generate Instance Information ---
    print("\n--- Step 4: Generating Instance Information ---")
    terraform_output_json_path = os.path.join(
        terraform_dir, "terraform_output.json")

    print(f"Generating Terraform output JSON to: {terraform_output_json_path}")
    tf_output_cmd = ["terraform", "output", "-json"]
    try:
        result = subprocess.run(
            tf_output_cmd, capture_output=True, text=True, check=True, cwd=terraform_dir)
        with open(terraform_output_json_path, 'w') as f_out:
            f_out.write(result.stdout)
        print("Terraform output saved successfully.")
    except subprocess.CalledProcessError as e:
        print(f"Error executing command: {' '.join(tf_output_cmd)}")
        print(f"Return code: {e.returncode}")
        print(f"Stderr: {e.stderr}")
        if config['cleanup_resources']:
            print("\nAttempting Terraform destroy due to output failure...")
            run_command(["terraform", "destroy", "-auto-approve"],
                        cwd=terraform_dir, check=False)
        sys.exit(1)
    except Exception as e:
        print(
            f"Error writing Terraform output to {terraform_output_json_path}: {e}")
        if config['cleanup_resources']:
            print("\nAttempting Terraform destroy due to output failure...")
            run_command(["terraform", "destroy", "-auto-approve"],
                        cwd=terraform_dir, check=False)
        sys.exit(1)

    if generate_instance_info(terraform_output_json_path, instance_info_file) != 0:
        print("Error: Failed to generate instance information.")
        if config['cleanup_resources']:
            print("\nAttempting Terraform destroy due to instance info failure...")
            run_command(["terraform", "destroy", "-auto-approve"],
                        cwd=terraform_dir, check=False)
        sys.exit(1)
    print(f"Instance information saved to: {instance_info_file}")

    print("Waiting 5 seconds for instances to fully initialize SSH...")
    time.sleep(5)

    # --- 5. Run Benchmark Tests ---
    print("\n--- Step 5: Running Benchmark Tests ---")
    test_results = {}

    # Latency Test
    if config.get('run_latency_tests', True):
        print("\n--- Running Latency Test ---")
        try:
            latency_summary = run_latency_benchmark(
                instance_info_file, ssh_key_path, config.get(
                    'ping_count', 20), data_dir,
                all_regions=True,
                use_private_ip=config['use_private_ip'],
                intra_region=config['test_intra_region']
            )
            test_results['latency'] = latency_summary
            print(f"Latency test summary: {latency_summary}")
        except Exception as e:
            print(f"An unexpected error occurred during latency test: {e}")
            traceback.print_exc()
            errors_occurred = True

    # Point-to-Point Test (iperf3)
    if config['run_p2p_tests']:
        print("\n--- Running Point-to-Point Test ---")
        try:
            p2p_summary = point_to_point_test(
                instance_info_file, ssh_key_path, config['p2p_duration'],
                config['p2p_parallel'], data_dir,
                all_regions=True,
                use_private_ip=config['use_private_ip'],
                intra_region=config['test_intra_region']
            )
            test_results['p2p'] = p2p_summary
            print(f"P2P test summary: {p2p_summary}")
        except Exception as e:
            print(f"An unexpected error occurred during P2P test: {e}")
            traceback.print_exc()
            errors_occurred = True

    # UDP Multicast Test (iperf3)
    if config['run_udp_tests']:
        print("\n--- Running UDP Multicast Test ---")
        try:
            udp_summary = run_udp_test(
                instance_info_file,
                ssh_key_path,
                data_dir,
                config['use_private_ip'],
                config['udp_server_region'],
                config['udp_bandwidth'],
                config['udp_duration']
            )
            test_results['udp'] = udp_summary
            print(f"UDP test summary: {udp_summary}")
        except Exception as e:
            print(f"An unexpected error occurred during UDP test: {e}")
            traceback.print_exc()
            errors_occurred = True

    if not test_results and (config.get('run_latency_tests', True) or config['run_p2p_tests'] or config['run_udp_tests']):
        print("\nWarning: No tests were run or all tests failed.")
    elif test_results:
        print("\nBenchmark tests completed.")

    # --- 6. Collect and Process Results ---
    print("\n--- Step 6: Collecting and Processing Results ---")
    parsed_results_file = os.path.join(results_dir, "parsed_results.json")
    formatted_results_file = os.path.join(results_dir, "formatted_results.md")

    print(f"\nCollecting results from {data_dir} to {results_dir}...")
    try:
        collect_results(data_dir, results_dir)
        print(f"Results collected in {results_dir}")
    except Exception as e:
        print(f"An unexpected error occurred during result collection: {e}")
        traceback.print_exc()
        errors_occurred = True

    # --- 7. Cleanup ---
    if config['cleanup_resources']:
        print("\n--- Step 7: Cleaning Up Resources (terraform destroy) ---")
        if not run_command(["terraform", "destroy", "-auto-approve"], cwd=terraform_dir):
            print("Warning: terraform destroy failed. Resources may need manual cleanup.")
        else:
            print("Terraform destroy completed successfully.")
    else:
        print("\n--- Skipping Resource Cleanup (cleanup_resources is false) ---")

    # --- Completion ---
    end_time = datetime.now()
    print(f"\nBenchmark finished at: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Total execution time: {end_time - start_time}")

    if errors_occurred:
        print("\nBenchmark completed with errors.")
        sys.exit(1)
    else:
        print("\nBenchmark completed successfully.")
        sys.exit(0)


if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__))
    if os.getcwd() != script_dir:
        print(f"Changing working directory to: {script_dir}")
        os.chdir(script_dir)

    main()
