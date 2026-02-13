from urllib.request import urlopen


def getIPv4():
    """Detects the current public IPv4 address of the user."""
    try:
        ipv4 = str(urlopen("https://api.ipify.org", timeout=5).read()).split("'")[1]
    except Exception as e:
        print(f">> Failed to get IP from https://api.ipify.org: {e}")
        ipv4 = None
    return ipv4

def getIPv6():
    """Detects the current public IPv6 address of the user."""
    try:
        ipv6 = str(urlopen('http://v6.ipv6-test.com/api/myip.php', timeout=5).read()).split("'")[1]
    except Exception as e:
        print(f">> Failed to get IP from http://v6.ipv6-test.com/api/myip.php: {e}")
        ipv6 = None
    if ipv6:
        if ":" not in ipv6:  # Basic check to see if it's a valid IPv6 address
            print(">> Detected IPv6 does not appear to be valid.")
            ipv6 = None
    return ipv6
