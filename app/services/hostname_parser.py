"""Hostname parsing utilities for extracting location information"""


def extract_city_from_hostname(hostname: str) -> str:
    """
    Extract city name from device hostname

    Examples:
        "Batumi-ATM 10.199.96.163" -> "Batumi"
        "PING-Kabali-AP 10.195.81.252" -> "Kabali"
        "Gori123-Router" -> "Gori"
    """
    # Remove IP if present: "Batumi-ATM 10.199.96.163" -> "Batumi-ATM"
    name = hostname.split()[0]

    # Handle special prefixes: "PING-Kabali-AP" -> skip "PING", use "Kabali"
    parts = name.split('-')

    # Skip common prefixes (PING, TEST, PROD, etc.)
    common_prefixes = ['PING', 'TEST', 'PROD', 'DEV', 'SW', 'RTR']
    if len(parts) > 1 and parts[0].upper() in common_prefixes:
        city = parts[1]  # Use second part as city
    else:
        city = parts[0]  # Use first part as city

    # Remove numbers: "Batumi1" -> "Batumi"
    city = ''.join([c for c in city if not c.isdigit()])

    return city.strip()
