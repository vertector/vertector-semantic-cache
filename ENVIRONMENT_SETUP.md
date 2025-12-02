# Environment Setup Guide

## The Problem: Multiple Python Environments

You have **3 different Python environments** on your system:

1. **pyenv** (`~/.pyenv/shims/python`) - Your default shell Python
2. **miniconda** (`/opt/miniconda3/lib/python3.12`) - Python 3.12 conda environment  
3. **uv virtual env** (`.venv`) - Python 3.13 managed by uv

This causes confusion because `pip install -e .` installs to **different locations** depending on which environment is active!

---

## The Solution: Use One Consistent Method

### ✅ Option 1: Use uv with PYTHONPATH (Recommended)

```bash
# Run any script
PYTHONPATH=src .venv/bin/python examples/google_adk_example.py

# Or use uv run (preferred)
PYTHONPATH=src uv run python examples/google_adk_example.py
```

**Or use the activation script:**
```bash
# Activate the environment (sets PYTHONPATH automatically)
source activate.sh

# Now run normally
python examples/google_adk_example.py
python examples/basic_usage.py
```

### Option 2: Use the Conda Environment

```bash
# Install once
/opt/miniconda3/bin/python -m pip install -e .

# Run with conda python
/opt/miniconda3/bin/python examples/google_adk_example.py
```

---

## Why It Works Sometimes and Not Others

| Command | Environment Used | Package Installed? |
|---------|-----------------|-------------------|
| `python examples/...` | pyenv (current shell) | ❌ No |
| `uv run python examples/...` | uv venv (Python 3.13) | ⚠️ Yes, but `.pth` not loading |
| `.venv/bin/python examples/...` | uv venv directly | ⚠️ Yes, but `.pth` not loading |
| `PYTHONPATH=src .venv/bin/python examples/...` | uv venv with path | ✅ **YES!** |
| `/opt/miniconda3/bin/python examples/...` | miniconda | ✅ Yes (if installed there) |

---

## The `.pth` File Issue

Python 3.13 has a bug/change where `.pth` files in `site-packages` aren't always loaded correctly. The package IS installed (you can see `_semantic_cache.pth`), but Python doesn't add `src/` to the path.

**Workaround:** Set `PYTHONPATH=src` before running.

---

## Quick Reference

```bash
# Best practice - use the activation script
source activate.sh
python examples/basic_usage.py

# Or use PYTHONPATH directly  
PYTHONPATH=src python examples/google_adk_example.py

# Or specify full path to venv python
PYTHONPATH=src .venv/bin/python examples/google_adk_example.py
```

---

## Bonus Finding: App Name Mismatch Warning

We also found the Google ADK "App name mismatch" warning! It appears when:
```
WARNING   App name mismatch detected. The runner is configured with app name "assistant_app", 
but the root agent was loaded from ".../google/adk/agents", which implies app name "agents".
```

This is just a **warning** (not an error) that occurs when the app name doesn't match the module path. It doesn't break functionality but can be ignored or fixed by ensuring consistent naming.
