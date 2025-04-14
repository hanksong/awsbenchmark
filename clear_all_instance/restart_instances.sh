#!/bin/bash
# 重启所有区域的EC2实例并重新安装iperf3

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 项目根目录
PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

# 区域列表
REGIONS=("ap-northeast-1" "ap-southeast-2" "eu-west-2")
REGION_NAMES=("东京" "悉尼" "伦敦")

# 检查AWS CLI是否安装
if ! command -v aws &> /dev/null; then
    echo -e "${RED}错误: AWS CLI 未安装${NC}"
    echo "请安装 AWS CLI: https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html"
    exit 1
fi

# 检查AWS凭证
echo -e "${YELLOW}检查AWS凭证...${NC}"
if ! aws sts get-caller-identity &> /dev/null; then
    echo -e "${RED}错误: AWS凭证未配置或无效${NC}"
    echo "请运行 'aws configure' 配置您的AWS凭证"
    exit 1
fi

# 获取和重启各区域的实例
for i in "${!REGIONS[@]}"; do
    REGION=${REGIONS[$i]}
    REGION_NAME=${REGION_NAMES[$i]}
    
    echo -e "\n${YELLOW}获取${REGION_NAME}区域 (${REGION}) 的实例...${NC}"
    
    # 获取具有特定标签的所有实例ID
    INSTANCE_IDS=$(aws ec2 describe-instances \
        --region $REGION \
        --filters "Name=tag:Project,Values=aws-network-benchmark" "Name=instance-state-name,Values=running,stopped,pending,stopping" \
        --query "Reservations[].Instances[].InstanceId" \
        --output text)
    
    if [ -z "$INSTANCE_IDS" ]; then
        echo -e "${YELLOW}在${REGION_NAME}区域没有找到实例${NC}"
        continue
    fi
    
    # 显示找到的实例
    echo -e "${GREEN}在${REGION_NAME}区域找到以下实例:${NC}"
    for id in $INSTANCE_IDS; do
        echo " - $id"
    done
    
    # 重启实例
    echo -e "${YELLOW}重启${REGION_NAME}区域的实例...${NC}"
    aws ec2 reboot-instances --region $REGION --instance-ids $INSTANCE_IDS
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}成功发送重启命令到${REGION_NAME}区域的实例${NC}"
    else
        echo -e "${RED}重启${REGION_NAME}区域的实例时出错${NC}"
    fi
done

echo -e "\n${YELLOW}等待实例重启 (60秒)...${NC}"
sleep 60

# 重新安装iperf3
echo -e "\n${YELLOW}重新安装iperf3...${NC}"

# 检查实例信息文件是否存在
INSTANCE_INFO_PATH="$PROJECT_ROOT/data/instance_info.json"
if [ ! -f "$INSTANCE_INFO_PATH" ]; then
    echo -e "${RED}错误: 找不到实例信息文件 $INSTANCE_INFO_PATH${NC}"
    echo "请先运行 benchmark 脚本以生成实例信息"
    exit 1
fi

# 获取SSH密钥路径
SSH_KEY_PATH="$HOME/.ssh/aws-network-benchmark"
if [ ! -f "$SSH_KEY_PATH" ]; then
    echo -e "${RED}错误: 找不到SSH密钥 $SSH_KEY_PATH${NC}"
    exit 1
fi

# 安装脚本路径
INSTALL_SCRIPT_PATH="$PROJECT_ROOT/scripts/install_iperf3.sh"
if [ ! -f "$INSTALL_SCRIPT_PATH" ]; then
    echo -e "${RED}错误: 找不到安装脚本 $INSTALL_SCRIPT_PATH${NC}"
    exit 1
fi

# 确保安装脚本有执行权限
chmod +x "$INSTALL_SCRIPT_PATH"

# 从实例信息文件获取IP地址并重新安装iperf3
echo -e "${YELLOW}从实例信息文件获取IP地址...${NC}"
for REGION in "${REGIONS[@]}"; do
    PUBLIC_IPS=$(jq -r ".instances[\"$REGION\"].public_ips[]" "$INSTANCE_INFO_PATH" 2>/dev/null)
    
    if [ -z "$PUBLIC_IPS" ]; then
        echo -e "${YELLOW}在$REGION区域没有找到公共IP地址${NC}"
        continue
    fi
    
    for IP in $PUBLIC_IPS; do
        echo -e "${YELLOW}在 $REGION 区域的实例 $IP 上重新安装iperf3...${NC}"
        
        # 等待SSH可用
        echo "等待SSH连接可用..."
        for i in {1..10}; do
            if ssh -i "$SSH_KEY_PATH" -o StrictHostKeyChecking=no -o ConnectTimeout=5 ec2-user@$IP "echo 连接成功" &>/dev/null; then
                break
            fi
            echo "尝试 $i/10..."
            sleep 10
            if [ $i -eq 10 ]; then
                echo -e "${RED}无法连接到 $IP，跳过此实例${NC}"
                continue 2
            fi
        done
        
        # 复制安装脚本到实例
        echo "复制安装脚本到实例..."
        scp -i "$SSH_KEY_PATH" -o StrictHostKeyChecking=no "$INSTALL_SCRIPT_PATH" ec2-user@$IP:/tmp/
        
        if [ $? -ne 0 ]; then
            echo -e "${RED}无法复制安装脚本到 $IP${NC}"
            continue
        fi
        
        # 执行安装脚本
        echo "执行安装脚本..."
        ssh -i "$SSH_KEY_PATH" -o StrictHostKeyChecking=no ec2-user@$IP 'chmod +x /tmp/install_iperf3.sh && sudo /tmp/install_iperf3.sh'
        
        if [ $? -eq 0 ]; then
            echo -e "${GREEN}在 $IP 上成功重新安装iperf3${NC}"
        else
            echo -e "${RED}在 $IP 上重新安装iperf3失败${NC}"
        fi
    done
done

echo -e "\n${GREEN}所有操作完成!${NC}" 