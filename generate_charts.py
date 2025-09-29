import json
from pathlib import Path
import matplotlib.pyplot as plt

# Precision/Recall values from evaluation
PR = {
    'PII': {'precision': 1.0, 'recall': 1.0},
    'Injection': {'precision': 1.0, 'recall': 1.0},
    'Toxicity': {'precision': 1.0, 'recall': 0.8},
}

# Latency metrics from EXPERIMENTS.md Experiment 4
LATENCY = {
    'baseline_avg_s': 1.8,
    'gateway_avg_s': 2.1,
    'p95_s': 4.1,
}

OUT_DIR = Path('charts')
OUT_DIR.mkdir(exist_ok=True)


def plot_precision_recall(pr_data: dict, out_path: Path):
    labels = list(pr_data.keys())
    precisions = [pr_data[k]['precision'] for k in labels]
    recalls = [pr_data[k]['recall'] for k in labels]

    x = range(len(labels))
    width = 0.35

    plt.figure(figsize=(6, 4))
    plt.bar([i - width/2 for i in x], precisions, width, label='Precision')
    plt.bar([i + width/2 for i in x], recalls, width, label='Recall')
    plt.ylim(0, 1.1)
    plt.xticks(list(x), labels)
    plt.ylabel('Score')
    plt.title('Precision / Recall by Category')
    plt.legend()
    plt.tight_layout()
    plt.savefig(out_path, dpi=150)
    plt.close()


def plot_latency(latency: dict, out_path: Path):
    labels = ['Baseline Avg', 'Gateway Avg', 'P95 Gateway']
    values = [latency['baseline_avg_s'], latency['gateway_avg_s'], latency['p95_s']]

    plt.figure(figsize=(6, 4))
    bars = plt.bar(labels, values, color=['#6baed6', '#3182bd', '#9ecae1'])
    for b in bars:
        plt.text(b.get_x() + b.get_width()/2, b.get_height() + 0.05, f"{b.get_height():.2f}s", ha='center', va='bottom')
    plt.ylabel('Seconds')
    plt.title('Latency Metrics')
    plt.tight_layout()
    plt.savefig(out_path, dpi=150)
    plt.close()


def main():
    pr_path = OUT_DIR / 'precision_recall.png'
    lat_path = OUT_DIR / 'latency.png'

    plot_precision_recall(PR, pr_path)
    plot_latency(LATENCY, lat_path)

    print(json.dumps({
        'precision_recall': str(pr_path),
        'latency': str(lat_path)
    }, indent=2))


if __name__ == '__main__':
    main()
