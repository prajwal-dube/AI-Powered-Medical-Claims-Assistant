"""Repeatable synthetic fixture benchmark. No network or LLM is used."""
import argparse
import json
import sys
import time
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from claims_assistant.extraction import PROMPT_VERSION, local_extract
from claims_assistant.review import review_claim


def cases():
    diagnoses = ["Asthma", "Sprain", "Migraine", "Allergy", "Fracture"]
    procedures = ["Office consultation", "X-ray", "Follow-up"]
    for index in range(30):
        fields = {"claim_id": f"C-{index:03d}", "patient_id": f"DEMO-{index:03d}",
                  "diagnosis": diagnoses[index % 5], "procedure": procedures[index % 3],
                  "amount": f"{150 + index * 25:.2f}", "service_date": "2025-08-03"}
        if index % 6 == 0:
            fields.pop("procedure")
        if index % 10 == 0:
            fields["amount"] = "0.00"
        if index == 29:
            fields["service_date"] = "2099-01-01"
        text = "SYNTHETIC TEST\n" + "\n".join(f"{k.replace('_', ' ').title()}: {v}" for k, v in fields.items())
        expected = set()
        if "procedure" not in fields:
            expected.add("missing_procedure")
        if fields["amount"] == "0.00":
            expected.add("invalid_amount")
        if index == 29 and date.today().year < 2099:
            expected.add("future_date")
        yield text, fields, expected


def run():
    total_fields = correct_fields = total_flags = correct_flags = 0
    latencies = []
    for document, expected, expected_flags in cases():
        start = time.perf_counter()
        extracted = local_extract(document)
        actual_flags = {flag.code for flag in review_claim(extracted)}
        latencies.append((time.perf_counter() - start) * 1000)
        for field in ("claim_id", "patient_id", "diagnosis", "procedure", "amount", "service_date"):
            total_fields += 1
            actual = getattr(extracted, field)
            correct_fields += str(actual) == str(expected.get(field))
        total_flags += 1
        correct_flags += actual_flags == expected_flags
    ordered = sorted(latencies)
    return {"fixture_count": 30, "field_values_correct": correct_fields,
            "field_values_total": total_fields, "field_exact_match_pct": round(100 * correct_fields / total_fields, 2),
            "documents_with_exact_flags": correct_flags, "flag_sets_total": total_flags,
            "flag_set_exact_match_pct": round(100 * correct_flags / total_flags, 2),
            "median_processing_ms": round((ordered[14] + ordered[15]) / 2, 3),
            "p95_processing_ms": round(ordered[28], 3),
            "extractor": "demo labeled-form baseline", "prompt_version": PROMPT_VERSION,
            "scope": "local extraction and rules only; excludes API, I/O, LLM, and deployment"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="benchmark_results.json")
    args = parser.parse_args()
    result = run()
    Path(args.output).write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
