"""Detection and decompilation of binary Lua bytecode (.lub) files."""
import os
import shutil
import subprocess
import tempfile

LUA_MAGIC = b"\x1bLua"

_JAR_SEARCH_PATHS = [
    "/usr/local/share/unluac/unluac.jar",
    "/usr/local/share/unluac.jar",
    "/usr/share/unluac/unluac.jar",
    "/usr/share/unluac.jar",
    "/opt/unluac/unluac.jar",
]


def is_binary(data: bytes) -> bool:
    if data[:4] == LUA_MAGIC:
        return True
    return b"\x00" in data[:1024]


def decompile(data: bytes) -> str:
    """Try to decompile binary Lua bytecode using available external tools.

    Returns decompiled Lua source on success, or a commented error message
    describing what tool to install if no decompiler is available.
    """
    commands: list[list[str]] = []
    if shutil.which("unluac"):
        commands.append(["unluac"])
    if shutil.which("luadec"):
        commands.append(["luadec"])
    for jar in _JAR_SEARCH_PATHS:
        if os.path.exists(jar) and shutil.which("java"):
            commands.append(["java", "-jar", jar])

    if not commands:
        return (
            "-- Binary Lua bytecode (.lub) detected\n"
            "-- No decompiler found. Install unluac to enable decompilation:\n"
            "--\n"
            "--   Download: https://github.com/nicowillis/unluac\n"
            "--   Then place 'unluac' (or 'unluac.jar') in your PATH.\n"
        )

    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".lub", delete=False) as tmp:
            tmp.write(data)
            tmp_path = tmp.name

        last_stderr = ""
        for cmd in commands:
            try:
                result = subprocess.run(
                    cmd + [tmp_path],
                    capture_output=True,
                    text=True,
                    timeout=15,
                )
                if result.returncode == 0 and result.stdout.strip():
                    return result.stdout
                last_stderr = result.stderr.strip()
            except (subprocess.TimeoutExpired, FileNotFoundError):
                continue

        return (
            "-- Binary Lua bytecode (.lub) detected\n"
            "-- Decompilation failed.\n"
            + (f"-- {last_stderr}\n" if last_stderr else "")
        )
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)
