#!/usr/bin/env python3
# collect_results.py
# 收集和整理iperf3测试结果

import json
import argparse
import os
import sys
import glob
from datetime import datetime

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
    
    # 解析点对点测试结果
    p2p_results = []
    for file in p2p_files:
        if 'summary' not in file:  # 跳过摘要文件
            result = parse_iperf3_result(file)
            filename = os.path.basename(file)
            region_info = extract_region_info(filename)
            
            if region_info:
                result.update(region_info)
            
            p2p_results.append(result)
    
    # 解析UDP测试结果
    udp_results = []
    for file in udp_files:
        if 'summary' not in file:  # 跳过摘要文件
            result = parse_iperf3_result(file)
            filename = os.path.basename(file)
            region_info = extract_region_info(filename)
            
            if region_info:
                result.update(region_info)
            
            udp_results.append(result)
    
    # 查找并解析摘要文件以获取区域信息
    p2p_summary_files = glob.glob(os.path.join(data_dir, 'p2p_test_summary_*.json'))
    udp_summary_files = glob.glob(os.path.join(data_dir, 'udp_multicast_summary_*.json'))
    
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
            print(f"警告：无法解析摘要文件 {summary_file}: {e}")
    
    udp_region_map = {}
    for summary_file in udp_summary_files:
        try:
            with open(summary_file, 'r') as f:
                summary = json.load(f)
                server_region = summary.get('server_region')
                for result in summary.get('results', []):
                    result_file = os.path.basename(result['result_file'])
                    # 找到客户端区域
                    client_region = None
                    for i, ip in enumerate(summary.get('client_regions', [])):
                        if i < len(summary.get('client_regions', [])):
                            if result['client_ip'] == ip:
                                client_region = summary['client_regions'][i]
                                break
                    
                    udp_region_map[result_file] = {
                        'server_region': server_region,
                        'client_region': client_region
                    }
        except Exception as e:
            print(f"警告：无法解析摘要文件 {summary_file}: {e}")
    
    # 将区域信息添加到测试结果中
    for result in p2p_results:
        filename = os.path.basename(result['file'])
        if filename in p2p_region_map:
            result.update(p2p_region_map[filename])
    
    for result in udp_results:
        filename = os.path.basename(result['file'])
        if filename in udp_region_map:
            result.update(udp_region_map[filename])
    
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
    
    print(f"结果收集完成，已保存到 {output_path}")
    print(f"点对点测试: {len(p2p_results)} 个结果")
    print(f"UDP测试: {len(udp_results)} 个结果")
    
    return output_path

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
