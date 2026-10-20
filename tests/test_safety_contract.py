"""Regression guard, not an OS sandbox or a proof of arbitrary future code safety."""
from pathlib import Path
import ast
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]


class SafetyContractTests(unittest.TestCase):
    def test_offline_c_has_no_hardware_or_interposition_transport(self):
        forbidden = re.compile(r"\b(open|open64|openat|ioctl|mmap|dlopen|dlsym|system|execv|execve|popen)\s*\(")
        for path in (ROOT / "07-prototype").glob("*.[ch]"):
            # Strip comments so historical explanations are not executable calls.
            text = re.sub(r"/\*.*?\*/|//[^\n]*", "", path.read_text(), flags=re.S)
            self.assertIsNone(forbidden.search(text), str(path))

    def test_no_prebuilt_live_artifacts(self):
        for name in ("fake_rm.so", "nvml_pstate_probe", "sniffer.so", "sniffer2.so", "rmctl"):
            self.assertFalse((ROOT / "07-prototype" / name).exists(), name)

    def test_monitor_is_the_only_live_entry_point(self):
        shell = (ROOT / "scripts/capture_state.sh").read_text()
        self.assertIn("capture_state.py", shell)
        self.assertNotRegex(shell, r"lspci|setpci|/sys/|/dev/|nvidia-smi")
        for path in (ROOT / "scripts/capture_state.py", ROOT / "10-monitor/collector/collector.py"):
            py = path.read_text()
            tree = ast.parse(py)
            imports = {alias.name for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names}
            self.assertNotIn("ctypes", imports)
            self.assertNotRegex(py, r"LD_PRELOAD=|--gpu-reset|--power-limit|--lock-gpu-clocks")

    def test_fetchers_never_execute_downloaded_installers(self):
        for path in (ROOT / "scripts").glob("fetch*.sh"):
            self.assertNotRegex(path.read_text(), r'\b(?:sh|bash)\s+"?\$(?:run|file)|\b(?:sudo|modprobe|insmod|nvflash)\b')


if __name__ == "__main__":
    unittest.main()
