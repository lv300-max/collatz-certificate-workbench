#!/usr/bin/env python3
"""
Final certificate pipeline audit.

This script audits the generated JSON reports. It does not run random seeds,
does not raise caps, and does not claim a complete proof. Proof-critical checks
use exact integer comparisons only.
"""

from __future__ import annotations

import ast
import json
import os
import re
from collections import Counter
from pathlib import Path
from typing import Any


B_LIMIT = 200_001
EXPECTED_PARENTS = 578
OUT = Path("final_certificate_audit_report.json")


def load_json(path: str, required: bool = True) -> Any:
    p = Path(path)
    if not p.exists():
        if required:
            raise FileNotFoundError(path)
        return None
    with p.open() as f:
        return json.load(f)


def key_id(value: Any) -> str:
    if isinstance(value, str):
        return value
    return json.dumps(value, separators=(",", ":"))


def as_int(value: Any, default: int = 0) -> int:
    if value is None:
        return default
    return int(value)


def list_json_reports(patterns: list[str]) -> list[str]:
    found: list[str] = []
    for p in Path(".").glob("*.json"):
        low = p.name.lower()
        if any(token in low for token in patterns):
            found.append(p.name)
    return sorted(found)


def parent_coverage_audit(batch: dict[str, Any]) -> dict[str, Any]:
    rows = batch.get("parent_rows", [])
    ids = [r.get("r0") for r in rows]
    counts = Counter(ids)
    duplicates = sorted(k for k, v in counts.items() if k is not None and v > 1)
    missing_field_rows = [r for r in rows if r.get("r0") is None]
    unclassified = [r.get("r0") for r in rows if not r.get("status")]
    summary = batch.get("summary", {})
    unprocessed = batch.get("unprocessed_parent_ids", [])

    passed = (
        as_int(summary.get("total_depth_gt_18_parents")) == EXPECTED_PARENTS
        and as_int(summary.get("processed_parents")) == EXPECTED_PARENTS
        and as_int(summary.get("missing_or_unprocessed_parents")) == 0
        and len(unprocessed) == 0
        and len(rows) == EXPECTED_PARENTS
        and not duplicates
        and not missing_field_rows
        and not unclassified
    )

    return {
        "pass": passed,
        "expected_total": EXPECTED_PARENTS,
        "reported_total": summary.get("total_depth_gt_18_parents"),
        "processed_parents": summary.get("processed_parents"),
        "unprocessed_parent_ids": unprocessed,
        "duplicate_parent_ids": duplicates,
        "missing_r0_rows": len(missing_field_rows),
        "unclassified_parent_ids": unclassified,
    }


def classification_audit(batch: dict[str, Any]) -> dict[str, Any]:
    rows = batch.get("parent_rows", [])
    row_counts = Counter(r.get("status", "UNCLASSIFIED") for r in rows)
    wanted = [
        "CLOSED_BY_QUOTIENT",
        "CLOSED_WITH_LOCAL_KEYS",
        "COVERED_BUT_CAP_REACHED",
        "PARTIAL",
        "BLOCKED",
        "CONFLICT",
        "NEEDS_HIGHER_LOCAL_CAP",
        "STILL_OPEN",
        "UNCLASSIFIED",
    ]
    counts = {k: row_counts.get(k, 0) for k in wanted}

    stale_summary_note = None
    summary_blocked = as_int(batch.get("summary", {}).get("partial_or_blocked_parents"))
    actual_bad_statuses = {
        k: v
        for k, v in counts.items()
        if k in {"PARTIAL", "BLOCKED", "CONFLICT", "NEEDS_HIGHER_LOCAL_CAP", "STILL_OPEN", "UNCLASSIFIED"}
        and v
    }
    if summary_blocked and not actual_bad_statuses:
        stale_summary_note = (
            "summary.partial_or_blocked_parents is conservative/stale for this audit; "
            "row statuses contain only closed or covered classifications."
        )

    conflict_rows = [r.get("r0") for r in rows if as_int(r.get("conflict_count")) > 0]
    local_still_rows = [r.get("r0") for r in rows if as_int(r.get("local_keys_still_open")) > 0]
    pass_ok = not actual_bad_statuses and not conflict_rows and not local_still_rows

    return {
        "pass": pass_ok,
        "counts": counts,
        "all_status_counts": dict(row_counts),
        "summary_partial_or_blocked_parents": summary_blocked,
        "stale_summary_note": stale_summary_note,
        "conflict_parent_ids": conflict_rows,
        "local_keys_still_open_parent_ids": local_still_rows,
    }


def local_key_audit(batch: dict[str, Any]) -> dict[str, Any]:
    rows = batch.get("parent_rows", [])
    allowed = {"CERTIFIED_RETURN", "HIGH_B_RETURN_THEN_CERTIFIED"}
    attempted = certified = high_b_certified = still_open = 0
    bad: list[dict[str, Any]] = []
    max_local_return_b = 0
    max_final_b = 0

    for row in rows:
        attempted += as_int(row.get("local_keys_attempted"))
        certified += as_int(row.get("local_keys_certified"))
        high_b_certified += as_int(row.get("local_keys_high_b_certified"))
        still_open += as_int(row.get("local_keys_still_open"))
        for ex in row.get("local_key_examples", []):
            cls = ex.get("classification")
            local_return_b = ex.get("B")
            final_b = ex.get("final_B", ex.get("B"))
            if cls == "HIGH_B_RETURN_THEN_CERTIFIED":
                final_b = ex.get("b_control_next", {}).get("B", final_b)
            local_return_b_int = as_int(local_return_b, -1) if local_return_b is not None else -1
            final_b_int = as_int(final_b, -1) if final_b is not None else -1
            max_local_return_b = max(max_local_return_b, local_return_b_int)
            max_final_b = max(max_final_b, final_b_int)
            reasons = []
            if cls not in allowed:
                reasons.append(f"bad classification {cls}")
            if not ex.get("key"):
                reasons.append("missing exact key")
            if not ex.get("return_pair"):
                reasons.append("missing return_pair")
            if final_b_int < 0:
                reasons.append("missing final B")
            elif final_b_int > B_LIMIT:
                reasons.append(f"final_B {final_b_int} > {B_LIMIT}")
            if reasons:
                bad.append({"parent_r0": row.get("r0"), "key": ex.get("key"), "reasons": reasons, "record": ex})

    pass_ok = still_open == 0 and not bad and attempted == certified + high_b_certified
    return {
        "pass": pass_ok,
        "local_keys_attempted": attempted,
        "local_keys_certified": certified,
        "local_keys_high_b_certified": high_b_certified,
        "local_keys_still_open": still_open,
        "max_local_return_B": max_local_return_b,
        "max_final_B": max_final_b,
        "bad_local_key_records": bad[:50],
        "bad_local_key_count": len(bad),
    }


def covered_cap_audit(batch: dict[str, Any]) -> dict[str, Any]:
    rows = [r for r in batch.get("parent_rows", []) if r.get("status") == "COVERED_BUT_CAP_REACHED"]
    parent_records: list[dict[str, Any]] = []
    bad: list[dict[str, Any]] = []

    for row in rows:
        open_count = as_int(row.get("open_key_count"))
        uncovered = as_int(row.get("uncovered_open_key_count"))
        covered = as_int(row.get("covered_open_key_count"))
        local_cert = as_int(row.get("local_keys_certified"))
        local_high = as_int(row.get("local_keys_high_b_certified"))
        local_open = as_int(row.get("local_keys_still_open"))

        coverage_source = "NONE"
        pass_reason = False
        if open_count == 0:
            coverage_source = "NO_OPEN_KEYS"
            pass_reason = True
        elif uncovered == 0 and covered == open_count:
            coverage_source = "ALL_OPEN_KEYS_RETURN_MAPPED_OR_FRONTIER_COVERED"
            pass_reason = True
        elif uncovered > 0 and local_open == 0 and uncovered == local_cert + local_high:
            coverage_source = "UNCOVERED_KEYS_CERTIFIED_BY_LOCAL_CONTINUATION"
            pass_reason = True

        max_final_b = 0
        for ex in row.get("local_key_examples", []):
            b = ex.get("final_B", ex.get("B"))
            if ex.get("classification") == "HIGH_B_RETURN_THEN_CERTIFIED":
                b = ex.get("b_control_next", {}).get("B", b)
            if b is not None:
                max_final_b = max(max_final_b, int(b))

        record = {
            "parent_r0": row.get("r0"),
            "coverage_source": coverage_source,
            "open_keys_count": open_count,
            "uncovered_keys_count": uncovered,
            "return_mapped_keys_count": covered,
            "high_B_keys_count": local_high,
            "high_B_certified_count": local_high,
            "max_final_B": max_final_b,
            "pass": pass_reason,
        }
        parent_records.append(record)
        if not pass_reason:
            bad.append(record)

    return {
        "pass": not bad,
        "covered_but_cap_reached_count": len(rows),
        "bad_count": len(bad),
        "bad_parent_records": bad[:100],
        "parent_records": parent_records,
    }


def frontier_coverage_audit(frontier_cov: dict[str, Any]) -> dict[str, Any]:
    s = frontier_cov.get("summary", {})
    checks = frontier_cov.get("checks", {})
    q_open = as_int(s.get("quotient_open_keys"))
    exported = as_int(s.get("quotient_open_frontier_exported"))
    mapped = as_int(s.get("return_map_records"))
    passed = (
        q_open == exported
        and mapped == q_open
        and as_int(s.get("still_debt_keys")) == 0
        and as_int(s.get("conflicts")) == 0
        and checks.get("every_high_B_key_B_controlled") is True
        and checks.get("every_high_B_eventually_certified") is True
        and as_int(s.get("final_B_over_limit")) == 0
        and as_int(s.get("max_final_B")) <= B_LIMIT
        and s.get("pass") is True
    )
    return {"pass": passed, "summary": s, "checks": checks}


def b_control_audit(bc: dict[str, Any]) -> dict[str, Any]:
    s = bc.get("summary", {})
    total = as_int(s.get("high_B_states_analyzed"))
    eventually = as_int(s.get("B_EVENTUALLY_CERTIFIED"))
    class_counts = s.get("classification_counts", {})
    bad_classes = {
        k: v
        for k, v in class_counts.items()
        if k not in {"B_EVENTUALLY_CERTIFIED"} and as_int(v) > 0
    }
    chains = bc.get("high_B_chains", [])
    missing_key_ids = [i for i, rec in enumerate(chains) if not rec.get("key")]
    passed = (
        total == eventually
        and as_int(s.get("B_GROWS")) == 0
        and as_int(s.get("STILL_OPEN")) == 0
        and as_int(s.get("max_later_B")) <= B_LIMIT
        and not bad_classes
        and not missing_key_ids
    )
    return {
        "pass": passed,
        "summary": s,
        "bad_classification_counts": bad_classes,
        "missing_high_B_key_record_indices": missing_key_ids[:50],
    }


def return_map_audit(rm: dict[str, Any]) -> dict[str, Any]:
    s = rm.get("summary", {})
    total = as_int(s.get("open_states_analyzed"))
    cert = as_int(s.get("certified_returns"))
    high = as_int(s.get("high_B_returns"))
    records = rm.get("return_records", [])
    bad_record_indices = [
        i
        for i, rec in enumerate(records)
        if rec.get("classification") not in {"CERTIFIED_RETURN", "HIGH_B_RETURN"}
        or not rec.get("return_pair")
    ]
    passed = (
        cert + high == total
        and len(records) == total
        and as_int(s.get("still_debt_at_cap")) == 0
        and as_int(s.get("conflicts")) == 0
        and not bad_record_indices
    )
    return {"pass": passed, "summary": s, "bad_record_indices": bad_record_indices[:50]}


def direct_bridge_audit() -> dict[str, Any]:
    bridge_report = load_json("direct_bridge_report.json", required=False)
    if isinstance(bridge_report, dict):
        s = bridge_report.get("summary", bridge_report)
        failures = s.get("failures", [])
        odd_min = as_int(s.get("odd_min"))
        odd_max = as_int(s.get("odd_max"))
        failure_count = as_int(s.get("failure_count", len(failures) if isinstance(failures, list) else 0))
        passed = (
            s.get("final_status") in ("PASS_DIRECT_BRIDGE", "PASS", None)
            and odd_min <= 3
            and odd_max >= B_LIMIT
            and failure_count == 0
        )
        return {
            "status": "PASS" if passed else "FAIL",
            "pass": passed,
            "source": "direct_bridge_report.json",
            "odd_min": odd_min,
            "odd_max": odd_max,
            "checked": s.get("checked"),
            "failure_count": failure_count,
            "final_status": s.get("final_status"),
        }

    cert = load_json("collatz_certificate.json", required=False)
    if not cert:
        return {"status": "MISSING", "pass": False, "missing": "DIRECT_BRIDGE_REPORT_MISSING"}
    dv = cert.get("direct_verification", {})
    meta = cert.get("meta", {})
    failures = dv.get("failures", [])
    odd_min = as_int(dv.get("odd_min"))
    odd_max = as_int(dv.get("odd_max"))
    direct_failures = as_int(meta.get("direct_failures", len(failures)))
    passed = odd_min <= 3 and odd_max >= B_LIMIT and not failures and direct_failures == 0
    return {
        "status": "PASS" if passed else "FAIL",
        "pass": passed,
        "source": "collatz_certificate.json",
        "odd_min": odd_min,
        "odd_max": odd_max,
        "checked": dv.get("checked"),
        "failure_count": len(failures),
        "meta_direct_failures": meta.get("direct_failures"),
    }


def exact_depth_audit() -> dict[str, Any]:
    exact_report = load_json("exact_depth_closure_report.json", required=False)
    if isinstance(exact_report, dict):
        s = exact_report.get("summary", {})
        method = exact_report.get("method", {})
        sampled = s.get("sampled_rows_used", method.get("sampled_rows_used"))
        passed = (
            s.get("final_status") == "PASS_EXACT_DEPTH"
            and as_int(s.get("max_exact_depth_closed")) >= 18
            and as_int(s.get("exact_parents_closed")) == as_int(s.get("exact_parents_total"))
            and as_int(s.get("exact_parents_closed")) > 0
            and as_int(s.get("exact_siblings_verified")) > 0
            and as_int(s.get("exact_failures")) == 0
            and as_int(s.get("max_B")) <= B_LIMIT
            and sampled in (0, False)
            and method.get("integer_checks_only_for_proof") is True
        )
        return {
            "status": "PASS" if passed else "FAIL",
            "pass": passed,
            "source": "exact_depth_closure_report.json",
            "summary": s,
            "method": method,
        }

    candidates = list_json_reports(["exact", "depth", "sibling", "closure", "certificate"])
    usable: list[dict[str, Any]] = []
    reject_notes: list[dict[str, Any]] = []

    for name in candidates:
        data = load_json(name, required=False)
        if not isinstance(data, dict):
            continue
        text = json.dumps(data).lower()
        if "sampled" in text or "sample" in text:
            reject_notes.append({"report": name, "reason": "contains sampled/sample markers"})
        cap = data.get("meta", {}).get("exhaustive_depth_cap") if isinstance(data.get("meta"), dict) else data.get("exhaustive_depth_cap")
        exact_failures = None
        for key in ("exact_failures", "failures", "sibling_failures", "closure_failures"):
            if key in data:
                exact_failures = data[key]
            elif isinstance(data.get("meta"), dict) and key in data["meta"]:
                exact_failures = data["meta"][key]
        if cap is not None and int(cap) >= 18 and exact_failures in (0, [], None) and "sample" not in text:
            usable.append({"report": name, "exhaustive_depth_cap": cap, "failures": exact_failures})

    if usable:
        return {"status": "PASS", "pass": True, "usable_reports": usable, "candidate_reports": candidates}
    return {
        "status": "MISSING",
        "pass": False,
        "missing": "EXACT_DEPTH_REPORT_MISSING",
        "candidate_reports": candidates,
        "rejected_reports": reject_notes[:20],
        "reason": "No exact, unsampled report found proving depth <= 18 closure with zero failures.",
    }


def quotient_key_validity_audit() -> dict[str, Any]:
    report = load_json("quotient_key_validity_audit_report.json", required=False)
    if not isinstance(report, dict):
        return {
            "status": "MISSING",
            "pass": False,
            "missing": "QUOTIENT_KEY_VALIDITY_AUDIT_REPORT_MISSING",
        }
    passed = (
        report.get("status") == "PASS_QUOTIENT_KEY_VALIDITY"
        and report.get("sampled_as_proof_count") == 0
        and report.get("parent_batch_audit", {}).get("pass") is True
        and report.get("frontier_coverage_audit", {}).get("pass") is True
        and report.get("return_map_audit", {}).get("pass") is True
        and report.get("b_control_audit", {}).get("pass") is True
    )
    return {
        "status": "PASS" if passed else "FAIL",
        "pass": passed,
        "source": "quotient_key_validity_audit_report.json",
        "summary": {
            "quotient_key_status": report.get("status"),
            "sampled_as_proof_count": report.get("sampled_as_proof_count"),
            "transition_table_exported": report.get("method", {}).get("transition_table_exported"),
            "parent_batch_pass": report.get("parent_batch_audit", {}).get("pass"),
            "frontier_coverage_pass": report.get("frontier_coverage_audit", {}).get("pass"),
            "return_map_pass": report.get("return_map_audit", {}).get("pass"),
            "b_control_pass": report.get("b_control_audit", {}).get("pass"),
        },
        "plain_truth": (
            "This gates the final pipeline on the exported quotient-key validity audit. "
            "Full independent quotient replay still requires transition-table export."
        ),
    }


def source_contains_exact_formulas(path: str) -> dict[str, Any]:
    p = Path(path)
    if not p.exists():
        return {"path": path, "exists": False, "pass": False}
    src = p.read_text()
    has_floor_ceil = "(a + b - 1) // b" in src or "(b + gap - 1) // gap" in src or "ceil_div" in src
    has_gap = "(1 << c) - (3 ** o)" in src or "(1 << c) - a" in src or "2^c - 3^o" in src
    has_int_method = "integer_checks_only" in src or "Python integers" in src or "Python int" in src
    float_lines = []
    for i, line in enumerate(src.splitlines(), 1):
        if re.search(r"\b(float|math\.log|log2)\b", line):
            float_lines.append({"line": i, "text": line.strip()[:160]})
    return {
        "path": path,
        "exists": True,
        "pass": has_floor_ceil and has_gap,
        "has_integer_method_marker": has_int_method,
        "has_integer_ceiling_formula": has_floor_ceil,
        "has_exact_gap_formula": has_gap,
        "float_or_log_lines": float_lines[:20],
    }


def exact_arithmetic_audit(reports: dict[str, dict[str, Any]]) -> dict[str, Any]:
    scripts = [
        "frontier_return_map.py",
        "b_control_test.py",
        "quotient_parent_batch_audit.py",
        "frontier_coverage_audit.py",
        "certificate_verify.py",
    ]
    script_checks = [source_contains_exact_formulas(p) for p in scripts]
    methods = {
        name: data.get("method", {})
        for name, data in reports.items()
        if isinstance(data, dict) and isinstance(data.get("method"), dict)
    }
    method_flags_ok = all(
        m.get("random_seeds") is not True and m.get("global_caps_increased") is not True
        for m in methods.values()
    )
    integer_flags_ok = (
        reports["frontier_return_map"].get("method", {}).get("integer_checks_only") is True
        and reports["b_control"].get("method", {}).get("integer_checks_only") is True
    )
    formula_ok = all(c["pass"] for c in script_checks[:3])
    passed = method_flags_ok and integer_flags_ok and formula_ok
    return {
        "pass": passed,
        "method_flags_ok": method_flags_ok,
        "integer_report_flags_ok": integer_flags_ok,
        "source_formula_checks_ok": formula_ok,
        "source_checks": script_checks,
        "note": "Float/log occurrences are reported for review; pass requires exact integer formulas in proof-critical pipeline scripts.",
    }


def collect_failures(audits: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    labels = [
        ("parent_coverage", "Parent coverage failed"),
        ("classification", "Classification audit failed"),
        ("local_keys", "Local key audit failed"),
        ("covered_but_cap_reached", "Covered-but-cap-reached audit failed"),
        ("frontier_coverage", "Frontier coverage audit failed"),
        ("b_control", "B-control audit failed"),
        ("return_map", "Return-map audit failed"),
        ("quotient_key_validity", "Quotient-key validity audit failed"),
        ("exact_arithmetic", "Exact arithmetic audit failed"),
    ]
    for key, label in labels:
        if not audits[key].get("pass"):
            failures.append(label)
    if audits["direct_bridge"].get("status") == "MISSING":
        failures.append("DIRECT_BRIDGE_REPORT_MISSING")
    elif not audits["direct_bridge"].get("pass"):
        failures.append("Direct bridge failed")
    if audits["exact_depth"].get("status") == "MISSING":
        failures.append("EXACT_DEPTH_REPORT_MISSING")
    elif not audits["exact_depth"].get("pass"):
        failures.append("Exact depth audit failed")

    pc = audits["parent_coverage"]
    if pc.get("unprocessed_parent_ids"):
        failures.append(f"Unprocessed parent IDs: {pc['unprocessed_parent_ids'][:20]}")
    if pc.get("duplicate_parent_ids"):
        failures.append(f"Duplicate parent IDs: {pc['duplicate_parent_ids'][:20]}")
    lk = audits["local_keys"]
    if lk.get("bad_local_key_count"):
        failures.append(f"Bad local key records: {lk['bad_local_key_count']}")
    cbc = audits["covered_but_cap_reached"]
    if cbc.get("bad_count"):
        failures.append(f"Unjustified COVERED_BUT_CAP_REACHED parents: {cbc['bad_count']}")
    return failures


def load_report_status(path: str, pass_status: str) -> tuple[str, dict[str, Any]]:
    data = load_json(path, required=False)
    if not isinstance(data, dict):
        return "INCOMPLETE", {"missing": path}
    status = data.get("status")
    if status == pass_status:
        return "PASS", data
    if isinstance(status, str) and status.startswith("FAIL"):
        return "FAIL", data
    return "INCOMPLETE", data


def load_full_framework_status() -> tuple[str, dict[str, Any]]:
    data = load_json("full_framework_closure_audit_report.json", required=False)
    if not isinstance(data, dict):
        return "INCOMPLETE", {"missing": "full_framework_closure_audit_report.json"}
    report_status = data.get("status")
    if report_status == "PASS_FULL_FRAMEWORK_EXACT_STATE_CLOSURE":
        return "PASS", data
    if report_status == "PASS_PIPELINE_BUT_QUOTIENT_DEPENDENCE_REMAINS":
        return "QUOTIENT_DEPENDENCE", data
    if report_status == "FAIL_FULL_FRAMEWORK_CLOSURE":
        return "FAIL", data
    return "INCOMPLETE", data


def audit_status(pass_value: bool, missing: bool = False) -> str:
    if missing:
        return "INCOMPLETE"
    return "PASS" if pass_value else "FAIL"


def build_master_checks(audits: dict[str, Any]) -> tuple[dict[str, str], dict[str, Any]]:
    source_status, source_report = load_report_status(
        "master_source_coverage_audit_report.json", "PASS"
    )
    residue_status, residue_report = load_report_status(
        "residue_partition_exhaustiveness_report.json", "PASS_RESIDUE_PARTITION_EXHAUSTIVENESS"
    )
    density_status, density_report = load_report_status(
        "residue_density_partition_audit_report.json", "PASS_DENSITY_PARTITION"
    )
    exact_arithmetic_status, exact_arithmetic_report = load_report_status(
        "exact_arithmetic_audit_report.json", "PASS_EXACT_ARITHMETIC"
    )
    exact_state_status, exact_state_report = load_report_status(
        "exact_state_closure_report.json", "PASS_EXACT_STATE_CLOSURE"
    )
    full_framework_status, full_framework_report = load_full_framework_status()
    quotient_abs = load_json("quotient_abstraction_validity_report.json", required=False)
    key_schema = load_json("quotient_key_schema_review_report.json", required=False)
    if not isinstance(quotient_abs, dict):
        quotient_abs_status = "INCOMPLETE"
        quotient_abs = {"missing": "quotient_abstraction_validity_report.json"}
    elif quotient_abs.get("status") == "PASS_QUOTIENT_ABSTRACTION":
        quotient_abs_status = "PASS"
    elif quotient_abs.get("status") == "FAIL_QUOTIENT_ABSTRACTION":
        quotient_abs_status = "FAIL"
    elif quotient_abs.get("status") == "PASS_TRACKED_QUOTIENT_TRANSITION_TABLE":
        quotient_abs_status = "TRACKED_PASS"
    elif quotient_abs.get("status") == "PASS_TRACKED_QUOTIENT_TABLE_WITH_EXACT_STATE_FALLBACK":
        quotient_abs_status = "TRACKED_EXACT_PASS"
    else:
        quotient_abs_status = "INCOMPLETE"

    direct = audits["direct_bridge"]
    exact_depth = audits["exact_depth"]
    checks = {
        "Source coverage": source_status,
        "Residue partition": residue_status,
        "Density partition": density_status,
        "Exact depth": audit_status(exact_depth.get("pass"), exact_depth.get("status") == "MISSING"),
        "Direct bridge": audit_status(direct.get("pass"), direct.get("status") == "MISSING"),
        "Parent coverage": audit_status(
            audits["parent_coverage"].get("pass")
            and audits["classification"].get("pass")
            and audits["covered_but_cap_reached"].get("pass")
        ),
        "Local keys": audit_status(audits["local_keys"].get("pass")),
        "Frontier coverage": audit_status(audits["frontier_coverage"].get("pass")),
        "Return map": audit_status(audits["return_map"].get("pass")),
        "B-control": audit_status(audits["b_control"].get("pass")),
        "Exact arithmetic": exact_arithmetic_status,
        "Exact state closure": exact_state_status,
        "Full framework closure": full_framework_status,
        "Quotient abstraction": quotient_abs_status,
    }
    detail = {
        "source_coverage_report": source_report,
        "residue_partition_report": {
            "status": residue_report.get("status"),
            "missing": residue_report.get("missing"),
            "duplicates": residue_report.get("duplicates"),
            "bucket_counts": residue_report.get("bucket_counts"),
            "sampled_as_proof_count": residue_report.get("sampled_as_proof_count"),
        },
        "density_partition_report": {
            "status": density_report.get("status"),
            "common_modulus_power": density_report.get("common_modulus_power"),
            "covered_slots": density_report.get("covered_slots"),
            "missing_slots": density_report.get("missing_slots"),
            "duplicate_overlap_slots": density_report.get("duplicate_overlap_slots"),
            "sampled_as_proof_count": density_report.get("sampled_as_proof_count"),
            "density_sum_as_fraction": density_report.get("density_sum_as_fraction"),
        },
        "exact_arithmetic_report": exact_arithmetic_report,
        "exact_state_closure_report": exact_state_report,
        "full_framework_closure_report": full_framework_report,
        "quotient_abstraction_report": quotient_abs,
        "quotient_key_schema_review_report": key_schema or {"missing": "quotient_key_schema_review_report.json"},
    }
    return checks, detail


def final_master_status(master_checks: dict[str, str]) -> tuple[str, list[str]]:
    failures = [f"{name}: {status}" for name, status in master_checks.items() if status == "FAIL"]
    incompletes = [
        f"{name}: {status}"
        for name, status in master_checks.items()
        if status == "INCOMPLETE"
    ]
    if failures:
        return "FAIL_CERTIFICATE_FRAMEWORK", failures
    quotient_only_incomplete = (
        master_checks.get("Quotient abstraction") == "INCOMPLETE"
        and all(
            status == "PASS"
            for name, status in master_checks.items()
            if name != "Quotient abstraction"
        )
    )
    if quotient_only_incomplete:
        return "PASS_CERTIFICATE_PIPELINE_BUT_QUOTIENT_REVIEW_REQUIRED", []
    quotient_tracked_open = (
        master_checks.get("Quotient abstraction") == "TRACKED_PASS"
        and all(
            status == "PASS"
            for name, status in master_checks.items()
            if name != "Quotient abstraction"
        )
    )
    if quotient_tracked_open:
        return "PASS_PIPELINE_WITH_TRACKED_QUOTIENT_TABLE_BUT_FULL_EQUIVALENCE_REVIEW_REQUIRED", []
    full_framework_pass = (
        master_checks.get("Full framework closure") == "PASS"
        and master_checks.get("Quotient abstraction") == "TRACKED_EXACT_PASS"
        and all(
            status == "PASS"
            for name, status in master_checks.items()
            if name not in {"Quotient abstraction"}
        )
    )
    if full_framework_pass:
        return "PASS_FULL_FRAMEWORK_EXACT_STATE_CLOSURE", []
    full_framework_quotient_dependency = (
        master_checks.get("Full framework closure") == "QUOTIENT_DEPENDENCE"
        and master_checks.get("Quotient abstraction") == "TRACKED_EXACT_PASS"
        and all(
            status == "PASS"
            for name, status in master_checks.items()
            if name not in {"Quotient abstraction", "Full framework closure"}
        )
    )
    if full_framework_quotient_dependency:
        return "PASS_PIPELINE_BUT_QUOTIENT_DEPENDENCE_REMAINS", []
    exact_state_closure_pass = (
        master_checks.get("Quotient abstraction") == "TRACKED_EXACT_PASS"
        and master_checks.get("Exact state closure") == "PASS"
        and all(
            status == "PASS"
            for name, status in master_checks.items()
            if name not in {"Quotient abstraction"}
        )
    )
    if exact_state_closure_pass:
        return "PASS_PIPELINE_WITH_FULL_EXACT_STATE_CLOSURE", []
    quotient_tracked_exact_open = (
        master_checks.get("Quotient abstraction") == "TRACKED_EXACT_PASS"
        and all(
            status == "PASS"
            for name, status in master_checks.items()
            if name != "Quotient abstraction"
        )
    )
    if quotient_tracked_exact_open:
        return "PASS_PIPELINE_WITH_EXACT_STATE_FALLBACK_BUT_FULL_EQUIVALENCE_REVIEW_REQUIRED", []
    if incompletes:
        return "INCOMPLETE_CERTIFICATE_FRAMEWORK", incompletes
    return "PASS_CERTIFICATE_FRAMEWORK_STRUCTURAL_AUDIT", []


def print_summary(report: dict[str, Any]) -> None:
    if "master_checks" in report:
        print("FINAL MASTER CERTIFICATE AUDIT")
        print()
        for name, status in report["master_checks"].items():
            print(f"{name}: {status}")
        print()
        print(f"Final status: {report['final_status']}")
        if report.get("incomplete_reasons"):
            print("Reasons:")
            for item in report["incomplete_reasons"]:
                print(f"- {item}")
        return

    a = report["audits"]
    def pf(key: str) -> str:
        return "PASS" if a[key].get("pass") else "FAIL"

    if report["final_status"] == "PASS_CERTIFICATE_PIPELINE":
        print("PASS_CERTIFICATE_PIPELINE:")
        print(
            "All tracked parent obstructions were covered by the certificate pipeline "
            "under exact integer arithmetic. Independent mathematical review is still "
            "required to verify that the certificate framework is logically exhaustive."
        )
        return

    print("FINAL CERTIFICATE AUDIT")
    print()
    print(f"Parent coverage: {pf('parent_coverage')}")
    print(f"Local keys: {pf('local_keys')}")
    print(f"Covered-but-cap-reached: {pf('covered_but_cap_reached')}")
    print(f"Frontier coverage: {pf('frontier_coverage')}")
    print(f"B-control: {pf('b_control')}")
    print(f"Return map: {pf('return_map')}")
    print(f"Quotient-key validity: {pf('quotient_key_validity')}")
    print(f"Direct bridge: {a['direct_bridge']['status']}")
    print(f"Exact depth: {a['exact_depth']['status']}")
    print(f"Exact arithmetic: {pf('exact_arithmetic')}")
    print()
    print("Final status:")
    if report["final_status"] == "PASS_CERTIFICATE_PIPELINE":
        print("PASS_CERTIFICATE_PIPELINE:")
        print(
            "All tracked parent obstructions were covered by the certificate pipeline "
            "under exact integer arithmetic. Independent mathematical review is still "
            "required to verify that the certificate framework is logically exhaustive."
        )
    else:
        print("INCOMPLETE:")
        for item in report["incomplete_reasons"]:
            print(f"- {item}")


FINAL_FULL_FRAMEWORK_WORDING = (
    "The declared r0 mod 2^16 frontier, exact-depth layer, 578 deep parents, "
    "cap-stopped rows, local keys, return-map states, high-B returns, and previously "
    "quotient-closed parents are now all covered by exact source reports or full "
    "exact-state certificates. No proof-critical row relies only on compact quotient "
    "abstraction. Independent mathematical review is still required before any public "
    "proof claim."
)


def final_wording_for_status(final_status: str) -> str:
    if final_status == "PASS_CERTIFICATE_PIPELINE_BUT_QUOTIENT_REVIEW_REQUIRED":
        return (
            "The internal certificate pipeline, residue partition, density partition, parent coverage, local continuation, "
            "return map, B-control, direct bridge, exact depth, and exact arithmetic audits passed. The remaining "
            "independent-review gate is quotient abstraction validity."
        )
    if final_status == "PASS_PIPELINE_WITH_TRACKED_QUOTIENT_TABLE_BUT_FULL_EQUIVALENCE_REVIEW_REQUIRED":
        return (
            "The tracked quotient transition table passed for proof-critical tracked keys. Full quotient equivalence "
            "still requires an external lemma or exhaustive representative coverage."
        )
    if final_status == "PASS_PIPELINE_WITH_EXACT_STATE_FALLBACK_BUT_FULL_EQUIVALENCE_REVIEW_REQUIRED":
        return (
            "The tracked quotient transition table and exact-state fallback passed for proof-critical tracked keys. "
            "Full quotient equivalence still requires an external lemma or exhaustive representative coverage."
        )
    if final_status == "PASS_PIPELINE_WITH_FULL_EXACT_STATE_CLOSURE":
        return (
            "The full exact-state closure passed for proof-critical tracked states, so the final tracked closure no "
            "longer depends on compact quotient-key full equivalence. Independent mathematical review is still required "
            "before any public proof claim."
        )
    if final_status == "PASS_PIPELINE_BUT_QUOTIENT_DEPENDENCE_REMAINS":
        return (
            "The exact-state pipeline passed for exported tracked states, cap-stopped rows, local keys, return-map states, "
            "and high-B returns, but the full framework audit found parent rows still justified only by compact quotient "
            "exploration. Independent mathematical review is still required before any public proof claim."
        )
    if final_status == "PASS_FULL_FRAMEWORK_EXACT_STATE_CLOSURE":
        return FINAL_FULL_FRAMEWORK_WORDING
    if final_status == "PASS_CERTIFICATE_FRAMEWORK_STRUCTURAL_AUDIT":
        return (
            "The internal certificate pipeline and structural reports passed under available exact source data. "
            "Independent mathematical review is still required before any public proof claim."
        )
    if final_status == "FAIL_CERTIFICATE_FRAMEWORK":
        return "At least one proof-critical audit failed. See listed failures."
    return "At least one proof-critical source report is missing or insufficient."


def main() -> None:
    batch = load_json("quotient_parent_batch_report.json")
    frontier_cov = load_json("frontier_coverage_audit_report.json")
    rm = load_json("frontier_return_map_report.json")
    bc = load_json("b_control_report.json")
    qparent_cov = load_json("quotient_parent_coverage_audit_report.json", required=False)
    excursion = load_json("excursion_quotient_report.json", required=False)

    reports = {
        "quotient_parent_batch": batch,
        "frontier_coverage": frontier_cov,
        "frontier_return_map": rm,
        "b_control": bc,
        "quotient_parent_coverage": qparent_cov or {},
        "excursion_quotient": excursion or {},
    }

    audits = {
        "parent_coverage": parent_coverage_audit(batch),
        "classification": classification_audit(batch),
        "local_keys": local_key_audit(batch),
        "covered_but_cap_reached": covered_cap_audit(batch),
        "frontier_coverage": frontier_coverage_audit(frontier_cov),
        "b_control": b_control_audit(bc),
        "return_map": return_map_audit(rm),
        "quotient_key_validity": quotient_key_validity_audit(),
        "direct_bridge": direct_bridge_audit(),
        "exact_depth": exact_depth_audit(),
        "exact_arithmetic": exact_arithmetic_audit(reports),
    }

    incomplete_reasons = collect_failures(audits)
    master_checks, master_details = build_master_checks(audits)
    final_status, master_reasons = final_master_status(master_checks)
    if not master_reasons:
        master_reasons = incomplete_reasons

    report = {
        "source_reports": {
            "quotient_parent_batch_report.json": Path("quotient_parent_batch_report.json").exists(),
            "quotient_parent_batch_report_smoke.json": Path("quotient_parent_batch_report_smoke.json").exists(),
            "frontier_coverage_audit_report.json": Path("frontier_coverage_audit_report.json").exists(),
            "frontier_return_map_report.json": Path("frontier_return_map_report.json").exists(),
            "b_control_report.json": Path("b_control_report.json").exists(),
            "quotient_parent_coverage_audit_report.json": Path("quotient_parent_coverage_audit_report.json").exists(),
            "quotient_key_validity_audit_report.json": Path("quotient_key_validity_audit_report.json").exists(),
            "excursion_quotient_report.json": Path("excursion_quotient_report.json").exists(),
            "direct_bridge_report.json": Path("direct_bridge_report.json").exists(),
            "collatz_certificate.json": Path("collatz_certificate.json").exists(),
            "master_source_coverage_audit_report.json": Path("master_source_coverage_audit_report.json").exists(),
            "residue_partition_exhaustiveness_report.json": Path("residue_partition_exhaustiveness_report.json").exists(),
            "residue_density_partition_audit_report.json": Path("residue_density_partition_audit_report.json").exists(),
            "exact_arithmetic_audit_report.json": Path("exact_arithmetic_audit_report.json").exists(),
            "quotient_abstraction_validity_report.json": Path("quotient_abstraction_validity_report.json").exists(),
            "quotient_transition_table.json": Path("quotient_transition_table.json").exists(),
            "quotient_transition_table_audit_report.json": Path("quotient_transition_table_audit_report.json").exists(),
            "quotient_exact_state_fallback_audit_report.json": Path("quotient_exact_state_fallback_audit_report.json").exists(),
            "quotient_key_schema_review_report.json": Path("quotient_key_schema_review_report.json").exists(),
            "exact_state_closure_report.json": Path("exact_state_closure_report.json").exists(),
            "full_framework_closure_audit_report.json": Path("full_framework_closure_audit_report.json").exists(),
        },
        "current_final_parent_status": batch.get("summary", {}),
        "audits": audits,
        "master_checks": master_checks,
        "master_details": master_details,
        "final_status": final_status,
        "incomplete_reasons": master_reasons,
        "final_wording": final_wording_for_status(final_status),
        "plain_truth": (
            "This audit verifies the generated certificate pipeline reports. It does not claim the Collatz theorem is proven."
        ),
    }

    with OUT.open("w") as f:
        json.dump(report, f, indent=2, sort_keys=True)
    print_summary(report)


if __name__ == "__main__":
    main()
