#!/usr/bin/env python3
"""
exact_arithmetic_audit.py

Audit proof scripts for exact integer arithmetic markers and sampled-proof
leaks. This script performs static/source and report checks; it does not run
random seeds and does not claim a proof.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


OUT = Path("exact_arithmetic_audit_report.json")
SCRIPTS = [
    "exact_depth_closure.py",
    "quotient_parent_batch_audit.py",
    "frontier_return_map.py",
    "b_control_test.py",
    "frontier_coverage_audit.py",
    "residue_partition_exhaustiveness.py",
    "residue_density_partition_audit.py",
    "quotient_key_validity_audit.py",
    "quotient_abstraction_validity.py",
    "quotient_transition_table_export.py",
    "quotient_transition_table_audit.py",
    "quotient_exact_state_fallback_audit.py",
    "quotient_key_schema_review.py",
    "final_certificate_audit.py",
]
REPORTS = [
    "exact_depth_closure_report.json",
    "quotient_parent_batch_report.json",
    "frontier_return_map_report.json",
    "b_control_report.json",
    "frontier_coverage_audit_report.json",
    "residue_partition_exhaustiveness_report.json",
    "residue_density_partition_audit_report.json",
    "quotient_key_validity_audit_report.json",
    "quotient_abstraction_validity_report.json",
    "quotient_transition_table_report.json",
    "quotient_transition_table.json",
    "quotient_transition_table_audit_report.json",
    "quotient_exact_state_fallback_audit_report.json",
    "quotient_key_schema_review_report.json",
]


def load_json(path: Path) -> Any:
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def scan_script(path_name: str) -> dict[str, Any]:
    path = Path(path_name)
    if not path.exists():
        return {"path": path_name, "exists": False, "pass": False, "reason": "missing"}
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    exact_gap = bool(re.search(r"\(1\s*<<\s*c\)\s*-\s*(a|\(3\s*\*\*\s*o\)|3\s*\*\*\s*o)", text))
    exact_ceil = "(b + gap - 1) // gap" in text or "ceil_div" in text or "(b + denom - 1) // denom" in text
    integer_marker = "integer" in text.lower() or "Fraction" in text
    random_seed_use = [
        {"line": i, "text": line.strip()}
        for i, line in enumerate(lines, 1)
        if re.search(r"\brandom\b|seed", line, re.IGNORECASE)
    ]
    float_or_log_lines = [
        {"line": i, "text": line.strip()}
        for i, line in enumerate(lines, 1)
        if re.search(r"\bfloat\b|math\.log|log2", line)
    ]
    suspicious_float_decision_lines = [
        item
        for item in float_or_log_lines
        if any(op in item["text"] for op in ("<", ">", "<=", ">=", "=="))
        and "diagnostic" not in item["text"].lower()
        and "display" not in item["text"].lower()
    ]
    proof_computation_scripts = {
        "exact_depth_closure.py",
        "quotient_parent_batch_audit.py",
        "frontier_return_map.py",
        "b_control_test.py",
    }
    if path_name in proof_computation_scripts:
        pass_ok = (exact_gap or exact_ceil) and not suspicious_float_decision_lines
    else:
        pass_ok = not suspicious_float_decision_lines
    return {
        "path": path_name,
        "exists": True,
        "pass": pass_ok,
        "has_exact_gap_formula": exact_gap,
        "has_exact_ceiling_formula": exact_ceil,
        "has_integer_marker": integer_marker,
        "random_or_seed_lines": random_seed_use[:20],
        "float_or_log_lines": float_or_log_lines[:20],
        "suspicious_float_decision_lines": suspicious_float_decision_lines[:20],
    }


def report_sampled_leaks(path_name: str) -> dict[str, Any]:
    data = load_json(Path(path_name))
    if data is None:
        return {"path": path_name, "exists": False, "pass": False}
    text = json.dumps(data).lower()
    sampled_true = []

    def walk(value: Any, loc: str = "$") -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                low = str(key).lower()
                if low in {"sampled", "sampled_as_proof", "sampled_rows_used", "random_seeds"} and child not in (False, 0, None, [], {}):
                    sampled_true.append({"path": f"{loc}.{key}", "value": child})
                walk(child, f"{loc}.{key}")
        elif isinstance(value, list):
            for i, child in enumerate(value):
                walk(child, f"{loc}[{i}]")

    walk(data)
    return {
        "path": path_name,
        "exists": True,
        "pass": not sampled_true,
        "sampled_or_random_true": sampled_true[:50],
        "contains_sample_marker": "sample" in text,
    }


def main() -> None:
    source_checks = [scan_script(path) for path in SCRIPTS]
    report_checks = [report_sampled_leaks(path) for path in REPORTS]
    failures = [
        {"path": item["path"], "kind": "source", "item": item}
        for item in source_checks
        if not item.get("pass")
    ] + [
        {"path": item["path"], "kind": "report", "item": item}
        for item in report_checks
        if not item.get("pass")
    ]
    status = "PASS_EXACT_ARITHMETIC" if not failures else "FAIL_EXACT_ARITHMETIC"
    report = {
        "status": status,
        "plain_truth": (
            "This is a static exact-arithmetic and sampled-leak audit. It does not claim proof completion."
        ),
        "source_checks": source_checks,
        "report_sampled_checks": report_checks,
        "failures": failures,
    }
    with OUT.open("w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, sort_keys=True)

    print("EXACT ARITHMETIC AUDIT")
    print(f"  Status      : {status}")
    print(f"  Failures    : {len(failures)}")
    print(f"  Report      : {OUT}")


if __name__ == "__main__":
    main()
