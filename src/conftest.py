import pytest

def pytest_addoption(parser):
    """Register the --query command-line argument."""
    parser.addoption(
        "--query",
        action="store",
        default="Codistan",
        help="Base query to generate variations"
    )

@pytest.fixture
def query_variations(request):
    """Fixture to generate query variations."""
    base_query = request.config.getoption("--query")
    return [f"{base_query} {suffix}" for suffix in ["website", "location", "web", "about us", "contact"]] 