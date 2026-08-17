# Graph Report - Prasad-Resumes-GraphRAG  (2026-08-17)

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 4125 nodes · 8392 edges · 193 communities (167 shown, 26 thin omitted)
- Extraction: 97% EXTRACTED · 3% INFERRED · 0% AMBIGUOUS · INFERRED: 266 edges (avg confidence: 0.6)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `4d4d2c79`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- engine.py
- _make_id
- _read_text
- extract.py
- graphify/cli.py
- GraphRAGEngine
- reflect.py
- resume_generator.py
- build.py
- .score_bullet
- watch.py
- dedup.py
- MetricsCollector
- cache.py
- hooks.py
- parse_master_resume
- convert_documents
- serve.py
- JobEntry
- CircuitBreaker
- analyze.py
- dispatch_install_cli
- symbol_resolution.py
- TestHealthCheckStructure
- pdf_renderer.py
- IntentClassifier
- facade.py
- TestSMEOntology
- TelemetryTracer
- ProviderConfig
- paths.py
- llm.py
- app.py
- service.py
- app.js
- write_callflow_html
- test_gateway_providers.py
- TestWebUI
- ats_matcher.py
- FileSlice
- __main__.py
- _call_bedrock
- prs.py
- SMEOntology
- PageCountCanvas
- TestGraphRAGE2E
- RetrievalGuardrail
- pascal.py
- scip_ingest.py
- SemanticCache
- parse_resume_markdown
- generate_section_flowchart
- Path
- CsharpNameResolver
- install.py
- TestTTLCache
- callflow_html.py
- diagnostics.py
- ingest.py
- mcp_ingest.py
- api_routes.py
- detect.py
- Path
- security.py
- TestInputSanitizer
- DeltaGraphIndexer
- EntityResolver
- star_generator.py
- static_graph_reader.py
- detect
- manifest_ingest.py
- execute_graphrag_query
- start_proxy_server
- BenchmarkEvaluator
- api_models.py
- export.py
- install
- ProfileManager
- FTS5SearchEngine
- TestPIIRedactor
- query/__init__.py
- ConversationStore
- GitHubIngester
- cover_letter_generator.py
- BenchmarkCase
- pick_text
- cluster.py
- objc.py
- _call_llm
- src/cli.py
- TestATSSimulator
- SlidingWindowRateLimiter
- affected.py
- semantic_cleanup.py
- google_workspace.py
- Path
- _ImageRef
- extract_files_direct
- generators/models.py
- transcribe.py
- TestVercelAPI
- evaluate_retrieval.py
- TestLinkedInOptimizer
- interview_prep.py
- TestSemanticSimilarity
- Counter
- is_rate_limit_error
- TestBenchmarkEvaluatorMetrics
- generate_raw_resume_stepwise
- save_manifest
- ImpactScorer
- sanitize_metadata
- _always_on
- _build_server
- serve
- search_engine.py
- to_wiki
- AggregateBenchmarkReport
- TestCLIMain
- TestConversationStore
- TestRelationshipUpdates
- tree_html.py
- html.py
- verilog.py
- _agents_install
- create_entity_resolver_with_embeddings
- ._cluster_type
- vercel.json
- attach_graph_impact
- resolver_registry.py
- generate_flow_diagram.py
- .get_verb_tier
- test_entity_resolver.py
- query_endpoint
- TestThresholdTuning
- _load_graph
- test_benchmark_eval.py
- OpenRouterProvider
- TestIntentClassifierClassification
- observability/__init__.py
- pad_embedding
- entity_resolver.py
- app_server
- test_baseline_ui.py
- TestDistinctEntitySafety
- TestRetrievalGuardrailEvaluation
- introspect_cargo
- test_graphrag_engine.py
- _extract_with_adaptive_retry
- Any
- reset_engine
- load_graph
- normalize_sections
- humanize_label
- _is_noise_dir
- .classify
- render_pdf_resume
- test_baseline_api.py
- test_capture_baseline_screenshots.py
- TestConfig
- TestErrorSanitization
- _StageTimer
- pascal_resolution.py
- introspect_postgres
- validate_url
- .detect_metrics
- scripts/benchmark_eval.py
- convert_structured_resume.py
- test_llm_live.py
- _ApiKeyMiddleware
- .format_context
- test_security_regressions.py
- test_conftest_fixtures.py
- graphify/__init__.py
- QueryIntent
- graphrag_engine.py
- run_e2e_baseline.py
- test_server_health.py
- setup_oci.sh
- config/__init__.py
- shared/__init__.py
- web/__init__.py
- AsyncClient
- BaseException
- NamedTuple
- post
- _platform_skill_destination
- TestRetrievalGuardrailSelfHealing
- TestConnectionPooling
- .extract_sources
- query.py

## God Nodes (most connected - your core abstractions)
1. `_read_text()` - 114 edges
2. `dispatch_command()` - 114 edges
3. `_make_id()` - 105 edges
4. `_file_stem()` - 72 edges
5. `_rebuild_code()` - 54 edges
6. `EntityResolver` - 48 edges
7. `GraphRAGEngine` - 40 edges
8. `_extract_generic()` - 36 edges
9. `dispatch_install_cli()` - 35 edges
10. `extract()` - 35 edges

## Surprising Connections (you probably didn't know these)
- `TestSemanticSimilarity` --uses--> `EntityResolver`  [INFERRED]
  tests/test_entity_resolver.py → src/postprocessing/entity_resolver.py
- `TestBenchmarkEvaluatorMetrics` --uses--> `BenchmarkEvaluator`  [INFERRED]
  tests/test_benchmark_eval.py → src/observability/benchmark_eval.py
- `TestBenchmarkEvaluatorExecution` --uses--> `AggregateBenchmarkReport`  [INFERRED]
  tests/test_benchmark_eval.py → src/observability/benchmark_eval.py
- `TestBenchmarkModels` --uses--> `AggregateBenchmarkReport`  [INFERRED]
  tests/test_benchmark_eval.py → src/observability/benchmark_eval.py
- `TestConversationStore` --uses--> `ConversationStore`  [INFERRED]
  tests/test_conversation_store.py → src/query/conversation_store.py

## Import Cycles
- None detected.

## Communities (193 total, 26 thin omitted)

### Community 0 - "engine.py"
Cohesion: 0.02
Nodes (122): _c_collect_type_refs(), _cpp_collect_type_refs(), _csharp_attribute_names(), _csharp_classify_base(), _csharp_collect_type_refs(), _csharp_extra_walk(), _csharp_method_receiver_types(), _csharp_namespace_id() (+114 more)

### Community 1 - "_make_id"
Cohesion: 0.02
Nodes (130): extract_lazarus_package(), _import_java(), _import_js(), _import_kotlin(), _import_php(), _import_python(), _import_scala(), _import_swift() (+122 more)

### Community 2 - "_read_text"
Cohesion: 0.06
Nodes (66): _augment_js_reexport_edges(), _get_c_func_name(), _import_lua(), Compatibility wrapper for the JS/TS symbol-resolution post-pass., Get the name from a node using config.name_field, falling back to child types., Recursively unwrap declarator to find the innermost identifier (C)., Extract require('module') from Lua variable_declaration nodes., _resolve_name() (+58 more)

### Community 3 - "extract.py"
Cohesion: 0.03
Nodes (118): _canonicalize_csharp_namespace_nodes(), _check_tree_sitter_version(), extract(), extract_c(), extract_cpp(), extract_csharp(), extract_csproj(), extract_groovy() (+110 more)

### Community 4 - "graphify/cli.py"
Cohesion: 0.07
Nodes (61): distinct_repo_tags(), prefix_graph_for_global(), prune_repo_from_graph(), Return a copy of G with all node IDs prefixed with repo_tag::. Labels are…, Return a unique, human-meaningful repo tag per input graph for merge-graphs.…, Remove all nodes tagged with repo_tag from G in-place. Returns count removed., _clone_repo(), _default_graph_path() (+53 more)

### Community 5 - "GraphRAGEngine"
Cohesion: 0.14
Nodes (7): object, GraphRAGEngine, Path, Loads GraphRAG parquet artifacts into memory and exposes retrieval/search…, Connect to LanceDB and load parquet artefacts (raises FileNotFoundError)., TestGraphRAGEngineInit, TestRetrievalModes

### Community 6 - "reflect.py"
Cohesion: 0.06
Nodes (61): _log_path(), log_query(), _log_responses(), nodes_from_result(), Any, Path, Query logging for graphify — append-only JSONL, fail-silent., Append one JSONL record to the query log. Never raises. (+53 more)

### Community 7 - "resume_generator.py"
Cohesion: 0.06
Nodes (39): constants.py — Generic constants for resume generation and PDF rendering., bold_keywords(), _can_bold_keyword(), _extract_gap_framing(), _extract_top_metrics(), format_tailored_markdown(), generate_raw_resume(), _get_graphrag_context() (+31 more)

### Community 8 - "build.py"
Cohesion: 0.06
Nodes (64): _abs_identity(), build(), build_from_json(), build_merge(), _build_prune_sets(), _coerce_hyperedge_member_refs(), _coerce_id(), _coerce_non_string_ids() (+56 more)

### Community 9 - ".score_bullet"
Cohesion: 0.13
Nodes (11): BaseModel, scoring.py — Action-Verb Impact Scoring & Recency Decay Engine. Provides rule-…, Structured breakdown of bullet impact, recency, and overall composite score., Calculates exponential recency decay: e^(-lambda * delta_t), where delta_t =…, Calculates parameterized composite weight: W = alpha * Duration + beta *…, ScoreBreakdown, tests/test_scoring.py — Unit tests for Action-Verb Impact Scoring & Recency…, Test exponential recency decay calculation. (+3 more)

### Community 10 - "watch.py"
Cohesion: 0.07
Nodes (54): dedupe_edges(), dedupe_nodes(), Collapse nodes sharing an ``id``, last-writer-wins on attributes. Mirrors what…, Collapse exact parallel edges by ``(source, target, relation)``, keeping the…, _apply_resource_limits(), _canonical_graph_for_compare(), _canonical_topology_for_compare(), _changed_path_candidates() (+46 more)

### Community 11 - "dedup.py"
Cohesion: 0.05
Nodes (53): _collision_rank(), _crossfile_fileanchored_blocked(), deduplicate_entities(), _defines_id(), _entropy(), _id_prefixes(), _is_code(), _is_variant_pair() (+45 more)

### Community 12 - "MetricsCollector"
Cohesion: 0.06
Nodes (26): collect_as_text(), get_collector(), MetricsCollector, metrics — In-process counters + histograms for Prometheus-compatible export.…, Return the application-wide MetricsCollector singleton., Reset the singleton -- mainly for tests., Render all stored metrics as Prometheus exposition-format text. Example:: #…, Thread-safe histogram tracking individual observations. (+18 more)

### Community 13 - "cache.py"
Cohesion: 0.07
Nodes (56): _absolutize_ids_in(), _absolutize_source_files_in(), _body_content(), cache_dir(), cached_files(), cached_word_count(), check_semantic_cache(), _cleanup_stale_ast_entries() (+48 more)

### Community 14 - "hooks.py"
Cohesion: 0.07
Nodes (49): _detached_launch(), _git_root(), _has_merge_attr(), _hooks_dir(), install(), _install_hook(), _merge_attr_line(), _merge_driver_status() (+41 more)

### Community 15 - "parse_master_resume"
Cohesion: 0.05
Nodes (38): _extract_certifications(), _extract_contact(), _extract_education(), _extract_gap_framing(), _extract_jobs(), _extract_name(), _extract_skills(), _extract_summary() (+30 more)

### Community 16 - "convert_documents"
Cohesion: 0.07
Nodes (31): main(), convert_documents(), make_out_name(), Path, input_converter.py — Batch document conversion orchestrator., Normalize output filename., Batch converts PDFs and Markdown files from source_dir into plain .txt in…, extract_pdf_text() (+23 more)

### Community 17 - "serve.py"
Cohesion: 0.07
Nodes (54): _bfs(), _complete_induced_edges(), _compute_idf(), _cut_lines_to_budget(), _dfs(), _filter_graph_by_context(), _find_node(), find_node_ambiguity() (+46 more)

### Community 18 - "JobEntry"
Cohesion: 0.13
Nodes (13): JobEntry, JobEntry, BaseModel, Pydantic model representing the complete structured resume data., Pydantic model representing a single job role entry., ResumeData, format_job_heading(), Format single line Job Heading: Job Title | Company Name | Location | Dates (+5 more)

### Community 19 - "CircuitBreaker"
Cohesion: 0.08
Nodes (22): BaseException, CircuitBreaker, ProviderCircuitOpen, Any, Exception, Circuit-breaker pattern for LLM provider failover. Prevents cascading failures…, Manually reset breaker to closed (primarily for testing)., Raised when a request is attempted while the circuit is open. (+14 more)

### Community 20 - "analyze.py"
Cohesion: 0.10
Nodes (35): _cross_community_surprises(), _cross_file_surprises(), _cross_language(), _file_category(), find_import_cycles(), god_nodes(), graph_diff(), _is_concept_node() (+27 more)

### Community 21 - "dispatch_install_cli"
Cohesion: 0.11
Nodes (33): _antigravity_uninstall(), claude_uninstall(), codebuddy_uninstall(), _cursor_uninstall(), dispatch_install_cli(), gemini_uninstall(), _kiro_uninstall(), _print_install_usage() (+25 more)

### Community 22 - "symbol_resolution.py"
Cohesion: 0.09
Nodes (38): disambiguate_ambiguous_candidates(), _path_proximity_winner(), Pick the candidate whose source file is closest to the call site.…, Resolve an ambiguous bare-name call to one candidate, or ``None``. Shared god-…, _bash_make_id(), build_label_index(), build_python_symbol_index(), existing_edge_pairs() (+30 more)

### Community 23 - "TestHealthCheckStructure"
Cohesion: 0.06
Nodes (19): FakeConn, FakeSQLite, mock_sqlite_conn(), patch, test_health_check — Verify /api/health endpoint behavior via unittest. Tests: -…, When LLM gateway raises -> 503 degraded., Response body contains detailed per-dependency information., X-Correlation-ID must be present and consistent. (+11 more)

### Community 24 - "pdf_renderer.py"
Cohesion: 0.09
Nodes (30): ParagraphStyle, _build_certifications_story(), _build_education_story(), _build_experience_story(), _build_header_story(), _build_skills_story(), _build_summary_story(), Any (+22 more)

### Community 25 - "IntentClassifier"
Cohesion: 0.13
Nodes (8): IntentClassifier, Classifies natural-language queries into structured intents using ontology-…, Args: min_confidence: Reserved for future confidence-weighted classification.…, Collect all canonical terms, synonyms, and categories from ontology for…, Test IntentClassifier.get_retrieval_strategy., Test IntentClassifier.classify_with_details., TestClassifyWithDetails, TestRetrievalStrategy

### Community 26 - "facade.py"
Cohesion: 0.08
Nodes (32): BaseProvider, dict, get_provider(), Get provider config by name. Args: provider_name: Key in PROVIDERS dict (e.g.,…, _breaker(), call_serverless_llm(), call_serverless_llm_stream(), _client() (+24 more)

### Community 27 - "TestSMEOntology"
Cohesion: 0.06
Nodes (17): Test suite for the Subject Matter Expert (SME) Technology Ontology., Test expanding empty input or unknown terms., Test relatedness check between synonyms., Test relatedness check between sibling technologies sharing a domain., Test relatedness check between parent categories and child skills., Test that unrelated technologies return False., Test relatedness with identical terms, empty strings, and None., Test normalization of common technology synonyms and abbreviations. (+9 more)

### Community 28 - "TelemetryTracer"
Cohesion: 0.08
Nodes (20): ActiveSpan, get_tracer(), Any, Exception, telemetry.py — Lightweight Distributed Tracing & Latency Telemetry for GraphRAG…, Clear all recorded spans., Return shared TelemetryTracer singleton., Record of a completed execution span. (+12 more)

### Community 29 - "ProviderConfig"
Cohesion: 0.07
Nodes (27): ABC, list_providers(), list_use_cases(), ProviderConfig, Provider registry for flexible LLM/embedding provider configuration. This…, List all available provider names., List all use-cases and their current provider., Configuration for an LLM/embedding provider. (+19 more)

### Community 30 - "paths.py"
Cohesion: 0.10
Nodes (27): _estimate_tokens(), _hr(), print_benchmark(), Graph, _query_subgraph_tokens(), Token-reduction benchmark - measures how much context graphify saves vs naive…, Print a human-readable benchmark report., Return unicode_char if stdout can encode it, else ascii_fallback. Windows… (+19 more)

### Community 31 - "llm.py"
Cohesion: 0.12
Nodes (23): _community_label_lines(), _custom_providers_path(), generate_community_labels(), _get_tokenizer(), _label_batch_with_retry(), label_communities(), _load_custom_providers(), _neutralise_injection_sentinels() (+15 more)

### Community 32 - "app.py"
Cohesion: 0.09
Nodes (31): get, middleware, Request, get_correlation_id(), Store a correlation ID for the current logical thread/task., Return the active correlation ID (generated on first call if absent)., set_correlation_id(), _pdf_to_data_uri() (+23 more)

### Community 33 - "service.py"
Cohesion: 0.09
Nodes (22): get_model_for(), Get (provider_name, model_id, provider_config) for a use-case. Args: use_case:…, llm package — Single LLM access facade for tailoring and matching modules., _build_call_kwargs(), call_llm(), call_llm_for_resume(), call_llm_safe(), call_llm_safe_for_resume() (+14 more)

### Community 34 - "app.js"
Cohesion: 0.11
Nodes (24): analyzeImpact(), appendAssistantMessage(), appendLoadingMessage(), appendUserMessage(), checkATSScore(), clearChat(), close(), copyToClipboard() (+16 more)

### Community 35 - "write_callflow_html"
Cohesion: 0.09
Nodes (28): build_section_node_map(), CallflowOptions, classify_edges(), detect_lang(), html_comment_text(), infer_project_name(), load_labels(), load_report() (+20 more)

### Community 36 - "test_gateway_providers.py"
Cohesion: 0.15
Nodes (14): Decorator that retries a callable on transient errors with exponential backoff.…, retry_with_backoff(), _cfg(), _KeysPatched, _mock_urlopen(), patch, Unit tests for individual provider response-parsing logic. Each provider's sync…, Build a context-manager mock that returns *payload_dict* as JSON bytes. (+6 more)

### Community 37 - "TestWebUI"
Cohesion: 0.06
Nodes (15): test_web_ui.py — Integration and Unit Tests for Web UI FastAPI Backend., Test POST /api/generate-stream returns correct content type., Test POST /api/generate-stream emits all expected progress steps in SSE format., Test POST /api/generate-stream with empty company returns validation error., Test POST /api/chat-stream returns event stream., Test POST /api/chat-stream validation on empty query., Test GET /api/default-resume returns master resume PDF and raw text., Test GET /api/history returns valid resume history entries. (+7 more)

### Community 38 - "ats_matcher.py"
Cohesion: 0.12
Nodes (15): compute_bm25_relevance(), extract_ats_keywords(), _load_tech_patterns(), match_graphrag_stories(), Path, rank_experience_bullets(), ats_matcher.py — ATS keyword extraction from Job Descriptions, SME Ontology…, Rank candidate experience bullets using Action-Verb Impact Scoring, Metric… (+7 more)

### Community 39 - "FileSlice"
Cohesion: 0.11
Nodes (27): _best_cut(), expand_oversized_files(), FileSlice, is_splittable_text(), Path, Intra-file slicing for oversized text documents (#1369). The extraction packer…, Replace each oversized splittable-text file with a list of ``FileSlice``s.…, Read just this slice's characters from its parent file. (+19 more)

### Community 40 - "__main__.py"
Cohesion: 0.10
Nodes (23): _devin_rules_uninstall(), _print_banner(), Remove .windsurf/rules/graphify.md., Remove JSONC-style comments while leaving string content intact., Remove the graphify PreToolUse hook from .claude/settings.json and its local-…, Drop graphify PreToolUse hooks from a single Claude settings file, if present., Remove graphify PreToolUse hook from .codebuddy/settings.json., Amber brain banner on graphify install. TTY-only, never raises. (+15 more)

### Community 41 - "_call_bedrock"
Cohesion: 0.10
Nodes (30): _azure_client(), _backend_pkg_hint(), _call_azure(), _call_bedrock(), _call_claude(), _call_claude_cli(), _call_openai_compat(), _claude_cli_supports_json_schema() (+22 more)

### Community 42 - "prs.py"
Cohesion: 0.23
Nodes (24): bold(), _c(), _ci_icon(), _classify(), cmd_prs(), cyan(), dim(), green() (+16 more)

### Community 43 - "SMEOntology"
Cohesion: 0.10
Nodes (11): SME Tech Ontology & Skill Hierarchy. Provides domain taxonomy, synonym…, Subject Matter Expert (SME) Technology Ontology and Skill Hierarchy., Normalize technology term by stripping whitespace, converting to lowercase, and…, Return parent domain categories for a given technology term. Returns empty list…, Return child skills associated with a high-level category or skill., Expand a list of query terms into related child skills, synonyms, and parent…, Calculate semantic graph distance between two technology terms. 0.0 =…, Evaluate whether two technology terms are related through exact match, parent-… (+3 more)

### Community 44 - "PageCountCanvas"
Cohesion: 0.22
Nodes (5): AdaptivePageCanvas, Canvas that records total generated pages for adaptive two-pass compaction., PageCountCanvas, Canvas recorder to enforce 2-page maximum constraint., TestPageCountCanvas

### Community 45 - "TestGraphRAGE2E"
Cohesion: 0.10
Nodes (16): skipif, TestClient, _has_api_key(), fixture, End-to-end integration tests for GraphRAG query engine., Test invalid mode returns 422 (Pydantic validator rejects it before endpoint)., Test DRIFT mode expands entity connections., Check if any LLM API key is available. (+8 more)

### Community 46 - "RetrievalGuardrail"
Cohesion: 0.15
Nodes (11): _call_retrieval(), Extract high-signal candidate entity terms and technical keywords from query., Check if an entity or its ontology synonyms/canonical form appear in context., Evaluate retrieved context quality against token density and entity coverage…, Find the next mode in the fallback ladder., Check if query contains terms mapped to canonical forms in SYNONYM_MAP., Expand query with canonical technology terms, parent categories, and child…, Execute self-healing retrieval. 1. Queries retrieval_fn with current mode. 2.… (+3 more)

### Community 47 - "pascal.py"
Cohesion: 0.13
Nodes (24): extract_pascal(), _extract_pascal_regex(), _pascal_find_body(), _pascal_split_bases(), _pascal_split_sections(), _pascal_split_uses(), _pascal_strip_comments(), Path (+16 more)

### Community 48 - "scip_ingest.py"
Cohesion: 0.14
Nodes (24): _build_scip_metadata(), _coerce_str(), _emit_relationships(), _emit_symbol_node(), _first_occurrence_line(), ingest_scip_json(), _is_true(), _make_scip_node_id() (+16 more)

### Community 49 - "SemanticCache"
Cohesion: 0.11
Nodes (12): CachedItem, cosine_similarity(), semantic_cache.py — In-memory vector semantic cache for LLM gateway queries.…, Store a query response in the semantic cache., Clear all cached entries., Calculate cosine similarity between two float vectors., In-memory LRU Semantic Vector Cache., Check for exact match or semantic vector match above similarity_threshold. (+4 more)

### Community 50 - "parse_resume_markdown"
Cohesion: 0.12
Nodes (17): clean_em_dashes(), clean_link_url(), create_job_entry(), extract_summary_variants(), _parse_contact_line(), parse_job_heading_components(), parse_resume_markdown(), resume_parser.py — Markdown resume parsing into the ResumeData Pydantic model.… (+9 more)

### Community 51 - "generate_section_flowchart"
Cohesion: 0.12
Nodes (22): generate_overview_graph(), generate_section_flowchart(), group_nodes_by_file(), mermaid_class_defs(), mermaid_init(), mermaid_section_id(), node_label(), node_mermaid_id() (+14 more)

### Community 52 - "Path"
Cohesion: 0.07
Nodes (48): _emit_rescued_import(), extract_astro(), extract_svelte(), extract_vue(), Shared edge/stub emit for the Svelte/Astro/Vue regex-rescue import passes.…, Extract imports from .svelte files: script-block via JS AST + template regex…, Extract imports from .astro files: frontmatter (TS) + template regex fallback.…, Extract imports, symbols, and type refs from a ``.vue`` SFC. Masks the… (+40 more)

### Community 53 - "CsharpNameResolver"
Cohesion: 0.07
Nodes (35): Resolve cross-file Swift member calls (``recv.method()``) to the real…, Resolve cross-file Python qualified class-method calls (``ClassName.method()``)…, Resolve cross-file TS/JS member calls via constructor-injection type tables…, Resolve cross-file C++ member calls (``f.bar()``, ``f->bar()``, ``Foo::bar()``,…, Resolve C# member calls (``recv.Method()``) to the receiver's declared type…, Resolve Java member calls against the receiver's declared type. Explicit type…, Resolve cross-file Objective-C message sends (``[recv sel]``) to the real…, _resolve_cpp_member_calls() (+27 more)

### Community 54 - "install.py"
Cohesion: 0.16
Nodes (23): _claude_pretooluse_hooks(), _gemini_hook(), _install_claude_hook(), _install_codebuddy_hook(), _install_codex_hook(), _install_gemini_hook(), _kilo_uninstall(), _kilo_uninstall_global() (+15 more)

### Community 55 - "TestTTLCache"
Cohesion: 0.09
Nodes (8): Thread-safe, in-memory TTL cache with LRU eviction. Configurable max_size and…, Return cached value or None (miss / expired)., Insert into cache, evicting oldest entry on overflow., Remove all entries and reset metrics. Test-friendly alias., Current number of entries (thread-safe snapshot)., TTLCache, Test TTL cache: basic CRUD, TTL expiry, LRU eviction., TestTTLCache

### Community 56 - "callflow_html.py"
Cohesion: 0.15
Nodes (18): build_community_index(), _community_text(), derive_sections_from_communities(), generate_header(), generate_nav(), _keyword_score(), label_for_community(), node_in_section() (+10 more)

### Community 57 - "diagnostics.py"
Cohesion: 0.19
Nodes (22): _canonical_edge(), _count_extra(), diagnose_extraction(), diagnose_file(), _edge_list(), _exact_signature(), format_diagnostic_json(), format_diagnostic_report() (+14 more)

### Community 58 - "ingest.py"
Cohesion: 0.15
Nodes (24): _detect_url_type(), _download_binary(), _fetch_arxiv(), _fetch_html(), _fetch_tweet(), _fetch_webpage(), _html_to_markdown(), ingest() (+16 more)

### Community 59 - "mcp_ingest.py"
Cohesion: 0.15
Nodes (21): _extract_spock_fallback(), Regex-based fallback for Spock spec files where tree-sitter-groovy cannot parse…, _add_edge(), _add_node(), _detect_package_from_args(), _emit_server(), extract_mcp_config(), is_mcp_config_path() (+13 more)

### Community 60 - "api_routes.py"
Cohesion: 0.15
Nodes (14): get_conversation_store(), conversation_store.py — SQLite-based conversation memory for GraphRAG Q&A…, Return a shared ConversationStore instance (singleton)., Reset singleton — useful for tests., reset_conversation_store(), chat_stream_endpoint(), _handle_query_core(), api_routes.py — Shared FastAPI router for endpoints identical across both apps.… (+6 more)

### Community 61 - "detect.py"
Cohesion: 0.11
Nodes (27): classify_file(), _env_command_args(), FileType, _generic_keyword_hit(), _is_env_template(), _is_graphable_source(), _is_prose_note(), _is_sensitive() (+19 more)

### Community 62 - "Path"
Cohesion: 0.13
Nodes (24): _auto_follow_symlinks(), convert_office_file(), count_words(), docx_to_markdown(), extract_pdf_text(), _file_within_size_cap(), _md5_file(), _os_path() (+16 more)

### Community 63 - "security.py"
Cohesion: 0.08
Nodes (23): _ip_is_blocked(), _max_graph_file_bytes(), Path, Resolve *host* once and return (family, validated_ip) for the first address…, HTTPConnection that resolves + validates DNS once, then connects to the exact…, HTTPSConnection variant of _SSRFGuardedHTTPConnection. Connects to the…, urllib handler that routes http:// through _SSRFGuardedHTTPConnection., urllib handler that routes https:// through _SSRFGuardedHTTPSConnection. (+15 more)

### Community 64 - "TestInputSanitizer"
Cohesion: 0.13
Nodes (10): Security & Input Sanitization Package., InputSanitizer, sanitizer.py — Defensive input sanitization and prompt injection guardrails.…, Result of input sanitization., Defensive input sanitization filter., Sanitizes text by stripping harmful control characters, enforcing maximum…, SanitizedResult, Unit tests for InputSanitizer and Prompt Injection Defense. (+2 more)

### Community 65 - "DeltaGraphIndexer"
Cohesion: 0.15
Nodes (12): DeltaDiffReport, DeltaGraphIndexer, Path, delta_indexer.py — Incremental Delta GraphRAG Indexer. Tracks chunk-level…, Report of changed chunks between runs., Computes incremental delta changes on source text files to avoid redundant…, Split text into semantic section chunks keyed by header title., Compare current source file chunk hashes against stored manifest. (+4 more)

### Community 66 - "EntityResolver"
Cohesion: 0.14
Nodes (11): EntityResolver, Detect and resolve duplicate entities in a GraphRAG entity set. Parameters…, Senior Engineer' / 'Staff Engineer' overlap (ratio 0.690)., AWS' / 'amazon web services' ratio 0.273 < 0.55 — stays separate., Azure' / 'Microsoft Azure' ratio 0.500 < 0.55 — stays separate., Tests for string-based deduplication with realistic name overlaps., Minor typo merged into first-found canonical form., Extra whitespace normalized to clean name. (+3 more)

### Community 67 - "star_generator.py"
Cohesion: 0.13
Nodes (11): star_generator.py — STAR Method Behavioral Interview Response Engine.…, Structured STAR interview response., Format STAR response as readable markdown., Generates behavioral interview answers structured in the STAR methodology., Classify question into a core behavioral dimension., Generate structured STAR response from question and candidate knowledge context., STARGenerator, STARResponse (+3 more)

### Community 68 - "static_graph_reader.py"
Cohesion: 0.18
Nodes (19): clear_static_cache(), Any, static_graph_reader.py — Fast static Parquet/JSON reader and dynamic resume…, Clear in-memory cached entities for testing/reloads., Read pre-computed entities from output graph artifacts or full…, Execute fast keyword match over static pre-computed entities in < 1 second., read_precomputed_entities(), search_static_graph() (+11 more)

### Community 69 - "detect"
Cohesion: 0.13
Nodes (20): detect(), _find_vcs_root(), _git_info_exclude(), ignored_predicate(), _is_ignored(), _load_dir_own_ignore(), _load_graphifyignore(), _parse_gitignore_line() (+12 more)

### Community 70 - "manifest_ingest.py"
Cohesion: 0.13
Nodes (17): _coerce_deps(), extract_package_manifest(), is_package_manifest_path(), _parse_apm(), _parse_apm_fallback(), _parse_pyproject(), _pep508_name(), _pkg_id() (+9 more)

### Community 71 - "execute_graphrag_query"
Cohesion: 0.22
Nodes (7): execute_graphrag_query(), Execute GraphRAG query -- transparently cached via TTLCache. Cache key is…, patch, Unit tests for query search engine module., Verify execute_graphrag_query transparently uses query_cache., TestQueryCacheIntegration, TestSearchEngine

### Community 72 - "start_proxy_server"
Cohesion: 0.16
Nodes (12): main(), check_proxy_health(), _find_litellm_cli(), Path, litellm_runner.py — LiteLLM server setup and process orchestration., Check if the LiteLLM proxy is responsive on specified host and port., Resolve the ``litellm`` CLI from the active venv rather than bare PATH., Launch LiteLLM proxy server using specified config. (+4 more)

### Community 73 - "BenchmarkEvaluator"
Cohesion: 0.14
Nodes (11): BenchmarkEvaluator, Any, Execute coroutine synchronously if needed, safely supporting existing event…, Evaluation harness for calculating precision, recall, faithfulness, and running…, Calculate the proportion of expected entities retrieved in the context., Check if a token or its stem/clean form matches in text., Calculate the recall of ground-truth facts within the retrieved context., Estimate claim groundedness of generated answer in the retrieved context. (+3 more)

### Community 74 - "api_models.py"
Cohesion: 0.15
Nodes (16): model_validator, ATSSimulationRequest, BehavioralQuestionRequest, CoverLetterRequest, DiffResumeRequest, InterviewPrepRequest, LinkedInProfileRequest, BaseModel (+8 more)

### Community 75 - "export.py"
Cohesion: 0.07
Nodes (45): _node_community_map(), Invert communities dict: node_id -> community_id., attach_hyperedges(), backup_if_protected(), _cap_filename(), _cypher_escape(), _cypher_label(), _dedup_node_filenames() (+37 more)

### Community 76 - "install"
Cohesion: 0.14
Nodes (21): _canonical_platform(), _copy_skill_file(), _cursor_install(), _devin_rules_install(), gemini_install(), install(), _kiro_install(), _packaged_skill_refs_dir() (+13 more)

### Community 77 - "ProfileManager"
Cohesion: 0.16
Nodes (11): CandidateProfile, ProfileManager, Path, profile_manager.py — Multi-Profile & Multi-Track Story Bank Manager. Enables…, List all discovered profiles on disk along with default profile., Candidate profile model representing a candidate persona or specialization…, Manages loading, caching, and querying multiple candidate profiles and story…, Retrieve candidate profile by ID. If 'default' or not found on disk, loads the… (+3 more)

### Community 78 - "FTS5SearchEngine"
Cohesion: 0.14
Nodes (12): FTS5SearchEngine, FTSResult, Path, fts_search.py — Embedded SQLite Full-Text Search (FTS5) Engine. Provides sub-…, FTS5 search result item., SQLite FTS5 Full-Text Search indexer and query engine., Initialize SQLite FTS5 virtual table., Clear and re-index a list of document dicts with 'title' and 'content'. (+4 more)

### Community 79 - "TestPIIRedactor"
Cohesion: 0.14
Nodes (10): PIIRedactionResult, PIIRedactor, pii_redactor.py — PII Redaction & Privacy Guardrail. Masks personally…, Result of PII redaction containing masked text and restoration mapping., Masks and restores personal identifiable information., Replace emails and phone numbers with deterministic placeholders., Restore original values using the placeholder mapping., Unit tests for PII Redactor and Data Privacy Guardrails. (+2 more)

### Community 80 - "query/__init__.py"
Cohesion: 0.19
Nodes (11): NamedTuple, ContextQualityReport, HealedRetrievalResult, HealingTraceStep, retrieval_guardrail.py — Self-Healing Retrieval Guardrail Agent. Evaluates…, Evaluation report on retrieved context quality., Step in self-healing execution trace., Result of self-healing retrieval supporting 2-tuple unpacking (context, trace). (+3 more)

### Community 81 - "ConversationStore"
Cohesion: 0.18
Nodes (8): Connection, ConversationStore, Check whether a session already exists., Open a new connection each call with WAL mode and busy timeout for high…, Thread-safe-ish SQLite store for per-session conversation histories., Record one message in the conversation. Returns message id., Return recent conversation history as ordered list of dicts., Delete all messages and the conversation record for *session_id*.

### Community 82 - "GitHubIngester"
Cohesion: 0.17
Nodes (11): GitHubIngester, GitHubProjectStory, Path, github_ingester.py — GitHub Repository & Open-Source Portfolio Ingestion…, Parsed repository project story., Parses code repositories into candidate story bank entries., Analyze repository folder, extracting description from README and detected…, Format GitHub project story as a GraphRAG knowledge graph section. (+3 more)

### Community 83 - "cover_letter_generator.py"
Cohesion: 0.17
Nodes (10): CoverLetterData, CoverLetterGenerator, cover_letter_generator.py — Tailored Cover Letter Generator. Synthesizes a…, Structured cover letter model., Generates targeted cover letters from candidate knowledge graph and job…, Synthesize tailored cover letter content., Render cover letter as formatted markdown., Unit tests for Tailored Cover Letter Generator. (+2 more)

### Community 84 - "BenchmarkCase"
Cohesion: 0.19
Nodes (9): BenchmarkCase, EvaluationResult, BaseModel, A test case definition for GraphRAG retrieval and generation benchmarking., Metrics result for an individual benchmark test case., Test data models for benchmark evaluation., Test engine evaluation execution in BenchmarkEvaluator., TestBenchmarkEvaluatorExecution (+1 more)

### Community 85 - "pick_text"
Cohesion: 0.12
Nodes (22): _describe_node(), format_node_refs(), generate_call_table_rows(), generate_section_cards(), generate_section_intro(), is_zh(), node_kind(), pick_text() (+14 more)

### Community 86 - "cluster.py"
Cohesion: 0.16
Nodes (19): cluster(), cohesion_score(), community_member_sigs(), label_communities_by_hub(), _partition(), Graph, Community detection on NetworkX graphs. Uses Leiden (graspologic) if available,…, Per-community membership fingerprints: ``{cid: sha256(sorted member ids)}``.… (+11 more)

### Community 87 - "objc.py"
Cohesion: 0.18
Nodes (13): _import_c(), _cpp_declarator_name(), _cpp_local_var_types(), Return the bare variable name from a C++ declaration declarator, unwrapping…, Collect ``var -> ClassName`` from local variable declarations in a C++ function…, extract_objc(), _objc_local_var_types(), Path (+5 more)

### Community 88 - "_call_llm"
Cohesion: 0.08
Nodes (30): _backend_env_keys(), _bedrock_inference_config(), _bedrock_response_text(), _call_llm(), _claude_cli_envelope(), _default_model_for_backend(), detect_backend(), _format_backend_env_keys() (+22 more)

### Community 89 - "src/cli.py"
Cohesion: 0.19
Nodes (8): ArgumentParser, build_parser(), main(), cli.py — Unified Command Line Interface for Prasad Resumes GraphRAG., Construct CLI argument parser., Unit tests for src/cli.py main() dispatch. All side effects are mocked; no…, Unit tests for CLI parser and subcommands., TestCLI

### Community 90 - "TestATSSimulator"
Cohesion: 0.17
Nodes (9): ATSReport, ATSSimulator, ats_simulator.py — Automated ATS Score Simulator & Keyword Gap Analyzer.…, Quantitative ATS analysis and gap report., ATS parser simulator and compatibility scorer., Evaluate resume text against target job description., Unit tests for ATS Simulator and Match Scorer., Test suite for ATS parsing simulator and gap analysis. (+1 more)

### Community 91 - "SlidingWindowRateLimiter"
Cohesion: 0.17
Nodes (8): rate_limiter.py — In-memory sliding window rate limiter for FastAPI serverless…, Thread-safe sliding window rate limiter per client IP or key., Check if request is permitted within the sliding window. Returns: Tuple[bool,…, Clear all rate limit state (useful in tests)., SlidingWindowRateLimiter, Unit tests for SlidingWindowRateLimiter., Test suite for sliding window rate limiter., TestSlidingWindowRateLimiter

### Community 92 - "affected.py"
Cohesion: 0.29
Nodes (14): affected_nodes(), AffectedHit, _bare_name(), format_affected(), _format_location(), load_graph(), _node_label(), _normalize_label() (+6 more)

### Community 93 - "semantic_cleanup.py"
Cohesion: 0.19
Nodes (14): _normalize_hyperedge_members(), Canonicalize a hyperedge's member list onto the `nodes` key, in place. If…, _append_rationale_attr(), _is_sentence_like_rationale_label(), load_validated_semantic_fragment(), Path, Load and validate a semantic chunk, rejecting oversize files before parsing.…, Clean up a semantic extraction fragment in-place. Operations: 1. Removes nodes… (+6 more)

### Community 94 - "google_workspace.py"
Cohesion: 0.24
Nodes (14): convert_google_workspace_file(), _extract_file_id_from_url(), _extract_resource_key(), Any, Path, Optional Google Workspace shortcut export support. Google Drive for desktop…, Export a Google Workspace shortcut to a Markdown sidecar. Returns the converted…, Extract a Drive file ID from common Google Docs/Drive URL shapes. (+6 more)

### Community 95 - "Path"
Cohesion: 0.19
Nodes (17): _agents_platform_uninstall(), _agents_uninstall(), _amp_uninstall(), _install_kilo_plugin(), _kilo_config_path(), _kilo_config_write_path(), _load_json_like(), Path (+9 more)

### Community 96 - "_ImageRef"
Cohesion: 0.17
Nodes (13): _anthropic_content(), _bedrock_content(), _image_notes(), _ImageRef, _openai_content(), A single image destined for a vision request. `raw` is None when the image is…, Return refs with pixel data dropped (for non-vision backends)., Text block listing the images so the model emits one node per image. Always… (+5 more)

### Community 97 - "extract_files_direct"
Cohesion: 0.16
Nodes (19): _backend_supports_vision(), _bind_node_evidence(), _build_image_refs(), _dispatched_source_text(), extract_files_direct(), _file_to_text(), _label_identifiers(), Path (+11 more)

### Community 98 - "generators/models.py"
Cohesion: 0.13
Nodes (14): _escape_latex(), ResumeData, latex_renderer.py — LaTeX Resume Markup Generator. Generates Overleaf and…, Escape special LaTeX characters safely., Generate clean LaTeX markup from ResumeData., render_latex_markup(), models.py — Pydantic models for generic, candidate-agnostic resume data…, ResumeData (+6 more)

### Community 99 - "transcribe.py"
Cohesion: 0.21
Nodes (14): build_whisper_prompt(), download_audio(), _get_whisper(), _get_yt_dlp(), is_url(), _model_name(), Path, Transcribe a video/audio file or URL to a .txt transcript. If video_path is a… (+6 more)

### Community 100 - "TestVercelAPI"
Cohesion: 0.13
Nodes (5): api/index.py — Vercel Serverless Entrypoint. Imports the canonical FastAPI app…, skipUnless, Unit tests for Vercel serverless FastAPI endpoints., Regression: empty raw_text must yield 400, not a masked 500 AttributeError., TestVercelAPI

### Community 101 - "evaluate_retrieval.py"
Cohesion: 0.20
Nodes (14): evaluate_query(), main(), _normalize(), _precision_recall(), Any, Path, Evaluation Script — Measure GraphRAG retrieval quality on a query dataset.…, Lowercase, strip non-alpha, return token set. (+6 more)

### Community 102 - "TestLinkedInOptimizer"
Cohesion: 0.19
Nodes (9): LinkedInOptimizer, LinkedInProfileData, linkedin_optimizer.py — LinkedIn Profile & Headline Optimizer. Synthesizes…, Optimized LinkedIn profile components., Synthesizes search-optimized LinkedIn assets., Generate optimized headline, about section, and skill tags., Unit tests for LinkedIn Profile & Headline Optimizer., Test suite for LinkedIn headline and profile optimization. (+1 more)

### Community 103 - "interview_prep.py"
Cohesion: 0.19
Nodes (9): InterviewPrepGenerator, InterviewPrepResult, interview_prep.py — Candidate Interview Prep Question & Talking Point…, Predicted interview questions and talking points., Anticipates interview questions and links them to candidate achievements., Generate predicted interview questions and tailored talking points., Unit tests for Candidate Interview Prep Question Generator., Test suite for interview question prediction and candidate talking points. (+1 more)

### Community 104 - "TestSemanticSimilarity"
Cohesion: 0.18
Nodes (9): _make_mock_embed(), Embedding-aware resolution with mocked vectors. The AND gate requires BOTH…, High embedding sim bridges gap where string sim is moderate., Skill type also benefits from embedding boost., When embed_fn returns None, resolution works via string alone., Both string AND semantic must individually pass for semantic types., Person types skip semantic check — pure string similarity only., Create an embed_fn returning pre-defined normalized vectors for texts. (+1 more)

### Community 105 - "Counter"
Cohesion: 0.12
Nodes (21): derive_flow_chain(), edge_score(), generate_overview_cards(), node_degree_scores(), node_importance(), preferred_edges(), Counter, Aggregate inter-section edge counts and relation names. (+13 more)

### Community 106 - "is_rate_limit_error"
Cohesion: 0.21
Nodes (7): is_rate_limit_error(), BaseException, Exception, _rate_limit_tags(), Return the unified rate-limit detection tags., Return ``True`` when *err* represents a rate-limit / throttling error. Works…, TestIsRateLimitError

### Community 108 - "generate_raw_resume_stepwise"
Cohesion: 0.14
Nodes (11): generate_raw_resume_stepwise(), ResumeData, Generate LLM-tailored raw_resume.txt and PDF resume stepwise, yielding progress., Unit tests for stepwise resume generator (TDD)., Verify correct 8-step sequence is yielded in order., Verify percentages strictly increase., Verify complete step includes correct file paths and non-empty content. Note:…, Verify pipeline continues when LLM is unavailable. (+3 more)

### Community 109 - "save_manifest"
Cohesion: 0.23
Nodes (12): detect_incremental(), load_manifest(), _nfc(), NFC-normalize a path string used as a manifest key. On macOS, ``os.walk`` /…, Return ``key`` as a forward-slash relative path from ``root``. Keys outside…, Inverse of :func:`_to_relative_for_storage`. Re-anchor a stored key against…, Load the manifest from a previous run. Returns {} on any error. When ``root``…, Save current file mtimes + content hashes for change detection. kind="ast" —… (+4 more)

### Community 110 - "ImpactScorer"
Cohesion: 0.15
Nodes (11): ImpactScorer, Engine for action-verb impact classification, quantified metric bonus…, JudgeScore, LLMJudgeEvaluator, judge_evaluator.py — Automated LLM-as-a-Judge Evaluation & Hallucination…, Evaluation output from the Judge auditor., Evaluates factual alignment between generated content and master facts., Score generated bullet against ground truth context for hallucinations. (+3 more)

### Community 111 - "sanitize_metadata"
Cohesion: 0.19
Nodes (12): _import_csharp(), _bash_assignment_base(), _bash_source_suffix(), extract_bash(), Path, Bash extractor. Moved verbatim from graphify/extract.py., Return the literal path suffix of a variable-built `source` argument, or None…, Resolve a top-level assignment's value to a directory, or None if untracked.… (+4 more)

### Community 112 - "_always_on"
Cohesion: 0.18
Nodes (13): _always_on(), claude_install(), codebuddy_install(), _install_skill_references(), Atomically install a packaged references/ sidecar next to SKILL.md. Stages the…, Write the graphify section to the local CLAUDE.md., Install the graphify skill and CODEBUDDY.md section for CodeBuddy., Read a packaged always-on instruction block from graphify/always_on/. The six… (+5 more)

### Community 113 - "_build_server"
Cohesion: 0.21
Nodes (13): _detect_default_branch(), fetch_prs(), fetch_worktrees(), format_prs_text(), _gh(), _parse_ci(), Auto-detect the repo's default branch via gh, then git, then fall back to…, Plain-text PR summary for MCP output (no ANSI). (+5 more)

### Community 114 - "serve"
Cohesion: 0.15
Nodes (11): _build_http_app(), _filter_blank_stdin(), _main(), _MCPASGIApp, Filter blank lines from stdin before MCP reads it. Some MCP clients (Claude…, Start the MCP server over stdio (the default, per-developer transport)., Raw-ASGI wrapper around the Streamable HTTP session manager. Passed to a…, Build the Starlette ASGI app for the Streamable HTTP transport. Split out from… (+3 more)

### Community 115 - "search_engine.py"
Cohesion: 0.18
Nodes (12): CommandRunner, CompletedProcess, default_command_runner(), _execute_query(), Path, search_engine.py -- Search execution and TTL-cached GraphRAG queries. Applies…, Internal: perform the actual GraphRAG query (no caching)., Default process runner using subprocess.run. (+4 more)

### Community 116 - "to_wiki"
Cohesion: 0.26
Nodes (13): _community_article(), _cross_community_links(), _god_node_article(), _index_md(), _md_link(), Graph, Path, Make a label safe for use as a filename across platforms. Substitutes… (+5 more)

### Community 119 - "TestConversationStore"
Cohesion: 0.15
Nodes (4): Fresh tmp db for each test so sessions are isolated., Remove temp db after each test., SQLite CHECK constraint should reject invalid roles., TestConversationStore

### Community 120 - "TestRelationshipUpdates"
Cohesion: 0.15
Nodes (7): Verify relationship relabeling after entity merging. NOTE: update_relationships…, Edges referencing merged variants get relabeled., No entity merges → no relationship relabeling., Both source AND target sides can be relabeled., Names not in canonical_map are left untouched., Audit trail records each relabeling change., TestRelationshipUpdates

### Community 121 - "tree_html.py"
Cohesion: 0.30
Nodes (11): _is_file_node_label(), Whether *label* is a file node's label for *source_file* — the bare basename,…, build_tree(), _common_root(), emit_html(), _make_truncation_leaf(), Any, Path (+3 more)

### Community 122 - "html.py"
Cohesion: 0.14
Nodes (17): Shared constants/helpers for the graphify exporters package. Symbols used by…, _html_script(), _html_styles(), _hyperedge_script(), Graph, html — moved verbatim from graphify/export.py., Return the effective viz node limit, honoring GRAPHIFY_VIZ_NODE_LIMIT env var.…, Generate an interactive vis.js HTML visualization of the graph. Features: node… (+9 more)

### Community 123 - "verilog.py"
Cohesion: 0.24
Nodes (10): _augment_systemverilog_semantics(), extract_verilog(), Path, Verilog extractor. Moved verbatim from graphify/extract.py., First `simple_identifier` under node in pre-order, or None. tree-sitter-verilog…, Extract modules, functions, tasks, package imports, instantiations, and…, _sv_collect_type_refs(), _sv_first_identifier() (+2 more)

### Community 124 - "_agents_install"
Cohesion: 0.17
Nodes (12): _agents_install(), _agents_platform_install(), _amp_install(), _amp_legacy_cleanup(), _install_opencode_plugin(), _kilo_install(), Write graphify.js plugin and register it in opencode.json., Write the graphify section to the local AGENTS.md for always-on platforms. (+4 more)

### Community 125 - "create_entity_resolver_with_embeddings"
Cohesion: 0.21
Nodes (8): main(), create_entity_resolver_with_embeddings(), Create an EntityResolver loaded with sentence-transformers embeddings. Returns…, Test create_entity_resolver_with_embeddings()., Absent sentence_transformers → string-only resolver., Present sentence_transformers → embed_fn configured., Custom thresholds forwarded correctly., TestFactoryFunction

### Community 126 - "._cluster_type"
Cohesion: 0.12
Nodes (9): Any, Resolve duplicate entities in-place and return cleaned set. Parameters…, Relabel relationships to use canonical entity names after resolution.…, Cluster entity indices of a single type into (lead_index → [member_indices]).…, Generate candidate index pairs using inverted n-gram index and prefix blocking.…, Return SequenceMatcher ratio between two strings., Compute cosine similarity between two text embeddings. Falls back to 0.0 when…, Composite score: AND-gate for semantic types, pure string otherwise. (+1 more)

### Community 127 - "vercel.json"
Cohesion: 0.17
Nodes (11): maxDuration, runtime, build, env, env, OUTPUT_DIR, PYTHON_VERSION, functions (+3 more)

### Community 128 - "attach_graph_impact"
Cohesion: 0.20
Nodes (11): attach_graph_impact(), build_community_labels(), compute_pr_impact(), fetch_pr_files(), _load_graph_json(), _path_match(), Path, True if graph_src and pr_file refer to the same file (path-boundary safe). (+3 more)

### Community 129 - "resolver_registry.py"
Cohesion: 0.24
Nodes (10): LanguageResolver, Path, Registry for cross-file, language-specific resolution passes. Some…, One cross-file, language-specific resolution pass. ``resolve`` has the…, Append a resolver to the global registry and return it (for inline use)., Return a copy of the registered resolvers, in registration order., Run every resolver whose suffix appears in ``paths``. Behaviorally identical to…, register() (+2 more)

### Community 130 - "generate_flow_diagram.py"
Cohesion: 0.33
Nodes (10): check_layout(), emit(), esc(), main(), generate_flow_diagram.py — Two-flow architecture diagram from how-it-works.md…, rects_intersect(), render_png(), seg_rect_cross() (+2 more)

### Community 131 - ".get_verb_tier"
Cohesion: 0.24
Nodes (5): Extracts and normalizes the leading verb/word from a bullet point., Determines the tier of the action verb in the bullet. Returns: 1: Tier 1…, Returns the base verb score corresponding to the bullet's action verb tier: -…, Test action-verb tier classification and scoring., TestImpactScorerVerbTiers

### Community 132 - "test_entity_resolver.py"
Cohesion: 0.20
Nodes (8): Records one merge decision., ResolutionPair, Unit tests for src/postprocessing/entity_resolver.EntityResolver. All tests use…, Boundary conditions and error-free operation., Attributes from merged variants accumulate into canonical row., Test candidate blocking on larger entity sets to verify O(N log N) scaling and…, TestCandidateBlockingScale, TestEmptyAndEdgeCases

### Community 133 - "query_endpoint"
Cohesion: 0.21
Nodes (7): post, query_endpoint(), Execute GraphRAG query with full retrieval → LLM streaming. Returns a single…, save_edit_endpoint(), Unit tests that both FastAPI apps serve /api/query and /api/chat-stream from…, Check if shared router routes are registered., TestSharedRoutes

### Community 134 - "TestThresholdTuning"
Cohesion: 0.18
Nodes (7): _build_full_entities(), Default threshold on full realistic dataset preserves distinct entities., Configurable thresholds control merge aggressiveness., Stricter threshold → fewer merges → more final entities., At zero threshold everything in same type bucket merges., Full realistic entity set used by several tests., TestThresholdTuning

### Community 135 - "_load_graph"
Cohesion: 0.22
Nodes (7): _communities_from_graph(), _GraphContextCache, _load_graph(), Thread-safe graph contexts: one pinned default plus an LRU of projects., Build one entry for an already-resolved path and known file key.…, Return a fresh context, retaining project contexts by LRU order.…, Reconstruct community dict from community property stored on nodes.

### Community 136 - "test_benchmark_eval.py"
Cohesion: 0.22
Nodes (5): asyncio, benchmark_eval.py — Automated Synthetic Evaluation Harness & Benchmarking for…, Unit tests for Automated Synthetic Evaluation Harness & Benchmarking., Verify default synthetic benchmark dataset covers key resume scenarios., TestDefaultBenchmarkDataset

### Community 137 - "OpenRouterProvider"
Cohesion: 0.33
Nodes (3): OpenRouterProvider, OpenRouter: OpenAI-compatible /chat/completions + /embeddings., nvidia/nemotron-3-embed-1b:free via /v1/embeddings.

### Community 139 - "observability/__init__.py"
Cohesion: 0.25
Nodes (7): Logger, LogRecord, get_logger(), observability — Structured logging with correlation ID propagation. Provides: -…, JSON-log formatter that always includes the correlation ID., Return a structured logger named *name*. Attaches a JSON formatter to the root…, _StructuredFormatter

### Community 140 - "pad_embedding"
Cohesion: 0.31
Nodes (5): _embedding_dim(), pad_embedding(), Resolve the canonical embedding dimension, falling back to 2048., Pad or truncate an embedding list to *target_dim*. Defaults to the value…, TestPadEmbedding

### Community 141 - "entity_resolver.py"
Cohesion: 0.25
Nodes (4): Entity resolution for GraphRAG knowledge graphs. Merges duplicate entities…, Minimal union-find for grouping indices., _UnionFind, Post-processing utilities for GraphRAG knowledge graphs.

### Community 142 - "app_server"
Cohesion: 0.28
Nodes (8): app_server(), _free_port(), fixture, Shared fixtures for end-to-end tests. `app_server` boots the FastAPI app…, Return an OS-assigned free TCP port on localhost., Poll GET / until it returns HTTP 200 or the timeout expires., Boot the local UI app in a subprocess and yield its base URL., _wait_until_healthy()

### Community 143 - "test_baseline_ui.py"
Cohesion: 0.39
Nodes (8): _goto(), Baseline characterization tests for the browser UI of the local server. Uses…, test_chat_elements_present(), test_default_tab_active_and_resume_loads(), test_page_loads_with_title(), test_system_status_badge_present(), test_tab_switching(), test_tailor_form_elements_present()

### Community 144 - "TestDistinctEntitySafety"
Cohesion: 0.22
Nodes (5): Verify truly distinct entities NEVER merge at default threshold (0.85)., AWS Lambda / EC2 / S3 are distinct products., Completely different technologies stay separate., Cross-type comparison is never attempted., TestDistinctEntitySafety

### Community 146 - "introspect_cargo"
Cohesion: 0.46
Nodes (7): introspect_cargo(), _load_toml(), _member_manifest_paths(), Any, Path, Cargo manifest introspection for workspace-internal crate dependencies., Return crate nodes and internal dependency edges from Cargo manifests.

### Community 147 - "test_graphrag_engine.py"
Cohesion: 0.23
Nodes (8): get_engine(), Return a shared GraphRAGEngine instance (singleton per root_dir)., _loop(), skipUnless, Tests for GraphRAGEngine — real parquet artifacts from GraphRAG index., _run(), TestGetEngine, TestRetrieveHealed

### Community 148 - "_extract_with_adaptive_retry"
Cohesion: 0.15
Nodes (13): bisect_slice(), Split a slice into two halves at a newline near its midpoint, or None. Used by…, _chunk_partial_files(), _extract_with_adaptive_retry(), _looks_like_context_exceeded(), _mark_partial(), _merged_partial_files(), BaseException (+5 more)

### Community 149 - "Any"
Cohesion: 0.24
Nodes (6): DataFrame, Any, Delegate embedding generation to serverless_gateway (OpenRouter → Gemini)., Simple keyword search fallback when vector embeddings fail., Single-entry retrieval dispatcher., Retrieve context with autonomous self-healing guardrail verification. Evaluates…

### Community 150 - "reset_engine"
Cohesion: 0.20
Nodes (8): Reset singleton — useful for tests., reset_engine(), fixture, Shared pytest fixtures for unit tests. These fixtures are consumed by pytest-…, Reset module-level singletons before each test to prevent pollution., Minimal master-resume document shaped like input/MASTER_RESUME.txt., _reset_singletons(), sample_master_resume_text()

### Community 151 - "load_graph"
Cohesion: 0.16
Nodes (14): endpoint_id(), first_list(), first_present(), load_graph(), _node_link_payload(), normalize_edge(), normalize_node(), Return the first non-empty value for any candidate key. (+6 more)

### Community 152 - "normalize_sections"
Cohesion: 0.33
Nodes (6): html_anchor_id(), normalize_communities(), normalize_sections(), Generate a stable, unique HTML anchor ID., Normalize section community lists from JSON or simple strings., Ensure sections have safe unique IDs and an overview section first.

### Community 153 - "humanize_label"
Cohesion: 0.33
Nodes (6): humanize_label(), node_display_name(), Readable node label for tables and summaries., Truncate without splitting Mermaid syntax., Convert graph labels into short labels people can scan in a diagram., truncate_text()

### Community 154 - "_is_noise_dir"
Cohesion: 0.33
Nodes (6): _has_coverage_artifacts(), _has_venv_markers(), _is_noise_dir(), True only when *d* holds files a coverage tool actually generated. ``coverage``…, True only when *d* has actual virtualenv/conda structure on disk.…, Return True if this directory name looks like a venv, cache, or dep dir.

### Community 155 - ".classify"
Cohesion: 0.21
Nodes (8): _check_any(), _norm(), Lowercase + collapse whitespace., Check if ANY regex trigger matches the normalized query., Extract recognized technology terms and domain categories from query using…, Determine the intent behind *query*. Classification priority: 1. Comparative…, Return the recommended retrieval configuration for an intent., Classify query with confidence score, extracted entities, intent, and suggested…

### Community 156 - "render_pdf_resume"
Cohesion: 0.24
Nodes (7): Path, Render PDF document directly from ResumeData Pydantic model with adaptive two-…, Render rule-based ATS compliant PDF resume supporting Path or pre-parsed…, render_pdf_from_model(), render_pdf_resume(), Unit tests for PDF renderer module., TestPDFRenderer

### Community 158 - "test_capture_baseline_screenshots.py"
Cohesion: 0.53
Nodes (5): _goto(), Captures baseline reference screenshots of the three main UI tabs. Screenshots…, test_capture_chat_tab(), test_capture_default_tab(), test_capture_tailor_tab()

### Community 162 - "pascal_resolution.py"
Cohesion: 0.50
Nodes (4): _pascal_raw_calls(), Cross-file resolution for Pascal/Delphi calls to inherited methods. The per-…, Resolve Pascal/Delphi calls to a method inherited across file boundaries.…, resolve_pascal_inherited_calls()

### Community 163 - "introspect_postgres"
Cohesion: 0.50
Nodes (4): introspect_postgres(), _quote_ident(), Connect to PostgreSQL, reconstruct DDL, and extract via extract_sql()., Double-quote a PostgreSQL identifier, escaping embedded double-quotes.

### Community 164 - "validate_url"
Cohesion: 0.22
Nodes (8): _build_opener(), _NoFileRedirectHandler, Raise ValueError if *url* is not http or https, or targets a private/internal…, Redirect handler that re-validates every redirect target. Prevents open-…, Fetch *url* and return raw bytes. Protections applied: - URL scheme validated…, safe_fetch(), validate_url(), OpenerDirector

### Community 165 - ".detect_metrics"
Cohesion: 0.31
Nodes (4): Detects quantified metrics (percentages, currency, latency, scale) within the…, Computes metric bonus (+0.2 if quantified metrics are present, optionally…, Test metric extraction and metric bonus calculation., TestImpactScorerMetricDetection

### Community 166 - "scripts/benchmark_eval.py"
Cohesion: 0.60
Nodes (4): main(), Path, scripts/benchmark_eval.py — Automated Synthetic Evaluation Harness runner.…, run_benchmark()

### Community 167 - "convert_structured_resume.py"
Cohesion: 0.50
Nodes (4): main(), _parse_master_resume(), Convert master resume from markdown to structured JSON before GraphRAG…, Parse the raw MASTER_RESUME.md into structured sections.

### Community 170 - ".format_context"
Cohesion: 0.29
Nodes (3): Render a retrieved *context* dict into a human-readable string for LLM…, Stream a GraphRAG answer token-by-token via SSE frames. This method combines…, TestFormatContext

### Community 174 - "QueryIntent"
Cohesion: 0.27
Nodes (7): Enum, QueryIntent, IntentClassifier — Classify query intent to optimize retrieval strategy. Routes…, Categories of user queries against the knowledge graph., Unit tests for IntentClassifier and QueryIntent enum., Test QueryIntent enum definitions., TestQueryIntentEnum

### Community 175 - "graphrag_engine.py"
Cohesion: 0.31
Nodes (4): graphrag_engine.py — Real GraphRAG query engine backed by LanceDB vector search…, Check whether *tid* appears inside *arr*, handling ndarray / list / set types., _tid_match(), TestTidMatch

### Community 188 - "_platform_skill_destination"
Cohesion: 0.25
Nodes (8): _antigravity_finalize(), _antigravity_install(), _platform_skill_destination(), Install graphify for Google Antigravity (global skill + .agents/rules +…, After a successful install, update .graphify_version in all other known skill…, Return the skill destination for a platform and scope., Write Antigravity's always-on layer next to an installed skill. Injects the…, _refresh_all_version_stamps()

### Community 190 - "TestConnectionPooling"
Cohesion: 0.33
Nodes (4): Verify _ensure_session produces correct TCPConnector + ClientTimeout config.…, Confirm _ensure_session source includes pooling configuration., Confirm _ensure_session source includes granular timeouts., TestConnectionPooling

### Community 192 - "query.py"
Cohesion: 1.00
Nodes (3): interactive(), main(), run_query()

## Knowledge Gaps
- **8 isolated node(s):** `FakeSQLite`, `maxDuration`, `runtime`, `OUTPUT_DIR`, `PYTHON_VERSION` (+3 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **26 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `get_model_for()` connect `service.py` to `app.py`, `facade.py`, `ProviderConfig`?**
  _High betweenness centrality (0.058) - this node is a cross-community bridge._
- **Why does `dispatch_command()` connect `graphify/cli.py` to `extract.py`, `reflect.py`, `_load_graph`, `build.py`, `watch.py`, `cache.py`, `hooks.py`, `serve.py`, `introspect_cargo`, `analyze.py`, `paths.py`, `llm.py`, `_StageTimer`, `write_callflow_html`, `introspect_postgres`, `FileSlice`, `__main__.py`, `_call_bedrock`, `prs.py`, `diagnostics.py`, `ingest.py`, `detect`, `export.py`, `cluster.py`, `_call_llm`, `affected.py`, `semantic_cleanup.py`, `save_manifest`, `_build_server`, `to_wiki`, `tree_html.py`, `html.py`?**
  _High betweenness centrality (0.047) - this node is a cross-community bridge._
- **Why does `SMEOntology` connect `SMEOntology` to `star_generator.py`, `ats_matcher.py`, `ImpactScorer`, `QueryIntent`, `query/__init__.py`, `RetrievalGuardrail`, `IntentClassifier`, `TestSMEOntology`?**
  _High betweenness centrality (0.046) - this node is a cross-community bridge._
- **Are the 5 inferred relationships involving `dispatch_command()` (e.g. with `to_html()` and `_file_hash()`) actually correct?**
  _`dispatch_command()` has 5 INFERRED edges - model-reasoned connections that need verification._
- **What connects `FakeSQLite`, `maxDuration`, `runtime` to the rest of the system?**
  _8 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `engine.py` be split into smaller, more focused modules?**
  _Cohesion score 0.01993181222134802 - nodes in this community are weakly interconnected._
- **Should `_make_id` be split into smaller, more focused modules?**
  _Cohesion score 0.024966442953020133 - nodes in this community are weakly interconnected._