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
        config.setdefault("ssh_user", "ec2-user")

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


def import_ssh_key_to_aws(key_name, public_key_path, regions):
    for region in regions:
        # best-effort delete any old key (ignore failures)
        run_command([
            "aws", "ec2", "delete-key-pair",
            "--region", region,
            "--key-name", key_name
        ], check=False)

        # import the .pub file directly
        run_command([
            "aws", "ec2", "import-key-pair",
            "--region", region,
            "--key-name", key_name,
            "--public-key-material", f"fileb://{public_key_path}"
        ])


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
    script_dir = os.path.dirname(os.path.abspath(__file__))
    instance_info_file = os.path.abspath(os.path.join(
        script_dir, "..", "data", "instance_info.json"))
    # Ensure terraform_dir is absolute or relative to script_dir if needed
    abs_terraform_dir = os.path.abspath(
        os.path.join(script_dir, terraform_dir))
    abs_data_dir = os.path.abspath(os.path.join(script_dir, data_dir))
    abs_results_dir = os.path.abspath(os.path.join(script_dir, results_dir))

    # Ensure data and results directories exist
    os.makedirs(abs_data_dir, exist_ok=True)
    os.makedirs(abs_results_dir, exist_ok=True)

    # --- 0. Load Configuration ---
    print("\n--- Step 0: Loading Configuration ---")
    # Assuming config_file = "../config.json" is relative to script_dir
    abs_config_file = os.path.abspath(os.path.join(script_dir, config_file))
    config = load_config(abs_config_file)
    print("Configuration loaded successfully.")

    # --- 1. Create SSH Key (if needed) ---
    print("\n--- Step 1: Checking/Creating SSH Key ---")
    # Use absolute path for ssh key
    ssh_key_path = os.path.join(abs_terraform_dir, config['ssh_key_name'])
    if config['create_ssh_key']:
        create_ssh_key(config['ssh_key_name'], abs_terraform_dir)
        pub_key_path = ssh_key_path + ".pub"
        import_ssh_key_to_aws(
            key_name=config["ssh_key_name"],
            public_key_path=pub_key_path,
            regions=config["aws_regions"]
        )
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
    if generate_terraform(abs_config_file, abs_terraform_dir) != 0:
        print("Error: Failed to generate Terraform configuration.")
        sys.exit(1)
    print(f"Terraform configuration files generated in: {abs_terraform_dir}")

    # --- 3. Apply Terraform Configuration ---
    print("\n--- Step 3: Applying Terraform Configuration (terraform init & apply) ---")
    if not run_command(["terraform", "init"], cwd=abs_terraform_dir):
        print("Error: terraform init failed.")
        sys.exit(1)
    if not run_command(["terraform", "apply", "-auto-approve"], cwd=abs_terraform_dir):
        print("Error: terraform apply failed.")
        if config['cleanup_resources']:
            print("Attempting to clean up resources...")
            run_command(["terraform", "destroy", "-auto-approve"],
                        cwd=abs_terraform_dir, check=False)
        sys.exit(1)
    print("Terraform apply completed successfully.")

    # --- 4. Generate Instance Info ---
    print("\n--- Step 4: Generating Instance Information ---")
    terraform_output_file = os.path.join(
        abs_terraform_dir, "terraform_output.json")
    if not run_command(["terraform", "output", "-json"], cwd=abs_terraform_dir):
        print("Error: terraform output failed.")
        # Attempt cleanup if apply succeeded but output failed
        if config['cleanup_resources']:
            print("Attempting to clean up resources...")
            run_command(["terraform", "destroy", "-auto-approve"],
                        cwd=abs_terraform_dir, check=False)
        sys.exit(1)
    # Capture the output to a file
    try:
        tf_output_result = subprocess.run(
            ["terraform", "output", "-json"], cwd=abs_terraform_dir, capture_output=True, text=True, check=True)
        with open(terraform_output_file, 'w') as f_out:
            f_out.write(tf_output_result.stdout)
        print(f"Terraform output saved to {terraform_output_file}")
    except subprocess.CalledProcessError as e:
        print(f"Error capturing terraform output: {e}")
        if config['cleanup_resources']:
            print("Attempting to clean up resources...")
            run_command(["terraform", "destroy", "-auto-approve"],
                        cwd=abs_terraform_dir, check=False)
        sys.exit(1)

    if generate_instance_info(terraform_output_file, instance_info_file) != 0:
        print("Error: Failed to generate instance information.")
        # Attempt cleanup
        if config['cleanup_resources']:
            print("Attempting to clean up resources...")
            run_command(["terraform", "destroy", "-auto-approve"],
                        cwd=abs_terraform_dir, check=False)
        sys.exit(1)
    print(f"Instance information saved to: {instance_info_file}")
    print("Waiting 5 seconds for instances to fully initialize SSH...")
    time.sleep(5)

    # --- 5. Run Benchmark Tests ---
    print("\n--- Step 5: Running Benchmark Tests ---")
    latency_summary = None
    p2p_summary = None
    udp_summary = None
    ssh_user = config['ssh_user']  # Assuming ssh_user is defined in config

    try:
        # --- Latency Test ---
        print("\n--- Running Latency Test ---")
        try:
            latency_summary = run_latency_benchmark(
                instance_info_path=instance_info_file,
                ssh_key_path=ssh_key_path,  # Pass absolute path
                ping_count=20,  # Example value, consider making configurable
                output_dir=abs_data_dir,
                all_regions=True,  # Default to all regions for now
                use_private_ip=config['use_private_ip'],
                intra_region=config['test_intra_region']
            )
            if latency_summary:
                print(f"Latency test summary: {latency_summary}")
            else:
                print("Latency test failed or produced no summary.")
                errors_occurred = True
        except Exception as e:
            print(f"An unexpected error occurred during latency test: {e}")
            traceback.print_exc()  # Print detailed traceback
            errors_occurred = True

        # --- Point-to-Point Test ---
        if config.get('run_p2p_tests', False):
            print("\n--- Running Point-to-Point Test ---")
            try:
                p2p_summary = point_to_point_test(
                    instance_info_path=instance_info_file,
                    ssh_key_path=ssh_key_path,  # Pass absolute path
                    duration=config['p2p_duration'],
                    parallel=config['p2p_parallel'],
                    output_dir=abs_data_dir,
                    use_private_ip=config['use_private_ip'],
                    # Corrected argument name
                    test_intra_region=config['test_intra_region'],
                    all_regions=True  # Assuming test all regions for P2P
                )
                if p2p_summary:
                    print(f"P2P test summary: {p2p_summary}")
                else:
                    print("P2P test failed or produced no summary.")
                    errors_occurred = True
            except Exception as e:
                print(f"An unexpected error occurred during P2P test: {e}")
                traceback.print_exc()  # Print detailed traceback
                errors_occurred = True
        else:
            print("\n--- Skipping Point-to-Point Test (run_p2p_tests is false) ---")

        # --- UDP Multicast Test ---
        if config.get('run_udp_tests', False):
            print("\n--- Running UDP Multicast Test ---")
            try:
                udp_summary = run_udp_test(
                    instance_info_path=instance_info_file,
                    ssh_key_path=ssh_key_path,  # Pass absolute path
                    output_dir=abs_data_dir,
                    use_private_ip=config['use_private_ip'],
                    server_region=config['udp_server_region'],
                    bandwidth=config['udp_bandwidth'],
                    duration=config['udp_duration']
                    # Note: udp_multicast_test.py doesn't currently use intra_region/all_regions flags directly
                )
                if udp_summary:
                    # run_udp_test returns a list of results, not a summary path currently
                    print(
                        f"UDP test completed. Results details logged in {abs_data_dir}")
                    # Consider saving a summary file similar to latency/p2p if needed
                else:
                    print("UDP test failed or produced no results.")
                    errors_occurred = True
            except Exception as e:
                print(f"An unexpected error occurred during UDP test: {e}")
                traceback.print_exc()  # Print detailed traceback
                errors_occurred = True
        else:
            print("\n--- Skipping UDP Multicast Test (run_udp_tests is false) ---")

        print("\nBenchmark tests completed.")

    except Exception as e:
        print(f"\nAn critical error occurred during benchmark execution: {e}")
        traceback.print_exc()  # Print detailed traceback
        errors_occurred = True
    finally:
        # --- 6. Collect and Process Results ---
        # This step might need adjustment depending on what the test functions return
        print("\n--- Step 6: Collecting and Processing Results ---")
        try:
            # Assuming collect_results aggregates files from data_dir
            collected_data_path = collect_results(
                abs_data_dir, abs_data_dir)  # Save collected in data_dir
            if collected_data_path:
                print(f"Collected results saved to: {collected_data_path}")
                # Assuming parse_data takes the collected file and outputs parsed files
                # Output parsed data to data_dir
                parse_data(collected_data_path, abs_data_dir)
                # Assuming format_data takes parsed files (or the dir) and outputs report
                # Output report to results_dir
                format_data(abs_data_dir, abs_results_dir)
            else:
                print("No results collected.")
                errors_occurred = True
        except Exception as e:
            print(f"An error occurred during results processing: {e}")
            traceback.print_exc()  # Print detailed traceback
            errors_occurred = True

        # --- 7. Cleanup Terraform Resources ---
        if config['cleanup_resources']:
            print("\n--- Step 7: Cleaning Up Terraform Resources ---")
            if not run_command(["terraform", "destroy", "-auto-approve"], cwd=abs_terraform_dir, check=False):
                print(
                    "Warning: terraform destroy failed. Manual cleanup might be required.")
                errors_occurred = True  # Mark as error if cleanup fails
            else:
                print("Terraform resources destroyed successfully.")
        else:
            print("\n--- Skipping Terraform Cleanup (cleanup_resources is false) ---")

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
    main()
