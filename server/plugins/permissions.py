"""
Dione AI — Permission Manager

Manages plugin permissions with grant/revoke, audit logging,
and risk-tier enforcement. Inspired by OpenClaw's security model.

Permission flow:
  1. Plugin declares required_permissions in manifest
  2. On first load, user is prompted to grant permissions
  3. Permissions are stored persistently in data/permissions.json
  4. Every tool call checks permissions via the manager
  5. All checks are audit-logged
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Optional
from loguru import logger

from server.plugins.types import (
    Permission, PermissionLevel, PERMISSION_LEVELS,
    PermissionGrant, PermissionAuditEntry,
)


class PermissionManager:
    """
    Central permission authority for the Dione plugin system.
    
    Features:
      - Grant/revoke permissions per plugin
      - Risk-tier classification
      - Persistent storage
      - Full audit trail
      - Expiring grants
      - Batch operations
    """
    
    def __init__(self, data_dir: str = "data"):
        self._data_dir = Path(data_dir)
        self._data_dir.mkdir(parents=True, exist_ok=True)
        self._grants_file = self._data_dir / "permissions.json"
        self._audit_file = self._data_dir / "permission_audit.jsonl"
        
        # {plugin_id: {permission: PermissionGrant}}
        self._grants: dict[str, dict[Permission, PermissionGrant]] = {}
        self._audit_log: list[PermissionAuditEntry] = []
        
        self._load_grants()
    
    # ─── Core Operations ─────────────────────────────────────
    
    def grant(
        self,
        plugin_id: str,
        permission: Permission,
        granted_by: str = "user",
        reason: str = "",
        expires_at: Optional[datetime] = None,
    ) -> PermissionGrant:
        """Grant a permission to a plugin."""
        grant = PermissionGrant(
            plugin_id=plugin_id,
            permission=permission,
            granted=True,
            granted_at=datetime.now(),
            granted_by=granted_by,
            expires_at=expires_at,
            reason=reason,
        )
        
        if plugin_id not in self._grants:
            self._grants[plugin_id] = {}
        self._grants[plugin_id][permission] = grant
        
        self._audit("grant", plugin_id, permission, True, reason)
        self._save_grants()
        
        level = PERMISSION_LEVELS.get(permission, PermissionLevel.SAFE)
        logger.info(
            f"Permission granted: {plugin_id} → {permission.value} "
            f"(level={level.value}, by={granted_by})"
        )
        return grant
    
    def revoke(self, plugin_id: str, permission: Permission, reason: str = "") -> None:
        """Revoke a permission from a plugin."""
        if plugin_id in self._grants:
            self._grants[plugin_id].pop(permission, None)
        
        self._audit("revoke", plugin_id, permission, True, reason)
        self._save_grants()
        logger.info(f"Permission revoked: {plugin_id} → {permission.value}")
    
    def check(self, plugin_id: str, permission: Permission) -> bool:
        """
        Check if a plugin has a specific permission.
        
        Returns True if granted and not expired.
        """
        grant = self._grants.get(plugin_id, {}).get(permission)
        
        if grant is None or not grant.granted:
            self._audit("denied", plugin_id, permission, False, "not granted")
            return False
        
        # Check expiration
        if grant.expires_at and datetime.now() > grant.expires_at:
            self._audit("denied", plugin_id, permission, False, "expired")
            self.revoke(plugin_id, permission, "expired")
            return False
        
        self._audit("check", plugin_id, permission, True)
        return True
    
    def check_multiple(
        self, plugin_id: str, permissions: list[Permission]
    ) -> dict[Permission, bool]:
        """Check multiple permissions at once."""
        return {p: self.check(plugin_id, p) for p in permissions}
    
    def require(self, plugin_id: str, permission: Permission) -> None:
        """Require a permission — raises if not granted."""
        if not self.check(plugin_id, permission):
            raise PermissionError(
                f"Plugin '{plugin_id}' requires '{permission.value}' permission "
                f"but it has not been granted."
            )
    
    # ─── Batch Operations ────────────────────────────────────
    
    def grant_all(
        self,
        plugin_id: str,
        permissions: list[Permission],
        granted_by: str = "user",
    ) -> list[PermissionGrant]:
        """Grant multiple permissions at once."""
        return [
            self.grant(plugin_id, p, granted_by=granted_by)
            for p in permissions
        ]
    
    def revoke_all(self, plugin_id: str) -> int:
        """Revoke all permissions for a plugin."""
        count = len(self._grants.get(plugin_id, {}))
        self._grants.pop(plugin_id, None)
        self._save_grants()
        logger.info(f"All permissions revoked for {plugin_id} ({count} grants)")
        return count
    
    # ─── Query Operations ────────────────────────────────────
    
    def get_plugin_permissions(self, plugin_id: str) -> list[PermissionGrant]:
        """Get all granted permissions for a plugin."""
        return list(self._grants.get(plugin_id, {}).values())
    
    def get_plugins_with_permission(self, permission: Permission) -> list[str]:
        """Get all plugins that have a specific permission."""
        return [
            pid for pid, perms in self._grants.items()
            if permission in perms and perms[permission].granted
        ]
    
    def get_pending_requests(self, plugin_id: str, required: list[Permission]) -> list[Permission]:
        """Get permissions that a plugin needs but doesn't have."""
        return [p for p in required if not self.check(plugin_id, p)]
    
    def get_risk_summary(self) -> dict:
        """Get a risk-level summary of all granted permissions."""
        summary = {level.value: [] for level in PermissionLevel}
        
        for plugin_id, perms in self._grants.items():
            for permission, grant in perms.items():
                if grant.granted:
                    level = PERMISSION_LEVELS.get(permission, PermissionLevel.SAFE)
                    summary[level.value].append({
                        "plugin": plugin_id,
                        "permission": permission.value,
                    })
        
        return summary
    
    # ─── Audit ───────────────────────────────────────────────
    
    def get_audit_log(self, limit: int = 100, plugin_id: Optional[str] = None) -> list[dict]:
        """Get recent audit log entries."""
        entries = self._audit_log
        if plugin_id:
            entries = [e for e in entries if e.plugin_id == plugin_id]
        return [
            {
                "timestamp": e.timestamp.isoformat(),
                "plugin_id": e.plugin_id,
                "permission": e.permission.value,
                "action": e.action,
                "result": e.result,
                "context": e.context,
            }
            for e in entries[-limit:]
        ]
    
    # ─── Persistence ─────────────────────────────────────────
    
    def _save_grants(self) -> None:
        """Save grants to disk."""
        data = {}
        for plugin_id, perms in self._grants.items():
            data[plugin_id] = {
                p.value: {
                    "granted": g.granted,
                    "granted_at": g.granted_at.isoformat(),
                    "granted_by": g.granted_by,
                    "expires_at": g.expires_at.isoformat() if g.expires_at else None,
                    "reason": g.reason,
                }
                for p, g in perms.items()
            }
        
        self._grants_file.write_text(json.dumps(data, indent=2))
    
    def _load_grants(self) -> None:
        """Load grants from disk."""
        if not self._grants_file.exists():
            return
        
        try:
            data = json.loads(self._grants_file.read_text())
            for plugin_id, perms in data.items():
                self._grants[plugin_id] = {}
                for perm_str, grant_data in perms.items():
                    try:
                        permission = Permission(perm_str)
                        self._grants[plugin_id][permission] = PermissionGrant(
                            plugin_id=plugin_id,
                            permission=permission,
                            granted=grant_data["granted"],
                            granted_at=datetime.fromisoformat(grant_data["granted_at"]),
                            granted_by=grant_data.get("granted_by", "user"),
                            expires_at=(
                                datetime.fromisoformat(grant_data["expires_at"])
                                if grant_data.get("expires_at")
                                else None
                            ),
                            reason=grant_data.get("reason", ""),
                        )
                    except (ValueError, KeyError) as e:
                        logger.warning(f"Skipping invalid grant: {perm_str} → {e}")
            
            total = sum(len(p) for p in self._grants.values())
            logger.info(f"Loaded {total} permission grants from disk")
            
        except Exception as e:
            logger.error(f"Failed to load permissions: {e}")
    
    def _audit(
        self,
        action: str,
        plugin_id: str,
        permission: Permission,
        result: bool,
        context: str = "",
    ) -> None:
        """Record an audit log entry."""
        entry = PermissionAuditEntry(
            timestamp=datetime.now(),
            plugin_id=plugin_id,
            permission=permission,
            action=action,
            result=result,
            context=context,
        )
        self._audit_log.append(entry)
        
        # Append to audit file
        try:
            with open(self._audit_file, "a") as f:
                f.write(json.dumps({
                    "timestamp": entry.timestamp.isoformat(),
                    "plugin_id": entry.plugin_id,
                    "permission": entry.permission.value,
                    "action": entry.action,
                    "result": entry.result,
                    "context": entry.context,
                }) + "\n")
        except Exception:
            pass  # Non-critical
    
    # ─── Info ────────────────────────────────────────────────
    
    def to_dict(self) -> dict:
        """Serialize the full permission state."""
        return {
            "total_plugins": len(self._grants),
            "total_grants": sum(len(p) for p in self._grants.values()),
            "grants": {
                pid: [
                    {
                        "permission": p.value,
                        "level": PERMISSION_LEVELS.get(p, PermissionLevel.SAFE).value,
                        "granted_at": g.granted_at.isoformat(),
                        "granted_by": g.granted_by,
                    }
                    for p, g in perms.items()
                ]
                for pid, perms in self._grants.items()
            },
            "risk_summary": self.get_risk_summary(),
        }
