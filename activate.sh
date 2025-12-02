#!/bin/bash
# Activation script for the uv virtual environment with semantic-cache package

# Activate the virtual environment
source .venv/bin/activate

# Add the src directory to PYTHONPATH so semantic_cache can be imported
export PYTHONPATH="${PWD}/src:${PYTHONPATH}"

echo "✅ Virtual environment activated with semantic-cache package available"
echo "Python version: $(python --version)"
echo "Package location: ${PWD}/src/semantic_cache"
echo ""
echo "Run examples with: python examples/basic_usage.py"
