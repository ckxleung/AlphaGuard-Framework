# -*- coding: utf-8 -*-
"""Audit SEC footnote retrieval, citations, and table cross-references."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.base_auditor import BaseAuditor


class SecFootnoteReasoningAuditor(BaseAuditor):
    """Verify SEC filing answers against retained source coordinates."""

    @staticmethod
    def _text(payload: Mapping[str, Any], key: str) -> str:
        value = payload.get(key)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{key} is required and must be non-empty text.")
        return value.strip()

    @staticmethod
    def _number(payload: Mapping[str, Any], key: str) -> float:
        value = payload.get(key)
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise TypeError(f"{key} must be numeric.")
        number = float(value)
        if not math.isfinite(number):
            raise ValueError(f"{key} must be finite.")
        return number

    @staticmethod
    def _text_list(payload: Mapping[str, Any], key: str) -> tuple[str, ...]:
        raw_values = payload.get(key)
        if not isinstance(raw_values, list):
            raise TypeError(f"{key} must be a list.")
        values: list[str] = []
        for index, value in enumerate(raw_values):
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{key}[{index}] must be non-empty text.")
            values.append(value.strip())
        if len(values) != len(set(values)):
            raise ValueError(f"{key} cannot contain duplicate values.")
        return tuple(values)

    @classmethod
    def _footnotes(cls, truth: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
        filing_text = cls._text(truth, "filing_text")
        raw_footnotes = truth.get("footnote_boundaries")
        if not isinstance(raw_footnotes, list) or not raw_footnotes:
            raise ValueError("footnote_boundaries must be a non-empty list.")
        footnotes: dict[str, dict[str, Any]] = {}
        for index, footnote in enumerate(raw_footnotes):
            if not isinstance(footnote, Mapping):
                raise TypeError(f"footnote_boundaries[{index}] must be an object.")
            footnote_id = cls._text(footnote, "footnote_id")
            if footnote_id in footnotes:
                raise ValueError("footnote_boundaries cannot duplicate footnote_id.")
            start_char = int(cls._number(footnote, "start_char"))
            end_char = int(cls._number(footnote, "end_char"))
            if start_char < 0 or end_char <= start_char or end_char > len(filing_text):
                raise ValueError("footnote_boundaries must be valid text ranges.")
            footnotes[footnote_id] = {
                "footnote_id": footnote_id,
                "title": cls._text(footnote, "title"),
                "start_char": start_char,
                "end_char": end_char,
                "position_bucket": cls._text(footnote, "position_bucket"),
            }
        return footnotes

    @classmethod
    def _table_cells(
        cls,
        truth: Mapping[str, Any],
        footnotes: Mapping[str, Mapping[str, Any]],
    ) -> dict[str, dict[str, Any]]:
        raw_cells = truth.get("table_cells")
        if not isinstance(raw_cells, list) or not raw_cells:
            raise ValueError("table_cells must be a non-empty list.")
        cells: dict[str, dict[str, Any]] = {}
        for index, cell in enumerate(raw_cells):
            if not isinstance(cell, Mapping):
                raise TypeError(f"table_cells[{index}] must be an object.")
            cell_id = cls._text(cell, "cell_id")
            if cell_id in cells:
                raise ValueError("table_cells cannot duplicate cell_id.")
            footnote_id = cls._text(cell, "footnote_id")
            if footnote_id not in footnotes:
                raise ValueError("table_cells references an unknown footnote_id.")
            cells[cell_id] = {
                "cell_id": cell_id,
                "footnote_id": footnote_id,
                "label": cls._text(cell, "label"),
                "value": cls._number(cell, "value"),
                "unit": cls._text(cell, "unit").upper(),
                "source_coordinate": cls._text(cell, "source_coordinate"),
                "position_bucket": cls._text(cell, "position_bucket"),
            }
        return cells

    @classmethod
    def _questions(cls, truth: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
        raw_questions = truth.get("benchmark_questions")
        if not isinstance(raw_questions, list) or not raw_questions:
            raise ValueError("benchmark_questions must be a non-empty list.")
        questions: dict[str, dict[str, Any]] = {}
        for index, question in enumerate(raw_questions):
            if not isinstance(question, Mapping):
                raise TypeError(f"benchmark_questions[{index}] must be an object.")
            question_id = cls._text(question, "question_id")
            if question_id in questions:
                raise ValueError("benchmark_questions cannot duplicate question_id.")
            questions[question_id] = {
                "question_id": question_id,
                "prompt": cls._text(question, "prompt"),
                "expected_numeric_answer": cls._number(
                    question,
                    "expected_numeric_answer",
                ),
                "expected_unit": cls._text(question, "expected_unit").upper(),
                "numeric_tolerance": cls._number(question, "numeric_tolerance"),
                "position_bucket": cls._text(question, "position_bucket"),
            }
        return questions

    @classmethod
    def _cross_references(
        cls,
        truth: Mapping[str, Any],
        *,
        questions: Mapping[str, Mapping[str, Any]],
        footnotes: Mapping[str, Mapping[str, Any]],
        cells: Mapping[str, Mapping[str, Any]],
    ) -> dict[str, dict[str, tuple[str, ...]]]:
        raw_graph = truth.get("cross_reference_graph")
        if not isinstance(raw_graph, list) or not raw_graph:
            raise ValueError("cross_reference_graph must be a non-empty list.")
        graph: dict[str, dict[str, tuple[str, ...]]] = {}
        for index, edge in enumerate(raw_graph):
            if not isinstance(edge, Mapping):
                raise TypeError(f"cross_reference_graph[{index}] must be an object.")
            question_id = cls._text(edge, "question_id")
            if question_id not in questions:
                raise ValueError("cross_reference_graph references unknown question_id.")
            footnote_ids = cls._text_list(edge, "required_footnote_ids")
            cell_ids = cls._text_list(edge, "required_cell_ids")
            unknown_footnotes = set(footnote_ids).difference(footnotes)
            unknown_cells = set(cell_ids).difference(cells)
            if unknown_footnotes or unknown_cells:
                raise ValueError("cross_reference_graph references unknown nodes.")
            graph[question_id] = {
                "required_footnote_ids": footnote_ids,
                "required_cell_ids": cell_ids,
            }
        missing_questions = set(questions).difference(graph)
        if missing_questions:
            raise ValueError("cross_reference_graph must cover every question.")
        return graph

    @classmethod
    def _spans(
        cls,
        ai_data: Mapping[str, Any],
        footnotes: Mapping[str, Mapping[str, Any]],
    ) -> dict[str, dict[str, Any]]:
        raw_spans = ai_data.get("cited_evidence_spans")
        if not isinstance(raw_spans, list):
            raise TypeError("cited_evidence_spans must be a list.")
        spans: dict[str, dict[str, Any]] = {}
        for index, span in enumerate(raw_spans):
            if not isinstance(span, Mapping):
                raise TypeError(f"cited_evidence_spans[{index}] must be an object.")
            span_id = cls._text(span, "span_id")
            if span_id in spans:
                raise ValueError("cited_evidence_spans cannot duplicate span_id.")
            footnote_id = cls._text(span, "footnote_id")
            if footnote_id not in footnotes:
                raise ValueError("cited_evidence_spans references unknown footnote_id.")
            start_char = int(cls._number(span, "start_char"))
            end_char = int(cls._number(span, "end_char"))
            if start_char < 0 or end_char <= start_char:
                raise ValueError("cited_evidence_spans must use valid text ranges.")
            spans[span_id] = {
                "span_id": span_id,
                "footnote_id": footnote_id,
                "source_coordinate": cls._text(span, "source_coordinate"),
                "start_char": start_char,
                "end_char": end_char,
                "text": cls._text(span, "text"),
            }
        return spans

    @classmethod
    def _answers(cls, ai_data: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
        raw_answers = ai_data.get("ai_answers")
        if not isinstance(raw_answers, list):
            raise TypeError("ai_answers must be a list.")
        answers: dict[str, dict[str, Any]] = {}
        for index, answer in enumerate(raw_answers):
            if not isinstance(answer, Mapping):
                raise TypeError(f"ai_answers[{index}] must be an object.")
            question_id = cls._text(answer, "question_id")
            if question_id in answers:
                raise ValueError("ai_answers cannot duplicate question_id.")
            answers[question_id] = {
                "question_id": question_id,
                "answer_text": cls._text(answer, "answer_text"),
                "numeric_answer": cls._number(answer, "numeric_answer"),
                "unit": cls._text(answer, "unit").upper(),
                "cited_span_ids": cls._text_list(answer, "cited_span_ids"),
                "cited_cell_ids": cls._text_list(answer, "cited_cell_ids"),
            }
        return answers

    def execute_audit(self, ai_output: dict, ground_truth: dict) -> dict:
        ai_data, truth = self.validate_inputs(ai_output, ground_truth)
        source_id = self._text(truth, "source_id")
        filing_id = self._text(truth, "filing_id")
        footnotes = self._footnotes(truth)
        cells = self._table_cells(truth, footnotes)
        questions = self._questions(truth)
        graph = self._cross_references(
            truth,
            questions=questions,
            footnotes=footnotes,
            cells=cells,
        )
        spans = self._spans(ai_data, footnotes)
        answers = self._answers(ai_data)

        unresolved_references: list[str] = []
        contradicted_values: list[str] = []
        citation_defects: list[str] = []
        correct_by_bucket: dict[str, int] = {}
        total_by_bucket: dict[str, int] = {}
        precise_citations = 0
        required_citations = 0

        for question_id, question in questions.items():
            bucket = question["position_bucket"]
            total_by_bucket[bucket] = total_by_bucket.get(bucket, 0) + 1
            answer = answers.get(question_id)
            if answer is None:
                unresolved_references.append(question_id)
                continue

            edge = graph[question_id]
            cited_span_ids = set(answer["cited_span_ids"])
            cited_cell_ids = set(answer["cited_cell_ids"])
            cited_footnote_ids = {
                spans[span_id]["footnote_id"]
                for span_id in cited_span_ids
                if span_id in spans
            }

            missing_spans = cited_span_ids.difference(spans)
            missing_cells = cited_cell_ids.difference(cells)
            if missing_spans or missing_cells:
                unresolved_references.append(question_id)
                continue

            required_footnotes = set(edge["required_footnote_ids"])
            required_cells = set(edge["required_cell_ids"])
            if not required_footnotes.issubset(cited_footnote_ids):
                unresolved_references.append(question_id)
            if not required_cells.issubset(cited_cell_ids):
                unresolved_references.append(question_id)

            numeric_delta = abs(
                answer["numeric_answer"] - question["expected_numeric_answer"]
            )
            if numeric_delta > question["numeric_tolerance"]:
                contradicted_values.append(f"{question_id}.numeric_answer")
            if answer["unit"] != question["expected_unit"]:
                contradicted_values.append(f"{question_id}.unit")

            question_citation_precise = True
            for span_id in answer["cited_span_ids"]:
                required_citations += 1
                span = spans[span_id]
                footnote = footnotes[span["footnote_id"]]
                if (
                    span["start_char"] < footnote["start_char"]
                    or span["end_char"] > footnote["end_char"]
                ):
                    citation_defects.append(f"{span_id}.text_range")
                    question_citation_precise = False
                expected_coordinates = {
                    cells[cell_id]["source_coordinate"]
                    for cell_id in required_cells
                }
                if span["source_coordinate"] not in expected_coordinates:
                    citation_defects.append(f"{span_id}.source_coordinate")
                    question_citation_precise = False
                else:
                    precise_citations += 1

            if (
                question_id not in unresolved_references
                and not any(item.startswith(f"{question_id}.") for item in contradicted_values)
                and question_citation_precise
            ):
                correct_by_bucket[bucket] = correct_by_bucket.get(bucket, 0) + 1

        unresolved_references = sorted(set(unresolved_references))
        contradicted_values = sorted(set(contradicted_values))
        citation_defects = sorted(set(citation_defects))
        position_bucket_accuracy = {
            bucket: round(correct_by_bucket.get(bucket, 0) / total, 4)
            for bucket, total in sorted(total_by_bucket.items())
        }
        citation_precision = (
            1.0
            if required_citations == 0
            else round(precise_citations / required_citations, 4)
        )
        context_integrity = round(
            sum(correct_by_bucket.values()) / max(len(questions), 1),
            4,
        )
        approved = (
            not unresolved_references
            and not contradicted_values
            and not citation_defects
            and context_integrity == 1.0
        )

        if approved:
            rigor_score = 5.0
            feedback = (
                "APPROVED: benchmark answers, table cells, footnotes, and "
                "source coordinates reconcile across all tested filing positions."
            )
        elif unresolved_references:
            rigor_score = 2.0
            feedback = (
                "REJECTED: at least one benchmark question has unresolved "
                "footnote or table cross-reference evidence."
            )
        elif contradicted_values:
            rigor_score = 2.5
            feedback = (
                "REJECTED: at least one answer contradicts the declared filing "
                "table value or unit."
            )
        else:
            rigor_score = 3.0
            feedback = (
                "REJECTED: citation coordinates do not precisely support the "
                "answer evidence."
            )

        scorecard = self.build_scorecard(
            rigor_score=rigor_score,
            approved=approved,
            feedback=feedback,
            evidence={
                "source_id": source_id,
                "filing_id": filing_id,
                "question_count": len(questions),
                "footnote_count": len(footnotes),
                "table_cell_count": len(cells),
            },
        )
        scorecard.update(
            {
                "context_retrieval_integrity": context_integrity,
                "unresolved_references": unresolved_references,
                "position_bucket_accuracy": position_bucket_accuracy,
                "citation_precision": citation_precision,
                "citation_defects": citation_defects,
                "contradicted_values": contradicted_values,
            }
        )
        return scorecard


def _load_json_object(path: Path) -> dict[str, Any]:  # pragma: no cover
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object.")
    return payload


def main() -> int:  # pragma: no cover
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ai-output", type=Path, required=True)
    parser.add_argument("--ground-truth", type=Path, required=True)
    arguments = parser.parse_args()
    result = SecFootnoteReasoningAuditor().execute_audit(
        _load_json_object(arguments.ai_output),
        _load_json_object(arguments.ground_truth),
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
