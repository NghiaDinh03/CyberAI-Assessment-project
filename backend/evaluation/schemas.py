"""Data structures and Pydantic models for RAG and LLM Evaluation.

Adheres to strict desensitization:
- No raw evidence text, corporate sensitive data, or raw prompts stored in evaluation artefacts.
- Only references, IDs, or content hashes are tracked.
"""

from typing import List, Dict, Any, Optional, Literal
from pydantic import BaseModel, Field


# Canonical verdicts accepted in the assessment system
CANONICAL_VERDICTS = [
    "satisfied",
    "partial",
    "not_evidenced",
    "missing",
    "needs_expert_review",
]


class RagEvalRecord(BaseModel):
    """Evaluation record for RAG retrieval quality evaluation."""
    case_id: str = Field(..., description="Stable unique identifier for the evaluation case")
    standard: str = Field(..., description="Target standard, e.g. 'iso27001' or 'tcvn11930'")
    query: str = Field(..., description="Desensitized query or fixture search prompt")
    relevant_chunk_ids: List[str] = Field(
        default_factory=list,
        description="List of ground-truth relevant chunk IDs from ChromaDB/corpus"
    )
    split: str = Field("test", description="Dataset split: 'test', 'few_shot', 'train'")
    label_source: str = Field("expert", description="Origin of label: 'expert', 'fixture', 'synthetic'")
    reviewed_at: Optional[str] = Field(None, description="ISO-8601 timestamp of expert review or null")
    notes: Optional[str] = Field(None, description="Optional reviewer notes or context")


class VerdictEvalRecord(BaseModel):
    """Evaluation record for LLM assessment verdict classification."""
    case_id: str = Field(..., description="Stable unique identifier for the case")
    standard: str = Field(..., description="Target standard, e.g. 'iso27001' or 'tcvn11930'")
    control_id: str = Field(..., description="Control code, e.g. 'A.5.1' or TCVN code")
    input_ref: str = Field(..., description="SHA-256 hash or fixture-id of input facts (no raw evidence)")
    expert_verdict: str = Field(
        ...,
        description="Canonical verdict: 'satisfied', 'partial', 'not_evidenced', 'missing', 'needs_expert_review'"
    )
    split: str = Field("test", description="Dataset split: 'test', 'few_shot'")
    label_source: str = Field("expert", description="Origin of label: 'expert', 'fixture'")
    reviewed_at: Optional[str] = Field(None, description="ISO-8601 timestamp or null")
    predicted_verdict: Optional[str] = Field(None, description="Model's predicted verdict if evaluated")


class RagQueryResult(BaseModel):
    """Per-query detail for RAG evaluation."""
    case_id: str
    query_preview: str  # Short desensitized preview (first 50 chars)
    retrieved_chunk_ids: List[str]
    relevant_chunk_ids: List[str]
    first_relevant_rank: Optional[int] = None  # 1-indexed rank of first relevant chunk, or None
    hit_at_k: bool = False
    reciprocal_rank: float = 0.0


class RagMetrics(BaseModel):
    """Metrics for RAG retrieval."""
    recall_at_k: float = Field(..., description="Proportion of queries with >= 1 relevant chunk in top-k")
    mrr_at_k: float = Field(..., description="Mean Reciprocal Rank within top-k")
    k: int = Field(..., description="Top-k cut-off used for retrieval")
    total_queries: int = Field(..., description="Total queries in split")
    valid_queries: int = Field(..., description="Queries with >= 1 labeled relevant chunk")
    unlabeled_or_empty_queries: int = Field(..., description="Queries skipped due to missing/empty labels")
    collection_version: str = Field("default", description="Vector collection / corpus identifier")
    embedding_model: str = Field("bge-m3", description="Embedding model name used")
    query_details: List[RagQueryResult] = Field(default_factory=list, description="Per-query evaluation trace")


class ClassMetric(BaseModel):
    precision: Optional[float] = None
    recall: Optional[float] = None
    f1: Optional[float] = None
    support: int = 0


class VerdictMetrics(BaseModel):
    """Metrics for LLM verdict evaluation."""
    accuracy: Optional[float] = Field(None, description="Exact-match accuracy on valid samples")
    macro_f1: Optional[float] = Field(None, description="Unweighted average F1 across classes with support > 0")
    per_class: Dict[str, ClassMetric] = Field(default_factory=dict, description="Per-class precision, recall, F1")
    confusion_matrix: Dict[str, Dict[str, int]] = Field(
        default_factory=dict,
        description="Confusion matrix [true_class][pred_class]"
    )
    valid_samples: int = Field(0, description="Number of valid, canonical labeled samples")
    excluded_samples: int = Field(0, description="Samples excluded (e.g. legacy non_compliant, invalid)")
    excluded_details: List[Dict[str, str]] = Field(default_factory=list, description="Reasons for exclusions")
    model_runtime: str = Field("local-runtime", description="Runtime identifier for LLM")
    schema_valid_rate: Optional[float] = Field(
        None,
        description="Proportion of predictions matching valid JSON/canonical schema"
    )
    classes: List[str] = Field(default_factory=list, description="Classes evaluated")


class EvaluationArtefact(BaseModel):
    """Reproducible evaluation artefact saved to disk (JSON / CSV)."""
    artefact_id: str
    timestamp: str  # ISO-8601
    mode: Literal["rag", "verdict", "all"]
    standard: str
    split: str
    code_version: Optional[str] = None
    git_commit_sha: Optional[str] = None
    dataset_source: str
    dataset_hash: str
    rag_metrics: Optional[RagMetrics] = None
    verdict_metrics: Optional[VerdictMetrics] = None
    metric_definitions: Dict[str, str] = Field(default_factory=dict)
    status: Literal["success", "insufficient_data", "error"]
    status_message: str
    source_record_ids: List[str] = Field(default_factory=list)


def to_dict(model: BaseModel) -> Dict[str, Any]:
    """Compatible dictionary conversion across Pydantic v1 and v2."""
    if hasattr(model, "model_dump"):
        return model.model_dump()
    return model.dict()

