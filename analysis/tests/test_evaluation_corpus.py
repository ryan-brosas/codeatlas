from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass

from codeatlas_analysis.architecture_view import build_architecture_view
from codeatlas_analysis.change_impact import analyze_change_impact
from codeatlas_analysis.cited_answers import AnswerStatus, answer_question
from codeatlas_analysis.repository_acquisition import RepositoryFile, RepositorySnapshot
from codeatlas_analysis.repository_intake import normalize_public_github_repository
from codeatlas_analysis.repository_structure import RepositoryStructure, analyze_repository
from codeatlas_analysis.retrieval import RetrievalStatus, SourceCitation
from codeatlas_analysis.tree_sitter_parser import parse_source_module

_PROXIMITY_WARNING = "Dependency proximity identifies possible impact, not certainty."


@dataclass(frozen=True, slots=True)
class QuestionCase:
    name: str
    query: str
    expected_status: AnswerStatus
    expected_citation: SourceCitation | None


@dataclass(frozen=True, slots=True)
class ImpactCase:
    name: str
    query: str
    expected_candidate: SourceCitation
    expected_impacts: tuple[tuple[str, int], ...]
    required_warning: str


@dataclass(frozen=True, slots=True)
class EvaluationResult:
    case: str
    metric: str
    passed: bool


@dataclass(frozen=True, slots=True)
class EvaluationReport:
    results: tuple[EvaluationResult, ...]

    def metric_pass_rates(self) -> dict[str, float]:
        grouped: dict[str, list[bool]] = defaultdict(list)
        for result in self.results:
            grouped[result.metric].append(result.passed)
        return {
            metric: sum(outcomes) / len(outcomes) for metric, outcomes in sorted(grouped.items())
        }

    def as_dict(self) -> dict[str, object]:
        rates = self.metric_pass_rates()
        return {
            "cases": len({result.case for result in self.results}),
            "checks": len(self.results),
            "overall_pass_rate": sum(result.passed for result in self.results) / len(self.results),
            "metric_pass_rates": rates,
            "failures": [
                {"case": result.case, "metric": result.metric}
                for result in self.results
                if not result.passed
            ],
        }


def _structure() -> RepositoryStructure:
    sources = (
        (
            "src/core/session.ts",
            "export function validateSession() { return true; }\n",
        ),
        (
            "src/core/session.d.ts",
            "export const validateSessionBackup: unique symbol;\n",
        ),
        (
            "src/features/login.ts",
            'import { validateSession } from "../core/session";\n'
            "export function login() { return validateSession(); }\n",
        ),
        (
            "src/app.ts",
            'import { login } from "./features/login";\n'
            "export function start() { return login(); }\n",
        ),
        (
            "src/external.ts",
            'import React, { useState } from "react";\n'
            "export const external = [React, useState];\n",
        ),
    )
    snapshot = RepositorySnapshot(
        repository=normalize_public_github_repository(
            "https://github.com/example/evaluation-fixture"
        ),
        revision="0123456789abcdef0123456789abcdef01234567",
        files=tuple(
            RepositoryFile(path=path, content=source, size_bytes=len(source.encode()))
            for path, source in sources
        ),
    )
    return analyze_repository(snapshot, parse_source_module)


def evaluate_corpus() -> EvaluationReport:
    structure = _structure()
    question_cases = (
        QuestionCase(
            name="exact-source-citation",
            query="Where is validateSession defined?",
            expected_status=AnswerStatus.ANSWERED,
            expected_citation=SourceCitation(
                path="src/core/session.ts",
                start_line=1,
                end_line=1,
                symbol="validateSession",
            ),
        ),
        QuestionCase(
            name="controlled-insufficient-evidence",
            query="How does customer billing work?",
            expected_status=AnswerStatus.INSUFFICIENT_EVIDENCE,
            expected_citation=None,
        ),
    )
    impact_cases = (
        ImpactCase(
            name="exact-change-impact",
            query="Where is validateSession implemented?",
            expected_candidate=SourceCitation(
                path="src/core/session.ts",
                start_line=1,
                end_line=1,
                symbol="validateSession",
            ),
            expected_impacts=(("src/features/login.ts", 1), ("src/app.ts", 2)),
            required_warning=_PROXIMITY_WARNING,
        ),
    )
    results: list[EvaluationResult] = []

    for question_case in question_cases:
        answer = answer_question(structure, question_case.query)
        results.append(
            EvaluationResult(
                case=question_case.name,
                metric="expected_status",
                passed=answer.status is question_case.expected_status,
            )
        )
        if question_case.expected_citation is None:
            supported = not answer.facts and not answer.evidence and not answer.inference
        else:
            citations = tuple(citation for fact in answer.facts for citation in fact.citations)
            supported = question_case.expected_citation in citations and all(
                fact.citations for fact in answer.facts
            )
        results.append(
            EvaluationResult(
                case=question_case.name,
                metric="citation_support",
                passed=supported,
            )
        )

    for impact_case in impact_cases:
        report = analyze_change_impact(structure, impact_case.query)
        candidate = report.candidates[0].citation if report.candidates else None
        results.extend(
            (
                EvaluationResult(
                    case=impact_case.name,
                    metric="expected_status",
                    passed=report.status is RetrievalStatus.FOUND,
                ),
                EvaluationResult(
                    case=impact_case.name,
                    metric="candidate_location",
                    passed=candidate == impact_case.expected_candidate,
                ),
                EvaluationResult(
                    case=impact_case.name,
                    metric="impact_traversal",
                    passed=tuple((impact.path, impact.depth) for impact in report.impacts)
                    == impact_case.expected_impacts,
                ),
                EvaluationResult(
                    case=impact_case.name,
                    metric="warning_preservation",
                    passed=impact_case.required_warning in report.warnings,
                ),
            )
        )

    architecture = build_architecture_view(structure)
    limitation_keys = tuple(
        (item.code, item.path, item.line, item.subject) for item in architecture.limitations
    )
    results.append(
        EvaluationResult(
            case="unique-limitations",
            metric="unique_limitations",
            passed=len(limitation_keys) == len(set(limitation_keys)) == 1,
        )
    )
    return EvaluationReport(results=tuple(results))


def test_offline_evaluation_corpus_passes_every_metric() -> None:
    report = evaluate_corpus()

    assert report.as_dict() == {
        "cases": 4,
        "checks": 9,
        "overall_pass_rate": 1.0,
        "metric_pass_rates": {
            "candidate_location": 1.0,
            "citation_support": 1.0,
            "expected_status": 1.0,
            "impact_traversal": 1.0,
            "unique_limitations": 1.0,
            "warning_preservation": 1.0,
        },
        "failures": [],
    }


if __name__ == "__main__":
    print(json.dumps(evaluate_corpus().as_dict(), indent=2, sort_keys=True))
