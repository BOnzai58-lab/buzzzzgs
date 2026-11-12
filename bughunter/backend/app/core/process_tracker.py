"""Process Tracker & Process-Level Task Termination.

Guarantees immediate and deterministic cancellation of CLI security tools
(nuclei, subfinder, httpx, katana, gau, etc.) across Windows, Linux, and macOS.
"""
from __future__ import annotations

import os
import signal
import subprocess
import sys
import threading
import time
from typing import Dict
from loguru import logger

# Thread-safe process registry: task_id -> subprocess.Popen
_ACTIVE_PROCESSES: Dict[str, subprocess.Popen] = {}
_LOCK = threading.Lock()


class ProcessTracker:
    @staticmethod
    def register_process(task_id: str, proc: subprocess.Popen) -> None:
        """Register an active child subprocess under task_id."""
        with _LOCK:
            _ACTIVE_PROCESSES[task_id] = proc
            logger.debug("Process registered: task_id={} PID={}", task_id, proc.pid)

    @staticmethod
    def unregister_process(task_id: str) -> None:
        """Unregister completed subprocess."""
        with _LOCK:
            if task_id in _ACTIVE_PROCESSES:
                del _ACTIVE_PROCESSES[task_id]
                logger.debug("Process unregistered: task_id={}", task_id)

    @staticmethod
    def terminate_process(task_id: str) -> bool:
        """Terminate the running process and all child processes immediately.
        
        Returns True if a running process was found and terminated.
        """
        proc: subprocess.Popen | None = None
        with _LOCK:
            proc = _ACTIVE_PROCESSES.pop(task_id, None)

        if not proc:
            logger.debug("No active OS process found for task_id={}", task_id)
            return False

        pid = proc.pid
        logger.warning("Terminating process tree for task_id={} PID={}", task_id, pid)

        try:
            if sys.platform == "win32":
                # Windows: /F = Forcefully terminate, /T = Kill child process tree as well
                subprocess.run(
                    ["taskkill", "/F", "/T", "/PID", str(pid)],
                    capture_output=True,
                    timeout=5,
                )
            else:
                # Unix / Linux: terminate process group
                try:
                    pgid = os.getpgid(pid)
                    os.killpg(pgid, signal.SIGTERM)
                    time.sleep(0.5)
                    os.killpg(pgid, signal.SIGKILL)
                except (ProcessLookupError, PermissionError):
                    proc.kill()
            return True
        except Exception as exc:
            logger.error("Error terminating process PID {}: {}", pid, exc)
            try:
                proc.kill()
            except Exception:
                pass
            return False

    @classmethod
    def run_cancellable(
        cls,
        cmd: list[str],
        task_id: str,
        timeout: int = 300,
    ) -> tuple[int, str, str]:
        """Run an external tool with process registration and timeout.
        
        Returns (exit_code, stdout, stderr).
        """
        try:
            # On Linux/macOS, create a new process group so child processes can be killed together
            popen_kwargs = {
                "stdout": subprocess.PIPE,
                "stderr": subprocess.PIPE,
                "text": True,
            }
            if sys.platform != "win32":
                popen_kwargs["preexec_fn"] = os.setsid

            proc = subprocess.Popen(cmd, **popen_kwargs)
            cls.register_process(task_id, proc)

            try:
                stdout, stderr = proc.communicate(timeout=timeout)
                return proc.returncode, stdout, stderr
            except subprocess.TimeoutExpired:
                cls.terminate_process(task_id)
                return -1, "", "Execution timed out"
            except Exception as exc:
                cls.terminate_process(task_id)
                return -1, "", str(exc)
            finally:
                cls.unregister_process(task_id)

        except FileNotFoundError:
            return -2, "", f"Tool binary not found: {cmd[0]}"
        except Exception as exc:
            return -1, "", f"Failed to execute {cmd[0]}: {exc}"


process_tracker = ProcessTracker()

