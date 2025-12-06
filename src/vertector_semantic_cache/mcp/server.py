"""MCP Server for Vertector Semantic Cache.

This server exposes semantic cache operations as MCP tools and resources,
allowing AI agents to use the cache for memory and knowledge management.

IMPORTANT: MCP uses stdio for JSON-RPC communication. All logging MUST go
to stderr, never stdout. This is configured at the top of this module.
"""

import os
import sys
import asyncio
import logging
from typing import Optional, Dict, Any, List

# CRITICAL: Redirect ALL logging to stderr before importing anything else
# MCP uses stdout for JSON-RPC, so any stdout output corrupts the protocol
logging.basicConfig(
    level=logging.WARNING,  # Reduce noise
    format='%(asctime)s %(name)s %(levelname)s %(message)s',
    stream=sys.stderr,
    force=True
)

# Also suppress specific noisy loggers
for logger_name in [
    'sentence_transformers',
    'transformers',
    'torch',
    'redisvl',
    'httpx',
    'httpcore',
    'vertector_semantic_cache',
]:
    logging.getLogger(logger_name).setLevel(logging.ERROR)

try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import (
        Tool,
        TextContent,
        Resource,
        ResourceContents,
        TextResourceContents,
    )
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False

from vertector_semantic_cache import AsyncSemanticCacheManager, CacheConfig

# Use stderr logger for this module
logger = logging.getLogger("mcp.server")
logger.setLevel(logging.INFO)

# Global cache manager instance
_cache_manager: Optional[AsyncSemanticCacheManager] = None


def get_config_from_env() -> CacheConfig:
    """Create CacheConfig from environment variables."""
    return CacheConfig(
        redis_url=os.environ.get("REDIS_URL", "redis://localhost:6380"),
        name=os.environ.get("CACHE_NAME", "mcp_cache"),
        ttl=int(os.environ.get("CACHE_TTL", "3600")),
        distance_threshold=float(os.environ.get("DISTANCE_THRESHOLD", "0.2")),
        overwrite=True,
        log_level="ERROR",  # Suppress cache logs
    )


async def get_cache_manager() -> AsyncSemanticCacheManager:
    """Get or create the global cache manager."""
    global _cache_manager
    
    if _cache_manager is None:
        config = get_config_from_env()
        _cache_manager = AsyncSemanticCacheManager(config)
        await _cache_manager.initialize()
        logger.info("Cache manager initialized", file=sys.stderr)
    
    return _cache_manager


async def shutdown_cache_manager():
    """Shutdown the global cache manager."""
    global _cache_manager
    
    if _cache_manager is not None:
        await _cache_manager.close()
        _cache_manager = None
        logger.info("Cache manager shut down", file=sys.stderr)


def create_server() -> "Server":
    """Create and configure the MCP server."""
    if not MCP_AVAILABLE:
        raise ImportError(
            "MCP is not installed. Install with: "
            "pip install vertector-semantic-cache[mcp]"
        )
    
    server = Server("vertector-semantic-cache")
    
    # =========================================================================
    # TOOLS
    # =========================================================================
    
    @server.list_tools()
    async def list_tools() -> List[Tool]:
        """List available cache tools."""
        return [
            Tool(
                name="cache_check",
                description="Check if a semantically similar prompt exists in cache",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "prompt": {
                            "type": "string",
                            "description": "The prompt to check"
                        },
                        "user_id": {
                            "type": "string",
                            "description": "Optional user ID for multi-tenancy"
                        },
                        "context": {
                            "type": "object",
                            "description": "Optional context for context-aware caching"
                        }
                    },
                    "required": ["prompt"]
                }
            ),
            Tool(
                name="cache_store",
                description="Store a prompt-response pair in the cache",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "prompt": {
                            "type": "string",
                            "description": "The prompt"
                        },
                        "response": {
                            "type": "string",
                            "description": "The response to cache"
                        },
                        "user_id": {
                            "type": "string",
                            "description": "Optional user ID"
                        },
                        "tags": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Optional tags for invalidation"
                        },
                        "context": {
                            "type": "object",
                            "description": "Optional context"
                        }
                    },
                    "required": ["prompt", "response"]
                }
            ),
            Tool(
                name="cache_clear",
                description="Clear all entries from the cache",
                inputSchema={
                    "type": "object",
                    "properties": {}
                }
            ),
            Tool(
                name="invalidate_by_tag",
                description="Invalidate cache entries by tag",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "tag": {
                            "type": "string",
                            "description": "Tag to invalidate"
                        }
                    },
                    "required": ["tag"]
                }
            ),
            Tool(
                name="invalidate_by_tags",
                description="Invalidate cache entries by multiple tags",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "tags": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Tags to invalidate"
                        },
                        "match_all": {
                            "type": "boolean",
                            "description": "If true, only invalidate entries with ALL tags"
                        }
                    },
                    "required": ["tags"]
                }
            ),
            Tool(
                name="batch_check",
                description="Check multiple prompts at once",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "prompts": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of prompts to check"
                        }
                    },
                    "required": ["prompts"]
                }
            ),
        ]
    
    @server.call_tool()
    async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
        """Execute a cache tool."""
        cache = await get_cache_manager()
        
        try:
            if name == "cache_check":
                result = await cache.check(
                    prompt=arguments["prompt"],
                    user_id=arguments.get("user_id"),
                    context=arguments.get("context"),
                )
                if result:
                    return [TextContent(type="text", text=f"Cache HIT: {result}")]
                else:
                    return [TextContent(type="text", text="Cache MISS: No matching entry found")]
            
            elif name == "cache_store":
                await cache.store(
                    prompt=arguments["prompt"],
                    response=arguments["response"],
                    user_id=arguments.get("user_id"),
                    tags=arguments.get("tags"),
                    context=arguments.get("context"),
                )
                return [TextContent(type="text", text="Successfully stored in cache")]
            
            elif name == "cache_clear":
                await cache.clear()
                return [TextContent(type="text", text="Cache cleared")]
            
            elif name == "invalidate_by_tag":
                count = await cache.invalidate_by_tag(arguments["tag"])
                return [TextContent(type="text", text=f"Invalidated {count} entries")]
            
            elif name == "invalidate_by_tags":
                count = await cache.invalidate_by_tags(
                    arguments["tags"],
                    match_all=arguments.get("match_all", False)
                )
                return [TextContent(type="text", text=f"Invalidated {count} entries")]
            
            elif name == "batch_check":
                results = await cache.batch_check(arguments["prompts"])
                output = []
                for prompt, result in zip(arguments["prompts"], results):
                    status = "HIT" if result else "MISS"
                    output.append(f"- {prompt[:50]}...: {status}")
                return [TextContent(type="text", text="\n".join(output))]
            
            else:
                return [TextContent(type="text", text=f"Unknown tool: {name}")]
                
        except Exception as e:
            logger.error(f"Tool {name} failed: {e}", file=sys.stderr)
            return [TextContent(type="text", text=f"Error: {str(e)}")]
    
    # =========================================================================
    # RESOURCES
    # =========================================================================
    
    @server.list_resources()
    async def list_resources() -> List[Resource]:
        """List available cache resources."""
        return [
            Resource(
                uri="cache://metrics",
                name="Cache Metrics",
                description="Current cache performance metrics",
                mimeType="application/json"
            ),
            Resource(
                uri="cache://config",
                name="Cache Configuration",
                description="Current cache configuration",
                mimeType="application/json"
            ),
            Resource(
                uri="cache://health",
                name="Cache Health",
                description="Cache health status",
                mimeType="application/json"
            ),
        ]
    
    @server.read_resource()
    async def read_resource(uri: str) -> ResourceContents:
        """Read a cache resource."""
        import json
        
        cache = await get_cache_manager()
        
        if uri == "cache://metrics":
            metrics = cache.get_metrics()
            return TextResourceContents(
                uri=uri,
                mimeType="application/json",
                text=json.dumps(metrics, indent=2)
            )
        
        elif uri == "cache://config":
            config = cache.config.model_dump()
            # Remove sensitive data
            config.pop("connection_kwargs", None)
            return TextResourceContents(
                uri=uri,
                mimeType="application/json",
                text=json.dumps(config, indent=2, default=str)
            )
        
        elif uri == "cache://health":
            try:
                # Simple health check - try to check cache
                health = {
                    "status": "healthy",
                    "cache_initialized": cache._initialized,
                    "l1_enabled": cache._l1_cache is not None,
                }
            except Exception as e:
                health = {
                    "status": "unhealthy",
                    "error": str(e)
                }
            return TextResourceContents(
                uri=uri,
                mimeType="application/json",
                text=json.dumps(health, indent=2)
            )
        
        else:
            raise ValueError(f"Unknown resource: {uri}")
    
    return server


async def main():
    """Run the MCP server."""
    if not MCP_AVAILABLE:
        print("Error: MCP is not installed. Install with:", file=sys.stderr)
        print("  pip install vertector-semantic-cache[mcp]", file=sys.stderr)
        return
    
    print("Starting Vertector Semantic Cache MCP Server", file=sys.stderr)
    
    server = create_server()
    
    try:
        async with stdio_server() as (read_stream, write_stream):
            await server.run(
                read_stream,
                write_stream,
                server.create_initialization_options()
            )
    finally:
        await shutdown_cache_manager()


if __name__ == "__main__":
    asyncio.run(main())
