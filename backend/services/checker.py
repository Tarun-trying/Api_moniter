"""
SSRF-protected HTTP checker using httpx.

Each check:
1. Validates the URL is not pointing to private/internal IPs.
2. Sends the HTTP request with the configured method and timeout.
3. Records response time, status code, and optional content check.
4. Returns a structured result dict without writing to DB (DB write happens in monitor_service).
"""
import ipaddress
import socket
import time
from typing import Optional
from urllib.parse import urlparse

import httpx

# ---------------------------------------------------------------------------
# SSRF Protection
# ---------------------------------------------------------------------------

_BLOCKED_RANGES = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),   # link-local / AWS metadata
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
    ipaddress.ip_network("fe80::/10"),
    ipaddress.ip_network("0.0.0.0/8"),
    ipaddress.ip_network("100.64.0.0/10"),    # shared address space
]

_BLOCKED_HOSTNAMES = {
    "localhost",
    "metadata.google.internal",
    "169.254.169.254",
}


def _is_private_ip(ip_str: str) -> bool:
    try:
        addr = ipaddress.ip_address(ip_str)
        return any(addr in net for net in _BLOCKED_RANGES)
    except ValueError:
        return False


def validate_url(url: str) -> Optional[str]:
    """
    Returns None if the URL is safe, or an error string if it should be blocked.
    Does NOT make a network request — uses a DNS lookup for IP validation.
    """
    try:
        parsed = urlparse(url)
    except Exception:
        return "Invalid URL format"

    if parsed.scheme not in ("http", "https"):
        return "URL must use http or https"

    hostname = parsed.hostname
    if not hostname:
        return "URL has no hostname"

    if hostname.lower() in _BLOCKED_HOSTNAMES:
        return f"Requests to '{hostname}' are not allowed"

    # Try to resolve and check IP
    try:
        infos = socket.getaddrinfo(hostname, None)
        for info in infos:
            ip = info[4][0]
            if _is_private_ip(ip):
                return f"Requests to private IP addresses are not allowed (resolved to {ip})"
    except socket.gaierror:
        # Allow DNS failures through at validation time; they'll fail at check time too.
        pass

    return None  # safe


# ---------------------------------------------------------------------------
# Check runner
# ---------------------------------------------------------------------------

async def run_check(
    url: str,
    method: str,
    timeout: int,
    expected_status: Optional[int],
    expected_content: Optional[str],
) -> dict:
    """
    Perform a single HTTP check.  Returns a dict with:
        success           bool
        status_code       int | None
        response_time     float | None   (milliseconds)
        error_message     str | None
        content_check_passed  bool | None
    """
    result = {
        "success": False,
        "status_code": None,
        "response_time": None,
        "error_message": None,
        "content_check_passed": None,
    }

    # Re-validate at check time to prevent DNS rebinding
    ssrf_error = validate_url(url)
    if ssrf_error:
        result["error_message"] = f"URL blocked: {ssrf_error}"
        return result

    start = time.perf_counter()

    try:
        async with httpx.AsyncClient(
            follow_redirects=True,
            timeout=httpx.Timeout(timeout),
            limits=httpx.Limits(max_connections=50, max_keepalive_connections=10),
        ) as client:
            response = await client.request(method, url)

        elapsed_ms = (time.perf_counter() - start) * 1000
        result["status_code"] = response.status_code
        result["response_time"] = round(elapsed_ms, 2)

        # Status code check
        expected = expected_status or 200
        status_ok = response.status_code == expected

        # Content check
        content_ok: Optional[bool] = None
        if expected_content:
            try:
                body = response.text
                content_ok = expected_content in body
            except Exception:
                content_ok = False
        result["content_check_passed"] = content_ok

        result["success"] = status_ok and (content_ok is not False)

        if not status_ok:
            result["error_message"] = (
                f"Expected HTTP {expected}, got {response.status_code}"
            )
        elif content_ok is False:
            result["error_message"] = (
                f"Response body did not contain expected string: {expected_content!r}"
            )

    except httpx.TimeoutException:
        elapsed_ms = (time.perf_counter() - start) * 1000
        result["response_time"] = round(elapsed_ms, 2)
        result["error_message"] = f"Request timed out after {timeout} seconds"

    except httpx.ConnectError as exc:
        result["error_message"] = f"Connection error: {exc}"

    except httpx.InvalidURL:
        result["error_message"] = "Invalid URL"

    except Exception as exc:
        result["error_message"] = f"Unexpected error: {type(exc).__name__}: {exc}"

    return result
