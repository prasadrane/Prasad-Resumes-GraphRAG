# Graph Report - .agents  (2026-09-22)

## Corpus Check
- 80 files · ~424,435 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 2099 nodes · 4393 edges · 27 communities detected
- Extraction: 74% EXTRACTED · 26% INFERRED · 0% AMBIGUOUS · INFERRED: 1153 edges (avg confidence: 0.7)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- [[_COMMUNITY_Community 0|Community 0]]
- [[_COMMUNITY_Community 1|Community 1]]
- [[_COMMUNITY_Community 2|Community 2]]
- [[_COMMUNITY_Community 3|Community 3]]
- [[_COMMUNITY_Community 4|Community 4]]
- [[_COMMUNITY_Community 5|Community 5]]
- [[_COMMUNITY_Community 6|Community 6]]
- [[_COMMUNITY_Community 7|Community 7]]
- [[_COMMUNITY_Community 8|Community 8]]
- [[_COMMUNITY_Community 9|Community 9]]
- [[_COMMUNITY_Community 10|Community 10]]
- [[_COMMUNITY_Community 11|Community 11]]
- [[_COMMUNITY_Community 12|Community 12]]
- [[_COMMUNITY_Community 13|Community 13]]
- [[_COMMUNITY_Community 14|Community 14]]
- [[_COMMUNITY_Community 15|Community 15]]
- [[_COMMUNITY_Community 16|Community 16]]
- [[_COMMUNITY_Community 17|Community 17]]
- [[_COMMUNITY_Community 18|Community 18]]
- [[_COMMUNITY_Community 19|Community 19]]
- [[_COMMUNITY_Community 20|Community 20]]
- [[_COMMUNITY_Community 21|Community 21]]
- [[_COMMUNITY_Community 22|Community 22]]
- [[_COMMUNITY_Community 23|Community 23]]
- [[_COMMUNITY_Community 24|Community 24]]
- [[_COMMUNITY_Community 25|Community 25]]
- [[_COMMUNITY_Community 26|Community 26]]

## God Nodes (most connected - your core abstractions)
1. `LanguageConfig` - 163 edges
2. `_read_text()` - 86 edges
3. `_make_id()` - 75 edges
4. `FileSlice` - 70 edges
5. `CsharpNameResolver` - 69 edges
6. `dispatch_command()` - 63 edges
7. `LanguageResolver` - 60 edges
8. `_rebuild_code()` - 51 edges
9. `_file_stem()` - 43 edges
10. `dispatch_install_cli()` - 33 edges

## Surprising Connections (you probably didn't know these)
- `dispatch_command()` --calls--> `format_diagnostic_json()`  [INFERRED]
  skills\graphify\cli.py → skills\graphify\diagnostics.py
- `dispatch_command()` --calls--> `format_diagnostic_report()`  [INFERRED]
  skills\graphify\cli.py → skills\graphify\diagnostics.py
- `FileSlice` --uses--> `Return the first configured API key for backend, or an empty string.`  [INFERRED]
  skills\graphify\file_slice.py → skills\graphify\llm.py
- `LanguageConfig` --uses--> `Nearest tsconfig.json/jsconfig.json walking up from start_dir.      `jsconfig.`  [INFERRED]
  skills\graphify\extractors\models.py → skills\graphify\extractors\resolution.py
- `LanguageConfig` --uses--> `Walk up from start_dir to find tsconfig/jsconfig.json and return compilerOptions`  [INFERRED]
  skills\graphify\extractors\models.py → skills\graphify\extractors\resolution.py

## Communities

### Community 0 - "Community 0"
Cohesion: 0.01
Nodes (292): extract_apex(), Apex extractor. Moved verbatim from graphify/extract.py., Extract classes, interfaces, enums, methods, and Salesforce constructs from, _file_stem(), Stem used as the node-ID prefix for a file and its symbols.      The full path, _read_text(), extract_elixir(), Elixir extractor. Moved verbatim from graphify/extract.py. (+284 more)

### Community 1 - "Community 1"
Cohesion: 0.02
Nodes (175): _make_id(), _build_csharp_type_def_index(), CsharpNameResolver, _is_cs_file(), _metadata(), _namespace(), C# cross-file resolution.  The config-driven C# *extractor* (``extract_csharp`, Namespace/using/alias-aware C# simple-name resolution.      Factored out of `` (+167 more)

### Community 2 - "Community 2"
Cohesion: 0.02
Nodes (167): affected_nodes(), AffectedHit, _bare_name(), format_affected(), _format_location(), _node_label(), _normalize_label(), _prefer_file_node() (+159 more)

### Community 3 - "Community 3"
Cohesion: 0.03
Nodes (156): _best_cut(), bisect_slice(), expand_oversized_files(), FileSlice, is_splittable_text(), Intra-file slicing for oversized text documents (#1369).  The extraction packe, Replace each oversized splittable-text file with a list of ``FileSlice``s., Read just this slice's characters from its parent file. (+148 more)

### Community 4 - "Community 4"
Cohesion: 0.03
Nodes (150): _reenter_main(), _agents_install(), _agents_platform_install(), _agents_platform_uninstall(), _agents_uninstall(), _always_on(), _amp_install(), _amp_legacy_cleanup() (+142 more)

### Community 5 - "Community 5"
Cohesion: 0.02
Nodes (122): edge_datas(), Return every edge attribute dict for (u, v); always a list., introspect_cargo(), _load_toml(), _member_manifest_paths(), Cargo manifest introspection for workspace-internal crate dependencies., Return crate nodes and internal dependency edges from Cargo manifests., _clone_repo() (+114 more)

### Community 6 - "Community 6"
Cohesion: 0.03
Nodes (99): _auto_follow_symlinks(), classify_file(), convert_office_file(), count_words(), detect(), detect_incremental(), docx_to_markdown(), _env_command_args() (+91 more)

### Community 7 - "Community 7"
Cohesion: 0.03
Nodes (94): _estimate_tokens(), _hr(), print_benchmark(), _query_subgraph_tokens(), Token-reduction benchmark - measures how much context graphify saves vs naive fu, Print a human-readable benchmark report., Return unicode_char if stdout can encode it, else ascii_fallback.      Windows, Horizontal rule that survives non-UTF-8 stdout (e.g. Windows cp1252 console). (+86 more)

### Community 8 - "Community 8"
Cohesion: 0.04
Nodes (84): _is_ast_tier(), _load_existing_graph(), Load (nodes, edges, hyperedges, directed) from an existing graph.json for     a, AST vs semantic tier. _origin wins when present; unstamped legacy items     (pr, cluster(), cohesion_score(), community_member_sigs(), label_communities_by_hub() (+76 more)

### Community 9 - "Community 9"
Cohesion: 0.03
Nodes (89): _abs_identity(), build(), build_from_json(), build_merge(), _build_prune_sets(), _coerce_hyperedge_member_refs(), _coerce_id(), _coerce_non_string_ids() (+81 more)

### Community 10 - "Community 10"
Cohesion: 0.05
Nodes (67): extract_dart(), Dart extractor. Moved verbatim from graphify/extract.py., Extract classes, mixins, functions, imports, generic calls, and annotations from, _collision_rank(), _crossfile_fileanchored_blocked(), deduplicate_entities(), _defines_id(), _entropy() (+59 more)

### Community 11 - "Community 11"
Cohesion: 0.05
Nodes (57): _detect_url_type(), _download_binary(), _fetch_arxiv(), _fetch_html(), _fetch_tweet(), _fetch_webpage(), _html_to_markdown(), ingest() (+49 more)

### Community 12 - "Community 12"
Cohesion: 0.05
Nodes (62): _import_csharp(), _build_scip_metadata(), _coerce_str(), _emit_relationships(), _emit_symbol_node(), _first_occurrence_line(), ingest_scip_json(), _is_true() (+54 more)

### Community 13 - "Community 13"
Cohesion: 0.05
Nodes (59): _absolutize_ids_in(), _absolutize_source_files_in(), _body_content(), cache_dir(), cached_files(), cached_word_count(), check_semantic_cache(), _cleanup_stale_ast_entries() (+51 more)

### Community 14 - "Community 14"
Cohesion: 0.05
Nodes (54): aggregate_lessons(), _build_id_label_maps(), build_learning_overlay(), _code_fingerprint(), _content_hash(), _decay(), _dedupe_by_question(), _doc_community() (+46 more)

### Community 15 - "Community 15"
Cohesion: 0.06
Nodes (45): _detached_launch(), _git_root(), _has_merge_attr(), _hooks_dir(), install(), _install_hook(), _merge_attr_line(), _merge_driver_status() (+37 more)

### Community 16 - "Community 16"
Cohesion: 0.05
Nodes (46): _add_edge(), _add_node(), _detect_package_from_args(), _emit_server(), extract_mcp_config(), is_mcp_config_path(), _make_id(), mcp_ingest.py — Extract MCP (Model Context Protocol) server configuration files. (+38 more)

### Community 17 - "Community 17"
Cohesion: 0.1
Nodes (46): _get_backend_api_key(), Return the first configured API key for backend, or an empty string., attach_graph_impact(), bold(), build_community_labels(), _c(), _ci_icon(), _classify() (+38 more)

### Community 18 - "Community 18"
Cohesion: 0.09
Nodes (35): _cross_community_surprises(), _cross_file_surprises(), _cross_language(), _file_category(), find_import_cycles(), god_nodes(), graph_diff(), _is_concept_node() (+27 more)

### Community 19 - "Community 19"
Cohesion: 0.16
Nodes (19): _canonical_edge(), _count_extra(), diagnose_extraction(), diagnose_file(), _edge_list(), _exact_signature(), format_diagnostic_json(), format_diagnostic_report() (+11 more)

### Community 20 - "Community 20"
Cohesion: 0.14
Nodes (15): _coerce_deps(), extract_package_manifest(), is_package_manifest_path(), _parse_apm(), _parse_apm_fallback(), _parse_pyproject(), _pep508_name(), _pkg_id() (+7 more)

### Community 21 - "Community 21"
Cohesion: 0.27
Nodes (9): _augment_systemverilog_semantics(), extract_verilog(), Verilog extractor. Moved verbatim from graphify/extract.py., First `simple_identifier` under node in pre-order, or None.      tree-sitter-v, Extract modules, functions, tasks, package imports, instantiations, and     Sys, _sv_collect_type_refs(), _sv_first_identifier(), _sv_split_type_list() (+1 more)

### Community 22 - "Community 22"
Cohesion: 0.2
Nodes (9): extract_powershell(), extract_powershell_manifest(), _psd1_collect_string_literals(), _psd1_module_name(), Powershell extractor. Moved verbatim from graphify/extract.py., Extract functions, classes, methods, and using statements from a .ps1 file., Recursively collect all string_literal text values under *node*., Derive a bare module name from a raw string value.      e.g. 'MyModule.psm1' → (+1 more)

### Community 23 - "Community 23"
Cohesion: 0.29
Nodes (7): _bash_assignment_base(), _bash_source_suffix(), extract_bash(), Bash extractor. Moved verbatim from graphify/extract.py., Return the literal path suffix of a variable-built `source` argument, or     No, Resolve a top-level assignment's value to a directory, or None if untracked., Extract functions, source imports, and cross-function calls from a .sh file.

### Community 24 - "Community 24"
Cohesion: 0.4
Nodes (5): extract_json(), _is_config_json(), Json_config extractor. Moved verbatim from graphify/extract.py., True if a .json file is a recognized config/manifest worth AST-extracting., Extract structure and dependency edges from a *config/manifest* .json file.

### Community 25 - "Community 25"
Cohesion: 0.5
Nodes (1): Per-language extractors, incrementally migrated out of graphify/extract.py.  D

### Community 26 - "Community 26"
Cohesion: 1.0
Nodes (1): Shared constants/helpers for the graphify exporters package.  Symbols used by

## Knowledge Gaps
- **645 isolated node(s):** `Lowercased label with the callable decoration (trailing "()") removed.`, `Return the file-level node when a source_file query matches many nodes.`, `Graph analysis: god nodes (most connected), surprising connections (cross-commun`, `Return True if two source files belong to different language families.`, `Invert communities dict: node_id -> community_id.` (+640 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **Thin community `Community 25`** (4 nodes): `__init__.py`, `__getattr__()`, `__init__.py`, `Per-language extractors, incrementally migrated out of graphify/extract.py.  D`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 26`** (2 nodes): `Shared constants/helpers for the graphify exporters package.  Symbols used by`, `base.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `dispatch_command()` connect `Community 5` to `Community 2`, `Community 3`, `Community 4`, `Community 7`, `Community 8`, `Community 9`, `Community 10`, `Community 13`, `Community 16`, `Community 17`, `Community 18`, `Community 19`?**
  _High betweenness centrality (0.110) - this node is a cross-community bridge._
- **Why does `_rebuild_code()` connect `Community 8` to `Community 1`, `Community 2`, `Community 5`, `Community 6`, `Community 7`, `Community 9`, `Community 10`, `Community 18`?**
  _High betweenness centrality (0.073) - this node is a cross-community bridge._
- **Why does `LanguageConfig` connect `Community 0` to `Community 1`?**
  _High betweenness centrality (0.046) - this node is a cross-community bridge._
- **Are the 244 inferred relationships involving `str` (e.g. with `_node_label()` and `_format_location()`) actually correct?**
  _`str` has 244 INFERRED edges - model-reasoned connections that need verification._
- **Are the 162 inferred relationships involving `LanguageConfig` (e.g. with `Deterministic structural extraction from source code using tree-sitter. Outputs` and `File-level node ID matching the skill.md spec: ``{parent_dir}_{stem}`` —     on`) actually correct?**
  _`LanguageConfig` has 162 INFERRED edges - model-reasoned connections that need verification._
- **Are the 85 inferred relationships involving `_read_text()` (e.g. with `_resolve_name()` and `_import_python()`) actually correct?**
  _`_read_text()` has 85 INFERRED edges - model-reasoned connections that need verification._
- **Are the 74 inferred relationships involving `_make_id()` (e.g. with `_file_node_id()` and `_repoint_python_package_imports()`) actually correct?**
  _`_make_id()` has 74 INFERRED edges - model-reasoned connections that need verification._