#!/usr/bin/env python3
# udp_multicast_test.py
# 执行一对多UDP网络性能测试

import json
import argparse
import subprocess
import time
import os
import sys  # Ensure sys is imported
from datetime import datetime


# --- Add this function ---
def get_ips(instance_info, ip_key, regions):
    """Gets all IPs for a list of regions."""
    all_ips = []
    # Ensure we handle the structure correctly: instance_info['instances'][region][ip_key]
    # Also handle cases where a region might be missing or the ip_key list is empty
    for region in regions:
        region_data = instance_info.get('instances', {}).get(region, {})
        ips = region_data.get(ip_key, [])
        if isinstance(ips, list):
            all_ips.extend(ips)  # Use extend for lists
        elif isinstance(ips, str) and ips:  # Handle single IP string case
            all_ips.append(ips)
    # Filter out empty strings or None values just in case
    return [ip for ip in all_ips if ip]
# --- End of added function ---


def load_instance_info(json_file):
    """load the ec2 instance info"""
    try:
        with open(json_file, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"error: unable to load the instance info file {json_file}: {e}")
        sys.exit(1)


def run_udp_test(instance_info_path, ssh_key_path, ssh_user, output_dir, use_private_ip, server_region, bandwidth, duration):
    """Runs iperf3 UDP tests from clients to a central server."""
    try:
        with open(instance_info_path, 'r') as f:
            instance_info = json.load(f)
    except FileNotFoundError:
        print(f"Error: Instance info file not found at {instance_info_path}")
        return None  # Return None on failure
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from {instance_info_path}")
        return None  # Return None on failure

    ip_key = 'private_ips' if use_private_ip else 'public_ips'
    print(f"Using {ip_key} for UDP tests.")

    regions = list(instance_info.get('instances', {}).keys())
    results = []  # Store detailed results or paths
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    # Define a summary file path, though we might return the list for run_benchmark
    summary_output_file = os.path.join(
        output_dir, f"udp_summary_{timestamp}.json")

    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)

    # Validate server_region
    if server_region not in instance_info.get('instances', {}):
        print(
            f"Error: Specified server region '{server_region}' not found in instance info.")
        if regions:
            server_region = regions[0]
            print(f"Warning: Falling back to server region '{server_region}'.")
        else:
            print("Error: No regions available in instance info. Cannot run UDP test.")
            return None  # Return None on failure

    # Use the added get_ips function
    server_ips = get_ips(instance_info, ip_key, [server_region])
    if not server_ips:
        print(f"Error: No {ip_key} found for server region {server_region}.")
        return None  # Return None on failure
    server_ip = server_ips[0]  # Use the first IP in the server region

    # Collect client IPs from all *other* regions
    client_ips = []
    for region in regions:
        if region != server_region:
            region_client_ips = get_ips(instance_info, ip_key, [region])
            if region_client_ips:
                # Take first IP from each client region
                client_ips.append(region_client_ips[0])

    if not client_ips:
        print(
            f"Warning: No client IPs found in regions other than {server_region}.")
        # Decide if this is an error or just means no tests run
        # return None # Or just continue and return empty results

    # Start the iperf3 server on the server
    # Use ssh_key_path variable passed to the function
    server_cmd = f"ssh -i {ssh_key_path} -o StrictHostKeyChecking=no {ssh_user}@{server_ip} 'pkill iperf3; iperf3 -s -D'"
    print(f"Attempting to start iperf3 server on {server_ip}...")
    try:
        # Use subprocess.run with capture_output for better error handling
        server_proc = subprocess.run(
            server_cmd, shell=True, check=True, capture_output=True, text=True)
        print(f"  Server start command stdout: {server_proc.stdout}")
        if server_proc.stderr:
            print(f"  Server start command stderr: {server_proc.stderr}")
        print(f"iperf3 server started or restarted on {server_ip}")
    except subprocess.CalledProcessError as e:
        # Log error but maybe continue if server might already be running
        print(
            f"Warning: Command to start iperf3 server on {server_ip} failed: {e}")
        print(f"Stderr: {e.stderr}")
        # Consider if this should be a fatal error

    # Give the server some time to start
    time.sleep(3)

    # Run the iperf3 UDP test on each client
    for i, client_ip in enumerate(client_ips):
        # Define unique output file per test
        result_json_file = f"udp_{server_ip}_to_{client_ip}_{timestamp}.json"
        local_result_path = os.path.join(output_dir, result_json_file)
        # Store on remote first
        remote_result_path = f"/tmp/{result_json_file}"

        # Run the iperf3 test on the client
        # Use ssh_key_path variable
        client_cmd = (
            f"ssh -i {ssh_key_path} -o StrictHostKeyChecking=no {ssh_user}@{client_ip} "
            f"'iperf3 -c {server_ip} -u -b {bandwidth} -t {duration} -J > {remote_result_path}'"
        )

        try:
            print(
                f"Starting UDP test ({i+1}/{len(client_ips)}): {client_ip} -> {server_ip}")
            client_proc = subprocess.run(
                client_cmd, shell=True, check=True, capture_output=True, text=True)
            if client_proc.stderr:
                print(f"  Client command stderr: {client_proc.stderr}")

            # Get the test results using scp
            # Use ssh_key_path variable
            get_result_cmd = f"scp -i {ssh_key_path} -o StrictHostKeyChecking=no {ssh_user}@{client_ip}:{remote_result_path} {local_result_path}"
            scp_proc = subprocess.run(
                get_result_cmd, shell=True, check=True, capture_output=True, text=True)
            if scp_proc.stderr:
                print(f"  SCP command stderr: {scp_proc.stderr}")

            print(f"Test completed, results saved to {local_result_path}")
            # Append result file path or parsed data to results list
            results.append({
                "client_ip": client_ip,
                "server_ip": server_ip,
                "result_file": local_result_path,
                "status": "success"  # Indicate success
            })
        except subprocess.CalledProcessError as e:
            print(f"Error: UDP test failed {client_ip} -> {server_ip}: {e}")
            if e.stdout:
                print(f"Stdout: {e.stdout}")
            if e.stderr:
                print(f"Stderr: {e.stderr}")
            results.append({
                "client_ip": client_ip,
                "server_ip": server_ip,
                "result_file": None,
                "status": "failed",  # Indicate failure
                "error": str(e)
            })
        except Exception as e:  # Catch other potential errors like scp failing
            print(f"Error during UDP test/scp {client_ip} -> {server_ip}: {e}")
            results.append({
               "client_ip": client_ip,
               "server_ip": server_ip,
               "result_file": None,
               "status": "failed",
               "error": str(e)
                })

    # Stop the iperf3 server (optional, but good practice)
    # Use ssh_key_path variable
    stop_cmd = f"ssh -i {ssh_key_path} -o StrictHostKeyChecking=no ec2-user@{server_ip} 'pkill iperf3'"
    try:
        print(f"Stopping iperf3 server on {server_ip}...")
        # Don't check=True, pkill returns error if no process found
        subprocess.run(stop_cmd, shell=True, check=False)
    except Exception as e:
        print(
            f"Warning: Failed to explicitly stop iperf3 server on {server_ip}: {e}")

    # Instead of writing a summary here, return the list of results/files
    # run_benchmark.py can then decide how to summarize or pass to collect/parse steps
    return results


# The main function here is for standalone execution, which might need updates
# but is not directly used by run_benchmark.py's flow.
def main():
    parser = argparse.ArgumentParser(
        description="execute the udp multicast test between ec2 instances")
    parser.add_argument("--instance-info", required=True,
                        help="the json file containing the ec2 instance info")
    parser.add_argument("--ssh-key", required=True,
                        help="the ssh key file path")  # This is ssh_key_path
    parser.add_argument("--bandwidth", default="1G",
                        help="the udp bandwidth limit, e.g. '100M' or '1G'")
    parser.add_argument("--duration", type=int, default=10,
                        help="the duration of each test (seconds)")
    parser.add_argument("--output-dir", default="../data",
                        help="the output directory for the test results")
    parser.add_argument("--server-region", required=True,
                        help="the region of the server")
    parser.add_argument("--use-private-ip", action="store_true",
                        help="use the private ip instead of the public ip for the test")
    # parser.add_argument("--intra-region", action="store_true",
    #                     help="also test between instances in the same region") # Not used by run_udp_test currently

    args = parser.parse_args()

    # Call run_udp_test with the correct argument name
    results = run_udp_test(
        instance_info_path=args.instance_info,
        ssh_key_path=args.ssh_key,  # Pass the key path correctly
        output_dir=args.output_dir,
        use_private_ip=args.use_private_ip,
        server_region=args.server_region,
        bandwidth=args.bandwidth,
        duration=args.duration
    )

    if results is not None:
        # Save a summary if run standalone
        summary_file = os.path.join(
            args.output_dir, f"udp_standalone_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        summary_data = {
            "server_region": args.server_region,
            "ip_type": "private" if args.use_private_ip else "public",
            "timestamp": datetime.now().isoformat(),
            "results": results  # Include the list returned by run_udp_test
        }
        try:
            with open(summary_file, 'w') as f:
                json.dump(summary_data, f, indent=2)
            print(f"\nStandalone test summary saved to {summary_file}")
            print(f"Completed {len(results)} UDP tests.")
        except Exception as e:
            print(f"Error saving standalone summary: {e}")
    else:
        print("\nUDP tests failed.")
        sys.exit(1)


if __name__ == "__main__":
    main()
