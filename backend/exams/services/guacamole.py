"""Apache Guacamole client for managing RDP connections.

Uses direct PostgreSQL inserts for connection creation (more reliable than
the REST API which can return opaque 500 errors on some versions).
"""
import logging
import urllib.parse

import psycopg2
import requests
from django.conf import settings

logger = logging.getLogger(__name__)

GUAC_BASE = settings.GUACAMOLE_URL.rstrip("/")
GUAC_USER = settings.GUACAMOLE_USER
GUAC_PASS = settings.GUACAMOLE_PASSWORD

# Database connection info for direct SQL operations
DB_NAME = settings.DATABASES["default"]["NAME"]
DB_USER = settings.DATABASES["default"]["USER"]
DB_PASSWORD = settings.DATABASES["default"]["PASSWORD"]
DB_HOST = settings.DATABASES["default"]["HOST"]
DB_PORT = settings.DATABASES["default"]["PORT"]


def _get_db_conn():
    return psycopg2.connect(
        dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD,
        host=DB_HOST, port=DB_PORT,
    )


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
    return resp.json()["authToken"]


def _ensure_root_group():
    """Ensure ROOT connection group exists."""
    conn = _get_db_conn()
    try:
        cur = conn.cursor()
        cur.execute("SELECT 1 FROM guacamole_connection_group WHERE connection_group_name = 'ROOT'")
        if not cur.fetchone():
            cur.execute(
                "INSERT INTO guacamole_connection_group (connection_group_name, type) "
                "VALUES ('ROOT', 'ORGANIZATIONAL') RETURNING connection_group_id"
            )
            root_id = cur.fetchone()[0]
            cur.execute(
                "INSERT INTO guacamole_connection_group_permission "
                "(entity_id, connection_group_id, permission) VALUES (1, %s, 'ADMINISTER')",
                (root_id,),
            )
            conn.commit()
            logger.info("Created ROOT connection group (id=%s)", root_id)
    finally:
        conn.close()


def create_rdp_connection(
    name, hostname, port, username, password, **kwargs
) -> str:
    """Create an RDP connection in Guacamole via direct SQL. Returns connection ID."""
    _ensure_root_group()

    conn = _get_db_conn()
    try:
        cur = conn.cursor()

        # Check if connection already exists
        cur.execute(
            "SELECT connection_id FROM guacamole_connection "
            "WHERE connection_name = %s AND parent_id = 1",
            (name,),
        )
        existing = cur.fetchone()

        if existing:
            conn_id = existing[0]
            # Update existing parameters
            cur.execute(
                "DELETE FROM guacamole_connection_parameter WHERE connection_id = %s",
                (conn_id,),
            )
        else:
            cur.execute(
                "INSERT INTO guacamole_connection (connection_name, parent_id, protocol) "
                "VALUES (%s, 1, 'rdp') RETURNING connection_id",
                (name,),
            )
            conn_id = cur.fetchone()[0]

        # Merge defaults with kwargs
        params = {
            "hostname": hostname,
            "port": str(port),
            "username": username,
            "password": password,
            "ignore-cert": "true",
            "security": "any",
            "resize-method": "display-update",
            "enable-wallpaper": "true",
            "enable-font-smoothing": "true",
            "enable-drive": "true",
            "create-drive-path": "true",
            "drive-path": "/tmp/guacamole-drive",
            "disable-upload": "false",
            "disable-download": "false",
            "enable-printing": "false",
        }
        params.update(kwargs)

        # Insert/update parameters
        for key, val in params.items():
            cur.execute(
                "INSERT INTO guacamole_connection_parameter "
                "(connection_id, parameter_name, parameter_value) VALUES (%s, %s, %s)",
                (conn_id, key, str(val)),
            )

        # Grant admin permission on the connection
        cur.execute(
            "INSERT INTO guacamole_connection_permission "
            "(entity_id, connection_id, permission) VALUES (1, %s, 'ADMINISTER') "
            "ON CONFLICT DO NOTHING",
            (conn_id,),
        )

        # Create sharing profile for scoped access
        cur.execute(
            "SELECT sharing_profile_id FROM guacamole_sharing_profile "
            "WHERE primary_connection_id = %s",
            (conn_id,),
        )
        if not cur.fetchone():
            cur.execute(
                "INSERT INTO guacamole_sharing_profile "
                "(sharing_profile_name, primary_connection_id) "
                "VALUES ('share', %s) RETURNING sharing_profile_id",
                (conn_id,),
            )
            profile_id = cur.fetchone()[0]

            cur.execute(
                "INSERT INTO guacamole_sharing_profile_parameter "
                "(sharing_profile_id, parameter_name, parameter_value) VALUES "
                "(%s, 'ftp-disable-download', 'false'),"
                "(%s, 'ftp-disable-upload', 'false')",
                (profile_id, profile_id),
            )

        conn.commit()
        action = "Updated" if existing else "Created"
        logger.info("%s Guacamole connection %s for %s", action, conn_id, name)
        return str(conn_id)
    finally:
        conn.close()


def _get_or_create_sharing_profile(conn_id: str) -> str:
    """Get or create a sharing profile for a connection."""
    conn = _get_db_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT sharing_profile_id FROM guacamole_sharing_profile "
            "WHERE primary_connection_id = %s",
            (conn_id,),
        )
        existing = cur.fetchone()
        if existing:
            return str(existing[0])

        cur.execute(
            "INSERT INTO guacamole_sharing_profile "
            "(sharing_profile_name, primary_connection_id) "
            "VALUES ('share', %s) RETURNING sharing_profile_id",
            (conn_id,),
        )
        profile_id = cur.fetchone()[0]

        cur.execute(
            "INSERT INTO guacamole_sharing_profile_parameter "
            "(sharing_profile_id, parameter_name, parameter_value) VALUES "
            "(%s, 'ftp-disable-download', 'false'),"
            "(%s, 'ftp-disable-upload', 'false')",
            (profile_id, profile_id),
        )
        conn.commit()
        return str(profile_id)
    finally:
        conn.close()


def get_connection_token(connection_id: str) -> str:
    """Get a one-time connection token for a Guacamole connection."""
    token = _auth_token()
    data_source = "postgresql"
    params_qs = urllib.parse.quote(token)

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
    """Delete a Guacamole connection via direct SQL."""
    conn = _get_db_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            "DELETE FROM guacamole_connection WHERE connection_id = %s",
            (connection_id,),
        )
        conn.commit()
    finally:
        conn.close()


def get_connection_url(vm_instance) -> str:
    """Get a Guacamole sharing link scoped to only this single connection.

    Uses the Guacamole sharing profile API to generate a token that only
    grants access to this specific connection. Other connections are not
    visible to the user.
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

    conn_id = vm_instance.guacamole_connection_id
    token = _auth_token()
    params_qs = urllib.parse.quote(token)
    profile_id = _get_or_create_sharing_profile(conn_id)

    url = (
        f"{GUAC_BASE}/api/session/data/postgresql"
        f"/connections/{conn_id}/sharingProfiles/{profile_id}/links"
    )
    resp = requests.post(
        f"{url}?token={params_qs}",
        json={},
        timeout=10,
    )
    resp.raise_for_status()
    result = resp.json()
    sharing_url = result.get("url", result.get("href", ""))
    logger.info("Generated sharing link for connection %s", conn_id)
    return sharing_url
