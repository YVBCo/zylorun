"""GitFlow Project Hub Analyzers Suite.

Provides unified registry and interface for all 10 code, security,
contract, architecture, database, deployment, and accessibility analyzers.
"""

from app.analyzers.base import BaseAnalyzer
from app.analyzers.dna import RepositoryDNAAnalyzer
from app.analyzers.security import SecurityAnalyzer
from app.analyzers.impact import ChangeImpactAnalyzer
from app.analyzers.test_intel import TestIntelligenceAnalyzer
from app.analyzers.quality import CodeQualityAnalyzer
from app.analyzers.api_contract import ApiContractAnalyzer
from app.analyzers.database import DatabaseMigrationAnalyzer
from app.analyzers.cicd import CicdDeploymentAnalyzer
from app.analyzers.accessibility import UiAccessibilityAnalyzer
from app.analyzers.docs import DocsOnboardingAnalyzer

from app.analyzers.registry import (
    DEFAULT_ANALYZERS,
    get_analyzer,
    list_analyzers,
    run_analyzers,
    register_analyzer,
    resolve_analyzers_for_changes,
)

ANALYZER_REGISTRY = DEFAULT_ANALYZERS

__all__ = [
    "BaseAnalyzer",
    "RepositoryDNAAnalyzer",
    "SecurityAnalyzer",
    "ChangeImpactAnalyzer",
    "TestIntelligenceAnalyzer",
    "CodeQualityAnalyzer",
    "ApiContractAnalyzer",
    "DatabaseMigrationAnalyzer",
    "CicdDeploymentAnalyzer",
    "UiAccessibilityAnalyzer",
    "DocsOnboardingAnalyzer",
    "get_analyzer",
    "list_analyzers",
    "run_analyzers",
    "register_analyzer",
    "resolve_analyzers_for_changes",
    "ANALYZER_REGISTRY",
    "DEFAULT_ANALYZERS",
]
