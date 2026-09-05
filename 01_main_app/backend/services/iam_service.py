"""
Enterprise Identity & Access Management (IAM) Service for AutoCourse Studio.
Inspired by sasi-erp microservices/IAM architecture.

Manages:
- Dynamic Role-Based Access Control (RBAC) & Attribute-Based Scopes (ABAC)
- Dynamic Permission Matrix (resource:action mapping)
- User Profiles & Active Session Switching
- JSON-backed file persistence (ready to plug SQLite/PostgreSQL later)
"""
from __future__ import annotations
import json
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional
from pydantic import BaseModel
from backend.core.config import project_root

DATA_DIR = project_root() / "data"
ROLES_FILE = DATA_DIR / "iam_roles.json"
PERMISSIONS_FILE = DATA_DIR / "iam_permissions.json"
USERS_FILE = DATA_DIR / "iam_users.json"
CURRENT_USER_FILE = DATA_DIR / "current_user.json"

DATA_DIR.mkdir(parents=True, exist_ok=True)

# Default Permissions Definition
DEFAULT_PERMISSIONS: List[Dict[str, Any]] = [
    # Workflows
    {"id": "perm-wf-view", "codename": "workflows:view", "name": "View Workflows", "module": "Studio Workflows"},
    {"id": "perm-wf-create", "codename": "workflows:create", "name": "Create Workflows", "module": "Studio Workflows"},
    {"id": "perm-wf-edit", "codename": "workflows:edit", "name": "Edit Workflows", "module": "Studio Workflows"},
    {"id": "perm-wf-delete", "codename": "workflows:delete", "name": "Delete Workflows", "module": "Studio Workflows"},
    {"id": "perm-wf-exec", "codename": "workflows:execute", "name": "Execute Workflows", "module": "Studio Workflows"},

    # Videos & Jobs
    {"id": "perm-vid-view", "codename": "videos:view", "name": "View Generated Videos", "module": "Video Production"},
    {"id": "perm-vid-create", "codename": "videos:create", "name": "Generate New Videos", "module": "Video Production"},
    {"id": "perm-vid-delete", "codename": "videos:delete", "name": "Delete Videos", "module": "Video Production"},
    {"id": "perm-vid-download", "codename": "videos:download", "name": "Download Video MP4", "module": "Video Production"},

    # Providers & Engines
    {"id": "perm-prov-view", "codename": "providers:view", "name": "View Provider Status", "module": "Engines & Providers"},
    {"id": "perm-prov-edit", "codename": "providers:edit", "name": "Configure Engine Endpoints & Keys", "module": "Engines & Providers"},
    {"id": "perm-prov-test", "codename": "providers:test", "name": "Test Engine Connectivity", "module": "Engines & Providers"},

    # YouTube Publishing
    {"id": "perm-yt-view", "codename": "youtube:view", "name": "View YouTube Channel & Analytics", "module": "YouTube Hub"},
    {"id": "perm-yt-publish", "codename": "youtube:publish", "name": "Publish Videos to YouTube", "module": "YouTube Hub"},
    {"id": "perm-yt-schedule", "codename": "youtube:schedule", "name": "Schedule Future Uploads", "module": "YouTube Hub"},
    {"id": "perm-yt-auth", "codename": "youtube:auth", "name": "Connect/Disconnect Channel OAuth", "module": "YouTube Hub"},

    # System & IAM
    {"id": "perm-sys-metrics", "codename": "system:metrics", "name": "View System & Worker Metrics", "module": "System Admin"},
    {"id": "perm-sys-cache", "codename": "system:cache", "name": "Manage Engine Cache", "module": "System Admin"},
    {"id": "perm-iam-manage", "codename": "iam:manage", "name": "Manage Roles & Permission Matrix", "module": "Security & IAM"},
]

DEFAULT_ROLES: List[Dict[str, Any]] = [
    {
        "id": "role-admin",
        "name": "System Administrator",
        "slug": "admin",
        "description": "Full unconstrained administrative access to all engines, workflows, policies, and system controls.",
        "permissions": [p["codename"] for p in DEFAULT_PERMISSIONS],
        "scopes": {p["codename"]: {"scope": "*", "enabled": True} for p in DEFAULT_PERMISSIONS},
        "is_system": True,
    },
    {
        "id": "role-creator",
        "name": "Video Creator / User",
        "slug": "creator",
        "description": "Access to create, execute, and monitor AI video generation workflows, preview videos, and publish to YouTube.",
        "permissions": [
            "workflows:view", "workflows:execute",
            "videos:view", "videos:create", "videos:download",
            "youtube:view", "youtube:publish", "youtube:schedule",
            "providers:view"
        ],
        "scopes": {
            "workflows:view": {"scope": "*", "enabled": True},
            "workflows:execute": {"scope": "*", "enabled": True},
            "videos:view": {"scope": "user_id", "enabled": True},
            "videos:create": {"scope": "user_id", "enabled": True},
            "videos:download": {"scope": "user_id", "enabled": True},
            "youtube:view": {"scope": "*", "enabled": True},
            "youtube:publish": {"scope": "*", "enabled": True},
            "youtube:schedule": {"scope": "*", "enabled": True},
            "providers:view": {"scope": "*", "enabled": True},
        },
        "is_system": True,
    },
    {
        "id": "role-reviewer",
        "name": "Content Reviewer",
        "slug": "reviewer",
        "description": "Audit and review completed videos and metadata without configuration or generation privileges.",
        "permissions": ["workflows:view", "videos:view", "videos:download", "youtube:view"],
        "scopes": {
            "workflows:view": {"scope": "*", "enabled": True},
            "videos:view": {"scope": "*", "enabled": True},
            "videos:download": {"scope": "*", "enabled": True},
            "youtube:view": {"scope": "*", "enabled": True},
        },
        "is_system": False,
    }
]

DEFAULT_USERS: List[Dict[str, Any]] = [
    {
        "id": "user-shamith",
        "username": "shamith",
        "display_name": "Shamith",
        "email": "shamith@autocourse.local",
        "avatar": "SH",
        "role_slug": "creator",
        "department": "Content & Media Production",
        "portal_access": ["user"],
        "active": True,
    },
    {
        "id": "user-shamith-admin",
        "username": "shamith_admin",
        "display_name": "Shamith Admin",
        "email": "admin.shamith@autocourse.local",
        "avatar": "SA",
        "role_slug": "admin",
        "department": "Enterprise AI Engineering",
        "portal_access": ["user", "admin"],
        "active": True,
    }
]


def _read_json(path: Path, default: Any) -> Any:
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return default
    return default


def _write_json(path: Path, data: Any):
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def ensure_iam_initialized():
    """Seed default permissions, roles, and user accounts if not present."""
    if not PERMISSIONS_FILE.exists():
        _write_json(PERMISSIONS_FILE, DEFAULT_PERMISSIONS)
    if not ROLES_FILE.exists():
        _write_json(ROLES_FILE, DEFAULT_ROLES)
    if not USERS_FILE.exists():
        _write_json(USERS_FILE, DEFAULT_USERS)
    if not CURRENT_USER_FILE.exists():
        _write_json(CURRENT_USER_FILE, {"username": "shamith", "role_slug": "creator"})


# Ensure initialization on module load
ensure_iam_initialized()


from backend.core.db import Database


class IAMService:
    @classmethod
    def get_permissions(cls) -> List[Dict[str, Any]]:
        return Database.get_permissions()

    @classmethod
    def get_roles(cls) -> List[Dict[str, Any]]:
        return Database.get_roles()

    @classmethod
    def get_role_by_slug(cls, slug: str) -> Optional[Dict[str, Any]]:
        return Database.get_role_by_slug(slug)

    @classmethod
    def update_role_permissions(cls, role_slug: str, permissions: List[str], scopes: Optional[Dict[str, Any]] = None):
        return Database.update_role_permissions(role_slug, permissions, scopes)

    @classmethod
    def create_role(cls, name: str, slug: str, description: str, permissions: List[str], scopes: Optional[Dict[str, Any]] = None):
        return Database.create_role(name, slug, description, permissions, scopes)

    @classmethod
    def delete_role(cls, slug: str) -> bool:
        return Database.delete_role(slug)

    @classmethod
    def get_users(cls) -> List[Dict[str, Any]]:
        return Database.get_users()

    @classmethod
    def get_current_user(cls) -> Dict[str, Any]:
        return Database.get_current_user()

    @classmethod
    def switch_user(cls, username: str) -> Dict[str, Any]:
        return Database.switch_user(username)

    @classmethod
    def get_permission_matrix(cls) -> Dict[str, Any]:
        """Returns the full permission matrix format matching sasi-erp PermissionMatrix component."""
        permissions = cls.get_permissions()
        roles = cls.get_roles()
        
        # Group permissions by module
        modules: Dict[str, List[Dict[str, Any]]] = {}
        for p in permissions:
            mod = p.get("module", "General")
            if mod not in modules:
                modules[mod] = []
            modules[mod].append(p)

        return {
            "permissions": permissions,
            "modules": modules,
            "roles": roles,
            "access_options": [
                {"value": "*", "label": "Full Access (*)"},
                {"value": "user_id", "label": "Self Only (user_id)"},
                {"value": "department_id", "label": "Department Only"},
            ]
        }
