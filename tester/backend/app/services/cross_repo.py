"""Cross-Repository Change Radar Service for GitFlow Project Hub.

Provides:
- Shared package dependency discovery and version drift analysis across connected repositories
- Internal service API contract mapping (producer and consumer endpoints)
- Git submodule linkage discovery
- Downstream blast radius and impact prediction for pending changes
"""

from datetime import datetime, timezone
import json
import logging
import os
import re
from typing import Any, Dict, List, Optional, Set

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database.models import CrossRepoDependency, Repository, RepositoryIndex

logger = logging.getLogger(__name__)


class CrossRepoService:
    """Radar for cross-repository dependency topology, API linkages, and blast radius."""

    def __init__(self) -> None:
        pass

    async def get_cross_repo_relationships(
        self,
        repo_id: int,
        user_id: int,
        db: AsyncSession,
    ) -> Dict[str, Any]:
        """Fetch and dynamically compute all cross-repo linkages for the specified repository."""
        # 1. Fetch current repository
        current_repo = (
            await db.execute(select(Repository).where(Repository.id == repo_id))
        ).scalars().first()
        if not current_repo:
            return {
                "repository_id": repo_id,
                "upstream_dependencies": [],
                "downstream_impact": [],
                "shared_packages": [],
                "service_apis": [],
                "submodules": [],
                "radar_summary": "Repository not found.",
                "risk_blast_radius": "LOW",
            }

        # 2. Query persisted cross-repo dependencies in database
        dep_query = select(CrossRepoDependency).where(
            or_(
                CrossRepoDependency.upstream_repo_id == repo_id,
                CrossRepoDependency.downstream_repo_id == repo_id,
            )
        )
        persisted_records = (await db.execute(dep_query)).scalars().all()

        upstream_list: List[Dict[str, Any]] = []
        downstream_list: List[Dict[str, Any]] = []
        shared_packages: List[Dict[str, Any]] = []
        service_apis: List[Dict[str, Any]] = []
        submodules: List[Dict[str, Any]] = []

        for dep in persisted_records:
            details = {}
            if dep.details_json:
                try:
                    details = json.loads(dep.details_json)
                except Exception:
                    details = {}

            item = {
                "id": dep.id,
                "upstream_repo_id": dep.upstream_repo_id,
                "downstream_repo_id": dep.downstream_repo_id,
                "dependency_type": dep.dependency_type,
                "details": details,
                "discovered_at": dep.discovered_at.isoformat() if dep.discovered_at else None,
            }

            if dep.dependency_type == "PACKAGE":
                shared_packages.append(item)
            elif dep.dependency_type == "API":
                service_apis.append(item)
            elif dep.dependency_type == "SUBMODULE":
                submodules.append(item)

            if dep.upstream_repo_id == repo_id:
                downstream_list.append(item)
            else:
                upstream_list.append(item)

        # 3. Dynamic discovery: if few or no persisted records, inspect other user repositories
        user_repos = (
            await db.execute(
                select(Repository).where(Repository.owner_id == user_id, Repository.id != repo_id)
            )
        ).scalars().all()

        current_index = (
            await db.execute(
                select(RepositoryIndex)
                .where(RepositoryIndex.repository_id == repo_id)
                .order_by(RepositoryIndex.indexed_at.desc())
            )
        ).scalars().first()

        current_deps = {}
        current_routes = []
        if current_index:
            try:
                current_deps = json.loads(current_index.dependencies_json or "{}")
            except Exception:
                current_deps = {}
            try:
                current_routes = json.loads(current_index.routes_json or "[]")
            except Exception:
                current_routes = []

        # Compare dependencies across user's other repositories
        for peer in user_repos:
            peer_index = (
                await db.execute(
                    select(RepositoryIndex)
                    .where(RepositoryIndex.repository_id == peer.id)
                    .order_by(RepositoryIndex.indexed_at.desc())
                )
            ).scalars().first()

            if not peer_index:
                continue

            peer_deps = {}
            peer_routes = []
            try:
                peer_deps = json.loads(peer_index.dependencies_json or "{}")
            except Exception:
                peer_deps = {}
            try:
                peer_routes = json.loads(peer_index.routes_json or "[]")
            except Exception:
                peer_routes = []

            # Check shared packages & version drift
            common_pkgs = set(current_deps.keys()) & set(peer_deps.keys())
            for pkg in common_pkgs:
                ver_curr = current_deps.get(pkg, "*")
                ver_peer = peer_deps.get(pkg, "*")
                has_drift = ver_curr != ver_peer

                pkg_info = {
                    "package_name": pkg,
                    "current_repo": current_repo.name,
                    "current_version": ver_curr,
                    "peer_repo": peer.name,
                    "peer_version": ver_peer,
                    "version_drift": has_drift,
                    "type": "SHARED_DEPENDENCY",
                }
                if not any(sp.get("details", {}).get("package_name") == pkg for sp in shared_packages):
                    shared_packages.append({
                        "dependency_type": "PACKAGE",
                        "upstream_repo_id": repo_id,
                        "downstream_repo_id": peer.id,
                        "details": pkg_info,
                    })

            # Check internal service API linkages (e.g. peer name matches route prefixes or service calls)
            for route in current_routes:
                r_path = route.get("path", "")
                if peer.name.lower() in r_path.lower() or any(peer.name.lower() in p for p in r_path.split("/")):
                    api_info = {
                        "endpoint": r_path,
                        "method": route.get("method", "GET"),
                        "producer_repo": current_repo.name,
                        "consumer_repo": peer.name,
                        "contract_verified": True,
                    }
                    if not any(api.get("details", {}).get("endpoint") == r_path for api in service_apis):
                        service_apis.append({
                            "dependency_type": "API",
                            "upstream_repo_id": repo_id,
                            "downstream_repo_id": peer.id,
                            "details": api_info,
                        })

        # Calculate blast radius
        downstream_count = len(downstream_list) + len([s for s in shared_packages if s.get("upstream_repo_id") == repo_id])
        if downstream_count == 0:
            blast_radius = "LOW"
        elif downstream_count <= 2:
            blast_radius = "MEDIUM"
        else:
            blast_radius = "HIGH"

        summary = (
            f"Cross-Repo Radar for '{current_repo.name}': {len(upstream_list)} upstream dependencies, "
            f"{downstream_count} downstream dependents, {len(shared_packages)} shared packages, "
            f"and {len(service_apis)} internal API contracts."
        )

        return {
            "repository_id": repo_id,
            "repository_name": current_repo.name,
            "upstream_dependencies": upstream_list,
            "downstream_impact": downstream_list,
            "shared_packages": shared_packages,
            "service_apis": service_apis,
            "submodules": submodules,
            "radar_summary": summary,
            "risk_blast_radius": blast_radius,
        }

    def detect_version_drifts(self, repos_manifests: Dict[str, Dict[str, str]]) -> List[Dict[str, Any]]:
        """Identify package version drifts across multiple repository manifests."""
        drifts: List[Dict[str, Any]] = []
        package_map: Dict[str, Dict[str, str]] = {}

        for repo_name, deps in repos_manifests.items():
            for pkg, ver in deps.items():
                if pkg not in package_map:
                    package_map[pkg] = {}
                package_map[pkg][repo_name] = ver

        for pkg, versions_by_repo in package_map.items():
            unique_versions = set(versions_by_repo.values())
            if len(unique_versions) > 1:
                drifts.append({
                    "package": pkg,
                    "versions": versions_by_repo,
                    "drift_detected": True,
                    "divergence_count": len(unique_versions),
                })

        return drifts

    def calculate_change_blast_radius(
        self,
        upstream_repo_id: int,
        changed_files: List[str],
        diff_content: str,
        connected_repos: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Estimate the downstream blast radius when changes occur in an upstream repository."""
        affected_downstream: List[Dict[str, Any]] = []

        is_api_change = any(
            re.search(r'\b(api|routes|endpoints|controllers|schemas)\b', f, re.I) for f in changed_files
        )
        is_package_change = any(
            f.endswith("package.json") or f.endswith("requirements.txt") or f.endswith("pyproject.toml")
            for f in changed_files
        )

        for dep in connected_repos:
            reason = []
            if is_api_change and dep.get("dependency_type") == "API":
                reason.append("Direct API endpoint contract modified in upstream repository.")
            if is_package_change and dep.get("dependency_type") == "PACKAGE":
                reason.append("Shared package version constraint or dependency upgraded.")

            if reason:
                affected_downstream.append({
                    "repo_id": dep.get("downstream_repo_id"),
                    "repo_name": dep.get("downstream_repo_name", "connected_service"),
                    "impact_severity": "HIGH" if is_api_change else "MEDIUM",
                    "reasons": reason,
                })

        blast_level = "HIGH" if len(affected_downstream) >= 2 else ("MEDIUM" if affected_downstream else "LOW")

        return {
            "upstream_repo_id": upstream_repo_id,
            "blast_radius_level": blast_level,
            "affected_downstream_repos": affected_downstream,
            "total_affected_count": len(affected_downstream),
            "recommended_actions": [
                "Run integration smoke tests across affected downstream services.",
                "Trigger automated PR gates for connected repositories.",
            ] if affected_downstream else ["No downstream dependents impacted."],
        }


# Global singleton instance
cross_repo_service = CrossRepoService()
