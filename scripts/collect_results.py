#!/usr/bin/env python3
# collect_results.py
# 收集和整理iperf3测试结果

import json
import argparse
import os
import sys
import glob
from datetime import datetime
import re

def parse_iperf3_result(result_file):
    """解析iperf3 JSON结果文件"""
    try:
        with open(result_file, 'r') as f:
            data = json.load(f)
        
        # 提取关键性能指标
        if 'end' in data:
            if data.get('error'):
                return {
                    'status': 'error',
                    'error_msg': data.get('error'),
                    'file': result_file
                }
            
            # TCP测试结果
            if 'sum_received' in data['end']:
                return {
                    'status': 'success',
                    'protocol': 'TCP',
                    'bits_per_second': data['end']['sum_received']['bits_per_second'],
                    'bytes': data['end']['sum_received']['bytes'],
                    'seconds': data['end']['sum_received']['seconds'],
                    'retransmits': data['end'].get('sum_sent', {}).get('retransmits', 0),
                    'file': result_file
                }
            # UDP测试结果
            elif 'sum' in data['end']:
                return {
                    'status': 'success',
                    'protocol': 'UDP',
                    'bits_per_second': data['end']['sum']['bits_per_second'],
                    'bytes': data['end']['sum']['bytes'],
                    'seconds': data['end']['sum']['seconds'],
                    'jitter_ms': data['end']['sum'].get('jitter_ms', 0),
                    'lost_packets': data['end']['sum'].get('lost_packets', 0),
                    'packets': data['end']['sum'].get('packets', 0),
                    'lost_percent': data['end']['sum'].get('lost_percent', 0),
                    'file': result_file
                }
        
        return {
            'status': 'unknown',
            'file': result_file
        }
    except Exception as e:
        print(f"错误：解析文件 {result_file} 时出错: {e}")
        return {
            'status': 'error',
            'error_msg': str(e),
            'file': result_file
        }

def extract_region_info(filename):
    """从文件名中提取区域信息"""
    try:
        # 对于点对点测试文件: p2p_<server_ip>_to_<client_ip>_<timestamp>.json
        if filename.startswith('p2p_'):
            return None  # 点对点测试文件中没有直接包含区域信息
        
        # 对于UDP测试文件: udp_multicast_<server_ip>_to_<client_ip>_<timestamp>.json
        elif filename.startswith('udp_multicast_'):
            return None  # UDP测试文件中没有直接包含区域信息
        
        return None
    except:
        return None

def collect_results(data_dir, output_file=None):
    """收集并整理所有测试结果"""
    # 查找所有测试结果文件
    p2p_files = glob.glob(os.path.join(data_dir, 'p2p_*.json'))
    udp_files = glob.glob(os.path.join(data_dir, 'udp_multicast_*.json'))
    
    # 首先查找并解析摘要文件以获取区域信息
    p2p_summary_files = glob.glob(os.path.join(data_dir, 'p2p_test_summary_*.json'))
    udp_summary_files = glob.glob(os.path.join(data_dir, 'udp_multicast_summary_*.json'))
    
    # 创建IP到区域的映射
    ip_to_region_map = {}
    # 先从UDP摘要文件获取
    for summary_file in udp_summary_files:
        try:
            with open(summary_file, 'r') as f:
                summary = json.load(f)
                if 'ip_to_region_map' in summary:
                    ip_to_region_map.update(summary['ip_to_region_map'])
                else:
                    # 兼容旧版本摘要文件
                    server_region = summary.get('server_region')
                    server_ip = summary.get('server_ip')
                    if server_ip and server_region:
                        ip_to_region_map[server_ip] = server_region
                    
                    for i, result in enumerate(summary.get('results', [])):
                        client_ip = result.get('client_ip')
                        if client_ip and i < len(summary.get('client_regions', [])):
                            ip_to_region_map[client_ip] = summary['client_regions'][i]
        except Exception as e:
            print(f"警告：无法解析UDP摘要文件 {summary_file}: {e}")
    
    p2p_region_map = {}
    for summary_file in p2p_summary_files:
        try:
            with open(summary_file, 'r') as f:
                summary = json.load(f)
                for test in summary:
                    result_file = os.path.basename(test['result_file'])
                    p2p_region_map[result_file] = {
                        'source_region': test['source_region'],
                        'target_region': test['target_region']
                    }
        except Exception as e:
            print(f"警告：无法解析P2P摘要文件 {summary_file}: {e}")
    
    # 解析点对点测试结果
    p2p_results = []
    for file in p2p_files:
        if 'summary' not in file:  # 跳过摘要文件
            result = parse_iperf3_result(file)
            filename = os.path.basename(file)
            region_info = extract_region_info(filename)
            
            if region_info:
                result.update(region_info)
            
            # 从区域映射获取信息
            if filename in p2p_region_map:
                result.update(p2p_region_map[filename])
            
            p2p_results.append(result)
    
    # 解析UDP测试结果
    udp_results = []
    for file in udp_files:
        if 'summary' not in file:  # 跳过摘要文件
            result = parse_iperf3_result(file)
            filename = os.path.basename(file)
            
            # 尝试直接从文件提取客户端和服务器区域
            try:
                with open(file, 'r') as f:
                    file_data = json.load(f)
                    if 'server_region' in file_data:
                        result['server_region'] = file_data['server_region']
                    if 'client_region' in file_data:
                        result['client_region'] = file_data['client_region']
            except Exception:
                pass
            
            # 如果没有区域信息，尝试从文件名提取IP，然后映射到区域
            if 'server_region' not in result or 'client_region' not in result:
                ip_info = extract_ip_info(filename)
                if ip_info:
                    server_ip = ip_info.get('server_ip')
                    client_ip = ip_info.get('client_ip')
                    
                    if server_ip and server_ip in ip_to_region_map:
                        result['server_region'] = ip_to_region_map[server_ip]
                    
                    if client_ip and client_ip in ip_to_region_map:
                        result['client_region'] = ip_to_region_map[client_ip]
            
            udp_results.append(result)
    
    # 整合所有结果
    all_results = {
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'point_to_point_tests': p2p_results,
        'udp_multicast_tests': udp_results
    }
    
    # 保存结果
    if output_file:
        output_path = output_file
    else:
        output_path = os.path.join(data_dir, f'collected_results_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json')
    
    with open(output_path, 'w') as f:
        json.dump(all_results, f, indent=2)
    
    print(f"测试结果已收集并保存到: {output_path}")
    print(f"共 {len(p2p_results)} 个点对点测试结果和 {len(udp_results)} 个UDP测试结果")
    
    return output_path

def extract_ip_info(filename):
    """从文件名中提取IP信息"""
    # 例如：udp_multicast_18.170.227.74_to_34.239.172.73_20250419_224615.json
    match = re.search(r'udp_multicast_([\d\.]+)_to_([\d\.]+)_', filename)
    if match:
        return {
            'server_ip': match.group(1),
            'client_ip': match.group(2)
        }
    return None

def main():
    parser = argparse.ArgumentParser(description="收集和整理iperf3测试结果")
    parser.add_argument("--data-dir", default="../data", help="测试结果数据目录")
    parser.add_argument("--output", help="输出文件路径")
    
    args = parser.parse_args()
    
    # 确保数据目录存在
    if not os.path.isdir(args.data_dir):
        print(f"错误：数据目录 {args.data_dir} 不存在")
        sys.exit(1)
    
    collect_results(args.data_dir, args.output)

if __name__ == "__main__":
    main()
