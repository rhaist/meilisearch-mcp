"""
Integration tests for Docker setup.

These tests verify that the Docker container works correctly and can
communicate with Meilisearch.
"""
import os
import subprocess
import time
import pytest
import requests


def wait_for_service(url, timeout=30):
    """Wait for a service to become available."""
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            response = requests.get(f"{url}/health")
            if response.status_code == 200:
                return True
        except requests.exceptions.ConnectionError:
            pass
        time.sleep(1)
    return False


@pytest.fixture(scope="module")
def docker_services():
    """Start Docker services for testing."""
    # Start services
    subprocess.run(["docker-compose", "up", "-d"], check=True)
    
    # Wait for Meilisearch to be ready
    if not wait_for_service("http://localhost:7700"):
        subprocess.run(["docker-compose", "down"], check=True)
        pytest.fail("Meilisearch failed to start")
    
    yield
    
    # Cleanup
    subprocess.run(["docker-compose", "down", "-v"], check=True)


def test_docker_build():
    """Test that the Docker image can be built successfully."""
    result = subprocess.run(
        ["docker", "build", "-t", "meilisearch-mcp-test", "."],
        capture_output=True,
        text=True
    )
    assert result.returncode == 0, f"Docker build failed: {result.stderr}"


def test_meilisearch_connectivity(docker_services):
    """Test that the MCP container can connect to Meilisearch."""
    # Run a simple connectivity test in the container
    result = subprocess.run(
        [
            "docker-compose", "run", "--rm", "meilisearch-mcp",
            "python", "-c",
            """
import os
from meilisearch import Client
client = Client(os.getenv('MEILI_HTTP_ADDR'), os.getenv('MEILI_MASTER_KEY'))
health = client.health()
assert health['status'] == 'available'
print('SUCCESS: Connected to Meilisearch')
"""
        ],
        capture_output=True,
        text=True
    )
    
    assert result.returncode == 0, f"Connectivity test failed: {result.stderr}"
    assert "SUCCESS: Connected to Meilisearch" in result.stdout


def test_mcp_server_import(docker_services):
    """Test that the MCP server module can be imported in the container."""
    result = subprocess.run(
        [
            "docker-compose", "run", "--rm", "meilisearch-mcp",
            "python", "-c",
            """
import src.meilisearch_mcp
from src.meilisearch_mcp.server import MeilisearchMCPServer
print('SUCCESS: MCP server imported')
"""
        ],
        capture_output=True,
        text=True
    )
    
    assert result.returncode == 0, f"Import test failed: {result.stderr}"
    assert "SUCCESS: MCP server imported" in result.stdout


def test_environment_variables(docker_services):
    """Test that environment variables are correctly set in the container."""
    result = subprocess.run(
        [
            "docker-compose", "run", "--rm", "meilisearch-mcp",
            "python", "-c",
            """
import os
assert os.getenv('MEILI_HTTP_ADDR') == 'http://meilisearch:7700'
assert os.getenv('MEILI_MASTER_KEY') == 'masterKey'
print('SUCCESS: Environment variables are correct')
"""
        ],
        capture_output=True,
        text=True
    )
    
    assert result.returncode == 0, f"Environment test failed: {result.stderr}"
    assert "SUCCESS: Environment variables are correct" in result.stdout


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])