import ipaddress
import socket
import urllib.parse


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
            if ip.is_private or ip.is_loopback or ip.is_reserved or ip.is_link_local:
                return True
    except (socket.gaierror, ValueError, OSError):
        return True  # si el DNS falla, rechazamos por defecto
    return False
