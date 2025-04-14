#!/bin/bash
# install_iperf3.sh
# 在EC2实例上安装iperf3

# 检测Linux发行版并安装iperf3
if [ -f /etc/os-release ]; then
    . /etc/os-release
    case $ID in
        amzn|rhel|centos)
            echo "检测到Amazon Linux/RHEL/CentOS，使用yum安装..."
            sudo yum update -y
            sudo yum install -y iperf3
            ;;
        ubuntu|debian)
            echo "检测到Ubuntu/Debian，使用apt安装..."
            sudo apt-get update
            sudo apt-get install -y iperf3
            ;;
        *)
            echo "不支持的Linux发行版: $ID"
            exit 1
            ;;
    esac
else
    echo "无法检测操作系统类型"
    exit 1
fi

# 验证安装
if command -v iperf3 >/dev/null 2>&1; then
    echo "iperf3安装成功！"
    iperf3 --version
else
    echo "iperf3安装失败！"
    exit 1
fi

# 确保iperf3服务可以在后台运行
echo "设置iperf3服务..."
cat > /tmp/iperf3.service << EOF
[Unit]
Description=iperf3 server
After=network.target

[Service]
Type=simple
ExecStart=/usr/bin/iperf3 -s
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

sudo mv /tmp/iperf3.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable iperf3
sudo systemctl start iperf3

echo "iperf3服务已启动并设置为开机自启"
