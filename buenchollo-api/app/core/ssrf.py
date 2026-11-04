import ipaddress
import socket
import urllib.parse


_EXTRA_BLOCKED = (
    ipaddress.ip_network("100.64.0.0/10"),  # CGNAT (Tailscale)
    ipaddress.ip_network("192.0.0.0/24"),  # IETF protocol assignments
)


def _is_blocked(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    if not ip.is_global or ip.is_multicast:
        return True
    return isinstance(ip, ipaddress.IPv4Address) and any(ip in net for net in _EXTRA_BLOCKED)


def resolves_to_private_ip(url: str) -> bool:
    """True si el host del URL resuelve a una IP privada/loopback/reservada.

    Bloqueo SSRF: evita que un atacante engañe el resolver para tocar
    servicios internos del NAS (192.168.x.x, 10.x.x.x, 127.0.0.1).
    """
    try:
        parsed = urllib.parse.urlparse(url)
        host = parsed.hostname
        if not host:
            return True  # rechazar por defecto si no podemos analizar
        for family, _type, _proto, _canon, sockaddr in socket.getaddrinfo(host, None):
            ip = ipaddress.ip_address(sockaddr[0])
            if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped:
                ip = ip.ipv4_mapped
            if _is_blocked(ip):
                return True
    except (socket.gaierror, ValueError, OSError):
        return True  # si el DNS falla, rechazamos por defecto
    return False
