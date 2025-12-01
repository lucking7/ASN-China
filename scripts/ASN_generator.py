import argparse
import time
from typing import Dict, Iterable, List, Tuple

import requests
from lxml import etree

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Safari/537.36"
)

COUNTRY_METADATA: Dict[str, Dict[str, str]] = {
    "CN": {"display": "China", "file": "ASN.China.list"},
    "US": {"display": "US", "file": "ASN.US.list"},
    "JP": {"display": "Japan", "file": "ASN.Japan.list"},
    "HK": {"display": "Hong Kong", "file": "ASN.HongKong.list"},
    "SG": {"display": "Singapore", "file": "ASN.Singapore.list"},
}

DEFAULT_COUNTRY_ORDER: List[str] = ["CN", "US", "JP", "HK", "SG"]


def init_file(display_name: str, output_path: str) -> None:
    local_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    with open(output_path, "w") as asn_file:
        asn_file.write(
            f"// ASN Information in {display_name}. (https://github.com/missuo/ASN-China) \n"
        )
        asn_file.write("// Last Updated: UTC " + local_time + "\n")
        asn_file.write("// Made by Vincent, All rights reserved. \n\n")


def fetch_country_asns(country_code: str) -> List[Tuple[str, str]]:
    url = f"https://bgp.he.net/country/{country_code}"
    headers = {"User-Agent": USER_AGENT}
    response = requests.get(url=url, headers=headers, timeout=30)
    response.raise_for_status()
    tree = etree.HTML(response.text)
    rows = tree.xpath('//*[@id="asns"]/tbody/tr')
    results: List[Tuple[str, str]] = []
    for row in rows:
        number_nodes = row.xpath("td[1]/a")
        name_nodes = row.xpath("td[2]")
        if not number_nodes or not name_nodes:
            continue
        asn_number = (number_nodes[0].text or "").replace("AS", "").strip()
        asn_name = (name_nodes[0].text or "").strip()
        if not asn_number or not asn_name:
            continue
        results.append((asn_number, asn_name))
    return results


def write_asn_entries(output_path: str, entries: Iterable[Tuple[str, str]]) -> int:
    count = 0
    with open(output_path, "a") as asn_file:
        for number, name in entries:
            asn_file.write(f"IP-ASN,{number} // {name}\n")
            count += 1
    return count


def generate_country_asn(
    country_code: str, output_path: str = None, display_name: str = None
) -> int:
    code = country_code.upper()
    metadata = COUNTRY_METADATA.get(code, {})
    file_path = output_path or metadata.get("file")
    display = display_name or metadata.get("display", code)

    if not file_path:
        raise ValueError(f"No output file configured for country code '{code}'.")

    asn_entries = fetch_country_asns(code)
    if not asn_entries:
        print(f"[WARN] No ASN entries found for {code}.")
        init_file(display, file_path)
        return 0

    init_file(display, file_path)
    count = write_asn_entries(file_path, asn_entries)
    print(f"[INFO] {code}: wrote {count} entries to {file_path}")
    return count


def generate_multiple(country_codes: Iterable[str] = None) -> None:
    codes = list(country_codes) if country_codes else DEFAULT_COUNTRY_ORDER
    for code in codes:
        if code.upper() not in COUNTRY_METADATA:
            print(f"[WARN] Country code '{code}' not configured, skipping.")
            continue
        try:
            generate_country_asn(code.upper())
        except requests.RequestException as exc:
            print(f"[ERROR] Failed to fetch ASN data for {code.upper()}: {exc}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate ASN lists for specific countries."
    )
    parser.add_argument(
        "--countries",
        nargs="+",
        metavar="CODE",
        help="ISO country codes to generate (default: CN US JP HK SG).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.countries:
        countries = [code.upper() for code in args.countries]
    else:
        countries = DEFAULT_COUNTRY_ORDER
    generate_multiple(countries)


if __name__ == "__main__":
    main()
