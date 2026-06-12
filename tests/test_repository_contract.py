from __future__ import annotations

import ast
import json
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

    def test_required_src_entrypoints_exist(self) -> None:
        for filename in (
            "base_auditor.py",
            "kernel_spec_catalog.py",
            "main_pipeline.py",
            "market_clock.py",
            "monitoring_control_plane.py",
            "output_standard.py",
            "telemetry_router.py",
        ):
            self.assertTrue((SRC / filename).is_file(), filename)

    def test_monitoring_control_plane_assets_exist(self) -> None:
        required_paths = (
            ROOT / "config" / "enterprise_monitoring_profiles.json",
            ROOT / "config" / "event_routing_policy.json",
            ROOT / "docs" / "MONITORING_OPERATIONS.md",
            ROOT / "examples" / "monitoring_event.example.json",
            ROOT / "examples" / "module_payloads.financing.synthetic.json",
            ROOT / "data" / "README.md",
            ROOT / "outputs" / "README.md",
        )
        for path in required_paths:
            self.assertTrue(path.is_file(), path)

    def test_publication_standard_assets_exist_and_example_validates(self) -> None:
        from src.output_standard import validate_publication_artifact

        required_paths = (
            ROOT / "docs" / "OUTPUT_STANDARD.md",
            ROOT / "docs" / "TEMPORAL_STANDARD.md",
            ROOT / "schemas" / "publication_artifact.schema.json",
            ROOT / "templates" / "telemetry_note.md",
            ROOT / "templates" / "deep_dive_whitepaper.md",
            ROOT / "examples" / "publication_artifact.example.json",
        )
        for path in required_paths:
            self.assertTrue(path.is_file(), path)

        schema = json.loads(required_paths[2].read_text(encoding="utf-8"))
        self.assertEqual(
            schema["$id"],
            "https://github.com/ckxleung/AlphaGuard-Framework/"
            "schemas/publication_artifact.schema.json",
        )
        example = json.loads(required_paths[5].read_text(encoding="utf-8"))
        self.assertTrue(validate_publication_artifact(example))

    def test_target_enterprise_config_lists_fifty_five_unique_tickers(self) -> None:
        config_path = ROOT / "config" / "target_55_enterprises.json"
        enterprise_config = json.loads(config_path.read_text(encoding="utf-8"))
        tickers = [
            ticker
            for layer_tickers in enterprise_config.values()
            for ticker in layer_tickers
        ]

        self.assertEqual(len(tickers), 55)
        self.assertEqual(len(set(tickers)), 55)

    def test_all_eighteen_kernel_architecture_directories_are_visible(self) -> None:
        from src.module_manifest import MODULE_SPECS

        for specification in MODULE_SPECS:
            path = (
                ROOT
                / "evaluation_kernels"
                / specification.layer
                / f"Module_{specification.module_id:02d}_{specification.code}"
            )
            self.assertTrue(path.is_dir(), path)

    def test_manifest_covers_exactly_eighteen_unique_module_ids(self) -> None:
        from src.module_manifest import MODULE_SPECS

        module_ids = [spec.module_id for spec in MODULE_SPECS]
        self.assertEqual(len(module_ids), 18)
        self.assertEqual(len(set(module_ids)), 18)
        self.assertEqual(set(module_ids), set(range(1, 19)))

    def test_module_twelve_is_registered_in_layer_four(self) -> None:
        from src.module_manifest import get_module_spec

        module = get_module_spec(12)
        self.assertEqual(module.code, "IRTA")
        self.assertEqual(module.layer, "layer_4_strategy")

    def test_all_eighteen_modules_have_complete_machine_readable_specs(self) -> None:
        from src.kernel_spec_catalog import KERNEL_SPECIFICATIONS
        from src.module_manifest import MODULE_SPECS

        self.assertEqual(len(KERNEL_SPECIFICATIONS), 18)
        self.assertEqual(
            {spec.module_id for spec in KERNEL_SPECIFICATIONS},
            {spec.module_id for spec in MODULE_SPECS},
        )
        self.assertEqual(
            {spec.code for spec in KERNEL_SPECIFICATIONS},
            {spec.code for spec in MODULE_SPECS},
        )

        for specification in KERNEL_SPECIFICATIONS:
            with self.subTest(module=specification.code):
                self.assertTrue(specification.problem_statement)
                self.assertTrue(specification.ai_inputs)
                self.assertTrue(specification.ground_truth_inputs)
                self.assertTrue(specification.deterministic_rules)
                self.assertTrue(specification.tolerance_policy)
                self.assertTrue(specification.rejection_conditions)
                self.assertTrue(specification.outputs)
                self.assertTrue(specification.data_boundary)

    def test_attachment_numbering_conflicts_are_explicitly_reconciled(self) -> None:
        from src.kernel_spec_catalog import get_kernel_spec

        self.assertIn("RSSF", get_kernel_spec(13).source_aliases)
        self.assertIn("FLIB", get_kernel_spec(6).source_aliases)
        self.assertIn("SCGV-17", get_kernel_spec(15).source_aliases)

    def test_kernel_spec_catalog_passes_its_own_validator(self) -> None:
        from src.kernel_spec_catalog import validate_kernel_spec_catalog

        self.assertEqual(validate_kernel_spec_catalog(), ())

    def test_master_spec_has_a_section_for_every_canonical_module(self) -> None:
        from src.module_manifest import MODULE_SPECS

        master_spec = (ROOT / "docs" / "MASTER_SPEC.md").read_text(
            encoding="utf-8"
        )
        for specification in MODULE_SPECS:
            heading = (
                f"## Module {specification.module_id:02d} {specification.code}"
            )
            self.assertIn(heading, master_spec)


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
            [sys.executable, str(SRC / "market_clock.py")],
            [sys.executable, str(SRC / "kernel_spec_catalog.py"), "--module", "1"],
            [sys.executable, str(SRC / "module_manifest.py"), "--module", "12"],
            [
                sys.executable,
                str(SRC / "output_standard.py"),
                str(ROOT / "examples" / "publication_artifact.example.json"),
            ],
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

    def test_main_pipeline_no_args_runs_daily_smoke_json(self) -> None:
        result = subprocess.run(
            [sys.executable, str(SRC / "main_pipeline.py")],
            cwd=ROOT.parent,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("ALPHAGUARD FRAMEWORK: AUTOMATED DAILY AUDIT PIPELINE RUN", result.stdout)
        json_start = result.stdout.index("{")
        json_end = result.stdout.rindex("}") + 1
        payload = json.loads(result.stdout[json_start:json_end])
        self.assertIn("telemetry_timestamp_matrix", payload)
        self.assertNotIn("telemetry_timestamp", payload)
        self.assertEqual(payload["routing_specs"]["ticker"], "NVDA")
        self.assertFalse(payload["substack_ready_flag"])
        self.assertTrue(payload["data_provenance"]["synthetic_data"])
        self.assertGreaterEqual(len(payload["forensic_audit_scorecard"]), 1)


if __name__ == "__main__":
    unittest.main()
