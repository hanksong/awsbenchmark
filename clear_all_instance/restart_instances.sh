#!/bin/bash
# Restart all EC2 instances in all regions and reinstall iperf3

# Color definitions
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Project root directory
PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

# Region list
REGIONS=("ap-northeast-1" "ap-southeast-2" "eu-west-2")
REGION_NAMES=("Tokyo" "Sydney" "London")

# Check if AWS CLI is installed
if ! command -v aws &> /dev/null; then
    echo -e "${RED}Error: AWS CLI is not installed${NC}"
    echo "Please install AWS CLI: https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html"
    exit 1
fi

# Check AWS credentials
echo -e "${YELLOW}Checking AWS credentials...${NC}"
if ! aws sts get-caller-identity &> /dev/null; then
    echo -e "${RED}Error: AWS credentials are not configured or invalid${NC}"
    echo "Please run 'aws configure' to set up your AWS credentials"
    exit 1
fi

# Get and restart instances in each region
for i in "${!REGIONS[@]}"; do
    REGION=${REGIONS[$i]}
    REGION_NAME=${REGION_NAMES[$i]}
    
    echo -e "\n${YELLOW}Getting instances in ${REGION_NAME} region (${REGION})...${NC}"
    
    # Get all instance IDs with specific tags
    INSTANCE_IDS=$(aws ec2 describe-instances \
        --region $REGION \
        --filters "Name=tag:Project,Values=aws-network-benchmark" "Name=instance-state-name,Values=running,stopped,pending,stopping" \
        --query "Reservations[].Instances[].InstanceId" \
        --output text)
    
    if [ -z "$INSTANCE_IDS" ]; then
        echo -e "${YELLOW}No instances found in ${REGION_NAME} region${NC}"
        continue
    fi
    
    # Display found instances
    echo -e "${GREEN}Found instances in ${REGION_NAME} region:${NC}"
    for id in $INSTANCE_IDS; do
        echo " - $id"
    done
    
    # Restart instances
    echo -e "${YELLOW}Restarting instances in ${REGION_NAME} region...${NC}"
    aws ec2 reboot-instances --region $REGION --instance-ids $INSTANCE_IDS
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}Successfully sent restart command to instances in ${REGION_NAME} region${NC}"
    else
        echo -e "${RED}Error restarting instances in ${REGION_NAME} region${NC}"
    fi
done

echo -e "\n${YELLOW}Waiting for instances to restart (60 seconds)...${NC}"
sleep 60

# Reinstall iperf3
echo -e "\n${YELLOW}Reinstalling iperf3...${NC}"

# Check if instance info file exists
INSTANCE_INFO_PATH="$PROJECT_ROOT/data/instance_info.json"
if [ ! -f "$INSTANCE_INFO_PATH" ]; then
    echo -e "${RED}Error: Instance information file not found $INSTANCE_INFO_PATH${NC}"
    echo "Please run the benchmark script first to generate instance information"
    exit 1
fi

# Get SSH key path
SSH_KEY_PATH="$HOME/.ssh/aws-network-benchmark"
if [ ! -f "$SSH_KEY_PATH" ]; then
    echo -e "${RED}Error: SSH key not found $SSH_KEY_PATH${NC}"
    exit 1
fi

# Installation script path
INSTALL_SCRIPT_PATH="$PROJECT_ROOT/scripts/install_iperf3.sh"
if [ ! -f "$INSTALL_SCRIPT_PATH" ]; then
    echo -e "${RED}Error: Installation script not found $INSTALL_SCRIPT_PATH${NC}"
    exit 1
fi

# Ensure installation script has execution permissions
chmod +x "$INSTALL_SCRIPT_PATH"

# Get IP addresses from instance info file and reinstall iperf3
echo -e "${YELLOW}Getting IP addresses from instance info file...${NC}"
for REGION in "${REGIONS[@]}"; do
    PUBLIC_IPS=$(jq -r ".instances[\"$REGION\"].public_ips[]" "$INSTANCE_INFO_PATH" 2>/dev/null)
    
    if [ -z "$PUBLIC_IPS" ]; then
        echo -e "${YELLOW}No public IP addresses found in $REGION region${NC}"
        continue
    fi
    
    for IP in $PUBLIC_IPS; do
        echo -e "${YELLOW}Reinstalling iperf3 on instance $IP in $REGION region...${NC}"
        
        # Wait for SSH to be available
        echo "Waiting for SSH connection to be available..."
        for i in {1..10}; do
            if ssh -i "$SSH_KEY_PATH" -o StrictHostKeyChecking=no -o ConnectTimeout=5 ec2-user@$IP "echo Connection successful" &>/dev/null; then
                break
            fi
            echo "Attempt $i/10..."
            sleep 10
            if [ $i -eq 10 ]; then
                echo -e "${RED}Unable to connect to $IP, skipping this instance${NC}"
                continue 2
            fi
        done
        
        # Copy installation script to instance
        echo "Copying installation script to instance..."
        scp -i "$SSH_KEY_PATH" -o StrictHostKeyChecking=no "$INSTALL_SCRIPT_PATH" ec2-user@$IP:/tmp/
        
        if [ $? -ne 0 ]; then
            echo -e "${RED}Unable to copy installation script to $IP${NC}"
            continue
        fi
        
        # Execute installation script
        echo "Executing installation script..."
        ssh -i "$SSH_KEY_PATH" -o StrictHostKeyChecking=no ec2-user@$IP 'chmod +x /tmp/install_iperf3.sh && sudo /tmp/install_iperf3.sh'
        
        if [ $? -eq 0 ]; then
            echo -e "${GREEN}Successfully reinstalled iperf3 on $IP${NC}"
        else
            echo -e "${RED}Failed to reinstall iperf3 on $IP${NC}"
        fi
    done
done

echo -e "\n${GREEN}All operations completed!${NC}" 