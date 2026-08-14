import json
import os
import re
import shutil

import pytest

AGENT_NAME = "intent-analyzer"
AGENT_PATH = os.path.join(
    os.path.dirname(__file__), "..", "agents", f"{AGENT_NAME}.md"
)


def _load_agent_body(path: str) -> str:
    with open(os.path.normpath(path)) as f:
        content = f.read()
    return re.sub(r"^---\n.*?\n---\n", "", content, flags=re.DOTALL).strip()


@pytest.fixture(scope="session")
def claude_bin():
    path = shutil.which("claude")
    if path is None:
        pytest.skip("'claude' CLI not found on PATH")
    return path


@pytest.fixture(scope="session")
def intent_analyzer_agents_json():
    body = _load_agent_body(AGENT_PATH)
    return json.dumps({
        AGENT_NAME: {
            "description": "Intent Analysis Engine",
            "prompt": body,
            "tools": ["Read", "AskUserQuestion"],
            "model": "haiku",
        }
    })
