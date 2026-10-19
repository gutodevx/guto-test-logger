import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class LoggerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.source = self.base / "entrada.jsonl"
        self.output = self.base / "saida"
        self.session = json.loads(
            (ROOT / "examples" / "sessao-ficticia.jsonl")
            .read_text(encoding="utf-8-sig")
        )

    def run_logger(self):
        self.source.write_text(
            json.dumps(self.session), encoding="utf-8"
        )
        return subprocess.run(
            [
                sys.executable, str(ROOT / "guto_logger.py"),
                "--input", str(self.source),
                "--output", str(self.output),
                "--test", "DEMO-T01",
                "--session-id", "sessao-demo-001",
                "--message-id", "1",
            ],
            capture_output=True, text=True, encoding="utf-8",
        )

    def test_success_and_integrity(self):
        result = self.run_logger()
        self.assertEqual(result.returncode, 0, result.stderr)
        folder = self.output / "DEMO-T01"
        expected = {
            "DEMO-T01-" + suffix for suffix in (
                "PROMPT.md", "RESPOSTA.md", "FERRAMENTAS.json",
                "METADADOS.json", "AVALIACAO.md",
                "ORIGEM-SHA256.txt", "ORIGEM.jsonl",
            )
        }
        self.assertEqual({p.name for p in folder.iterdir()}, expected)
        metadata = json.loads(
            (folder / "DEMO-T01-METADADOS.json").read_text("utf-8")
        )
        original = self.source.read_bytes()
        self.assertEqual(
            (folder / "DEMO-T01-ORIGEM.jsonl").read_bytes(), original
        )
        self.assertEqual(
            metadata["source_sha256"], hashlib.sha256(original).hexdigest()
        )
        self.assertEqual(metadata["tool_call_count"], 1)
        self.assertEqual(metadata["user_message_id"], 1)
        self.assertEqual(metadata["review_status"], "pendente")
        self.assertIn(
            "2 dias uteis",
            (folder / "DEMO-T01-RESPOSTA.md").read_text("utf-8"),
        )

    def test_existing_output_is_preserved(self):
        first = self.run_logger()
        self.assertEqual(first.returncode, 0, first.stderr)
        folder = self.output / "DEMO-T01"
        before = {p.name: p.read_bytes() for p in folder.iterdir()}
        second = self.run_logger()
        self.assertNotEqual(second.returncode, 0)
        self.assertIn("--force", second.stderr)
        after = {p.name: p.read_bytes() for p in folder.iterdir()}
        self.assertEqual(before, after)
        self.assertEqual(len(list(self.output.iterdir())), 1)

    def test_missing_tool_result_is_rejected(self):
        self.session["messages"] = [
            m for m in self.session["messages"] if m["role"] != "tool"
        ]
        result = self.run_logger()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("nao correspondem", result.stderr)
        self.assertFalse(self.output.exists())

    def test_compacted_segment_is_rejected(self):
        self.session["messages"][0]["compacted"] = True
        result = self.run_logger()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("compactadas", result.stderr)
        self.assertFalse(self.output.exists())


if __name__ == "__main__":
    unittest.main()
