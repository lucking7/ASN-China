#!/usr/bin/env python3
"""
从 IPInfo country.mmdb 提取指定国家的 IP 数据，生成精简版 MMDB 文件。
"""

import os
import sys
import argparse
import tempfile
import urllib.request

# 目标国家列表
DEFAULT_COUNTRIES = ['CN', 'HK', 'US', 'JP', 'SG']

# 数据源 URL
MMDB_SOURCE_URL = "https://github.com/xream/geoip/releases/latest/download/ipinfo.country.mmdb"


def download_mmdb(url: str, dest: str) -> bool:
    """下载 MMDB 文件"""
    print(f"正在下载: {url}")
    try:
        urllib.request.urlretrieve(url, dest)
        print(f"下载完成: {os.path.getsize(dest) / 1024 / 1024:.2f} MB")
        return True
    except Exception as e:
        print(f"下载失败: {e}")
        return False


def generate_mmdb(source_path: str, output_path: str, countries: list) -> bool:
    """从源 MMDB 提取指定国家，生成精简版"""
    try:
        import maxminddb
        from mmdb_writer import MMDBWriter
        from netaddr import IPSet, IPNetwork
    except ImportError as e:
        print(f"缺少依赖: {e}")
        print("请安装: pip install maxminddb mmdb-writer netaddr")
        return False

    countries_set = set(countries)
    print(f"目标国家: {', '.join(sorted(countries_set))}")

    # 读取源文件
    print(f"读取源文件: {source_path}")
    reader = maxminddb.open_database(source_path)

    networks_to_write = []
    stats = {c: 0 for c in countries_set}
    total = 0

    for network, data in reader:
        total += 1
        if total % 500000 == 0:
            print(f"  已处理 {total:,} 个网络...")

        if not data or 'country' not in data:
            continue

        country_code = data['country'].get('iso_code', '')
        if country_code in countries_set:
            networks_to_write.append((str(network), data))
            stats[country_code] += 1

    reader.close()
    print(f"源文件共 {total:,} 个网络，提取 {len(networks_to_write):,} 个")

    # 创建新 MMDB
    print("创建精简版 MMDB...")
    writer = MMDBWriter(
        ip_version=6,
        ipv4_compatible=True,
        database_type='ipinfo.lite'
    )

    for network_str, data in networks_to_write:
        try:
            ip_set = IPSet([IPNetwork(network_str)])
            writer.insert_network(ip_set, data)
        except Exception:
            pass

    writer.to_db_file(output_path)
    output_size = os.path.getsize(output_path)
    print(f"输出文件: {output_path} ({output_size / 1024 / 1024:.2f} MB)")

    # 统计
    print("\n各国家网络数:")
    for c in sorted(stats.keys()):
        print(f"  {c}: {stats[c]:,}")

    return True


def main():
    parser = argparse.ArgumentParser(description='生成精简版 Country MMDB')
    parser.add_argument('--source', help='源 MMDB 文件路径（不指定则自动下载）')
    parser.add_argument('--output', default='ipinfo.lite.mmdb', help='输出文件路径')
    parser.add_argument('--countries', nargs='+', default=DEFAULT_COUNTRIES,
                        help=f'要提取的国家代码，默认: {DEFAULT_COUNTRIES}')
    args = parser.parse_args()

    # 确定源文件
    if args.source and os.path.exists(args.source):
        source_path = args.source
    else:
        # 下载到临时目录
        temp_dir = tempfile.gettempdir()
        source_path = os.path.join(temp_dir, 'ipinfo.country.mmdb')
        if not download_mmdb(MMDB_SOURCE_URL, source_path):
            sys.exit(1)

    # 生成精简版
    if not generate_mmdb(source_path, args.output, args.countries):
        sys.exit(1)

    print("\n✅ 完成!")


if __name__ == '__main__':
    main()

