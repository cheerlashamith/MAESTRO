"""
Production SQLite Database Engine for AutoCourse Studio.
Provides dynamic, zero-hardcode SQL persistence for:
- IAM Roles, Permissions, Policies & User Sessions
- AI Studio Visual Graph Workflows
- Execution Job History & Telemetry
"""
from __future__ import annotations
import json
import sqlite3
import threading
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from backend.core.config import project_root

DATA_DIR = project_root() / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DATA_DIR / "autocourse.db"

_LOCAL = threading.local()

def get_connection() -> sqlite3.Connection:
    """Thread-local SQLite connection with WAL mode for high concurrency."""
    if not hasattr(_LOCAL, "connection") or _LOCAL.connection is None:
        conn = sqlite3.connect(str(DB_PATH), timeout=30.0, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        _LOCAL.connection = conn
    return _LOCAL.connection


def init_db():
    """Initializes the database schema and seeds initial records if not present."""
    conn = get_connection()
    with conn:
        # 1. IAM Roles
        conn.execute("""
            CREATE TABLE IF NOT EXISTS iam_roles (
                slug TEXT PRIMARY KEY,
                id TEXT NOT NULL,
                name TEXT NOT NULL,
                description TEXT,
                permissions_json TEXT NOT NULL DEFAULT '[]',
                scopes_json TEXT NOT NULL DEFAULT '{}',
                is_system INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL
            );
        """)

        # 2. IAM Permissions
        conn.execute("""
            CREATE TABLE IF NOT EXISTS iam_permissions (
                codename TEXT PRIMARY KEY,
                id TEXT NOT NULL,
                name TEXT NOT NULL,
                module TEXT NOT NULL,
                description TEXT
            );
        """)

        # 3. IAM Users
        conn.execute("""
            CREATE TABLE IF NOT EXISTS iam_users (
                username TEXT PRIMARY KEY,
                id TEXT NOT NULL,
                display_name TEXT NOT NULL,
                email TEXT NOT NULL,
                avatar TEXT NOT NULL,
                role_slug TEXT NOT NULL,
                department TEXT,
                portal_access_json TEXT NOT NULL DEFAULT '["user"]',
                active INTEGER NOT NULL DEFAULT 1
            );
        """)

        # 4. IAM Active Session
        conn.execute("""
            CREATE TABLE IF NOT EXISTS iam_session (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                username TEXT NOT NULL
            );
        """)

        # 5. Studio Workflows
        conn.execute("""
            CREATE TABLE IF NOT EXISTS studio_workflows (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                category TEXT,
                icon TEXT,
                status TEXT NOT NULL DEFAULT 'published',
                version TEXT NOT NULL DEFAULT '1.0.0',
                nodes_json TEXT NOT NULL,
                edges_json TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
        """)

    _seed_initial_data()


def _seed_initial_data():
    conn = get_connection()
    
    # Check if permissions exist
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) as cnt FROM iam_permissions")
    if cur.fetchone()["cnt"] == 0:
        default_perms = [
            ("workflows:view", "perm-wf-view", "View Workflows", "Studio Workflows", "View studio workflow graphs"),
            ("workflows:create", "perm-wf-create", "Create Workflows", "Studio Workflows", "Create new pipeline workflows"),
            ("workflows:edit", "perm-wf-edit", "Edit Workflows", "Studio Workflows", "Edit existing workflow node graphs"),
            ("workflows:delete", "perm-wf-delete", "Delete Workflows", "Studio Workflows", "Delete studio workflows"),
            ("workflows:execute", "perm-wf-exec", "Execute Workflows", "Studio Workflows", "Run live workflow executions"),
            ("videos:view", "perm-vid-view", "View Generated Videos", "Video Production", "View rendered videos"),
            ("videos:create", "perm-vid-create", "Generate New Videos", "Video Production", "Submit new video rendering jobs"),
            ("videos:delete", "perm-vid-delete", "Delete Videos", "Video Production", "Delete video jobs and assets"),
            ("videos:download", "perm-vid-download", "Download Video MP4", "Video Production", "Download master video files"),
            ("providers:view", "perm-prov-view", "View Provider Status", "Engines & Providers", "View AI engine health"),
            ("providers:edit", "perm-prov-edit", "Configure Engine Endpoints & Keys", "Engines & Providers", "Configure Ollama, ComfyUI, etc"),
            ("providers:test", "perm-prov-test", "Test Engine Connectivity", "Engines & Providers", "Run live connectivity diagnostics"),
            ("youtube:view", "perm-yt-view", "View YouTube Channel & Analytics", "YouTube Hub", "View channel stats"),
            ("youtube:publish", "perm-yt-publish", "Publish Videos to YouTube", "YouTube Hub", "Publish videos directly"),
            ("youtube:schedule", "perm-yt-schedule", "Schedule Future Uploads", "YouTube Hub", "Schedule future uploads"),
            ("youtube:auth", "perm-yt-auth", "Connect/Disconnect Channel OAuth", "YouTube Hub", "Manage YouTube credentials"),
            ("system:metrics", "perm-sys-metrics", "View System & Worker Metrics", "System Admin", "Inspect hardware & task metrics"),
            ("system:cache", "perm-sys-cache", "Manage Engine Cache", "System Admin", "Flush or warm system cache"),
            ("iam:manage", "perm-iam-manage", "Manage Roles & Permission Matrix", "Security & IAM", "Configure security matrix & roles")
        ]
        with conn:
            conn.executemany("""
                INSERT OR IGNORE INTO iam_permissions (codename, id, name, module, description)
                VALUES (?, ?, ?, ?, ?)
            """, default_perms)

    # Check if roles exist
    cur.execute("SELECT COUNT(*) as cnt FROM iam_roles")
    if cur.fetchone()["cnt"] == 0:
        all_perms = [
            "workflows:view", "workflows:create", "workflows:edit", "workflows:delete", "workflows:execute",
            "videos:view", "videos:create", "videos:delete", "videos:download",
            "providers:view", "providers:edit", "providers:test",
            "youtube:view", "youtube:publish", "youtube:schedule", "youtube:auth",
            "system:metrics", "system:cache", "iam:manage"
        ]
        admin_scopes = {p: {"scope": "*", "enabled": True} for p in all_perms}
        creator_perms = [
            "workflows:view", "workflows:execute",
            "videos:view", "videos:create", "videos:download",
            "youtube:view", "youtube:publish", "youtube:schedule",
            "providers:view"
        ]
        creator_scopes = {
            "workflows:view": {"scope": "*", "enabled": True},
            "workflows:execute": {"scope": "*", "enabled": True},
            "videos:view": {"scope": "user_id", "enabled": True},
            "videos:create": {"scope": "user_id", "enabled": True},
            "videos:download": {"scope": "user_id", "enabled": True},
            "youtube:view": {"scope": "*", "enabled": True},
            "youtube:publish": {"scope": "*", "enabled": True},
            "youtube:schedule": {"scope": "*", "enabled": True},
            "providers:view": {"scope": "*", "enabled": True}
        }
        reviewer_perms = ["workflows:view", "videos:view", "videos:download", "youtube:view"]
        reviewer_scopes = {p: {"scope": "*", "enabled": True} for p in reviewer_perms}

        now_iso = datetime.utcnow().isoformat()
        roles_data = [
            ("admin", "role-admin", "System Administrator", "Full unconstrained administrative access to all engines, workflows, policies, and controls.", json.dumps(all_perms), json.dumps(admin_scopes), 1, now_iso),
            ("creator", "role-creator", "Video Creator / User", "Access to create, execute, and monitor AI video generation workflows, preview videos, and publish to YouTube.", json.dumps(creator_perms), json.dumps(creator_scopes), 1, now_iso),
            ("reviewer", "role-reviewer", "Content Reviewer", "Audit and review completed videos and metadata without configuration privileges.", json.dumps(reviewer_perms), json.dumps(reviewer_scopes), 0, now_iso)
        ]
        with conn:
            conn.executemany("""
                INSERT OR IGNORE INTO iam_roles (slug, id, name, description, permissions_json, scopes_json, is_system, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, roles_data)

    # Check if users exist
    cur.execute("SELECT COUNT(*) as cnt FROM iam_users")
    if cur.fetchone()["cnt"] == 0:
        users_data = [
            ("shamith", "user-shamith", "Shamith", "shamith@autocourse.local", "SH", "creator", "Content & Media Production", '["user"]', 1),
            ("shamith_admin", "user-shamith-admin", "Shamith Admin", "admin.shamith@autocourse.local", "SA", "admin", "Enterprise AI Engineering", '["user", "admin"]', 1)
        ]
        with conn:
            conn.executemany("""
                INSERT OR IGNORE INTO iam_users (username, id, display_name, email, avatar, role_slug, department, portal_access_json, active)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, users_data)

    # Check session
    cur.execute("SELECT COUNT(*) as cnt FROM iam_session")
    if cur.fetchone()["cnt"] == 0:
        with conn:
            conn.execute("INSERT OR REPLACE INTO iam_session (id, username) VALUES (1, 'shamith')")

    # Migrate workflows from studio_workflows.json if DB is empty
    cur.execute("SELECT COUNT(*) as cnt FROM studio_workflows")
    if cur.fetchone()["cnt"] == 0:
        wf_file = DATA_DIR / "studio_workflows.json"
        if wf_file.exists():
            try:
                raw = json.loads(wf_file.read_text(encoding="utf-8"))
                with conn:
                    for wf in raw:
                        conn.execute("""
                            INSERT OR REPLACE INTO studio_workflows (id, name, description, category, icon, status, version, nodes_json, edges_json, updated_at)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            wf.get("id"),
                            wf.get("name"),
                            wf.get("description", ""),
                            wf.get("category", "YouTube Automation"),
                            wf.get("icon", "GitBranch"),
                            wf.get("status", "published"),
                            wf.get("version", "1.0.0"),
                            json.dumps(wf.get("nodes", [])),
                            json.dumps(wf.get("edges", [])),
                            datetime.utcnow().isoformat()
                        ))
            except Exception as e:
                print(f"[DB] Workflow migration warning: {e}")


# Initialize on import
init_db()


# ---------------------------------------------------------------------------
# IAM SQLite Database Access Methods
# ---------------------------------------------------------------------------

class Database:
    @staticmethod
    def get_roles() -> List[Dict[str, Any]]:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM iam_roles ORDER BY is_system DESC, name ASC")
        rows = cur.fetchall()
        result = []
        for r in rows:
            result.append({
                "slug": r["slug"],
                "id": r["id"],
                "name": r["name"],
                "description": r["description"],
                "permissions": json.loads(r["permissions_json"]),
                "scopes": json.loads(r["scopes_json"]),
                "is_system": bool(r["is_system"]),
                "created_at": r["created_at"]
            })
        return result

    @staticmethod
    def get_role_by_slug(slug: str) -> Optional[Dict[str, Any]]:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM iam_roles WHERE slug = ?", (slug,))
        r = cur.fetchone()
        if not r:
            return None
        return {
            "slug": r["slug"],
            "id": r["id"],
            "name": r["name"],
            "description": r["description"],
            "permissions": json.loads(r["permissions_json"]),
            "scopes": json.loads(r["scopes_json"]),
            "is_system": bool(r["is_system"]),
            "created_at": r["created_at"]
        }

    @staticmethod
    def create_role(name: str, slug: str, description: str, permissions: List[str], scopes: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) as cnt FROM iam_roles WHERE slug = ?", (slug,))
        if cur.fetchone()["cnt"] > 0:
            raise ValueError(f"Role with slug '{slug}' already exists in database.")
        
        role_id = f"role-{uuid.uuid4().hex[:8]}"
        created_at = datetime.utcnow().isoformat()
        with conn:
            conn.execute("""
                INSERT INTO iam_roles (slug, id, name, description, permissions_json, scopes_json, is_system, created_at)
                VALUES (?, ?, ?, ?, ?, ?, 0, ?)
            """, (slug, role_id, name, description, json.dumps(permissions), json.dumps(scopes or {}), created_at))

        return {
            "slug": slug,
            "id": role_id,
            "name": name,
            "description": description,
            "permissions": permissions,
            "scopes": scopes or {},
            "is_system": False,
            "created_at": created_at
        }

    @staticmethod
    def update_role_permissions(slug: str, permissions: List[str], scopes: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM iam_roles WHERE slug = ?", (slug,))
        r = cur.fetchone()
        if not r:
            raise ValueError(f"Role '{slug}' not found in database.")

        scopes_json = json.dumps(scopes) if scopes is not None else r["scopes_json"]
        with conn:
            conn.execute("""
                UPDATE iam_roles 
                SET permissions_json = ?, scopes_json = ?
                WHERE slug = ?
            """, (json.dumps(permissions), scopes_json, slug))

        return Database.get_role_by_slug(slug)

    @staticmethod
    def delete_role(slug: str) -> bool:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT is_system FROM iam_roles WHERE slug = ?", (slug,))
        r = cur.fetchone()
        if not r or r["is_system"]:
            return False
        with conn:
            conn.execute("DELETE FROM iam_roles WHERE slug = ?", (slug,))
        return True

    @staticmethod
    def get_permissions() -> List[Dict[str, Any]]:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM iam_permissions ORDER BY module ASC, name ASC")
        return [dict(r) for r in cur.fetchall()]

    @staticmethod
    def get_users() -> List[Dict[str, Any]]:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM iam_users ORDER BY display_name ASC")
        rows = cur.fetchall()
        result = []
        for r in rows:
            result.append({
                "username": r["username"],
                "id": r["id"],
                "display_name": r["display_name"],
                "email": r["email"],
                "avatar": r["avatar"],
                "role_slug": r["role_slug"],
                "department": r["department"],
                "portal_access": json.loads(r["portal_access_json"]),
                "active": bool(r["active"])
            })
        return result

    @staticmethod
    def get_current_user() -> Dict[str, Any]:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT username FROM iam_session WHERE id = 1")
        sess = cur.fetchone()
        username = sess["username"] if sess else "shamith"
        
        cur.execute("SELECT * FROM iam_users WHERE username = ?", (username,))
        u = cur.fetchone()
        if not u:
            # Fallback
            cur.execute("SELECT * FROM iam_users LIMIT 1")
            u = cur.fetchone()

        role = Database.get_role_by_slug(u["role_slug"])
        return {
            "username": u["username"],
            "id": u["id"],
            "display_name": u["display_name"],
            "email": u["email"],
            "avatar": u["avatar"],
            "role_slug": u["role_slug"],
            "department": u["department"],
            "portal_access": json.loads(u["portal_access_json"]),
            "active": bool(u["active"]),
            "role_details": role
        }

    @staticmethod
    def switch_user(username: str) -> Dict[str, Any]:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT username FROM iam_users WHERE username = ?", (username,))
        if not cur.fetchone():
            raise ValueError(f"User '{username}' not found in database.")
        with conn:
            conn.execute("INSERT OR REPLACE INTO iam_session (id, username) VALUES (1, ?)", (username,))
        return Database.get_current_user()

    # -----------------------------------------------------------------------
    # Studio Workflows SQLite Methods
    # -----------------------------------------------------------------------
    @staticmethod
    def get_workflows() -> List[Dict[str, Any]]:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM studio_workflows ORDER BY name ASC")
        rows = cur.fetchall()
        result = []
        for r in rows:
            result.append({
                "id": r["id"],
                "name": r["name"],
                "description": r["description"],
                "category": r["category"],
                "icon": r["icon"],
                "status": r["status"],
                "version": r["version"],
                "nodes": json.loads(r["nodes_json"]),
                "edges": json.loads(r["edges_json"]),
                "updated_at": r["updated_at"]
            })
        return result

    @staticmethod
    def get_workflow(workflow_id: str) -> Optional[Dict[str, Any]]:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM studio_workflows WHERE id = ?", (workflow_id,))
        r = cur.fetchone()
        if not r:
            return None
        return {
            "id": r["id"],
            "name": r["name"],
            "description": r["description"],
            "category": r["category"],
            "icon": r["icon"],
            "status": r["status"],
            "version": r["version"],
            "nodes": json.loads(r["nodes_json"]),
            "edges": json.loads(r["edges_json"]),
            "updated_at": r["updated_at"]
        }

    @staticmethod
    def save_workflow(data: Dict[str, Any]) -> Dict[str, Any]:
        conn = get_connection()
        wf_id = data.get("id") or f"wf-{uuid.uuid4().hex[:8]}"
        now_iso = datetime.utcnow().isoformat()
        with conn:
            conn.execute("""
                INSERT OR REPLACE INTO studio_workflows (id, name, description, category, icon, status, version, nodes_json, edges_json, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                wf_id,
                data.get("name", "Untitled Pipeline"),
                data.get("description", ""),
                data.get("category", "YouTube Automation"),
                data.get("icon", "GitBranch"),
                data.get("status", "published"),
                data.get("version", "1.0.0"),
                json.dumps(data.get("nodes", [])),
                json.dumps(data.get("edges", [])),
                now_iso
            ))
        return Database.get_workflow(wf_id)

    @staticmethod
    def delete_workflow(workflow_id: str) -> bool:
        conn = get_connection()
        with conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM studio_workflows WHERE id = ?", (workflow_id,))
            return cur.rowcount > 0
