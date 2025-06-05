# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a **Model Context Protocol (MCP) server** for Meilisearch, allowing LLM interfaces like Claude to interact with Meilisearch search engines. The project implements a Python-based MCP server that provides comprehensive tools for index management, document operations, search functionality, and system monitoring.

## Development Commands

### Environment Setup
```bash
# Create virtual environment and install dependencies
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv pip install -e .

# Install development dependencies
uv pip install -r requirements-dev.txt
```

### Testing
```bash
# Run all tests
python -m pytest tests/ -v

# Run specific test file
python -m pytest tests/test_mcp_integration.py -v

# Run tests with coverage
python -m pytest --cov=src tests/

# Run integration tests (requires running Meilisearch)
python -m pytest tests/test_mcp_integration.py -v
```

### Code Quality
```bash
# Format code (Black >=23.0.0)
black src/ tests/

# Run the MCP server locally for testing
python -m src.meilisearch_mcp

# Test with MCP Inspector
npx @modelcontextprotocol/inspector python -m src.meilisearch_mcp
```

### Prerequisites for Testing
- **Meilisearch server** must be running on `http://localhost:7700`
- **Docker option**: `docker run -d -p 7700:7700 getmeili/meilisearch:v1.6`
- **Node.js** for MCP Inspector testing

## Architecture

### Modular Manager Design
The codebase follows a modular architecture where functionality is organized into specialized managers:

```
MeilisearchClient
├── IndexManager      - Index creation, listing, deletion
├── DocumentManager   - Document CRUD operations 
├── SettingsManager   - Index configuration management
├── TaskManager       - Asynchronous task monitoring
├── KeyManager        - API key management
└── MonitoringManager - Health checks and system metrics
```

### MCP Server Integration
- **Server Class**: `MeilisearchMCPServer` in `server.py` handles MCP protocol communication
- **Tool Registration**: All tools are defined with JSON schemas for input validation
- **Error Handling**: Comprehensive exception handling with logging through `MCPLogger`
- **Dynamic Configuration**: Runtime connection settings updates via MCP tools

### Key Components

#### Tool Handler Pattern
All MCP tools follow a consistent pattern:
1. Input validation via JSON schema
2. Delegation to appropriate manager class
3. Error handling with structured logging
4. Formatted response as `TextContent`

#### Search Architecture
- **Single Index Search**: Direct search in specified index
- **Multi-Index Search**: Parallel search across all indices when no `indexUid` provided
- **Result Aggregation**: Smart filtering of results with hits

#### Connection Management
- **Runtime Configuration**: Dynamic URL and API key updates
- **Environment Variables**: `MEILI_HTTP_ADDR` and `MEILI_MASTER_KEY` for defaults
- **Connection State**: Maintained in server instance for session persistence

## Testing Strategy

### Test Structure
- **Integration Tests** (`test_mcp_integration.py`): End-to-end MCP tool execution with real Meilisearch
- **Synchronous Tests** (`test_mcp_sync.py`, `test_mcp_simple.py`): Simplified testing avoiding async complications
- **Unit Tests** (`test_server.py`): Basic server instantiation

### Tool Simulation
Tests use `simulate_tool_call()` function that:
- Directly invokes server tool handlers
- Bypasses MCP protocol overhead
- Returns proper `TextContent` responses
- Provides comprehensive coverage of all 20+ tools

### Test Isolation
- **Unique Index Names**: Timestamped index names prevent test interference
- **Cleanup Fixtures**: Automatic test environment cleanup
- **Service Dependencies**: Tests require running Meilisearch instance

## Environment Configuration

### Required Environment Variables
```bash
MEILI_HTTP_ADDR=http://localhost:7700  # Meilisearch server URL
MEILI_MASTER_KEY=your_master_key       # Optional: API key for authenticated instances
```

### Claude Desktop Integration
Add to `claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "meilisearch": {
      "command": "uvx", 
      "args": ["-n", "meilisearch-mcp"]
    }
  }
}
```

### GitHub Actions Integration
The repository includes Claude Code integration via GitHub Actions:
- **Trigger**: Comments containing `@claude` on issues, PRs, or reviews
- **Workflow**: `.github/workflows/claude.yml` handles automated Claude responses
- **Permissions**: Read contents, write to pull requests and issues

## Available MCP Tools

### Core Categories
- **Connection Management**: Dynamic configuration updates
- **Index Operations**: CRUD operations for search indices  
- **Document Management**: Add, retrieve, and manage documents
- **Search Capabilities**: Single and multi-index search with filtering
- **Settings Control**: Index configuration and optimization
- **Task Monitoring**: Asynchronous operation tracking
- **API Key Management**: Authentication and authorization
- **System Monitoring**: Health checks and performance metrics

### Search Tool Features
- **Flexible Targeting**: Search specific index or all indices
- **Rich Parameters**: Filtering, sorting, pagination support
- **Result Formatting**: JSON formatted responses with proper serialization
- **Error Resilience**: Graceful handling of index-specific failures

## Development Notes

### Dependencies
- **MCP Framework**: `mcp>=1.2.1` for protocol implementation
- **Meilisearch Client**: `meilisearch>=0.33.0` for search engine integration
- **HTTP Client**: `httpx>=0.24.0` for async HTTP operations
- **Data Validation**: `pydantic>=2.0.0` for structured data handling

### Logging Infrastructure
- **Structured Logging**: JSON-formatted logs with contextual information
- **Log Directory**: `~/.meilisearch-mcp/logs/` for persistent logging
- **Error Tracking**: Comprehensive error logging with tool context