# EC2实例重启和iperf3重新安装工具

本目录包含用于重启AWS EC2实例并重新安装iperf3的工具，适用于网络基准测试项目中的问题修复。

## 文件说明

- `restart_instances.sh`: Bash脚本，用于重启所有区域的EC2实例并重新安装iperf3
- `clear_all.tf`: Terraform脚本，用于通过Terraform管理方式重启实例

## 使用方法

### 方法1: 使用Bash脚本（推荐）

这是最简单的方法，直接使用Bash脚本一键重启所有实例并重新安装iperf3：

```bash
# 确保脚本有执行权限
chmod +x restart_instances.sh

# 运行脚本
./restart_instances.sh
```

### 方法2: 使用Terraform

如果您更熟悉Terraform，可以使用Terraform脚本：

```bash
# 切换到clear_all_instance目录
cd clear_all_instance

# 初始化Terraform
terraform init

# 应用Terraform配置
terraform apply
```

## 注意事项

1. 这些脚本会重启项目标签为 `Project=aws-network-benchmark`的所有EC2实例
2. 重启后脚本会等待60秒，然后尝试重新安装iperf3
3. 需要已配置AWS CLI和有效的AWS凭证
4. 脚本假设EC2实例使用Amazon Linux 2系统，用户名为 `ec2-user`

## 故障排除

如果遇到问题，请检查以下几点：

1. AWS凭证是否正确配置：`aws configure`
2. SSH密钥是否存在于 `~/.ssh/aws-network-benchmark`
3. 检查 `data/instance_info.json`文件是否存在并包含正确的IP地址
4. 确保 `scripts/install_iperf3.sh`安装脚本存在并有执行权限

## 备用方法

如果脚本不起作用，您也可以通过AWS控制台手动重启实例：

1. 登录AWS控制台
2. 分别进入三个区域（东京、悉尼、伦敦）的EC2控制面板
3. 找到带有 `Project=aws-network-benchmark`标签的实例
4. 选择实例，点击"实例状态" > "重启实例"

## 停止所有EC2实例

如果您需要快速停止所有区域中的AWS EC2实例，可以使用以下脚本：

```bash
./stop_all.sh
```

这个脚本将：

1. 在所有配置的区域（东京、悉尼和伦敦）中查找带有 `Project=aws-network-benchmark`标签的运行中的EC2实例
2. 显示找到的所有实例信息并请求确认
3. 发送停止命令到所有实例
4. 监控实例状态直到所有实例都已停止

### 手动执行Python脚本

如果您需要直接运行Python脚本，可以使用：

```bash
python3 stop_all_instances.py
```

### 前提条件

- Python 3
- boto3库 (`pip install boto3`)
- 配置好的AWS凭证

### 注意事项

- 该脚本只会停止实例，不会终止(terminate)实例
- 已停止的实例不会产生计算费用，但存储卷和弹性IP仍会产生费用
- 如果需要完全避免所有费用，请考虑终止实例
