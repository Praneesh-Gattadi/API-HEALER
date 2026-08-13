import httpx
import json
import yaml
import socket
import ipaddress
from typing import Dict, Any, Union
from urllib.parse import urlparse

class SecurityError(Exception):
    pass

class ContractParser:
    MAX_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB
    TIMEOUT_SECONDS = 10.0

    @classmethod
    def _is_safe_url(cls, url: str) -> bool:
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            raise SecurityError(f"Unsupported scheme: {parsed.scheme}")
            
        hostname = parsed.hostname
        if not hostname:
            raise SecurityError("Invalid URL format")

        try:
            # Resolve hostname to IP
            ip_str = socket.gethostbyname(hostname)
            ip = ipaddress.ip_address(ip_str)
            
            # Allow mock tests with 127.0.0.1 or localhost when testing locally,
            # but for this strict requirement we'll reject private/loopback 
            # unless a specific bypass flag is used (which we won't add per instructions,
            # we will just rely on httpx mock transports for testing without actual network calls).
            if ip.is_loopback or ip.is_private or ip.is_link_local or ip.is_reserved:
                raise SecurityError(f"URL resolves to restricted IP: {ip_str}")
                
        except socket.gaierror:
            raise SecurityError(f"Could not resolve hostname: {hostname}")
            
        return True

    @classmethod
    def fetch_and_parse(cls, url: str) -> Dict[str, Any]:
        """
        Fetches an OpenAPI spec from a URL and parses it into a dictionary.
        Enforces security rules (SSRF protection, size limit, timeout).
        """
        cls._is_safe_url(url)
        
        try:
            # We use httpx.Client to easily limit max download size by reading chunks if needed,
            # but for simplicity we can just use a stream and enforce limits.
            # Wait, httpx mock won't do DNS resolution in tests if we mock httpx, 
            # but our DNS check above runs before httpx.
            # For testing with httpx-mock, we might need a way to mock the DNS check or use a public IP.
            # Actually, the user said "Use mocked HTTP/local fixtures for tests."
            # So in tests, we will mock `_is_safe_url` to return True.
            
            with httpx.Client(timeout=cls.TIMEOUT_SECONDS) as client:
                with client.stream("GET", url) as response:
                    response.raise_for_status()
                    
                    content_length = response.headers.get("Content-Length")
                    if content_length and int(content_length) > cls.MAX_SIZE_BYTES:
                        raise SecurityError("Response too large")

                    content_bytes = bytearray()
                    for chunk in response.iter_bytes():
                        content_bytes.extend(chunk)
                        if len(content_bytes) > cls.MAX_SIZE_BYTES:
                            raise SecurityError("Response exceeded maximum size limit")
                            
            content_str = content_bytes.decode('utf-8')
            return cls.parse_content(content_str)
            
        except httpx.RequestError as e:
            raise SecurityError(f"Network error during fetch: {str(e)}")
        except httpx.HTTPStatusError as e:
            raise SecurityError(f"HTTP error {e.response.status_code}")

    @classmethod
    def fetch_text(cls, url: str) -> str:
        """Fetches plain text content securely (e.g., for changelogs)."""
        cls._is_safe_url(url)
        try:
            with httpx.Client(timeout=cls.TIMEOUT_SECONDS) as client:
                with client.stream("GET", url) as response:
                    response.raise_for_status()
                    content_length = response.headers.get("Content-Length")
                    if content_length and int(content_length) > cls.MAX_SIZE_BYTES:
                        raise SecurityError("Response too large")

                    content_bytes = bytearray()
                    for chunk in response.iter_bytes():
                        content_bytes.extend(chunk)
                        if len(content_bytes) > cls.MAX_SIZE_BYTES:
                            raise SecurityError("Response exceeded maximum size limit")
            return content_bytes.decode('utf-8')
        except Exception as e:
            raise SecurityError(f"Network error during fetch: {str(e)}")

    @classmethod
    def parse_content(cls, content: str) -> Dict[str, Any]:
        """Parses a string containing JSON or YAML into a dict."""
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            try:
                # safe_load prevents code execution in YAML
                result = yaml.safe_load(content)
                if not isinstance(result, dict):
                    raise ValueError("Parsed YAML is not a dictionary")
                return result
            except yaml.YAMLError as e:
                raise ValueError(f"Content is neither valid JSON nor YAML: {str(e)}")
