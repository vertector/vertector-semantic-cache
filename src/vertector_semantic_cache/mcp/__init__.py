"""MCP Server for Vertector Semantic Cache.

This module provides a Model Context Protocol (MCP) server that exposes
the semantic cache functionality as tools and resources for AI agents.

Usage:
    python -m vertector_semantic_cache.mcp.server

Or via Claude Desktop config:
    {
        "mcpServers": {
            "vertector-cache": {
                "command": "python",
                "args": ["-m", "vertector_semantic_cache.mcp.server"]
            }
        }
    }
"""

from vertector_semantic_cache.mcp.server import main, create_server

__all__ = ["main", "create_server"]
