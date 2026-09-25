"""CyberAI Quantitative Evaluation Module for RAG Retrieval & LLM Assessment Verdicts.

Provides:
- Schema definitions for RAG and Verdict evaluation records and artefacts
- Normalization logic separating canonical verdicts from legacy/review labels
- Metrics: Recall@k, MRR@k, Accuracy, Macro-F1, per-class P/R/F1, confusion matrix
- Offline evaluator and CLI runner producing reproducible, desensitized JSON/CSV artefacts
"""

__version__ = "1.0.0"
