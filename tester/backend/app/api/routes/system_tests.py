from fastapi import APIRouter
from app.services.system_tests import SystemTestService

router = APIRouter(prefix="/system-tests", tags=["System Assurance Tests"])

@router.get("/run-all")
def run_all_system_tests():
    """Execute the full suite of system assurance, security, environment, and performance tests."""
    return SystemTestService.run_all_tests()

@router.get("/sbom")
def get_cyclonedx_sbom():
    """Export standardized CycloneDX v1.5 Software Bill of Materials (SBOM)."""
    return SystemTestService.generate_cyclonedx_sbom()

@router.get("/category/{category_id}")
def run_category_test(category_id: str):
    """Execute a single category of tests."""
    mapping = {
        "security": SystemTestService.run_security_tests,
        "environment": SystemTestService.run_environment_tests,
        "performance": SystemTestService.run_performance_tests,
        "database": SystemTestService.run_database_tests,
        "frontend": SystemTestService.run_frontend_tests,
        "dast": SystemTestService.run_dast_tests,
        "crypto": SystemTestService.run_crypto_secrets_tests,
        "network": SystemTestService.run_network_topology_tests,
        "supply_chain": SystemTestService.run_supply_chain_tests,
        "concurrency": SystemTestService.run_concurrency_query_tests,
        "chaos": SystemTestService.run_chaos_tests,
        "container": SystemTestService.run_container_tests,
        "cloud": SystemTestService.run_cloud_posture_tests,
        "privacy": SystemTestService.run_data_privacy_tests,
        "ai_safety": SystemTestService.run_ai_safety_tests,
    }
    runner = mapping.get(category_id, SystemTestService.run_security_tests)
    return runner()
