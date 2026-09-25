"""CLI Runner for Quantitative Evaluation of RAG Retrieval and LLM Verdicts.

Usage:
    python -m evaluation.run --standard iso27001 --split test --mode rag
    python -m evaluation.run --standard iso27001 --split test --mode verdict
    python -m evaluation.run --standard all --split test --mode all
"""

import sys
import argparse
import logging
from pathlib import Path

# Add backend directory to sys.path so sibling imports work properly
backend_dir = Path(__file__).parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from evaluation.evaluator import (
    run_rag_evaluation,
    run_verdict_evaluation,
    save_evaluation_artefact,
)
from evaluation.schemas import EvaluationArtefact

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("evaluation.run")


def main():
    parser = argparse.ArgumentParser(
        description="CyberAI Quantitative Evaluation CLI for RAG & LLM Assessment Verdicts."
    )
    parser.add_argument(
        "--standard",
        type=str,
        default="iso27001",
        help="Target standard: 'iso27001', 'tcvn11930', or 'all' (default: iso27001)",
    )
    parser.add_argument(
        "--split",
        type=str,
        default="test",
        help="Dataset split to evaluate: 'test' or 'few_shot' (default: test)",
    )
    parser.add_argument(
        "--mode",
        type=str,
        choices=["rag", "verdict", "all"],
        default="all",
        help="Evaluation mode: 'rag', 'verdict', or 'all' (default: all)",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=5,
        help="Top-k retrieval cut-off for RAG evaluation (default: 5)",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="Directory to save output evaluation artefacts (default: data/evaluations)",
    )
    parser.add_argument(
        "--custom-rag-dataset",
        type=str,
        default=None,
        help="Path to custom RAG evaluation JSON dataset",
    )
    parser.add_argument(
        "--custom-verdict-dataset",
        type=str,
        default=None,
        help="Path to custom Verdict evaluation JSON dataset",
    )

    args = parser.parse_args()

    print("=" * 70)
    print("CYBERAI ASSESSMENT PLATFORM — QUANTITATIVE EVALUATION RUNNER")
    print(f"Standard: {args.standard} | Split: {args.split} | Mode: {args.mode} | Top-K: {args.top_k}")
    print("=" * 70)

    # 1. RAG Evaluation
    rag_artefact = None
    if args.mode in ("rag", "all"):
        print("\n>>> Running RAG Retrieval Evaluation...")
        rag_artefact = run_rag_evaluation(
            standard=args.standard,
            split=args.split,
            top_k=args.top_k,
            custom_dataset_path=args.custom_rag_dataset,
        )
        if rag_artefact.rag_metrics and rag_artefact.rag_metrics.valid_queries > 0:
            m = rag_artefact.rag_metrics
            print(f"  [RAG SUCCESS] Valid Queries: {m.valid_queries}/{m.total_queries}")
            print(f"  Recall@{m.k}: {m.recall_at_k:.4f}")
            print(f"  MRR@{m.k}: {m.mrr_at_k:.4f}")
            print(f"  Unlabeled Queries (Skipped): {m.unlabeled_or_empty_queries}")
        else:
            print(f"  [RAG NOTICE] {rag_artefact.status_message}")

        j_path, c_path = save_evaluation_artefact(rag_artefact, output_dir=args.output_dir)
        print(f"  Saved RAG artefact: {j_path}")

    # 2. Verdict Evaluation
    verdict_artefact = None
    if args.mode in ("verdict", "all"):
        print("\n>>> Running LLM Verdict Evaluation...")
        verdict_artefact = run_verdict_evaluation(
            standard=args.standard,
            split=args.split,
            custom_dataset_path=args.custom_verdict_dataset,
        )
        if verdict_artefact.verdict_metrics and verdict_artefact.verdict_metrics.valid_samples > 0:
            vm = verdict_artefact.verdict_metrics
            print(f"  [VERDICT SUCCESS] Valid Samples: {vm.valid_samples} | Excluded: {vm.excluded_samples}")
            print(f"  Accuracy: {vm.accuracy if vm.accuracy is not None else 'N/A'}")
            print(f"  Macro-F1: {vm.macro_f1 if vm.macro_f1 is not None else 'Undefined (< 2 classes)'}")
            print(f"  Per-class Breakdown:")
            for cls_name, cm in vm.per_class.items():
                print(f"    - {cls_name:20s}: Precision={cm.precision}, Recall={cm.recall}, F1={cm.f1}, Support={cm.support}")
        else:
            print(f"  [VERDICT NOTICE] {verdict_artefact.status_message}")

        j_path, c_path = save_evaluation_artefact(verdict_artefact, output_dir=args.output_dir)
        print(f"  Saved Verdict artefact: {j_path}")

    print("\n" + "=" * 70)
    print("EVALUATION COMPLETED.")
    print("=" * 70)


if __name__ == "__main__":
    main()
