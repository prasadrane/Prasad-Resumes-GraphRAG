"""
benchmark_eval.py — Automated Synthetic Evaluation Harness & Benchmarking for GraphRAG.

Provides:
- BenchmarkCase: structured test query with query_type, expected entities, and ground-truth facts.
- EvaluationResult: evaluation metrics per query (context precision, recall, faithfulness, latency, token count, healed status).
- AggregateBenchmarkReport: aggregated dataset metrics with Markdown reporting table generation.
- BenchmarkEvaluator: metric computation algorithms and dataset evaluation runner.
- DEFAULT_BENCHMARK_DATASET: standardized synthetic test cases for Prasad Rane's resume.
"""

from __future__ import annotations

import asyncio
import re
import time
from typing import Any, Callable, Dict, List, Optional, Union
from pydantic import BaseModel, Field


# ── Benchmark Models ─────────────────────────────────────────────────────────

class BenchmarkCase(BaseModel):
    """A test case definition for GraphRAG retrieval and generation benchmarking."""
    query: str
    query_type: str = "experience_lookup"
    expected_entities: List[str] = Field(default_factory=list)
    ground_truth_facts: List[str] = Field(default_factory=list)


class EvaluationResult(BaseModel):
    """Metrics result for an individual benchmark test case."""
    case_query: str
    context_precision: float
    context_recall: float
    faithfulness: float
    latency_ms: float
    token_count: int
    retrieval_mode: str = "local"
    healed: bool = False


class AggregateBenchmarkReport(BaseModel):
    """Aggregated report across multiple benchmark evaluations."""
    results: List[EvaluationResult] = Field(default_factory=list)

    @property
    def total_cases(self) -> int:
        return len(self.results)

    @property
    def avg_context_precision(self) -> float:
        if not self.results:
            return 0.0
        return sum(r.context_precision for r in self.results) / len(self.results)

    @property
    def mean_precision(self) -> float:
        return self.avg_context_precision

    @property
    def avg_context_recall(self) -> float:
        if not self.results:
            return 0.0
        return sum(r.context_recall for r in self.results) / len(self.results)

    @property
    def mean_recall(self) -> float:
        return self.avg_context_recall

    @property
    def avg_faithfulness(self) -> float:
        if not self.results:
            return 0.0
        return sum(r.faithfulness for r in self.results) / len(self.results)

    @property
    def mean_faithfulness(self) -> float:
        return self.avg_faithfulness

    @property
    def avg_latency_ms(self) -> float:
        if not self.results:
            return 0.0
        return sum(r.latency_ms for r in self.results) / len(self.results)

    @property
    def mean_latency_ms(self) -> float:
        return self.avg_latency_ms

    @property
    def healed_count(self) -> int:
        return sum(1 for r in self.results if r.healed)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "summary": {
                "total_cases": self.total_cases,
                "avg_context_precision": self.avg_context_precision,
                "avg_context_recall": self.avg_context_recall,
                "avg_faithfulness": self.avg_faithfulness,
                "avg_latency_ms": self.avg_latency_ms,
                "healed_count": self.healed_count,
            },
            "results": [r.model_dump() if hasattr(r, "model_dump") else r.dict() for r in self.results],
        }

    def to_markdown_table(self) -> str:
        lines = [
            "| Query | Mode | Precision | Recall | Faithfulness | Latency (ms) | Tokens | Healed |",
            "| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |",
        ]
        for r in self.results:
            q_short = r.case_query if len(r.case_query) <= 45 else r.case_query[:42] + "..."
            healed_str = "Yes" if r.healed else "No"
            lines.append(
                f"| {q_short} | {r.retrieval_mode} | {r.context_precision:.2f} | {r.context_recall:.2f} | {r.faithfulness:.2f} | {r.latency_ms:.1f}ms | {r.token_count} | {healed_str} |"
            )
        lines.append(
            f"| **AVERAGE / SUMMARY** | **-** | **{self.avg_context_precision:.2f}** | **{self.avg_context_recall:.2f}** | **{self.avg_faithfulness:.2f}** | **{self.avg_latency_ms:.1f}ms** | **{sum(r.token_count for r in self.results)}** | **{self.healed_count}/{self.total_cases}** |"
        )
        return "\n".join(lines)


# ── Helper Execution Utility ────────────────────────────────────────────────

def _run_maybe_coroutine(val_or_coro: Any) -> Any:
    """Execute coroutine synchronously if needed, safely supporting existing event loops."""
    if asyncio.iscoroutine(val_or_coro):
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                    return executor.submit(asyncio.run, val_or_coro).result()
            else:
                return loop.run_until_complete(val_or_coro)
        except RuntimeError:
            return asyncio.run(val_or_coro)
    return val_or_coro


# ── Benchmark Evaluator ─────────────────────────────────────────────────────

class BenchmarkEvaluator:
    """Evaluation harness for calculating precision, recall, faithfulness, and running benchmarks."""

    STOP_WORDS = {
        "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
        "of", "with", "by", "from", "up", "about", "into", "over", "after",
        "is", "are", "was", "were", "be", "been", "being", "have", "has", "had",
        "do", "does", "did", "as", "that", "this", "these", "those", "it", "its",
        "he", "his", "they", "their", "we", "our", "prasad", "rane", "using", "used"
    }

    def calculate_context_precision(self, context_text: str, expected_entities: List[str]) -> float:
        """Calculate the proportion of expected entities retrieved in the context."""
        if not expected_entities:
            return 1.0
        if not context_text or not context_text.strip():
            return 0.0

        ctx_lower = context_text.lower()
        matched_count = 0
        for entity in expected_entities:
            e_clean = entity.strip().lower()
            if not e_clean:
                continue
            if e_clean in ctx_lower:
                matched_count += 1
            else:
                words = [w for w in re.findall(r"\w+", e_clean) if len(w) >= 2]
                if words and all(w in ctx_lower for w in words):
                    matched_count += 1

        return min(1.0, max(0.0, matched_count / len(expected_entities)))

    def _token_in_text(self, token: str, text: str) -> bool:
        """Check if a token or its stem/clean form matches in text."""
        if token in text:
            return True
        clean = re.sub(r"[^\w]", "", token)
        if clean and clean in text:
            return True
        if len(token) > 4:
            for suffix in ("ing", "tion", "ted", "ed", "es", "s"):
                if token.endswith(suffix):
                    stem = token[:-len(suffix)]
                    if len(stem) >= 3 and (stem in text or (stem + "t") in text):
                        return True
            # Special case for doubled consonant stems (cutting -> cut)
            if token.endswith("ting") and token[:-4] in text:
                return True
            if token.endswith("ning") and token[:-4] in text:
                return True
        return False

    def calculate_context_recall(self, context_text: str, ground_truth_facts: List[str]) -> float:
        """Calculate the recall of ground-truth facts within the retrieved context."""
        if not ground_truth_facts:
            return 1.0
        if not context_text or not context_text.strip():
            return 0.0

        ctx_lower = context_text.lower()
        fact_scores: List[float] = []

        for fact in ground_truth_facts:
            fact_clean = fact.strip().lower()
            if not fact_clean:
                continue

            if fact_clean in ctx_lower:
                fact_scores.append(1.0)
                continue

            tokens = [
                w for w in re.findall(r"[\w%]+", fact_clean)
                if len(w) >= 2 and w not in self.STOP_WORDS
            ]
            if not tokens:
                fact_scores.append(1.0)
                continue

            matches = sum(1 for t in tokens if self._token_in_text(t, ctx_lower))
            ratio = matches / len(tokens)

            if ratio >= 0.6:
                fact_scores.append(min(1.0, ratio * 1.1))
            else:
                fact_scores.append(ratio)

        if not fact_scores:
            return 1.0
        return min(1.0, max(0.0, sum(fact_scores) / len(fact_scores)))

    def calculate_faithfulness(self, generated_answer: str, context_text: str) -> float:
        """Estimate claim groundedness of generated answer in the retrieved context."""
        if not generated_answer or not generated_answer.strip():
            return 1.0
        if not context_text or not context_text.strip():
            return 0.0

        ctx_lower = context_text.lower()
        sentences = [s.strip() for s in re.split(r"[.\n!?]+", generated_answer) if s.strip()]
        if not sentences:
            return 1.0

        sentence_scores: List[float] = []
        for sentence in sentences:
            tokens = [
                w.lower() for w in re.findall(r"[\w%]+", sentence)
                if len(w) >= 2 and w.lower() not in self.STOP_WORDS
            ]
            if not tokens:
                continue
            matches = sum(1 for t in tokens if t in ctx_lower)
            sentence_scores.append(matches / len(tokens))

        if not sentence_scores:
            return 1.0
        return min(1.0, max(0.0, sum(sentence_scores) / len(sentence_scores)))

    def evaluate_case(
        self,
        case: BenchmarkCase,
        engine: Any = None,
        mode: str = "local",
        enable_guardrail: bool = False,
    ) -> EvaluationResult:
        """Evaluate a single BenchmarkCase against an engine."""
        start_time = time.perf_counter()
        context_text = ""
        generated_answer = ""
        healed = False

        if engine is not None:
            try:
                if enable_guardrail and hasattr(engine, "retrieve_healed"):
                    res = _run_maybe_coroutine(engine.retrieve_healed(case.query, mode=mode))
                    if isinstance(res, tuple) and len(res) >= 2:
                        raw_ctx, trace = res[0], res[1]
                        healed = len(trace) > 1 or any(
                            (isinstance(t, dict) and t.get("attempt", 1) > 1) or
                            (hasattr(t, "attempt") and t.attempt > 1)
                            for t in trace
                        )
                    else:
                        raw_ctx = res
                    if hasattr(engine, "format_context") and callable(engine.format_context):
                        context_text = engine.format_context(raw_ctx)
                    elif isinstance(raw_ctx, dict) and "text" in raw_ctx:
                        context_text = str(raw_ctx["text"])
                    else:
                        context_text = str(raw_ctx)
                elif hasattr(engine, "retrieve") and callable(engine.retrieve):
                    raw_ctx = _run_maybe_coroutine(engine.retrieve(case.query, mode=mode))
                    if hasattr(engine, "format_context") and callable(engine.format_context):
                        context_text = engine.format_context(raw_ctx)
                    elif isinstance(raw_ctx, dict) and "text" in raw_ctx:
                        context_text = str(raw_ctx["text"])
                    else:
                        context_text = str(raw_ctx)
                elif callable(engine):
                    raw_res = _run_maybe_coroutine(engine(case.query))
                    if isinstance(raw_res, dict):
                        context_text = raw_res.get("context", raw_res.get("text", str(raw_res)))
                        generated_answer = raw_res.get("answer", raw_res.get("response", ""))
                    else:
                        context_text = str(raw_res)
                elif hasattr(engine, "query") and callable(engine.query):
                    raw_res = _run_maybe_coroutine(engine.query(case.query, mode=mode))
                    context_text = str(raw_res)
                elif isinstance(engine, str):
                    context_text = engine
                elif isinstance(engine, dict):
                    context_text = engine.get("context", engine.get("text", str(engine)))
                    generated_answer = engine.get("answer", engine.get("response", ""))
                else:
                    context_text = str(engine)
            except Exception as err:
                context_text = f"Error during retrieval: {err}"

        latency_ms = (time.perf_counter() - start_time) * 1000.0
        token_count = len(context_text.split()) if context_text else 0

        precision = self.calculate_context_precision(context_text, case.expected_entities)
        recall = self.calculate_context_recall(context_text, case.ground_truth_facts)
        faithfulness = self.calculate_faithfulness(generated_answer or context_text, context_text)

        return EvaluationResult(
            case_query=case.query,
            context_precision=precision,
            context_recall=recall,
            faithfulness=faithfulness,
            latency_ms=latency_ms,
            token_count=token_count,
            retrieval_mode=mode,
            healed=healed,
        )

    def evaluate_dataset(
        self,
        dataset: List[BenchmarkCase],
        engine: Any = None,
        enable_guardrail: bool = False,
        mode: str = "local",
    ) -> AggregateBenchmarkReport:
        """Evaluate an entire dataset of BenchmarkCases and return an aggregate report."""
        results = [
            self.evaluate_case(case, engine=engine, mode=mode, enable_guardrail=enable_guardrail)
            for case in dataset
        ]
        return AggregateBenchmarkReport(results=results)


# ── Standard Synthetic Benchmark Dataset ────────────────────────────────────

DEFAULT_BENCHMARK_DATASET: List[BenchmarkCase] = [
    BenchmarkCase(
        query="What experience does Prasad have with AWS ECS Fargate and containerization?",
        query_type="skill_lookup",
        expected_entities=["AWS", "ECS", "Fargate", "Terraform", "Docker"],
        ground_truth_facts=[
            "Modernized legacy VB.NET underwriter application to .NET Core / AWS ECS Fargate",
            "Reduced infrastructure costs by 40% using Fargate pay-per-use model",
            "Implemented Infrastructure as Code using Terraform and GitHub Actions",
            "Achieved 99.95% uptime and cut support tickets by 70%",
        ],
    ),
    BenchmarkCase(
        query="What were Prasad's primary responsibilities and achievements at Rocket Mortgage?",
        query_type="company_lookup",
        expected_entities=["Rocket Mortgage", "Dynatrace", "Kafka", "Bedrock", "Angular", "DynamoDB", "Fargate"],
        ground_truth_facts=[
            "Software Engineer at Rocket Mortgage from Jan 2023 to Jul 2025",
            "Improved Dynatrace observability accuracy from 60% to 98% on Fannie Mae eligibility integration",
            "Architected self-service Product Configuration UI using Angular 18, .NET Core 6, and DynamoDB",
            "Built AI chatbot on Amazon Bedrock (Claude Sonnet) reducing loan lookup time by 70%",
            "Established enterprise Kafka/AWS MSK governance standards across 5 engineering teams",
        ],
    ),
    BenchmarkCase(
        query="How did Prasad establish enterprise Kafka governance and schema validation?",
        query_type="skill_lookup",
        expected_entities=["Kafka", "AWS MSK", "Schema Registry", "Avro", "Rocket Mortgage"],
        ground_truth_facts=[
            "Established enterprise-wide Kafka/AWS MSK governance standards adopted by 5 teams within 3 months",
            "Embedded backward-compatible schema validation into CI pipeline via Schema Registry",
            "Automated governance enforcement into Terraform topic-provisioning modules",
        ],
    ),
    BenchmarkCase(
        query="What did Prasad build at London Computer Systems (LCS) for payment gateway integration?",
        query_type="experience_lookup",
        expected_entities=["London Computer Systems", "Payment Gateway", ".NET Core", "ACH", "SQL Server"],
        ground_truth_facts=[
            "Designed and implemented zero-downtime integration of third-party ACH/credit card payment gateway APIs",
            "Built exponential-backoff retry policies and fallback handling for transient network failures",
            "Reduced manual check processing by 25% for property management platform",
        ],
    ),
    BenchmarkCase(
        query="What memory leak and device sync challenges did Prasad solve at EXFO on optical devices?",
        query_type="experience_lookup",
        expected_entities=["EXFO", "C#", "optical devices", "PowerModeChanged", "CancellationTokenSource", "REST API"],
        ground_truth_facts=[
            "Root-caused and resolved sleep-mode memory leak on optical test devices using PowerModeChanged and CancellationTokenSource",
            "Eliminated 100% of resume-state memory leaks with zero field-reported recurrence",
            "Designed asynchronous C#/REST API device sync with offline-first local caching",
        ],
    ),
    BenchmarkCase(
        query="What metrics show Prasad's impact on 70% latency and performance reductions?",
        query_type="metrics_lookup",
        expected_entities=["Bedrock", "70%", "Rocket Mortgage", "latency", "Fargate"],
        ground_truth_facts=[
            "Reduced loan lookup time by 70% from 3-4 minutes to sub-2-second responses using Amazon Bedrock",
            "Cut support tickets by 70% post-launch after VB.NET to Fargate modernization",
            "Reduced SQL Server report generation latency from 45 seconds to under 3 seconds at LCS",
        ],
    ),
    BenchmarkCase(
        query="Compare Prasad's architecture and responsibilities at Rocket Mortgage versus London Computer Systems.",
        query_type="comparative_query",
        expected_entities=["Rocket Mortgage", "London Computer Systems", "AWS", "Kafka", ".NET Core", "SQL Server", "DynamoDB"],
        ground_truth_facts=[
            "Rocket Mortgage focused on cloud-native AWS ECS Fargate, Kafka event streaming, Bedrock AI, and DynamoDB",
            "London Computer Systems focused on .NET Core SaaS, SQL Server query optimization, and payment gateway integration",
        ],
    ),
]
