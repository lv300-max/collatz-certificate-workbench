"""
frontier_coverage_certificate.py
=================================
Coverage test for the zero-repayment certificates.

frontier_return_map.py proved an exact fact for exported open states:

    from each debt word w, the zero extension w + 0^r is certified
    with gap > 0 and B <= 200001.

That is only a cylinder certificate.  It covers continuations beginning with
w0^r, not arbitrary continuations from w.  This file checks whether the finite
set of exported zero-repayment cylinders covers the open frontier language, and
if not, constructs an escaping branch.

No random seeds and no cap increases.
"""

import json
from collections import Counter, defaultdict

QREPORT = "excursion_quotient_report.json"
RREPORT = "frontier_return_map_report.json"
OUTFILE = "frontier_coverage_certificate_report.json"


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def zero_certificates(qreport, rreport):
    # rreport may only store a sampled list of repayment records, so rebuild the
    # certificate words from the full quotient open export when needed.
    by_key = {tuple(item["key"]): item for item in qreport.get("open_frontier", [])}
    certs = []
    stored = rreport.get("repayment_records", []) + rreport.get("all_one_repayment_records", [])
    seen = set()
    for rec in stored:
        key = tuple(rec["key"])
        if key in seen or key not in by_key:
            continue
        seen.add(key)
        word = by_key[key].get("accumulated_frontier_word", "")
        r = rec["r_to_B_limit"]
        certs.append({
            "key": key,
            "word": word,
            "r": r,
            "certificate_prefix": word + ("0" * r),
            "return_pair": rec["return_pair"],
            "return_B": rec["return_B"],
            "is_all_one": rec["is_all_one"],
        })
    return certs


def prefix_covers(word, cert_prefix):
    """Whether cylinder cert_prefix covers the exact finite word prefix."""
    return word.startswith(cert_prefix)


def covered_by_any(word, certs):
    return any(prefix_covers(word, cert["certificate_prefix"]) for cert in certs)


def next_bit_counts(words):
    by_prefix = defaultdict(Counter)
    for word in words:
        for i in range(len(word)):
            by_prefix[word[:i]][word[i]] += 1
    return by_prefix


def greedy_escape(certs, max_len):
    """
    Construct a finite prefix that avoids every zero-repayment certificate prefix
    up to max_len when possible.  Choosing 1 always avoids a certificate whose
    next required bit is 0, so this exposes the all-1 obstruction.
    """
    prefix = ""
    steps = []
    for _ in range(max_len):
        options = []
        for bit in "10":
            cand = prefix + bit
            killed = [c for c in certs if c["certificate_prefix"].startswith(cand)]
            covered = any(cand.startswith(c["certificate_prefix"]) for c in certs)
            options.append((bit, covered, len(killed)))
        viable = [x for x in options if not x[1]]
        if not viable:
            steps.append({"prefix": prefix, "status": "covered", "options": options})
            break
        # Prefer the branch that leaves fewer certificates still relevant.
        bit, covered, remaining = min(viable, key=lambda x: (x[2], x[0] != "1"))
        prefix += bit
        steps.append({"prefix": prefix, "chosen": bit, "remaining_certificate_prefixes": remaining})
    return prefix, steps[-20:]


def trie_coverage_summary(open_words, certs):
    exact_covered = sum(1 for w in open_words if covered_by_any(w, certs))
    all_one_words = [w for w in open_words if w and set(w) == {"1"}]
    prefixes = Counter(w[:96] for w in open_words)
    suffixes = Counter(w[-96:] for w in open_words)
    bit_counts = next_bit_counts(open_words)
    root_bits = dict(bit_counts.get("", Counter()))
    return {
        "open_words": len(open_words),
        "certificates": len(certs),
        "open_words_already_inside_certificate": exact_covered,
        "all_one_open_words": len(all_one_words),
        "root_next_bit_counts": root_bits,
        "common_prefixes": [
            {"prefix": k, "count": v}
            for k, v in prefixes.most_common(12)
        ],
        "common_suffixes": [
            {"suffix": k, "count": v}
            for k, v in suffixes.most_common(12)
        ],
    }


def main():
    qreport = load_json(QREPORT)
    rreport = load_json(RREPORT)
    open_items = qreport.get("open_frontier", [])
    open_words = [item.get("accumulated_frontier_word", "") for item in open_items]
    certs = zero_certificates(qreport, rreport)
    max_len = max((len(w) for w in open_words), default=0)
    escape_prefix, escape_tail = greedy_escape(certs, max_len)
    summary = trie_coverage_summary(open_words, certs)

    # Direct all-1 certificate test. If no certificate prefix is all ones, then
    # the infinite 111... branch avoids every zero-repayment certificate.
    all_one_certificates = [
        c for c in certs
        if c["certificate_prefix"] and set(c["certificate_prefix"]) == {"1"}
    ]
    all_one_escape = not all_one_certificates

    report = {
        "source_reports": [QREPORT, RREPORT],
        "summary": {
            **summary,
            "finite_zero_certificates_cover_all_continuations": False,
            "all_one_escape_branch_exists": all_one_escape,
            "escape_prefix_length": len(escape_prefix),
        },
        "escape_prefix": escape_prefix[:5000],
        "escape_tail": escape_tail,
        "certificate_examples": certs[:30],
        "uncovered_open_examples": [
            {
                "key": item["key"],
                "pair": item["pair"],
                "word_length": item["word_length"],
                "word_prefix": item.get("accumulated_frontier_word", "")[:160],
                "word_suffix": item.get("accumulated_frontier_word", "")[-160:],
            }
            for item in open_items
            if not covered_by_any(item.get("accumulated_frontier_word", ""), certs)
        ][:30],
        "candidate_coverage_lemma": {
            "status": "false_for_finite_zero_cylinders",
            "failed_candidate": "The zero-repayment sibling certificates cover all continuations.",
            "counterexample": "The infinite all-1 frontier branch avoids every certificate prefix w0^r.",
            "exact_reason": (
                "Every exported repayment certificate requires at least one 0 "
                "after its debt word. A continuation that keeps choosing 1 at "
                "frontier boundaries never enters any such cylinder."
            ),
            "next_viable_form": (
                "Prove the infinite all-1 frontier branch is not a valid positive "
                "integer/residue path, or prove it is already covered by another "
                "non-frontier descent certificate."
            ),
        },
        "what_is_proven": [
            "Each exported debt state has a certified zero-repayment sibling cylinder.",
            "The finite set of zero-repayment cylinders does not cover all binary frontier continuations.",
            "An all-1 frontier continuation is a formal escaping branch for these certificates.",
        ],
        "what_remains_open": [
            "Need to rule out or separately certify the all-1 2-adic frontier path.",
            "Need a coverage lemma that includes nonzero repayment cylinders or external descent certificates.",
            "No proof closure follows from zero-repayment certificates alone.",
        ],
    }

    with open(OUTFILE, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print("=" * 78)
    print("FRONTIER COVERAGE CERTIFICATE")
    print("=" * 78)
    print(f"Open words                         : {summary['open_words']:,}")
    print(f"Zero-repayment certificates         : {summary['certificates']:,}")
    print(f"Open words already inside cert      : {summary['open_words_already_inside_certificate']:,}")
    print(f"All-1 open words                    : {summary['all_one_open_words']:,}")
    print(f"All-1 escape branch exists          : {all_one_escape}")
    print(f"Escape prefix length checked        : {len(escape_prefix):,}")
    print()
    print("Candidate coverage lemma:")
    for k, v in report["candidate_coverage_lemma"].items():
        print(f"  {k}: {v}")
    print()
    print("What remains open:")
    for item in report["what_remains_open"]:
        print(f"  - {item}")
    print(f"\nReport: {OUTFILE}")


if __name__ == "__main__":
    main()
