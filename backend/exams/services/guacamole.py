"""Apache Guacamole REST API client for managing RDP connections."""
import logging
import urllib.parse

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

GUAC_BASE = settings.GUACAMOLE_URL.rstrip("/")
GUAC_USER = settings.GUACAMOLE_USER
GUAC_PASS = settings.GUACAMOLE_PASSWORD


def _auth_token() -> str:
    """Get Guacamole auth token via POST /api/tokens."""
    url = f"{GUAC_BASE}/api/tokens"
    resp = requests.post(
        url,
        data={"username": GUAC_USER, "password": GUAC_PASS},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=10,
    )
    resp.raise_for_status()
    token = resp.json()["authToken"]
    return token


def create_rdp_connection(
    name, hostname, port, username, password, **kwargs
) -> str:
    """Create an RDP connection in Guacamole. Returns connection ID."""
    token = _auth_token()
    data_source = "postgresql"

    # Build connection parameters
    params = {
        "name": name,
        "protocol": "rdp",
        "parameters": {
            "hostname": hostname,
            "port": str(port),
            "username": username,
            "password": password,
            "ignore-cert": "true",
            "security": "any",
            "resize-method": "display-update",
            "enable-wallpaper": "true",
            "enable-font-smoothing": "true",
            "enable-drive": "false",
            "create-drive-path": "false",
            "enable-printing": "false",
        },
    }

    # Merge extra params
    params["parameters"].update(kwargs)

    url = f"{GUAC_BASE}/api/session/data/{data_source}/connections"
    params_qs = urllib.parse.quote(token)

    resp = requests.post(
        f"{url}?token={params_qs}",
        json=params,
        timeout=10,
    )
    resp.raise_for_status()
    connection_id = resp.json()["identifier"]
    logger.info("Created Guacamole connection %s for %s", connection_id, name)
    return str(connection_id)


def get_connection_token(connection_id: str) -> str:
    """Get a one-time connection token for a Guacamole connection."""
    token = _auth_token()
    data_source = "postgresql"

    url = (
        f"{GUAC_BASE}/api/session/data/{data_source}/connections/"
        f"{connection_id}/parameters"
    )
    params_qs = urllib.parse.quote(token)

    resp = requests.get(f"{url}?token={params_qs}", timeout=10)
    resp.raise_for_status()

    # Generate connection tunnel token
    connect_url = (
        f"{GUAC_BASE}/api/session/tunnels/{connection_id}/connection/rdp"
    )
    connect_resp = requests.post(
        f"{connect_url}?token={params_qs}",
        json={},
        timeout=10,
    )
    connect_resp.raise_for_status()
    return token


def delete_connection(connection_id: str):
    """Delete a Guacamole connection."""
    token = _auth_token()
    data_source = "postgresql"
    url = (
        f"{GUAC_BASE}/api/session/data/{data_source}/connections/"
        f"{connection_id}"
    )
    params_qs = urllib.parse.quote(token)
    resp = requests.delete(f"{url}?token={params_qs}", timeout=10)
    resp.raise_for_status()


def get_connection_url(vm_instance) -> str:
    """Get the direct Guacamole iframe URL for a VM instance.

    Creates a Guacamole connection if one doesn't exist yet.
    Returns a URL that can be embedded in an iframe.
    """
    if not vm_instance.guacamole_connection_id:
        conn_id = create_rdp_connection(
            name=f"{vm_instance.group.student.username}-{vm_instance.role_label}",
            hostname=vm_instance.private_ip,
            port=getattr(vm_instance, "rdp_port", 3389) or 3389,
            username=vm_instance.admin_username,
            password=vm_instance.admin_password,
        )
        vm_instance.guacamole_connection_id = conn_id
        vm_instance.save(update_fields=["guacamole_connection_id"])

    token = get_connection_token(vm_instance.guacamole_connection_id)
    return (
        f"/guacamole/#/client/{vm_instance.guacamole_connection_id}"
        f"?token={token}"
    )
