import os
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
TERRAFORM_DIR = os.path.join(PROJECT_ROOT, "terraform")
RUNS_DIR = os.path.join(PROJECT_ROOT, "runs")
SCRIPTS_DIR = os.path.join(PROJECT_ROOT, "scripts")

# Initialize state for credentials and config options
DEFAULT_CONFIG_OPTIONS = {
    # General
    # Example defaults
    "aws_regions": ["us-east-1", "eu-west-2", "ap-northeast-1"],
    "instance_type": "t2.micro",
    # Default key name expected by scripts
    "ssh_key_name": "aws-network-benchmark",
    "use_private_ip": False,
    "test_intra_region": True,
    # Latency
    "run_latency_tests": True,
    "ping_count": 20,
    # P2P
    "run_p2p_tests": True,
    "p2p_duration": 10,
    "p2p_parallel": 1,
    # UDP
    "run_udp_tests": True,
    "udp_server_region": "",  # Will be set based on aws_regions
    "udp_bandwidth": "1G",
    "udp_duration": 10,
    # Workflow
    "run_terraform_apply": True,
    "run_terraform_destroy": True,  # Corresponds to cleanup
    "generate_visualizations": True,
    "generate_report": True,
}