import json
from typing import Tuple
from filters.pii import redact_pii
from filters.injection import detect_injection
from filters.toxicity import check_toxicity

LABEL_TO_CHECK = {
    "pii": "pii",
    "injection": "injection",
    "toxic": "toxic",
    "normal": "normal",
}

def evaluate_sample(text: str) -> Tuple[bool, str]:
    # Pre-filters mirroring gateway order (without rate-limit/cache)
    redacted, pii_types = redact_pii(text)
    if pii_types:
        return True, "pii"
    inj, _ = detect_injection(redacted)
    if inj:
        return True, "injection"
    tox, _, _ = check_toxicity(redacted)
    if tox:
        return True, "toxic"
    return False, "normal"


def main():
    with open("attack_set.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    totals = {k: 0 for k in LABEL_TO_CHECK.keys()}
    tp = {k: 0 for k in LABEL_TO_CHECK.keys()}
    fp = {k: 0 for k in LABEL_TO_CHECK.keys()}
    fn = {k: 0 for k in LABEL_TO_CHECK.keys()}

    for item in data:
        text = item["input"]
        label = item["label"]
        totals[label] += 1

        detected, detected_label = evaluate_sample(text)

        if label == "normal":
            if detected:
                # any detection on normal is false positive for that detected_label
                fp[detected_label] += 1
        else:
            # for attack labels
            if detected:
                if detected_label == label:
                    tp[label] += 1
                else:
                    # detected but wrong class -> count as FN for true label and FP for detected
                    fn[label] += 1
                    fp[detected_label] += 1
            else:
                fn[label] += 1

    def prec_recall(tp_val, fp_val, fn_val):
        precision = tp_val / max(1, (tp_val + fp_val))
        recall = tp_val / max(1, (tp_val + fn_val))
        return precision, recall

    results = {}
    for k in ["pii", "injection", "toxic"]:
        p, r = prec_recall(tp[k], fp[k], fn[k])
        results[k] = {
            "total": totals[k],
            "tp": tp[k],
            "fp": fp[k],
            "fn": fn[k],
            "precision": round(p, 3),
            "recall": round(r, 3),
        }

    macro_p = sum(results[k]["precision"] for k in results) / 3
    macro_r = sum(results[k]["recall"] for k in results) / 3

    report = {
        "results": results,
        "macro_precision": round(macro_p, 3),
        "macro_recall": round(macro_r, 3),
        "normal_fp_total": sum(fp.values()) - (fp["normal"] if "normal" in fp else 0),
    }

    print(json.dumps(report, indent=2))

if __name__ == "__main__":
    main()
