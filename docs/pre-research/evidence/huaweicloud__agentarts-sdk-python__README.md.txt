Source: https://github.com/huaweicloud/agentarts-sdk-python/blob/main/README.md
Retrieved: 2026-11-16
Snapshot: full; upstream chars=16283

# Huawei Cloud AgentArts SDK

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python](https://img.shields.io/badge/Python-3.10%2B-brightgreen.svg)](https://www.python.org/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

Build, deploy and manage AI agents with Huawei Cloud capabilities.

## Overview

Huawei Cloud AgentArts SDK is a comprehensive toolkit for developing, deploying, and managing AI agents. It provides seamless integration with Huawei Cloud services while supporting mainstream agent frameworks.

### Key Features

- **Framework Agnostic** - Compatible with LangChain, LangGraph, AutoGen, CrewAI, Google ADK, and any custom agent framework
- **One-Click Deployment** - Deploy agents to Huawei Cloud with a single command
- **Built-in Tools** - Code interpreter sandbox, memory management, gateway support
- **Cloud Integration** - Seamless integration with Huawei Cloud authentication, monitoring, and logging
- **CLI Toolkit** - Complete command-line tools for project initialization, local development, and cloud deployment

### Repository Structure

```
agentarts-sdk-python/
├── src/agentarts/
│   ├── sdk/                    # Core SDK modules
│   │   ├── runtime/            # HTTP server runtime (AgentArtsRuntimeApp)
│   │   ├── memory/             # Conversation memory management
│   │   ├── tools/              # Built-in tools (Code Interpreter)
│   │   ├── gateway/            # Gateway client
│   │   ├── identity/           # Authentication & authorization
│   │   ├── integration/        # Framework adapters (LangGraph, etc.)
│   │   └── service/            # HTTP clients for cloud services
│   └── toolkit/                # CLI toolkit
│       ├── cli/                # Command-line interface
│       ├── operations/         # CLI operation handlers
│       ├── plugins/memory/    # Memory plugins
│       │   ├── ai_agent/      # Platform assets (claude_code, codex, opencode, hermes)
│       │   ├── installer/     # Unified installer
│       │   ├── mcp/           # MCP server (local adapter)
│       │   └── resources/     # Manifests + shared hook scripts
│       └── utils/             # Utilities
│           ├── runtime/       # Runtime utilities
│           └── templates/     # Project templates
├── docs/                       # Documentation
│   └── cn/                     # Chinese documentation
│       ├── sdk_user_guide/     # SDK usage guides
│       └── toolkit_user_guide/ # CLI usage guides
├── examples/                   # Example projects
└── tests/                      # Test suites
    ├── unit/                   # Unit tests mirroring src/ tree
    │   ├── sdk/                # SDK tests
    │   └── toolkit/            # Toolkit tests
    │       └── plugins/memory/ # Memory plugin tests
    └── integration/            # Integration tests
```

## Wrapping Your Agent as HTTP Server

The SDK provides `AgentArtsRuntimeApp` to wrap your agent logic as a standard HTTP server, exposing:

- `POST /invocations` - Main agent invocation endpoint
- `GET /ping` - Health check endpoint
- `WS /ws` - WebSocket endpoint for streaming

### Example: LangGraph Agent

```python
# agent.py
import os
from typing import Dict, Any, TypedDict, Annotated
from operator i
[Selected excerpt only; full source available at URL above.]