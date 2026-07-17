import json

from langchain_core.tools import tool

from app.agent.sandbox.shell import run_sandbox_command
from app.agent.tools.runtime import note_tool


@tool
async def run_sandbox(cmd: str) -> str:
    """Chạy lệnh sandbox whitelist (date, ls, cat data/*, head, wc, pwd, echo). Không network, không rm."""
    note_tool("run_sandbox")
    result = await run_sandbox_command(cmd)
    return json.dumps(result, ensure_ascii=False)
