from Constants import PROJECT_ROOT, RUNS_DIR, SCRIPTS_DIR, TERRAFORM_DIR, DEFAULT_CONFIG_OPTIONS
from UiUtilities.verify_aws_credentials import verify_aws_credentials
import streamlit as st
import subprocess
import threading
import tempfile
import queue
import json
import glob
import os


def run_script_in_thread(command, output_queue, env_vars=None):
    """Runs a shell command in a separate thread and puts output lines into a queue."""
    try:
        # Merge provided env_vars with current environment
        env = os.environ.copy()
        if env_vars:
            env.update(env_vars)

        process = subprocess.Popen(
            command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True,
            # Run commands from project root
            cwd=PROJECT_ROOT,
            # Pass the modified environment
            env=env
        )
        for line in iter(process.stdout.readline, ''):
            output_queue.put(line)
        process.stdout.close()
        process.wait()
        if process.returncode != 0:
            output_queue.put(
                f"ERROR: Process exited with code {process.returncode}")
    except Exception as e:
        output_queue.put(
          f"ERROR: Failed to run command '{command}'. Exception: {str(e)}")
    finally:
        # Signal completion
        output_queue.put(None)



st.set_page_config(
    page_title="AWS Network Benchmark Tool",
    layout="wide"
)
st.title("AWS Network Benchmark Tool")


# Initialize session state keys if they don't exist
if 'aws_access_key_id' not in st.session_state:
    st.session_state.aws_access_key_id = ""
if 'aws_secret_access_key' not in st.session_state:
    st.session_state.aws_secret_access_key = ""
if 'aws_region' not in st.session_state:
    st.session_state.aws_region = "us-east-1"  # Default region example
if 'config_options' not in st.session_state:
    st.session_state.config_options = DEFAULT_CONFIG_OPTIONS.copy()
# Ensure udp_server_region is set initially if regions exist
if not st.session_state.config_options.get('udp_server_region') and st.session_state.config_options.get('aws_regions'):
    st.session_state.config_options['udp_server_region'] = st.session_state.config_options['aws_regions'][0]

if 'benchmark_running' not in st.session_state:
    st.session_state.benchmark_running = False
if 'cleanup_running' not in st.session_state:
    st.session_state.cleanup_running = False
if 'run_output' not in st.session_state:
    st.session_state.run_output = ""
if 'cleanup_output' not in st.session_state:
    st.session_state.cleanup_output = ""


# --- Sidebar ---
st.sidebar.header("Actions")

# AWS Credentials
st.sidebar.subheader("1. AWS Credentials")
st.session_state.aws_access_key_id = st.sidebar.text_input(
  "AWS Access Key ID", value=st.session_state.aws_access_key_id)
st.session_state.aws_secret_access_key = st.sidebar.text_input(
  "AWS Secret Access Key", type="password", value=st.session_state.aws_secret_access_key)
st.session_state.aws_region = st.sidebar.text_input(
  "AWS Default Region", value=st.session_state.aws_region)  # Added region input

if st.sidebar.button("Verify AWS Credentials"):
    verify_aws_credentials(
        st.session_state.aws_access_key_id,
        st.session_state.aws_secret_access_key,
        st.session_state.aws_region
    )

# Configuration - Removed file loading
st.sidebar.subheader("2. Configuration")
st.sidebar.info("Configure benchmark options in the 'Configuration' tab.")


# Run Benchmark
st.sidebar.subheader("3. Run Benchmark")
run_button = st.sidebar.button(
  "Start Benchmark Run", disabled=st.session_state.benchmark_running or st.session_state.cleanup_running)

# Cleanup
st.sidebar.subheader("4. Cleanup Resources")
cleanup_button = st.sidebar.button(
  "Destroy AWS Resources", disabled=st.session_state.benchmark_running or st.session_state.cleanup_running)

tab1, tab2, tab3, tab4 = st.tabs(
  ["Configuration", "Run Output", "Results", "Cleanup Output"])

with tab1:
    st.header("Benchmark Configuration")
    st.info("Modify the benchmark parameters below. These settings will be used when you start a run.")

    # Use columns for better layout
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("General Settings")
        available_regions = ["us-east-1", "us-east-2", "us-west-1", "us-west-2", "ca-central-1", "eu-west-1", "eu-central-1", "eu-west-2", "eu-west-3",
                             "eu-north-1", "ap-northeast-1", "ap-northeast-2", "ap-southeast-1", "ap-southeast-2", "ap-south-1", "sa-east-1"] 
        st.session_state.config_options['aws_regions'] = st.multiselect(
            "AWS Regions for Instances",
            options=available_regions,
            default=st.session_state.config_options.get('aws_regions', [])
        )
        st.session_state.config_options['instance_type'] = st.text_input(
            "EC2 Instance Type",
            value=st.session_state.config_options.get(
                'instance_type', 't2.micro')
        )
        st.session_state.config_options['ssh_key_name'] = st.text_input(
            "EC2 SSH Key Name (must exist in selected regions)",
            value=st.session_state.config_options.get(
              'ssh_key_name', 'aws-network-benchmark')
        )
        # Add create_ssh_key option
        st.session_state.config_options['create_ssh_key'] = st.checkbox(
            "Create SSH Key if Missing Locally (~/.ssh/)",
            value=st.session_state.config_options.get('create_ssh_key', True),
            help="If checked, will attempt to generate the key pair if it doesn't exist."
        )
        st.session_state.config_options['use_private_ip'] = st.checkbox(
            "Use Private IPs for Tests (within VPC)",
            value=st.session_state.config_options.get('use_private_ip', False)
        )
        st.session_state.config_options['test_intra_region'] = st.checkbox(
            "Include Tests Within the Same Region",
            value=st.session_state.config_options.get(
                'test_intra_region', True)
        )

        st.subheader("Workflow Steps")
        st.session_state.config_options['run_terraform_apply'] = st.checkbox(
            "Deploy Infrastructure (Terraform Apply)",
            value=st.session_state.config_options.get(
                'run_terraform_apply', True)
        )
        # Add skip_install option (as inverse logic for config)
        # We'll handle the --skip-install flag separately based on this
        st.session_state.config_options['install_iperf3'] = st.checkbox(
            "Install/Update iperf3 on Instances",
            value=st.session_state.config_options.get('install_iperf3', True),
            help="Uncheck to skip the iperf3 installation step."
        )
        # Add skip_tests option (as inverse logic for config)
        # We'll handle the --skip-tests flag separately based on this
        st.session_state.config_options['run_tests'] = st.checkbox(
            "Run Network Tests (Latency, P2P, UDP)",
            value=st.session_state.config_options.get('run_tests', True),
            help="Uncheck to skip all network performance tests."
        )
        st.session_state.config_options['generate_visualizations'] = st.checkbox(
            "Generate Visualization Charts",
            value=st.session_state.config_options.get(
              'generate_visualizations', True)
        )
        st.session_state.config_options['generate_report'] = st.checkbox(
            "Generate HTML Report",
            value=st.session_state.config_options.get('generate_report', True)
        )
        st.session_state.config_options['run_terraform_destroy'] = st.checkbox(
            "Destroy Infrastructure After Run (Cleanup)",
            value=st.session_state.config_options.get(
              'run_terraform_destroy', True)
        )

    with col2:
        st.subheader("Latency Tests (Ping)")
        st.session_state.config_options['run_latency_tests'] = st.checkbox(
            "Run Latency Tests",
            value=st.session_state.config_options.get(
                'run_latency_tests', True)
        )
        st.session_state.config_options['ping_count'] = st.number_input(
            "Ping Count per Test",
            min_value=1,
            value=st.session_state.config_options.get('ping_count', 20),
            disabled=not st.session_state.config_options['run_latency_tests']
        )

        st.subheader("Point-to-Point Tests (iperf3 TCP)")
        st.session_state.config_options['run_p2p_tests'] = st.checkbox(
            "Run Point-to-Point Tests",
            value=st.session_state.config_options.get('run_p2p_tests', True)
        )
        st.session_state.config_options['p2p_duration'] = st.number_input(
            "P2P Test Duration (seconds)",
            min_value=1,
            value=st.session_state.config_options.get('p2p_duration', 10),
            disabled=not st.session_state.config_options['run_p2p_tests']
        )
        st.session_state.config_options['p2p_parallel'] = st.number_input(
            "P2P Parallel Streams",
            min_value=1,
            value=st.session_state.config_options.get('p2p_parallel', 1),
            disabled=not st.session_state.config_options['run_p2p_tests']
        )

        st.subheader("UDP Tests (iperf3 UDP)")
        st.session_state.config_options['run_udp_tests'] = st.checkbox(
            "Run UDP Tests",
            value=st.session_state.config_options.get('run_udp_tests', True)
        )
        # Update UDP server region options based on selected regions
        udp_region_options = st.session_state.config_options.get(
            'aws_regions', [])
        udp_server_default_index = 0
        current_udp_server = st.session_state.config_options.get(
          'udp_server_region')
        if current_udp_server in udp_region_options:
            udp_server_default_index = udp_region_options.index(
                current_udp_server)
        elif udp_region_options:
            # Default to first if current is invalid
            st.session_state.config_options['udp_server_region'] = udp_region_options[0]

        st.session_state.config_options['udp_server_region'] = st.selectbox(
            "UDP Server Region",
            options=udp_region_options,
            index=udp_server_default_index,
            disabled=not st.session_state.config_options['run_udp_tests'] or not udp_region_options,
            help="Select one of the chosen AWS regions to host the UDP server."
        )
        st.session_state.config_options['udp_bandwidth'] = st.text_input(
            "UDP Target Bandwidth (e.g., 1G, 500M)",
            value=st.session_state.config_options.get('udp_bandwidth', '1G'),
            disabled=not st.session_state.config_options['run_udp_tests']
        )
        st.session_state.config_options['udp_duration'] = st.number_input(
            "UDP Test Duration (seconds)",
            min_value=1,
            value=st.session_state.config_options.get('udp_duration', 10),
            disabled=not st.session_state.config_options['run_udp_tests']
        )


with tab2:
    st.header("Benchmark Run Output")
    output_placeholder = st.empty()
    output_placeholder.text_area(
      "Output", value=st.session_state.run_output, height=600, key="run_output_area")


with tab3:
    st.header("Benchmark Results")
    st.info("Results will appear here after a successful benchmark run.")
    # Placeholder for results display
    # Example: Load latest results_summary.json from the runs directory
    try:
        if not os.path.exists(RUNS_DIR):
            os.makedirs(RUNS_DIR)  # Create runs dir if it doesn't exist

        run_dirs = sorted([os.path.join(RUNS_DIR, d) for d in os.listdir(RUNS_DIR) if os.path.isdir(
          os.path.join(RUNS_DIR, d))], key=lambda p: os.path.getmtime(p), reverse=True)
        if run_dirs:
            latest_run_dir = run_dirs[0]
            st.write(
              f"Displaying results from latest run: `{os.path.basename(latest_run_dir)}`")

            # Display Report Link if exists
            report_pattern = os.path.join(
              latest_run_dir, 'visualization', 'network_benchmark_report_*.html')
            report_files = glob.glob(report_pattern)
            if report_files:
                latest_report = sorted(
                  report_files, key=os.path.getmtime, reverse=True)[0]
                # Make link relative for potentially serving via streamlit
                # This might require hosting the report files appropriately
                # For local use, providing the path is okay.
                # Or try to embed?
                st.markdown(
                  f"**[View HTML Report]({latest_report})** (Link might require file access)")

            # Display Summary JSON
            summary_file = os.path.join(latest_run_dir, 'results_summary.json')
            if os.path.exists(summary_file):
                st.subheader(f"Run Summary")
                with open(summary_file, 'r') as f:
                    results_data = json.load(f)
                st.json(results_data)
            else:
                st.warning(
                  f"No results_summary.json found in the latest run directory: {latest_run_dir}")

            # Display Visualization Images if they exist
            vis_dir = os.path.join(latest_run_dir, 'visualization')
            image_files = glob.glob(os.path.join(
              vis_dir, '*.png'))  # Find PNG images
            if image_files:
                st.subheader("Visualizations")
                for img_file in sorted(image_files):
                    st.image(img_file, caption=os.path.basename(img_file))

        else:
            st.info("No previous run directories found.")
    except FileNotFoundError:
        st.info(f"Runs directory '{RUNS_DIR}' not found or inaccessible.")
    except Exception as e:
        st.error(f"Error loading results: {str(e)}")


with tab4:
    st.header("Cleanup Output")
    cleanup_output_placeholder = st.empty()
    cleanup_output_placeholder.text_area(
      "Output", value=st.session_state.cleanup_output, height=400, key="cleanup_output_area")


# --- Background Script Execution Logic ---

output_queue: queue.Queue = queue.Queue()

# Handle Run Benchmark Button Click
if run_button and not st.session_state.benchmark_running:
    # Validate required inputs
    if not all([st.session_state.aws_access_key_id, st.session_state.aws_secret_access_key, st.session_state.aws_region]):
        st.error(
          "Please provide AWS Credentials (Key ID, Secret Key, Region) in the sidebar.")
    elif not st.session_state.config_options.get('aws_regions'):
        st.error("Please select at least one AWS Region in the Configuration tab.")
    else:
        st.session_state.benchmark_running = True
        st.session_state.run_output = "Starting benchmark...\n"
        output_placeholder.text_area("Output", value=st.session_state.run_output,
                                     height=600, key="run_output_area_update_run") # Key change forces redraw

        # Create a temporary config file
        try:
            with tempfile.NamedTemporaryFile(mode='w', suffix=".json", delete=False) as temp_config:
                # Prepare config, removing UI-specific flags if necessary
                config_to_save = st.session_state.config_options.copy()
                # Remove flags handled by CLI args directly if they exist
                config_to_save.pop('run_tests', None) # This logic is handled by --skip-tests
                config_to_save.pop('install_iperf3', None) # This logic is handled by --skip-install

                json.dump(config_to_save, temp_config, indent=2)
                temp_config_path = temp_config.name
            st.session_state.run_output += f"Generated temporary config: {temp_config_path}\n"

            # Prepare environment variables for AWS credentials
            env_vars = {
                "AWS_ACCESS_KEY_ID": st.session_state.aws_access_key_id,
                "AWS_SECRET_ACCESS_KEY": st.session_state.aws_secret_access_key,
                "AWS_DEFAULT_REGION": st.session_state.aws_region
            }

            # Construct the command
            command = f"python3 {os.path.join(SCRIPTS_DIR, 'run_benchmark.py')} --config {temp_config_path}"

            # Add optional flags based on UI checkboxes
            if not st.session_state.config_options.get('run_terraform_apply', True):
                command += " --skip-terraform"
            if not st.session_state.config_options.get('install_iperf3', True): # Check the install_iperf3 state
                command += " --skip-install"
            if not st.session_state.config_options.get('run_tests', True): # Check the run_tests state
                command += " --skip-tests"
            if st.session_state.config_options.get('run_terraform_destroy', True):
                command += " --cleanup"

            st.session_state.run_output += f"Running command: {command}\n"
            output_placeholder.text_area("Output", value=st.session_state.run_output,
                                         height=600, key="run_output_area_update_cmd") # Key change forces redraw

            # Start the script in a separate thread
            thread = threading.Thread(target=run_script_in_thread, args=(
                command, output_queue, env_vars))
            thread.start()

            # Start a separate thread to update the UI periodically
            ui_update_thread = threading.Thread(target=update_output_area, args=(
                output_placeholder, "run_output", "run_output_area", output_queue, "benchmark_running", temp_config_path))
            ui_update_thread.start()

        except Exception as e:
            st.error(f"Failed to create temporary config file: {str(e)}")
            st.session_state.benchmark_running = False


# Handle Cleanup Button Click
if cleanup_button and not st.session_state.cleanup_running:
    # Validate required inputs
    if not all([st.session_state.aws_access_key_id, st.session_state.aws_secret_access_key, st.session_state.aws_region]):
        st.error(
          "Please provide AWS Credentials (Key ID, Secret Key, Region) in the sidebar.")
    else:
        st.session_state.cleanup_running = True
        st.session_state.cleanup_output = "Starting resource cleanup (Terraform Destroy)...\n"
        cleanup_output_placeholder.text_area(
          "Output", value=st.session_state.cleanup_output, height=400, key="cleanup_output_area_running")

        # Prepare environment variables for AWS credentials
        aws_env_vars = {
            "AWS_ACCESS_KEY_ID": st.session_state.aws_access_key_id,
            "AWS_SECRET_ACCESS_KEY": st.session_state.aws_secret_access_key,
            "AWS_DEFAULT_REGION": st.session_state.aws_region
        }

        # Command to run terraform destroy
        # Note: Assumes terraform init has been run previously (likely by run_benchmark.py)
        # It might be safer to run 'terraform init -upgrade' first.
        # Using -auto-approve for non-interactive execution.
        command = f"cd {TERRAFORM_DIR} && terraform destroy -auto-approve"

        # Start the script in a thread
        thread = threading.Thread(target=run_script_in_thread, args=(
          command, output_queue, aws_env_vars))
        thread.start()

        # Update output area periodically
        while thread.is_alive() or not output_queue.empty():
            while not output_queue.empty():
                line = output_queue.get()
                if line is None:  # End signal
                    break
                st.session_state.cleanup_output += line
            cleanup_output_placeholder.text_area(
              "Output", value=st.session_state.cleanup_output, height=400, key="cleanup_output_area_running_update")
            st.rerun()

        thread.join()
        st.session_state.cleanup_output += "Cleanup process finished.\n"
        st.session_state.cleanup_running = False
        st.rerun()
