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

# Region name mappings for human-readable output
AWS_REGION_NAMES = {
    "us-east-1": "virginia",
    "us-east-2": "ohio",
    "us-west-1": "california",
    "us-west-2": "oregon",
    "ca-central-1": "canada",
    "eu-west-1": "ireland",
    "eu-west-2": "london",
    "eu-west-3": "paris",
    "eu-central-1": "frankfurt",
    "eu-north-1": "stockholm",
    "ap-northeast-1": "tokyo",
    "ap-northeast-2": "seoul",
    "ap-northeast-3": "osaka",
    "ap-southeast-1": "singapore",
    "ap-southeast-2": "sydney",
    "ap-south-1": "mumbai",
    "sa-east-1": "saopaulo",
    "af-south-1": "capetown",
    "me-south-1": "bahrain"
}

# Fallback AMI IDs for Amazon Linux 2 in case API call fails
AWS_FALLBACK_AMI_IDS = {
    "us-east-1": "ami-0230bd60aa48260c6",
    "us-east-2": "ami-06d6c38e6097eb144",
    "us-west-1": "ami-079a2a9ac6ed793e6",
    "us-west-2": "ami-09ee0d355a6091e77",
    "ca-central-1": "ami-0bb3fae62b2968c22",
    "eu-west-1": "ami-0cc7e92b19e61b6a4",
    "eu-west-2": "ami-02e122a5b090f377d",
    "eu-west-3": "ami-086ebba2a8fb34f1f",
    "eu-central-1": "ami-05189af83ce42a6a7",
    "eu-north-1": "ami-0bf30fc96c6ca89dc",
    "ap-northeast-1": "ami-06ae089b59b645ddc",
    "ap-northeast-2": "ami-0e4791176ea06b114",
    "ap-northeast-3": "ami-0ede394b2c6f5af3c",
    "ap-southeast-1": "ami-034f51cae2865c0e5",
    "ap-southeast-2": "ami-0db6fa4ad94ed2496",
    "ap-south-1": "ami-0a0d9cf81c5acd58c",
    "sa-east-1": "ami-0fb4cf3a99aa89f49",
    "af-south-1": "ami-028307eb8d34710b0",
    "me-south-1": "ami-0255b97934a9bdc27"
}
