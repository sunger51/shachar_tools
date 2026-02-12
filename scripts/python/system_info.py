#!/usr/bin/env python3
"""
System Info - Display system information and resource usage.

This script provides a quick overview of system information including
CPU, memory, disk usage, and network information.
"""

import platform
import psutil
import socket
from datetime import datetime


def get_size(bytes):
    """Convert bytes to human readable format."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes < 1024.0:
            return f"{bytes:.2f} {unit}"
        bytes /= 1024.0


def print_system_info():
    """Print system information."""
    print("=" * 60)
    print("SYSTEM INFORMATION")
    print("=" * 60)
    
    # System info
    uname = platform.uname()
    print(f"System: {uname.system}")
    print(f"Node Name: {uname.node}")
    print(f"Release: {uname.release}")
    print(f"Version: {uname.version}")
    print(f"Machine: {uname.machine}")
    print(f"Processor: {uname.processor}")
    
    # Boot time
    boot_time = datetime.fromtimestamp(psutil.boot_time())
    print(f"Boot Time: {boot_time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    print("\n" + "=" * 60)
    print("CPU INFORMATION")
    print("=" * 60)
    
    # CPU info
    print(f"Physical cores: {psutil.cpu_count(logical=False)}")
    print(f"Total cores: {psutil.cpu_count(logical=True)}")
    
    # CPU frequencies
    cpufreq = psutil.cpu_freq()
    if cpufreq:
        print(f"Max Frequency: {cpufreq.max:.2f}Mhz")
        print(f"Min Frequency: {cpufreq.min:.2f}Mhz")
        print(f"Current Frequency: {cpufreq.current:.2f}Mhz")
    
    # CPU usage
    print(f"CPU Usage Per Core:")
    for i, percentage in enumerate(psutil.cpu_percent(percpu=True, interval=1)):
        print(f"  Core {i}: {percentage}%")
    print(f"Total CPU Usage: {psutil.cpu_percent()}%")
    
    print("\n" + "=" * 60)
    print("MEMORY INFORMATION")
    print("=" * 60)
    
    # Memory info
    svmem = psutil.virtual_memory()
    print(f"Total: {get_size(svmem.total)}")
    print(f"Available: {get_size(svmem.available)}")
    print(f"Used: {get_size(svmem.used)}")
    print(f"Percentage: {svmem.percent}%")
    
    # Swap memory
    swap = psutil.swap_memory()
    print(f"\nSwap Total: {get_size(swap.total)}")
    print(f"Swap Free: {get_size(swap.free)}")
    print(f"Swap Used: {get_size(swap.used)}")
    print(f"Swap Percentage: {swap.percent}%")
    
    print("\n" + "=" * 60)
    print("DISK INFORMATION")
    print("=" * 60)
    
    # Disk info
    partitions = psutil.disk_partitions()
    for partition in partitions:
        print(f"\nDevice: {partition.device}")
        print(f"  Mountpoint: {partition.mountpoint}")
        print(f"  File system type: {partition.fstype}")
        try:
            partition_usage = psutil.disk_usage(partition.mountpoint)
            print(f"  Total Size: {get_size(partition_usage.total)}")
            print(f"  Used: {get_size(partition_usage.used)}")
            print(f"  Free: {get_size(partition_usage.free)}")
            print(f"  Percentage: {partition_usage.percent}%")
        except PermissionError:
            print("  Permission denied")
    
    print("\n" + "=" * 60)
    print("NETWORK INFORMATION")
    print("=" * 60)
    
    # Network info
    hostname = socket.gethostname()
    print(f"Hostname: {hostname}")
    try:
        ip_address = socket.gethostbyname(hostname)
        print(f"IP Address: {ip_address}")
    except:
        print("IP Address: Unable to get IP")
    
    # Network interfaces
    if_addrs = psutil.net_if_addrs()
    for interface_name, interface_addresses in if_addrs.items():
        print(f"\nInterface: {interface_name}")
        for address in interface_addresses:
            if str(address.family) == 'AddressFamily.AF_INET':
                print(f"  IP Address: {address.address}")
                print(f"  Netmask: {address.netmask}")
                print(f"  Broadcast IP: {address.broadcast}")
            elif str(address.family) == 'AddressFamily.AF_PACKET':
                print(f"  MAC Address: {address.address}")
    
    print("\n" + "=" * 60)


def main():
    try:
        print_system_info()
    except Exception as e:
        print(f"Error: {e}")
        return 1
    return 0


if __name__ == '__main__':
    import sys
    sys.exit(main())
