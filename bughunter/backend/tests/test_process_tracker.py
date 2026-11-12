"""
tests/test_process_tracker.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Tests for the ProcessTracker: registration, unregistration,
safe termination, and cancellable tool execution.

Covers review §1.2 (Worker safety and stop behavior).
"""
import sys
import time
import uuid

import pytest

from app.core.process_tracker import ProcessTracker


class TestProcessTracker:

    def test_register_and_unregister(self):
        import subprocess
        # Use a long-running no-op process
        if sys.platform == "win32":
            proc = subprocess.Popen(["timeout", "60"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            proc = subprocess.Popen(["sleep", "60"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        task_id = str(uuid.uuid4())
        ProcessTracker.register_process(task_id, proc)
        from app.core.process_tracker import _ACTIVE_PROCESSES
        assert task_id in _ACTIVE_PROCESSES

        ProcessTracker.unregister_process(task_id)
        assert task_id not in _ACTIVE_PROCESSES

        # Cleanup
        proc.kill()
        proc.wait()

    def test_terminate_running_process(self):
        import subprocess
        if sys.platform == "win32":
            proc = subprocess.Popen(["timeout", "60"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            proc = subprocess.Popen(["sleep", "60"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        task_id = str(uuid.uuid4())
        ProcessTracker.register_process(task_id, proc)

        result = ProcessTracker.terminate_process(task_id)
        assert result is True

        # Give OS time to terminate
        time.sleep(0.3)
        returncode = proc.poll()
        assert returncode is not None, "Process should have been terminated"

    def test_terminate_nonexistent_task_returns_false(self):
        result = ProcessTracker.terminate_process(str(uuid.uuid4()))
        assert result is False

    def test_run_cancellable_success(self):
        task_id = str(uuid.uuid4())
        if sys.platform == "win32":
            cmd = ["cmd", "/c", "echo hello"]
        else:
            cmd = ["echo", "hello"]
        exit_code, stdout, stderr = ProcessTracker.run_cancellable(cmd, task_id, timeout=10)
        assert exit_code == 0
        assert "hello" in stdout.lower() or stdout.strip() != ""

    def test_run_cancellable_missing_binary(self):
        task_id = str(uuid.uuid4())
        exit_code, stdout, stderr = ProcessTracker.run_cancellable(
            ["__nonexistent_binary_xyz__"], task_id, timeout=5
        )
        assert exit_code == -2
        assert "__nonexistent_binary_xyz__" in stderr

    def test_run_cancellable_cleans_up_on_complete(self):
        from app.core.process_tracker import _ACTIVE_PROCESSES
        task_id = str(uuid.uuid4())
        if sys.platform == "win32":
            cmd = ["cmd", "/c", "echo done"]
        else:
            cmd = ["echo", "done"]
        ProcessTracker.run_cancellable(cmd, task_id, timeout=10)
        assert task_id not in _ACTIVE_PROCESSES
