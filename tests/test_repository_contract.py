from __future__ import annotations

import ast
import importlib.util
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(ROOT))


class RepositoryStructureTests(unittest.TestCase):
    def test_required_layer_directories_exist(self) -> None:
        expected = (
            "layer_1_telemetry",
            "layer_2_valuation",
            "layer_3_compliance",
            "layer_4_strategy",
        )
        for directory in expected:
            self.assertTrue((ROOT / "evaluation_kernels" / directory).is_dir())

    def test_manifest_covers_exactly_eighteen_unique_module_ids(self) -> None:
        from src.module_manifest import MODULE_SPECS

        module_ids = [spec.module_id for spec in MODULE_SPECS]
        self.assertEqual(len(module_ids), 18)
        self.assertEqual(len(set(module_ids)), 18)
        self.assertEqual(set(module_ids), set(range(1, 19)))

    def test_unprovided_module_twelve_is_not_marked_implemented(self) -> None:
        from src.module_manifest import get_module_spec

        module = get_module_spec(12)
        self.assertEqual(module.status, "SPEC_REQUIRED")
        self.assertFalse(module.implementation_path)


class BaseAuditorContractTests(unittest.TestCase):
    def test_base_auditor_requires_execute_audit(self) -> None:
        from src.base_auditor import BaseAuditor

        self.assertIn("execute_audit", BaseAuditor.__abstractmethods__)

        class IncompleteAuditor(BaseAuditor):
            pass

        with self.assertRaises(TypeError):
            IncompleteAuditor()

    def test_scorecard_validation_accepts_institutional_contract(self) -> None:
        from src.base_auditor import BaseAuditor

        scorecard = BaseAuditor.validate_scorecard(
            {
                "rigor_score": 4.5,
                "data_quality_status": "APPROVED",
                "structured_written_feedback": "Evidence reconciles within tolerance.",
            }
        )
        self.assertEqual(scorecard["rigor_score"], 4.5)

    def test_scorecard_validation_rejects_unknown_status(self) -> None:
        from src.base_auditor import BaseAuditor

        with self.assertRaises(ValueError):
            BaseAuditor.validate_scorecard(
                {
                    "rigor_score": 4.0,
                    "data_quality_status": "MAYBE",
                    "structured_written_feedback": "Ambiguous.",
                }
            )


class KernelQualityTests(unittest.TestCase):
    def test_kernel_scripts_have_no_placeholder_implementation(self) -> None:
        forbidden_text = ("TODO", "NotImplementedError")
        kernel_root = ROOT / "evaluation_kernels"

        for path in kernel_root.rglob("*.py"):
            source = path.read_text(encoding="utf-8")
            for marker in forbidden_text:
                self.assertNotIn(marker, source, path)

            tree = ast.parse(source, filename=str(path))
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    self.assertFalse(
                        len(node.body) == 1 and isinstance(node.body[0], ast.Pass),
                        f"{path}:{node.lineno} contains an empty implementation",
                    )

    def test_implemented_kernel_classes_inherit_base_auditor(self) -> None:
        from src.base_auditor import BaseAuditor
        from src.module_manifest import MODULE_SPECS

        implemented = [spec for spec in MODULE_SPECS if spec.status == "IMPLEMENTED"]
        for spec in implemented:
            path = ROOT / spec.implementation_path
            module_name = f"alphaguard_contract_{spec.module_id}"
            module_spec = importlib.util.spec_from_file_location(module_name, path)
            self.assertIsNotNone(module_spec)
            self.assertIsNotNone(module_spec.loader)
            module = importlib.util.module_from_spec(module_spec)
            module_spec.loader.exec_module(module)
            auditor_class = getattr(module, spec.class_name)
            self.assertTrue(issubclass(auditor_class, BaseAuditor))
            self.assertIn("execute_audit", auditor_class.__dict__)


class StandaloneScriptTests(unittest.TestCase):
    def test_generated_python_scripts_run_outside_repository_root(self) -> None:
        commands = (
            [sys.executable, str(SRC / "base_auditor.py")],
            [sys.executable, str(SRC / "module_manifest.py"), "--module", "12"],
            [sys.executable, str(SRC / "repository_validator.py")],
            [sys.executable, str(SRC / "main_pipeline.py"), "--validate-only"],
        )
        layer_scripts = sorted(
            (ROOT / "evaluation_kernels").rglob("layer_contract.py")
        )
        commands += tuple([sys.executable, str(path)] for path in layer_scripts)

        for command in commands:
            result = subprocess.run(
                command,
                cwd=ROOT.parent,
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
            self.assertEqual(
                result.returncode,
                0,
                f"{' '.join(command)} failed:\n{result.stderr}",
            )


if __name__ == "__main__":
    unittest.main()
