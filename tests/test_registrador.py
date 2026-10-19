import contextlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "registrador_em_teste", ROOT / "registrar_teste.py"
)
registrador = importlib.util.module_from_spec(spec)
spec.loader.exec_module(registrador)
REAL_RUN = subprocess.run


class RegistradorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.output = Path(self.temp.name) / "registros"
        self.source = ROOT / "examples" / "sessao-ficticia.jsonl"

    def execute(self, mutation=None):
        def simulated_run(command, **kwargs):
            if command[0] == "hermes":
                Path(command[5]).write_bytes(self.source.read_bytes())
                return subprocess.CompletedProcess(command, 0, "", "")
            result = REAL_RUN(command, **kwargs)
            if result.returncode == 0 and mutation:
                mutation(self.run_folder() / "EVIDENCIAS" / "DEMO-T01")
            return result

        argv = [
            "registrar_teste.py",
            "--profile", "perfil-ficticio",
            "--session-id", "sessao-demo-001",
            "--test", "DEMO-T01",
            "--message-id", "1",
            "--output", str(self.output),
        ]
        with patch.object(sys, "argv", argv), patch.object(
            registrador.subprocess, "run", side_effect=simulated_run
        ), contextlib.redirect_stdout(io.StringIO()):
            registrador.main()

    def run_folder(self):
        folders = list(self.output.iterdir())
        self.assertEqual(len(folders), 1)
        return folders[0]

    def test_success_creates_receipt(self):
        self.execute()
        folder = self.run_folder()
        receipt = json.loads((folder / "REGISTRO.json").read_text("utf-8"))
        self.assertEqual(receipt["status"], "concluido")
        self.assertEqual(receipt["assessment_status"], "pendente")
        self.assertEqual(receipt["tool_counts"], {"read_file": 1})
        self.assertFalse((folder / "INCOMPLETO.txt").exists())

    def assert_rejected(self, mutation):
        with self.assertRaisesRegex(ValueError, "Conferencia final"):
            self.execute(mutation)
        folder = self.run_folder()
        self.assertTrue((folder / "INCOMPLETO.txt").is_file())
        self.assertFalse((folder / "REGISTRO.json").exists())

    def test_wrong_filename_is_rejected(self):
        def rename(folder):
            (folder / "DEMO-T01-PROMPT.md").rename(folder / "ERRADO.md")
        self.assert_rejected(rename)

    def test_directory_instead_of_file_is_rejected(self):
        def replace(folder):
            prompt = folder / "DEMO-T01-PROMPT.md"
            prompt.unlink()
            prompt.mkdir()
        self.assert_rejected(replace)


if __name__ == "__main__":
    unittest.main()
