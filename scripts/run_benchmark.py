#!/usr/bin/env python3
# run_benchmark.py

import json
import subprocess
import os
import sys
import time
from datetime import datetime

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
        config.setdefault("instance_count", 1) # Default instances per region if not specified
        config.setdefault("region_instance_counts", {}) # Specific counts per region
        config.setdefault("use_private_ip", False)
        config.setdefault("test_intra_region", False) # Default for latency/p2p intra-region

        config.setdefault("run_p2p_tests", False)
        config.setdefault("p2p_duration", 10)
        config.setdefault("p2p_parallel", 1)

        config.setdefault("run_udp_tests", False)
        config.setdefault("udp_server_region", None) # Must be specified if run_udp_tests is true
        config.setdefault("udp_bandwidth", "1G")
        config.setdefault("udp_duration", 10)

        config.setdefault("cleanup_resources", True)
        # --- Validation ---
        if not config.get("aws_regions"):
            print("Error: 'aws_regions' must be specified in the config file.")
            sys.exit(1)
        if config["run_udp_tests"] and not config.get("udp_server_region"):
             print("Error: 'udp_server_region' must be specified in the config file when 'run_udp_tests' is true.")
             sys.exit(1)
        if config["run_udp_tests"] and config["udp_server_region"] not in config["aws_regions"]:
             print(f"Error: 'udp_server_region' ({config['udp_server_region']}) must be one of the regions listed in 'aws_regions'.")
             sys.exit(1)

        return config
    except FileNotFoundError:
        print(f"Error: Configuration file '{config_file}' not found.")
        sys.exit(1)
    except json.JSONDecodeError:
        print(f"Error: Configuration file '{config_file}' contains invalid JSON.")
        sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred loading the config: {e}")
        sys.exit(1)

def run_command(command, cwd=None, check=True):
    """Helper function to run shell commands."""
    print(f"Executing: {' '.join(command)}")
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=check, cwd=cwd)
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
        print(f"SSH key '{key_name}' not found. Creating new key pair in {key_dir}...")
        os.makedirs(key_dir, exist_ok=True)
        # Create key without passphrase
        command = ["ssh-keygen", "-t", "rsa", "-b", "2048", "-f", private_key_path, "-N", ""]
        if run_command(command):
            print(f"Successfully created SSH key pair: {private_key_path}, {public_key_path}")
            # Set appropriate permissions for the private key
            os.chmod(private_key_path, 0o600)
        else:
            print(f"Error: Failed to create SSH key pair.")
            sys.exit(1)
    else:
        print(f"Using existing SSH key: {private_key_path}")
    return private_key_path # Return the path to the private key

def main():
    start_time = datetime.now()
    print(f"Benchmark started at: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")

    config_file = "../config.json" # Relative to the script's location
    instance_info_file = "../instance_info.json" # Relative path for instance info
    terraform_dir = "../terraform"
    data_dir = "../data"
    results_dir = "../results"

    # Ensure data and results directories exist
    os.makedirs(data_dir, exist_ok=True)
    os.makedirs(results_dir, exist_ok=True)

    # --- 0. Load Configuration ---
    print("\n--- Step 0: Loading Configuration ---")
    config = load_config(config_file) # Keep loading config here
    print("Configuration loaded successfully.")
    # print(json.dumps(config, indent=2)) # Optional: Print loaded config

    # --- 1. Create SSH Key (if needed) ---
    print("\n--- Step 1: Checking/Creating SSH Key ---")
    ssh_key_path = os.path.join(terraform_dir, config['ssh_key_name'])
    if config['create_ssh_key']:
        create_ssh_key(config['ssh_key_name'], terraform_dir)
    elif not os.path.exists(ssh_key_path):
         print(f"Error: SSH key '{ssh_key_path}' not found and 'create_ssh_key' is false.")
         print("Please create the key manually or set 'create_ssh_key' to true in the config.")
         sys.exit(1)
    else:
        print(f"Using existing SSH key: {ssh_key_path}")


    # --- 2. Generate Terraform Configuration ---
    print("\n--- Step 2: Generating Terraform Configuration ---")
    # Pass the config file path (string) and terraform directory path (string)
    if generate_terraform(config_file, terraform_dir) != 0:
         print("Error: Failed to generate Terraform configuration.")
         sys.exit(1)
    # The specific tfvars file isn't generated by generate_terraform, adjust log message if needed
    print(f"Terraform configuration files generated in: {terraform_dir}")


    # --- 3. Apply Terraform Configuration ---
    print("\n--- Step 3: Applying Terraform Configuration (terraform init & apply) ---")
    if not run_command(["terraform", "init"], cwd=terraform_dir):
        print("Error: terraform init failed.")
        sys.exit(1)
    if not run_command(["terraform", "apply", "-auto-approve"], cwd=terraform_dir):
        print("Error: terraform apply failed.")
        # Optional: Attempt cleanup even if apply fails?
        if config['cleanup_resources']:
             print("\nAttempting Terraform destroy despite apply failure...")
             run_command(["terraform", "destroy", "-auto-approve"], cwd=terraform_dir, check=False)
        sys.exit(1)
    print("Terraform apply completed successfully.")


    # --- 4. Generate Instance Information ---
    print("\n--- Step 4: Generating Instance Information ---")
    if generate_instance_info(terraform_dir, instance_info_file) != 0:
        print("Error: Failed to generate instance information.")
        if config['cleanup_resources']:
             print("\nAttempting Terraform destroy due to instance info failure...")
             run_command(["terraform", "destroy", "-auto-approve"], cwd=terraform_dir, check=False)
        sys.exit(1)
    print(f"Instance information saved to: {instance_info_file}")

    # Give instances a bit more time to fully initialize SSH
    print("Waiting 60 seconds for instances to fully initialize SSH...")
    time.sleep(60)


    # --- 5. Run Benchmark Tests ---
    print("\n--- Step 5: Running Benchmark Tests ---")
    test_threads = []
    test_results = {"latency": None, "p2p": None, "udp": None}
    errors_occurred = False

    # 5a. Latency Test (Always Run)
    print("\n--- Running Latency Test ---")
    latency_output_dir = os.path.join(data_dir, "latency")
    try:
        if run_latency_benchmark(instance_info_file, ssh_key_path, latency_output_dir, config['use_private_ip'], config['test_intra_region']) == 0:
            print("Latency test completed successfully.")
            test_results["latency"] = True
        else:
            print("Error: Latency test failed.")
            errors_occurred = True
            test_results["latency"] = False
    except Exception as e:
        print(f"An unexpected error occurred during latency test: {e}")
        errors_occurred = True
        test_results["latency"] = False


    # 5b. Point-to-Point Test (Conditional)
    if config['run_p2p_tests']:
        print("\n--- Running Point-to-Point Test ---")
        p2p_output_dir = os.path.join(data_dir, "p2p")
        try:
            if point_to_point_test(instance_info_file, ssh_key_path, p2p_output_dir, config['use_private_ip'], config['p2p_duration'], config['p2p_parallel'], config['test_intra_region']) == 0:
                print("Point-to-Point test completed successfully.")
                test_results["p2p"] = True
            else:
                print("Error: Point-to-Point test failed.")
                errors_occurred = True
                test_results["p2p"] = False
        except Exception as e:
            print(f"An unexpected error occurred during P2P test: {e}")
            errors_occurred = True
            test_results["p2p"] = False
    else:
        print("\nSkipping Point-to-Point Test (run_p2p_tests is false).")


    # 5c. UDP Multicast Test (Conditional)
    if config['run_udp_tests']:
        print("\n--- Running UDP Multicast Test ---")
        udp_output_dir = os.path.join(data_dir, "udp")
        try:
            if run_udp_test(instance_info_file, ssh_key_path, udp_output_dir, config['use_private_ip'], config['udp_server_region'], config['udp_bandwidth'], config['udp_duration'], config['test_intra_region']) == 0:
                 print("UDP Multicast test completed successfully.")
                 test_results["udp"] = True
            else:
                 print("Error: UDP Multicast test failed.")
                 errors_occurred = True
                 test_results["udp"] = False
        except Exception as e:
            print(f"An unexpected error occurred during UDP test: {e}")
            errors_occurred = True
            test_results["udp"] = False
    else:
        print("\nSkipping UDP Multicast Test (run_udp_tests is false).")

    if errors_occurred:
        print("\nWarning: One or more tests failed. Results might be incomplete.")

    # --- 6. Collect and Process Results ---
    print("\n--- Step 6: Collecting and Processing Results ---")

    # 6a. Collect Results
    collected_files_log = os.path.join(results_dir, "collected_files.log")
    print(f"\nCollecting results from {data_dir} to {results_dir}...")
    try:
        if collect_results(data_dir, results_dir, collected_files_log) == 0:
            print("Results collected successfully.")
        else:
            print("Warning: Result collection may have encountered issues.")
            # Decide if this is critical enough to stop
    except Exception as e:
        print(f"An unexpected error occurred during result collection: {e}")
        # Decide if this is critical enough to stop

    # 6b. Parse Data
    parsed_output_file = os.path.join(results_dir, "parsed_results.json")
    print(f"\nParsing collected data from {results_dir}...")
    try:
        if parse_data(results_dir, parsed_output_file) == 0:
             print(f"Parsed data saved to {parsed_output_file}")
        else:
             print("Error: Failed to parse data.")
             # Decide if this is critical enough to stop
    except Exception as e:
        print(f"An unexpected error occurred during data parsing: {e}")
        # Decide if this is critical enough to stop


    # 6c. Format Data
    formatted_output_file = os.path.join(results_dir, "formatted_results.md")
    print(f"\nFormatting parsed data from {parsed_output_file}...")
    try:
        if format_data(parsed_output_file, formatted_output_file) == 0:
            print(f"Formatted results saved to {formatted_output_file}")
        else:
            print("Error: Failed to format data.")
            # Decide if this is critical enough to stop
    except Exception as e:
        print(f"An unexpected error occurred during data formatting: {e}")
        # Decide if this is critical enough to stop


    # --- 7. Cleanup Resources (Conditional) ---
    if config['cleanup_resources']:
        print("\n--- Step 7: Cleaning Up Resources (terraform destroy) ---")
        if not run_command(["terraform", "destroy", "-auto-approve"], cwd=terraform_dir):
            print("Warning: terraform destroy failed. Resources may need manual cleanup.")
        else:
            print("Terraform destroy completed successfully.")
            # Optionally remove terraform state files etc.
            # run_command(["rm", "-f", "terraform.tfstate*", "terraform.tfvars.json", ".terraform.lock.hcl"], cwd=terraform_dir, check=False)
            # run_command(["rm", "-rf", ".terraform"], cwd=terraform_dir, check=False)
    else:
        print("\n--- Skipping Resource Cleanup (cleanup_resources is false) ---")


    # --- Completion ---
    end_time = datetime.now()
    print(f"\nBenchmark finished at: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Total execution time: {end_time - start_time}")

    if errors_occurred:
        print("\nBenchmark completed with errors in one or more tests.")
        sys.exit(1) # Exit with error code if tests failed
    else:
        print("\nBenchmark completed successfully.")
        sys.exit(0)


if __name__ == "__main__":
    # Ensure the script is run from the 'scripts' directory for relative paths to work correctly
    script_dir = os.path.dirname(os.path.abspath(__file__))
    if os.getcwd() != script_dir:
        print(f"Changing working directory to: {script_dir}")
        os.chdir(script_dir)

    main()
