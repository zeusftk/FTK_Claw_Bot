# -*- coding: utf-8 -*-
"""
SSRF (Server-Side Request Forgery) Guard.

Validates URLs to prevent access to internal/private network resources.
"""

import ipaddress
from urllib.parse import urlparse
from typing import Set, Tuple


class SSRFGuard:
    """
    Guards against SSRF attacks by blocking access to internal networks.
    
    Blocks:
    - Loopback addresses (127.0.0.0/8, ::1)
    - Private IPv4 ranges (10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16)
    - Link-local addresses (169.254.0.0/16, fe80::/10)
    - Unique local addresses (fc00::/7)
    - Common localhost hostnames
    """
    
    BLOCKED_IPS: Set[str] = {
        "127.0.0.0/8",
        "10.0.0.0/8",
        "172.16.0.0/12",
        "192.168.0.0/16",
        "169.254.0.0/16",
        "::1/128",
        "fc00::/7",
        "fe80::/10",
    }
    
    BLOCKED_DOMAINS: Set[str] = {
        "localhost",
        "localhost.localdomain",
        "ip6-localhost",
        "ip6-loopback",
        "0.0.0.0",
        "0.0.0.0.0.0.0.0",
        "::",
        "*",
    }
    
    @classmethod
    def is_safe_url(cls, url: str) -> Tuple[bool, str]:
        """
        Check if a URL is safe to access.
        
        Args:
            url: The URL to validate
            
        Returns:
            Tuple of (is_safe, error_message)
            - is_safe: True if URL is safe to access
            - error_message: Description of why URL is blocked, empty if safe
        """
        try:
            parsed = urlparse(url)
            hostname = parsed.hostname
            
            if not hostname:
                return False, "Invalid URL: no hostname"
            
            hostname_lower = hostname.lower()
            
            if hostname_lower in cls.BLOCKED_DOMAINS:
                return False, f"Blocked domain: {hostname}"
            
            for blocked in cls.BLOCKED_DOMAINS:
                if hostname_lower.endswith(f".{blocked}"):
                    return False, f"Blocked domain: {hostname}"
            
            try:
                ip = ipaddress.ip_address(hostname)
                
                for blocked_range in cls.BLOCKED_IPS:
                    network = ipaddress.ip_network(blocked_range, strict=False)
                    if ip in network:
                        return False, f"Blocked IP range: {blocked_range}"
                        
            except ValueError:
                pass
            
            if parsed.scheme not in ("http", "https"):
                return False, f"Blocked scheme: {parsed.scheme}"
            
            return True, ""
            
        except Exception as e:
            return False, f"Invalid URL: {e}"
    
    @classmethod
    def is_safe_hostname(cls, hostname: str) -> Tuple[bool, str]:
        """
        Check if a hostname is safe to resolve/connect.
        
        Args:
            hostname: The hostname to validate
            
        Returns:
            Tuple of (is_safe, error_message)
        """
        if not hostname:
            return False, "Empty hostname"
        
        hostname_lower = hostname.lower()
        
        if hostname_lower in cls.BLOCKED_DOMAINS:
            return False, f"Blocked domain: {hostname}"
        
        try:
            ip = ipaddress.ip_address(hostname)
            for blocked_range in cls.BLOCKED_IPS:
                network = ipaddress.ip_network(blocked_range, strict=False)
                if ip in network:
                    return False, f"Blocked IP range: {blocked_range}"
        except ValueError:
            pass
        
        return True, ""
