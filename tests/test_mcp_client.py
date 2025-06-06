"""
MCP Client Integration Tests

These tests simulate an MCP client connecting to the MCP server to test:
1. Tool discovery functionality
2. Connection settings verification

The tests require a running Meilisearch instance in the background.
"""
import asyncio
import os
import json
from typing import Dict, Any, List
import pytest
from unittest.mock import AsyncMock, patch

from src.meilisearch_mcp.server import MeilisearchMCPServer, create_server


async def simulate_mcp_call(server: MeilisearchMCPServer, tool_name: str, arguments: Dict[str, Any] = None):
    """Simulate an MCP client call to the server"""
    from mcp.types import CallToolRequest, CallToolRequestParams
    
    # Get the call_tool handler from request_handlers
    handler = server.server.request_handlers.get(CallToolRequest)
    if not handler:
        raise RuntimeError("No call_tool handler found")
    
    # Create a proper CallToolRequest
    request = CallToolRequest(
        method="tools/call",
        params=CallToolRequestParams(
            name=tool_name,
            arguments=arguments or {}
        )
    )
    
    result = await handler(request)
    return result.root.content


async def simulate_list_tools(server: MeilisearchMCPServer):
    """Simulate an MCP client request to list tools"""
    from mcp.types import ListToolsRequest
    
    # Get the list_tools handler from request_handlers
    handler = server.server.request_handlers.get(ListToolsRequest)
    if not handler:
        raise RuntimeError("No list_tools handler found")
    
    # Create a proper ListToolsRequest
    request = ListToolsRequest(method="tools/list")
    
    result = await handler(request)
    return result.root.tools


class TestMCPClientIntegration:
    """Test MCP client interaction with the server"""
    
    @pytest.fixture
    async def mcp_server(self):
        """Create and return an MCP server instance for testing"""
        # Use test environment variables or defaults
        url = os.getenv("MEILI_HTTP_ADDR", "http://localhost:7700")
        api_key = os.getenv("MEILI_MASTER_KEY")
        
        server = create_server(url, api_key)
        yield server
        await server.cleanup()
    
    async def test_tool_discovery(self, mcp_server):
        """Test that MCP client can discover all available tools from the server"""
        # Simulate MCP list_tools request
        tools = await simulate_list_tools(mcp_server)
        
        # Verify we get the expected tools
        assert isinstance(tools, list)
        assert len(tools) > 0
        
        # Check for essential tools
        tool_names = [tool.name for tool in tools]
        
        expected_tools = [
            "get-connection-settings",
            "update-connection-settings", 
            "health-check",
            "get-version",
            "get-stats",
            "create-index",
            "list-indexes",
            "get-documents",
            "add-documents",
            "search",
            "get-settings",
            "update-settings"
        ]
        
        for expected_tool in expected_tools:
            assert expected_tool in tool_names, f"Tool '{expected_tool}' not found in discovered tools"
        
        # Verify tool structure
        for tool in tools:
            assert hasattr(tool, 'name')
            assert hasattr(tool, 'description')
            assert hasattr(tool, 'inputSchema')
            assert isinstance(tool.name, str)
            assert isinstance(tool.description, str)
            assert isinstance(tool.inputSchema, dict)
        
        # Log discovered tools for debugging
        print(f"Discovered {len(tools)} tools: {tool_names}")
    
    async def test_connection_settings_verification(self, mcp_server):
        """Test connection settings tools to verify MCP client can connect to server"""
        # Test getting current connection settings
        result = await simulate_mcp_call(mcp_server, "get-connection-settings")
        
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0].type == "text"
        assert "Current connection settings:" in result[0].text
        assert "URL:" in result[0].text
        
        # Test updating connection settings
        new_url = "http://localhost:7701"
        update_result = await simulate_mcp_call(
            mcp_server, 
            "update-connection-settings", 
            {"url": new_url}
        )
        
        assert isinstance(update_result, list)
        assert len(update_result) == 1
        assert update_result[0].type == "text"
        assert "Successfully updated connection settings" in update_result[0].text
        assert new_url in update_result[0].text
        
        # Verify the update took effect
        verify_result = await simulate_mcp_call(mcp_server, "get-connection-settings")
        
        assert new_url in verify_result[0].text
    
    async def test_health_check_tool(self, mcp_server):
        """Test health check tool through MCP client interface"""
        # Mock the health check to avoid requiring actual Meilisearch
        with patch.object(mcp_server.meili_client, 'health_check', new_callable=AsyncMock) as mock_health:
            mock_health.return_value = True
            
            result = await simulate_mcp_call(mcp_server, "health-check")
            
            assert isinstance(result, list)
            assert len(result) == 1
            assert result[0].type == "text"
            assert "available" in result[0].text
            
            mock_health.assert_called_once()
    
    async def test_tool_error_handling(self, mcp_server):
        """Test that MCP client receives proper error responses from server"""
        # Test calling a non-existent tool
        result = await simulate_mcp_call(mcp_server, "non-existent-tool")
        
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0].type == "text"
        assert "Error:" in result[0].text
        assert "Unknown tool" in result[0].text
    
    async def test_tool_schema_validation(self, mcp_server):
        """Test that tools have proper input schemas for MCP client validation"""
        tools = await simulate_list_tools(mcp_server)
        
        # Check specific tool schemas
        create_index_tool = next(tool for tool in tools if tool.name == "create-index")
        assert create_index_tool.inputSchema["type"] == "object"
        assert "uid" in create_index_tool.inputSchema["required"]
        assert "uid" in create_index_tool.inputSchema["properties"]
        assert create_index_tool.inputSchema["properties"]["uid"]["type"] == "string"
        
        search_tool = next(tool for tool in tools if tool.name == "search")
        assert search_tool.inputSchema["type"] == "object"
        assert "query" in search_tool.inputSchema["required"]
        assert "query" in search_tool.inputSchema["properties"]
        assert search_tool.inputSchema["properties"]["query"]["type"] == "string"
    
    async def test_mcp_server_initialization(self, mcp_server):
        """Test that MCP server initializes correctly for client connections"""
        # Verify server has required attributes
        assert hasattr(mcp_server, 'server')
        assert hasattr(mcp_server, 'meili_client')
        assert hasattr(mcp_server, 'url')
        assert hasattr(mcp_server, 'api_key')
        assert hasattr(mcp_server, 'logger')
        
        # Verify server name and basic configuration
        assert mcp_server.server.name == "meilisearch"
        assert mcp_server.url is not None
        assert mcp_server.meili_client is not None


class TestMCPToolDiscovery:
    """Detailed tests for MCP tool discovery functionality"""
    
    @pytest.fixture
    async def server(self):
        """Create server instance for tool discovery tests"""
        url = os.getenv("MEILI_HTTP_ADDR", "http://localhost:7700")
        api_key = os.getenv("MEILI_MASTER_KEY")
        server = create_server(url, api_key)
        yield server
        await server.cleanup()
    
    async def test_complete_tool_list(self, server):
        """Test that all expected tools are discoverable by MCP clients"""
        tools = await simulate_list_tools(server)
        
        # Complete list of expected tools (21 total)
        expected_tools = [
            "get-connection-settings",
            "update-connection-settings",
            "health-check", 
            "get-version",
            "get-stats",
            "create-index",
            "list-indexes",
            "get-documents", 
            "add-documents",
            "get-settings",
            "update-settings",
            "search",
            "get-task",
            "get-tasks", 
            "cancel-tasks",
            "get-keys",
            "create-key",
            "delete-key",
            "get-health-status",
            "get-index-metrics",
            "get-system-info"
        ]
        
        tool_names = [tool.name for tool in tools]
        
        assert len(tools) == len(expected_tools)
        for expected_tool in expected_tools:
            assert expected_tool in tool_names
    
    async def test_tool_categorization(self, server):
        """Test that tools can be categorized for MCP client organization"""
        tools = await simulate_list_tools(server)
        
        # Categorize tools
        connection_tools = [t for t in tools if "connection" in t.name]
        index_tools = [t for t in tools if any(word in t.name for word in ["index", "create-index", "list-indexes"])]
        document_tools = [t for t in tools if "document" in t.name]
        search_tools = [t for t in tools if "search" in t.name]
        task_tools = [t for t in tools if "task" in t.name]
        key_tools = [t for t in tools if "key" in t.name]
        monitoring_tools = [t for t in tools if any(word in t.name for word in ["health", "stats", "version", "system", "metrics"])]
        
        # Verify each category has expected tools
        assert len(connection_tools) >= 2  # get/update connection settings
        assert len(index_tools) >= 2  # create/list indexes
        assert len(document_tools) >= 2  # get/add documents  
        assert len(search_tools) >= 1  # search
        assert len(task_tools) >= 2  # get-task/get-tasks/cancel-tasks
        assert len(key_tools) >= 3  # get/create/delete keys
        assert len(monitoring_tools) >= 4  # health-check, get-version, get-stats, etc.


class TestMCPConnectionSettings:
    """Detailed tests for MCP connection settings functionality"""
    
    @pytest.fixture 
    async def server(self):
        """Create server instance for connection tests"""
        url = os.getenv("MEILI_HTTP_ADDR", "http://localhost:7700") 
        api_key = os.getenv("MEILI_MASTER_KEY")
        server = create_server(url, api_key)
        yield server
        await server.cleanup()
    
    async def test_get_connection_settings_format(self, server):
        """Test connection settings response format for MCP clients"""
        result = await simulate_mcp_call(server, "get-connection-settings")
        
        assert len(result) == 1
        text_content = result[0]
        assert text_content.type == "text"
        
        # Verify format contains expected information
        text = text_content.text
        assert "Current connection settings:" in text
        assert "URL:" in text
        assert "API Key:" in text
        
        # Check URL is properly displayed
        assert server.url in text
        
        # Check API key is masked for security
        if server.api_key:
            assert "********" in text or "Not set" in text
        else:
            assert "Not set" in text
    
    async def test_update_connection_settings_persistence(self, server):
        """Test that connection updates persist for MCP client sessions"""
        original_url = server.url
        original_key = server.api_key
        
        # Test URL update
        new_url = "http://localhost:7701"
        await simulate_mcp_call(
            server,
            "update-connection-settings",
            {"url": new_url}
        )
        
        assert server.url == new_url
        assert server.meili_client.client.config.url == new_url
        
        # Test API key update  
        new_key = "test_api_key_123"
        await simulate_mcp_call(
            server, 
            "update-connection-settings", 
            {"api_key": new_key}
        )
        
        assert server.api_key == new_key
        assert server.meili_client.client.config.api_key == new_key
        
        # Test both updates together
        final_url = "http://localhost:7702" 
        final_key = "final_test_key"
        await simulate_mcp_call(
            server,
            "update-connection-settings",
            {"url": final_url, "api_key": final_key}
        )
        
        assert server.url == final_url
        assert server.api_key == final_key
    
    async def test_connection_settings_validation(self, server):
        """Test that MCP client receives validation for connection settings"""
        # Test with empty/invalid updates
        result = await simulate_mcp_call(
            server,
            "update-connection-settings", 
            {}
        )
        
        # Should succeed but not change anything
        assert len(result) == 1
        assert "Successfully updated" in result[0].text
        
        # Test partial updates
        original_url = server.url
        result = await simulate_mcp_call(
            server,
            "update-connection-settings",
            {"api_key": "new_key_only"}
        )
        
        assert server.url == original_url  # URL unchanged
        assert server.api_key == "new_key_only"  # Key updated