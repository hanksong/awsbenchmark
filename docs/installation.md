# AWS Network Benchmark Tool Installation Guide

This document provides detailed steps for installing and configuring the AWS Network Benchmark Tool.

## System Requirements

- Operating System: Linux, macOS, or Windows (using WSL)
- Python 3.6+
- Terraform 0.14+
- AWS account and configured AWS CLI credentials
- Sufficient AWS permissions to create and manage EC2 instances, VPCs, security groups, and other resources

## Installation Steps

### 1. Install Dependencies

#### Install Python

Ensure Python 3.6 or higher is installed on your system:

```bash
# Check Python version
python3 --version
```

If you need to install Python, follow the instructions for your operating system:

- **Ubuntu/Debian**:
  ```bash
  sudo apt update
  sudo apt install python3 python3-pip
  ```

- **CentOS/RHEL**:
  ```bash
  sudo yum install python3 python3-pip
  ```

- **macOS**:
  ```bash
  brew install python
  ```

#### Install Terraform

Install Terraform 0.14 or higher:

- **Ubuntu/Debian**:
  ```bash
  sudo apt update
  sudo apt install -y gnupg software-properties-common curl
  curl -fsSL https://apt.releases.hashicorp.com/gpg | sudo apt-key add -
  sudo apt-add-repository "deb [arch=amd64] https://apt.releases.hashicorp.com $(lsb_release -cs) main"
  sudo apt update
  sudo apt install terraform
  ```

- **CentOS/RHEL**:
  ```bash
  sudo yum install -y yum-utils
  sudo yum-config-manager --add-repo https://rpm.releases.hashicorp.com/RHEL/hashicorp.repo
  sudo yum install terraform
  ```

- **macOS**:
  ```bash
  brew tap hashicorp/tap
  brew install hashicorp/tap/terraform
  ```

- **Windows**:
  Download and install [Terraform for Windows](https://www.terraform.io/downloads.html)

Verify the installation:
```bash
terraform --version
```

#### Install AWS CLI

Install and configure AWS CLI:

- **Ubuntu/Debian**:
  ```bash
  sudo apt update
  sudo apt install -y awscli
  ```

- **CentOS/RHEL**:
  ```bash
  sudo yum install -y awscli
  ```

- **macOS**:
  ```bash
  brew install awscli
  ```

- **Windows**:
  Download and install [AWS CLI for Windows](https://aws.amazon.com/cli/)

Configure AWS CLI:
```bash
aws configure
```

Enter your AWS access key ID, secret access key, default region, and output format.

### 2. Get the Project Code

Clone the project repository:

```bash
git clone https://github.com/yourusername/aws-network-benchmark.git
cd aws-network-benchmark
```

Alternatively, you can download a ZIP file of the project and extract it.

### 3. Install Python Dependencies

Install the Python packages required for the project:

```bash
pip3 install pandas matplotlib seaborn jinja2 numpy
```

Or use the requirements.txt file in the project:

```bash
pip3 install -r requirements.txt
```

### 4. Configure SSH Key

If you set `"create_ssh_key": true` in `config.json`, the script will automatically create an SSH key. Otherwise, you need to create it manually:

```bash
ssh-keygen -t rsa -b 2048 -f ~/.ssh/aws-network-benchmark -N ''
```

### 5. Verify Installation

Verify that all components are correctly installed:

```bash
# Verify Python
python3 --version

# Verify Terraform
terraform --version

# Verify AWS CLI
aws --version

# Verify Python packages
pip3 list | grep -E 'pandas|matplotlib|seaborn|jinja2|numpy'
```

## Troubleshooting

### Common Issues

1. **AWS Credential Problems**:
   - Ensure you have correctly configured AWS credentials
   - Check the `~/.aws/credentials` and `~/.aws/config` files
   - Try running `aws sts get-caller-identity` to verify credentials

2. **Terraform Initialization Failure**:
   - Ensure you have a stable internet connection
   - Check if your AWS credentials are valid
   - Try running `terraform init` manually to see detailed errors

3. **Python Dependency Issues**:
   - Try using a virtual environment:
     ```bash
     python3 -m venv venv
     source venv/bin/activate  # Linux/macOS
     # or
     venv\Scripts\activate  # Windows
     pip install -r requirements.txt
     ```

4. **SSH Key Permission Issues**:
   - Ensure SSH key file permissions are correct:
     ```bash
     chmod 600 ~/.ssh/aws-network-benchmark
     ```

## Next Steps

After installation is complete, refer to the [Usage Instructions](usage.md) to learn how to configure and run the network benchmark.
