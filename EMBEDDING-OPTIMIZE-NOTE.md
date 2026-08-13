# Embedding & Graph Quality Optimization Plan

**Document Type:** Technical Implementation Plan  
**Created:** 2026-08-12  
**Status:** Draft - Pending Review  
**Corpus Size:** ~26 text units (MASTER_RESUME.txt + 03-Story-Bank.txt)

---

## Executive Summary

This document outlines a pragmatic optimization plan for improving GraphRAG retrieval quality in the resume generator system. After critical analysis, we identified that the **primary bottlenecks are entity extraction quality and query understanding**, not advanced retrieval techniques.

**Key Insight:** For a tiny corpus (~26 text units), most advanced retrieval methods (cross-encoder reranking, GNN embeddings, hybrid search) are overkill. The real gains come from:
1. Better entity extraction (multi-pass + domain-specific prompts)
2. Entity deduplication/resolution
3. Query routing by intent
4. Structured preprocessing before GraphRAG

**Expected Outcomes:**
- 15-25% more entities extracted (multi-pass)
- Higher quality entities with better prompts
- Cleaner graph with deduplicated entities
- More accurate retrieval for specific query types

**Total Effort Estimate:** 15-25 hours over 2-3 weeks

---

## Current State Analysis

### Architecture Overview

```
Resume Content (MASTER_RESUME.txt + Story Bank)
    ↓
GraphRAG Indexing (settings.yaml)
    ↓
Entities, Relationships, Communities, Text Units
    ↓
LanceDB Vector Store (text_units + communities only)
    ↓
Query Engine (local/global/drift modes)
    ↓
LLM Response Generation
```

### Current Configuration

**Embeddings:**
- Model: `nvidia/nemotron-3-embed-1b:free` (2048 dim)
- Fallbacks: LiteLLM proxy → Gemini text-embedding-004 (768 dim, padded to 2048)
- Only text_units and communities are embedded
- IVF_PQ index disabled (corpus too small)

**Entity Extraction:**
- 10 entity types: Person, Company, Role, Technology, Skill, Competency, Project, Achievement, Story, Metric
- Single-pass extraction: `max_gleanings: 1`
- Generic GraphRAG prompts (no domain-specific examples)

**Retrieval:**
- Local mode: vector search on text_units (top_k=26, retrieves almost everything)
- Global mode: vector search on communities
- Drift mode: local search + 1-hop graph expansion
- Keyword fallback when vector search fails
- No reranking, no hybrid search, no query routing

### Identified Problems

1. **Low entity extraction coverage:** Single pass misses entities requiring multi-sentence context
2. **Entity duplication:** "AWS", "Amazon Web Services", "AWS Cloud" treated as separate entities
3. **No query intent detection:** All queries use same retrieval strategy
4. **Generic extraction prompts:** Not optimized for resume domain
5. **No evaluation framework:** Cannot measure retrieval quality objectively

### What's NOT a Problem

- **Embedding model quality:** Nemotron 2048-dim is adequate for tiny corpus
- **Vector search precision:** With 26 units, most are relevant anyway
- **Retrieval latency:** No need for optimization at this scale
- **Token limits:** Context compression is premature

---

## Prioritized Recommendations

### Priority 1: Multi-Pass Entity Extraction

**Problem:** Single-pass extraction (`max_gleanings: 1`) misses entities that require context from multiple sentences.

**Solution:** Increase to 3 passes for better coverage.

**Implementation Steps:**

1. **Update settings.yaml**
   ```yaml
   # File: settings.yaml (lines 87-99)
   entity_extraction:
     max_gleanings: 3  # Changed from 1
   ```

2. **Test indexing time vs entity count**
   ```bash
   # Measure current state
   time python -m graphrag index --root .
   # Count entities
   python -c "import pandas as pd; print(len(pd.read_parquet('output/create_final_entities.parquet')))"
   ```

3. **Compare before/after**
   - Indexing time: Should be ~3x longer (acceptable for small corpus)
   - Entity count: Should increase 15-25%
   - Check for quality: Are new entities actually useful?

4. **Monitor diminishing returns**
   - Run with `max_gleanings: 5` to see if 4th-5th passes add value
   - Expected: 3 passes is sweet spot, 5+ has minimal gain

**Effort:** 30 minutes (config change + testing)  
**Risk:** 3x indexing time (acceptable)  
**Impact:** High - better graph coverage

**Success Criteria:**
- Entity count increases 15-25%
- New entities are relevant (manual inspection)
- Indexing time remains under 10 minutes

---

### Priority 2: Domain-Specific Extraction Prompts

**Problem:** Generic GraphRAG prompts don't leverage resume domain knowledge.

**Solution:** Create custom prompts with few-shot examples tailored to resume content.

**Implementation Steps:**

1. **Create custom extraction prompt**
   ```python
   # File: src/prompts/entity_extraction.py (new file)
   
   ENTITY_EXTRACTION_PROMPT = """
   Extract entities from this resume content.

   Entity types:
   - PERSON: Names of people (e.g., "Prasad Rane", "John Smith")
   - COMPANY: Company names (e.g., "Microsoft", "Amazon", "Google")
   - TECHNOLOGY: Technical skills, tools, frameworks (e.g., "Python", "AWS", "Kubernetes", "React")
   - PROJECT: Named projects or initiatives (e.g., "Cloud Migration", "API Redesign")
   - METRIC: Quantifiable achievements (e.g., "reduced latency by 40%", "served 1M+ users")
   - ROLE: Job titles (e.g., "Senior Engineer", "Tech Lead", "Engineering Manager")
   - SKILL: Broader skill categories (e.g., "System Design", "Team Leadership", "Agile")
   - COMPETENCY: Demonstrated abilities (e.g., "Cross-functional collaboration", "Mentoring")
   - CERTIFICATION: Professional certifications (e.g., "AWS Solutions Architect", "PMP")

   Examples:

   Text: "Led migration of 50+ microservices to Kubernetes at Amazon, reducing deployment time by 60% and saving $200K annually."
   Entities:
   - ROLE: "Led" (implicit: Tech Lead/Engineering Manager)
   - TECHNOLOGY: "Kubernetes", "microservices"
   - COMPANY: "Amazon"
   - METRIC: "50+ microservices", "reducing deployment time by 60%", "saving $200K annually"
   - PROJECT: "migration of 50+ microservices to Kubernetes"

   Text: "Architected and implemented real-time data pipeline processing 10M+ events/day using Apache Kafka, Spark, and AWS Kinesis."
   Entities:
   - ROLE: "Architected and implemented" (implicit: Data Engineer/Architect)
   - TECHNOLOGY: "Apache Kafka", "Spark", "AWS Kinesis", "data pipeline"
   - METRIC: "10M+ events/day"
   - SKILL: "real-time data processing"

   Now extract from:
   {text}

   Output format: JSON array of entities with type, name, and description.
   """
   ```

2. **Update GraphRAG settings to use custom prompt**
   ```yaml
   # File: settings.yaml
   entity_extraction:
     prompt: src/prompts/entity_extraction.py
   ```

3. **Test extraction quality**
   - Run indexing on sample text
   - Inspect extracted entities
   - Compare with generic prompt results

4. **Iterate on prompt**
   - Add more examples for edge cases
   - Adjust entity types if needed
   - Test with different resume sections

**Effort:** 2-3 hours (prompt crafting + testing)  
**Risk:** Requires iteration to get right  
**Impact:** High - better entity quality without multi-pass overhead

**Success Criteria:**
- Extracted entities are more accurate (manual inspection)
- Fewer false positives (irrelevant entities)
- Better coverage of resume-specific patterns

---

### Priority 3: Entity Resolution and Deduplication

**Problem:** GraphRAG extracts "AWS", "Amazon Web Services", "AWS Cloud" as separate entities.

**Solution:** Post-processing step to merge similar entities.

**Implementation Steps:**

1. **Create entity resolution module**
   ```python
   # File: src/postprocessing/entity_resolver.py (new file)
   
   import pandas as pd
   from difflib import SequenceMatcher
   from sentence_transformers import SentenceTransformer, util
   import logging

   logger = logging.getLogger(__name__)

   class EntityResolver:
       def __init__(self, similarity_threshold=0.85):
           self.similarity_threshold = similarity_threshold
           self.model = SentenceTransformer('all-MiniLM-L6-v2')
       
       def similar(self, a: str, b: str) -> float:
           """Calculate string similarity using SequenceMatcher."""
           return SequenceMatcher(None, a.lower(), b.lower()).ratio()
       
       def embedding_similarity(self, a: str, b: str) -> float:
           """Calculate semantic similarity using embeddings."""
           embeddings = self.model.encode([a, b])
           return util.cos_sim(embeddings[0], embeddings[1]).item()
       
       def resolve_entities(self, entities_df: pd.DataFrame) -> pd.DataFrame:
           """
           Merge similar entities.
           
           Args:
               entities_df: DataFrame with columns [id, name, type, description]
           
           Returns:
               DataFrame with merged entities
           """
           resolved = {}
           aliases = {}
           
           for idx, row in entities_df.iterrows():
               entity_name = row['name']
               entity_type = row['type']
               
               # Check if similar entity exists
               merged = False
               for existing_name in list(resolved.keys()):
                   # Only compare entities of same type
                   if resolved[existing_name]['type'] != entity_type:
                       continue
                   
                   # Check string similarity
                   string_sim = self.similar(entity_name, existing_name)
                   
                   # Check semantic similarity for TECHNOLOGY entities
                   if entity_type == 'TECHNOLOGY':
                       semantic_sim = self.embedding_similarity(entity_name, existing_name)
                       combined_sim = 0.5 * string_sim + 0.5 * semantic_sim
                   else:
                       combined_sim = string_sim
                   
                   if combined_sim > self.similarity_threshold:
                       # Merge: keep the shorter/more common name
                       if len(entity_name) < len(existing_name):
                           # Replace existing with shorter name
                           aliases[existing_name] = entity_name
                           resolved[entity_name] = resolved.pop(existing_name)
                           resolved[entity_name]['aliases'].append(existing_name)
                       else:
                           # Keep existing, add current as alias
                           aliases[entity_name] = existing_name
                           resolved[existing_name]['aliases'].append(entity_name)
                       
                       # Merge descriptions
                       resolved[existing_name if existing_name in resolved else entity_name]['descriptions'].append(row['description'])
                       merged = True
                       break
               
               if not merged:
                   resolved[entity_name] = {
                       'type': entity_type,
                       'aliases': [],
                       'descriptions': [row['description']]
                   }
           
           # Build resolved DataFrame
           resolved_rows = []
           for name, data in resolved.items():
               resolved_rows.append({
                   'id': name.lower().replace(' ', '_'),
                   'name': name,
                   'type': data['type'],
                   'description': ' '.join(data['descriptions']),
                   'aliases': data['aliases']
               })
           
           resolved_df = pd.DataFrame(resolved_rows)
           
           logger.info(f"Resolved {len(entities_df)} entities to {len(resolved_df)} unique entities")
           logger.info(f"Merged {len(aliases)} aliases")
           
           return resolved_df
       
       def update_relationships(self, relationships_df: pd.DataFrame, alias_map: dict) -> pd.DataFrame:
           """Update relationship source/target to use canonical entity names."""
           updated = relationships_df.copy()
           updated['source'] = updated['source'].map(lambda x: alias_map.get(x, x))
           updated['target'] = updated['target'].map(lambda x: alias_map.get(x, x))
           return updated
   ```

2. **Integrate into indexing pipeline**
   ```python
   # File: scripts/postprocess_graph.py (new file)
   
   import pandas as pd
   import logging
   from src.postprocessing.entity_resolver import EntityResolver

   logging.basicConfig(level=logging.INFO)
   logger = logging.getLogger(__name__)

   def main():
       logger.info("Loading entities and relationships...")
       entities_df = pd.read_parquet('output/create_final_entities.parquet')
       relationships_df = pd.read_parquet('output/create_final_relationships.parquet')
       
       logger.info(f"Loaded {len(entities_df)} entities, {len(relationships_df)} relationships")
       
       # Resolve entities
       resolver = EntityResolver(similarity_threshold=0.85)
       resolved_df = resolver.resolve_entities(entities_df)
       
       # Build alias map
       alias_map = {}
       for idx, row in resolved_df.iterrows():
           for alias in row['aliases']:
               alias_map[alias] = row['name']
       
       # Update relationships
       updated_relationships = resolver.update_relationships(relationships_df, alias_map)
       
       # Save resolved entities
       resolved_df.to_parquet('output/create_final_entities_resolved.parquet', index=False)
       updated_relationships.to_parquet('output/create_final_relationships_resolved.parquet', index=False)
       
       logger.info(f"Saved resolved entities to output/create_final_entities_resolved.parquet")
       logger.info(f"Merged {len(alias_map)} aliases")

   if __name__ == '__main__':
       main()
   ```

3. **Test entity resolution**
   ```bash
   # Run entity resolution
   python scripts/postprocess_graph.py
   
   # Compare before/after
   python -c "import pandas as pd; print('Before:', len(pd.read_parquet('output/create_final_entities.parquet')))"
   python -c "import pandas as pd; print('After:', len(pd.read_parquet('output/create_final_entities_resolved.parquet')))"
   ```

4. **Tune similarity threshold**
   - Start with 0.85 (conservative)
   - Inspect merged entities manually
   - Adjust threshold if over-merging or under-merging

**Effort:** 3-4 hours (implementation + testing)  
**Risk:** Over-merging (losing distinct entities) or under-merging (missing duplicates)  
**Impact:** Medium - cleaner graph, better retrieval

**Success Criteria:**
- 10-20% reduction in entity count (after merging duplicates)
- Merged entities are actually duplicates (manual inspection)
- No loss of distinct entities (e.g., "AWS Lambda" vs "AWS EC2" should not merge)

---

### Priority 4: Query Routing by Intent

**Problem:** All queries use same retrieval strategy (local/global/drift). Different query types need different strategies.

**Solution:** Detect query intent and route to appropriate retrieval method.

**Implementation Steps:**

1. **Create query classifier**
   ```python
   # File: src/query/intent_classifier.py (new file)
   
   import re
   from enum import Enum
   from typing import List, Dict

   class QueryIntent(Enum):
       SKILL_LOOKUP = "skill_lookup"
       COMPANY_LOOKUP = "company_lookup"
       EXPERIENCE_LOOKUP = "experience_lookup"
       GENERAL_QUERY = "general_query"

   class IntentClassifier:
       def __init__(self):
           # Keyword patterns for each intent
           self.skill_patterns = [
               r'\b(python|java|aws|kubernetes|docker|react|node\.?js|sql|ml|machine learning)\b',
               r'\b(skills?|technologies|tools|frameworks|languages|experience with)\b',
               r'\b(what.*(?:know|used|experience)|familiar with)\b',
           ]
           
           self.company_patterns = [
               r'\b(worked at|at|company|employer|microsoft|amazon|google|meta|apple)\b',
               r'\b(employed|job|position|role at)\b',
           ]
           
           self.experience_patterns = [
               r'\b(tell me about|describe|explain|project|initiative|led|built|developed)\b',
               r'\b(what did you do|your experience|background)\b',
           ]
       
       def classify(self, query: str) -> QueryIntent:
           """Classify query intent based on keyword patterns."""
           query_lower = query.lower()
           
           # Check skill patterns
           for pattern in self.skill_patterns:
               if re.search(pattern, query_lower):
                   return QueryIntent.SKILL_LOOKUP
           
           # Check company patterns
           for pattern in self.company_patterns:
               if re.search(pattern, query_lower):
                   return QueryIntent.COMPANY_LOOKUP
           
           # Check experience patterns
           for pattern in self.experience_patterns:
               if re.search(pattern, query_lower):
                   return QueryIntent.EXPERIENCE_LOOKUP
           
           # Default to general query
           return QueryIntent.GENERAL_QUERY
       
       def get_retrieval_strategy(self, intent: QueryIntent) -> Dict:
           """Get retrieval parameters for given intent."""
           strategies = {
               QueryIntent.SKILL_LOOKUP: {
                   'mode': 'local',
                   'entity_filter': 'TECHNOLOGY|SKILL',
                   'top_k': 15,
                   'use_keyword_search': True,
               },
               QueryIntent.COMPANY_LOOKUP: {
                   'mode': 'local',
                   'entity_filter': 'COMPANY',
                   'top_k': 15,
                   'use_keyword_search': True,
               },
               QueryIntent.EXPERIENCE_LOOKUP: {
                   'mode': 'drift',
                   'expansion_hops': 2,
                   'top_k': 20,
               },
               QueryIntent.GENERAL_QUERY: {
                   'mode': 'global',
                   'top_k': 10,
               },
           }
           return strategies[intent]
   ```

2. **Integrate into query engine**
   ```python
   # File: src/query/graphrag_engine.py (modify existing)
   
   from src.query.intent_classifier import IntentClassifier

   class GraphRAGEngine:
       def __init__(self, ...):
           # ... existing init ...
           self.intent_classifier = IntentClassifier()
       
       async def query(self, query_text: str, mode: str = None, ...):
           """Query with intent-based routing."""
           
           # Classify intent if mode not explicitly set
           if mode is None:
               intent = self.intent_classifier.classify(query_text)
               strategy = self.intent_classifier.get_retrieval_strategy(intent)
               mode = strategy['mode']
               # Use strategy parameters
               top_k = strategy.get('top_k', 10)
               # ... apply other strategy params ...
           
           # Execute query based on mode
           if mode == 'local':
               return await self.local_search(query_text, ...)
           elif mode == 'global':
               return await self.global_search(query_text, ...)
           elif mode == 'drift':
               return await self.drift_search(query_text, ...)
   ```

3. **Test query routing**
   ```python
   # Test cases
   test_queries = [
       ("What Python experience does Prasad have?", QueryIntent.SKILL_LOOKUP),
       ("Did Prasad work at Amazon?", QueryIntent.COMPANY_LOOKUP),
       ("Tell me about the cloud migration project", QueryIntent.EXPERIENCE_LOOKUP),
       ("Summarize Prasad's background", QueryIntent.GENERAL_QUERY),
   ]
   
   classifier = IntentClassifier()
   for query, expected_intent in test_queries:
       actual_intent = classifier.classify(query)
       assert actual_intent == expected_intent, f"Failed for: {query}"
   ```

4. **Add entity filtering for skill/company queries**
   ```python
   # In local_search method
   async def local_search(self, query: str, entity_filter: str = None, ...):
       # ... existing vector search ...
       
       # Filter entities by type if specified
       if entity_filter:
           entities = [e for e in entities if re.match(entity_filter, e['type'])]
       
       return results
   ```

**Effort:** 3-4 hours (implementation + testing)  
**Risk:** Misclassification of queries  
**Impact:** Medium - better retrieval for specific query types

**Success Criteria:**
- 80%+ accuracy on query classification (manual testing)
- Better retrieval for skill/company queries (user testing)
- No degradation for general queries

---

### Priority 5: Structured Resume Parsing

**Problem:** Resume content has predictable structure (experience, education, skills sections) but GraphRAG treats it as unstructured text.

**Solution:** Parse resume into structured format before GraphRAG indexing.

**Implementation Steps:**

1. **Create resume parser**
   ```python
   # File: src/converters/resume_structured_parser.py (new file)
   
   import re
   from typing import Dict, List
   from dataclasses import dataclass

   @dataclass
   class Job:
       title: str
       company: str
       start_date: str
       end_date: str
       description: str
       technologies: List[str]
       achievements: List[str]

   @dataclass
   class Education:
       degree: str
       institution: str
       year: str
       gpa: str = None

   @dataclass
   class StructuredResume:
       summary: str
       experience: List[Job]
       education: List[Education]
       skills: Dict[str, List[str]]  # category -> list of skills
       certifications: List[str]
       projects: List[str]

   class StructuredResumeParser:
       def parse(self, resume_text: str) -> StructuredResume:
           """Parse resume into structured format."""
           
           # Extract sections
           summary = self._extract_summary(resume_text)
           experience = self._extract_experience(resume_text)
           education = self._extract_education(resume_text)
           skills = self._extract_skills(resume_text)
           certifications = self._extract_certifications(resume_text)
           
           return StructuredResume(
               summary=summary,
               experience=experience,
               education=education,
               skills=skills,
               certifications=certifications,
               projects=[]  # TODO: implement
           )
       
       def _extract_summary(self, text: str) -> str:
           """Extract executive summary section."""
           # Look for summary/profile section
           match = re.search(r'(?:summary|profile|about).*?\n(.*?)(?=\n\s*\n|\n[A-Z])', text, re.IGNORECASE | re.DOTALL)
           return match.group(1).strip() if match else ""
       
       def _extract_experience(self, text: str) -> List[Job]:
           """Extract work experience section."""
           jobs = []
           
           # Pattern: Job Title at Company (Date - Date)
           pattern = r'([A-Za-z\s]+?)\s+at\s+([A-Za-z\s]+?)\s*\((\w+ \d{4})\s*-\s*(\w+ \d{4}|Present)\)(.*?)(?=\n[A-Z]|\Z)'
           
           for match in re.finditer(pattern, text, re.IGNORECASE | re.DOTALL):
               title = match.group(1).strip()
               company = match.group(2).strip()
               start_date = match.group(3).strip()
               end_date = match.group(4).strip()
               description = match.group(5).strip()
               
               # Extract technologies from description
               technologies = self._extract_technologies(description)
               
               # Extract achievements (bullet points)
               achievements = [line.strip('- ').strip() for line in description.split('\n') if line.strip().startswith('-')]
               
               jobs.append(Job(
                   title=title,
                   company=company,
                   start_date=start_date,
                   end_date=end_date,
                   description=description,
                   technologies=technologies,
                   achievements=achievements
               ))
           
           return jobs
       
       def _extract_technologies(self, text: str) -> List[str]:
           """Extract technology names from text."""
           # Common tech keywords
           tech_pattern = r'\b(Python|Java|JavaScript|TypeScript|AWS|Azure|GCP|Kubernetes|Docker|React|Node\.?js|SQL|PostgreSQL|MongoDB|Redis|Kafka|Spark|TensorFlow|PyTorch)\b'
           
           return list(set(re.findall(tech_pattern, text, re.IGNORECASE)))
       
       def _extract_skills(self, text: str) -> Dict[str, List[str]]:
           """Extract skills section, categorized."""
           skills = {}
           
           # Look for skills section
           match = re.search(r'skills.*?\n(.*?)(?=\n\s*\n|\n[A-Z]|\Z)', text, re.IGNORECASE | re.DOTALL)
           if match:
               skills_text = match.group(1).strip()
               
               # Parse categories (e.g., "Programming: Python, Java, C++")
               for line in skills_text.split('\n'):
                   if ':' in line:
                       category, items = line.split(':', 1)
                       skills[category.strip()] = [item.strip() for item in items.split(',')]
           
           return skills
       
       def _extract_education(self, text: str) -> List[Education]:
           """Extract education section."""
           education = []
           
           # Pattern: Degree at Institution (Year)
           pattern = r'([A-Za-z\s]+?)\s+at\s+([A-Za-z\s]+?)\s*\((\d{4})\)'
           
           for match in re.finditer(pattern, text, re.IGNORECASE):
               degree = match.group(1).strip()
               institution = match.group(2).strip()
               year = match.group(3).strip()
               
               education.append(Education(
                   degree=degree,
                   institution=institution,
                   year=year
               ))
           
           return education
       
       def _extract_certifications(self, text: str) -> List[str]:
           """Extract certifications section."""
           # Look for certifications section
           match = re.search(r'certifications?.*?\n(.*?)(?=\n\s*\n|\n[A-Z]|\Z)', text, re.IGNORECASE | re.DOTALL)
           if match:
               cert_text = match.group(1).strip()
               return [line.strip('- ').strip() for line in cert_text.split('\n') if line.strip()]
           return []
   ```

2. **Convert structured resume to GraphRAG format**
   ```python
   # File: scripts/convert_structured_resume.py (new file)
   
   import json
   from pathlib import Path
   from src.converters.resume_structured_parser import StructuredResumeParser

   def main():
       # Parse resume
       parser = StructuredResumeParser()
       resume_text = Path('input/MASTER_RESUME.txt').read_text()
       structured = parser.parse(resume_text)
       
       # Convert to GraphRAG input format
       output_lines = []
       
       # Add summary
       if structured.summary:
           output_lines.append("# Executive Summary\n")
           output_lines.append(structured.summary)
           output_lines.append("\n")
       
       # Add experience with metadata
       output_lines.append("# Work Experience\n")
       for job in structured.experience:
           output_lines.append(f"## {job.title} at {job.company} ({job.start_date} - {job.end_date})\n")
           output_lines.append(f"**Company:** {job.company}\n")
           output_lines.append(f"**Role:** {job.title}\n")
           output_lines.append(f"**Technologies:** {', '.join(job.technologies)}\n")
           output_lines.append("\n")
           output_lines.append(job.description)
           output_lines.append("\n")
       
       # Add skills
       output_lines.append("# Skills\n")
       for category, skills in structured.skills.items():
           output_lines.append(f"## {category}\n")
           output_lines.append(', '.join(skills))
           output_lines.append("\n")
       
       # Add education
       output_lines.append("# Education\n")
       for edu in structured.education:
           output_lines.append(f"- {edu.degree} at {edu.institution} ({edu.year})\n")
       
       # Add certifications
       if structured.certifications:
           output_lines.append("# Certifications\n")
           for cert in structured.certifications:
               output_lines.append(f"- {cert}\n")
       
       # Write output
       output_path = Path('input/MASTER_RESUME_structured.txt')
       output_path.write_text('\n'.join(output_lines))
       print(f"Structured resume written to {output_path}")

   if __name__ == '__main__':
       main()
   ```

3. **Test structured parsing**
   ```bash
   # Run parser
   python scripts/convert_structured_resume.py
   
   # Inspect output
   cat input/MASTER_RESUME_structured.txt
   ```

4. **Re-index with structured input**
   ```bash
   # Backup original
   mv input/MASTER_RESUME.txt input/MASTER_RESUME_original.txt
   mv input/MASTER_RESUME_structured.txt input/MASTER_RESUME.txt
   
   # Re-index
   python -m graphrag index --root .
   ```

**Effort:** 6-8 hours (parser implementation + testing + re-indexing)  
**Risk:** Regex-based parsing may miss edge cases  
**Impact:** High - metadata-aware retrieval, better entity extraction

**Success Criteria:**
- Structured resume captures all key information
- GraphRAG extracts better entities with structured input
- Retrieval quality improves for specific queries

---

### Priority 6: Simple Evaluation Framework

**Problem:** No systematic way to measure retrieval quality.

**Solution:** Build a simple evaluation dataset with 20-30 real queries.

**Implementation Steps:**

1. **Create evaluation dataset**
   ```python
   # File: evaluation/query_dataset.json (new file)
   [
     {
       "query": "What AWS services has Prasad used?",
       "expected_entities": ["AWS", "EC2", "S3", "Lambda", "RDS", "CloudFormation"],
       "expected_keywords": ["AWS", "EC2", "S3", "Lambda"],
       "category": "skill_lookup"
     },
     {
       "query": "Tell me about Prasad's experience at Amazon",
       "expected_entities": ["Amazon"],
       "expected_keywords": ["Amazon", "engineer", "led", "built"],
       "category": "company_lookup"
     },
     {
       "query": "What Python projects has Prasad worked on?",
       "expected_entities": ["Python"],
       "expected_keywords": ["Python", "project", "developed", "built"],
       "category": "skill_lookup"
     },
     {
       "query": "Describe Prasad's cloud migration experience",
       "expected_entities": ["Kubernetes", "Docker", "AWS"],
       "expected_keywords": ["migration", "cloud", "kubernetes", "docker"],
       "category": "experience_lookup"
     }
   ]
   ```

2. **Create evaluation script**
   ```python
   # File: evaluation/evaluate_retrieval.py (new file)
   
   import json
   import asyncio
   from pathlib import Path
   from src.query.graphrag_engine import GraphRAGEngine
   from typing import Dict, List

   async def evaluate_query(engine: GraphRAGEngine, query_item: Dict) -> Dict:
       """Evaluate a single query."""
       query = query_item['query']
       expected_entities = set(query_item['expected_entities'])
       expected_keywords = set(query_item['expected_keywords'])
       
       # Run query
       result = await engine.query(query)
       
       # Extract retrieved entities and keywords
       retrieved_text = ' '.join([unit['text'] for unit in result.get('text_units', [])])
       retrieved_entities = set([e['name'] for e in result.get('entities', [])])
       
       # Calculate metrics
       entity_precision = len(retrieved_entities & expected_entities) / len(retrieved_entities) if retrieved_entities else 0
       entity_recall = len(retrieved_entities & expected_entities) / len(expected_entities) if expected_entities else 0
       
       keyword_precision = len(set(retrieved_text.split()) & expected_keywords) / len(set(retrieved_text.split())) if retrieved_text else 0
       keyword_recall = len(set(retrieved_text.split()) & expected_keywords) / len(expected_keywords) if expected_keywords else 0
       
       return {
           'query': query,
           'entity_precision': entity_precision,
           'entity_recall': entity_recall,
           'keyword_precision': keyword_precision,
           'keyword_recall': keyword_recall,
       }

   async def main():
       # Load evaluation dataset
       dataset_path = Path('evaluation/query_dataset.json')
       dataset = json.loads(dataset_path.read_text())
       
       # Initialize engine
       engine = GraphRAGEngine()
       
       # Evaluate each query
       results = []
       for query_item in dataset:
           result = await evaluate_query(engine, query_item)
           results.append(result)
           print(f"Query: {query_item['query']}")
           print(f"  Entity F1: {2 * result['entity_precision'] * result['entity_recall'] / (result['entity_precision'] + result['entity_recall']) if result['entity_precision'] + result['entity_recall'] > 0 else 0:.2f}")
           print(f"  Keyword F1: {2 * result['keyword_precision'] * result['keyword_recall'] / (result['keyword_precision'] + result['keyword_recall']) if result['keyword_precision'] + result['keyword_recall'] > 0 else 0:.2f}")
       
       # Calculate average metrics
       avg_entity_precision = sum(r['entity_precision'] for r in results) / len(results)
       avg_entity_recall = sum(r['entity_recall'] for r in results) / len(results)
       avg_keyword_precision = sum(r['keyword_precision'] for r in results) / len(results)
       avg_keyword_recall = sum(r['keyword_recall'] for r in results) / len(results)
       
       print("\n=== Average Metrics ===")
       print(f"Entity Precision: {avg_entity_precision:.2f}")
       print(f"Entity Recall: {avg_entity_recall:.2f}")
       print(f"Entity F1: {2 * avg_entity_precision * avg_entity_recall / (avg_entity_precision + avg_entity_recall):.2f}")
       print(f"Keyword Precision: {avg_keyword_precision:.2f}")
       print(f"Keyword Recall: {avg_keyword_recall:.2f}")
       print(f"Keyword F1: {2 * avg_keyword_precision * avg_keyword_recall / (avg_keyword_precision + avg_keyword_recall):.2f}")

   if __name__ == '__main__':
       asyncio.run(main())
   ```

3. **Run baseline evaluation**
   ```bash
   # Before optimizations
   python evaluation/evaluate_retrieval.py > evaluation/baseline_results.txt
   ```

4. **Re-run after each optimization**
   ```bash
   # After multi-pass extraction
   python evaluation/evaluate_retrieval.py > evaluation/after_multipass.txt
   
   # After entity resolution
   python evaluation/evaluate_retrieval.py > evaluation/after_resolution.txt
   
   # Compare results
   diff evaluation/baseline_results.txt evaluation/after_multipass.txt
   ```

**Effort:** 2-3 hours (dataset creation + evaluation script)  
**Risk:** Dataset may not cover all query types  
**Impact:** High - data-driven optimization

**Success Criteria:**
- Evaluation dataset covers major query types
- Metrics show improvement after each optimization
- Can identify which optimizations have real impact

---

## Implementation Timeline

### Week 1: Quick Wins
- **Day 1-2:** Multi-pass entity extraction (Priority 1)
- **Day 3-5:** Domain-specific extraction prompts (Priority 2)

### Week 2: Graph Quality
- **Day 1-3:** Entity resolution and deduplication (Priority 3)
- **Day 4-5:** Simple evaluation framework (Priority 6)

### Week 3: Advanced Features
- **Day 1-3:** Query routing by intent (Priority 4)
- **Day 4-5:** Structured resume parsing (Priority 5)

**Total:** 15-25 hours over 3 weeks

---

## Testing Strategy

### Unit Tests
- Entity resolution: Test merging logic with known duplicates
- Intent classifier: Test classification accuracy on labeled queries
- Resume parser: Test extraction on sample resume sections

### Integration Tests
- End-to-end query: Run full pipeline on test queries
- Retrieval quality: Compare before/after metrics
- Indexing time: Monitor performance impact

### Manual Testing
- Inspect extracted entities for quality
- Test real queries from stakeholders
- Review merged entities for correctness

---

## Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Multi-pass extraction increases indexing time 3x | Medium | Acceptable for small corpus; monitor indexing time |
| Entity resolution over-merges distinct entities | High | Start with conservative threshold (0.85); manual inspection |
| Query classifier misclassifies queries | Medium | Allow manual mode override; test with real queries |
| Structured parser misses edge cases | Medium | Fallback to unstructured parsing; regex refinement |
| Evaluation dataset doesn't cover all query types | Low | Expand dataset based on real user queries |

---

## Success Metrics

### Quantitative
- Entity count increases 15-25% (multi-pass)
- Entity count decreases 10-20% after resolution (deduplication)
- Retrieval F1 score improves 10-20% (evaluation framework)
- Query classification accuracy > 80% (intent classifier)

### Qualitative
- Extracted entities are more accurate (manual inspection)
- Graph is cleaner (fewer duplicates)
- Retrieval feels more accurate for specific queries (user feedback)
- System handles skill/company/experience queries differently (observable behavior)

---

## Future Work (Out of Scope)

These were considered but rejected for current corpus size:

1. **Cross-encoder reranking** - Revisit when corpus grows to 100+ text units
2. **Hybrid search (BM25 + vector)** - Current keyword fallback is sufficient
3. **Advanced embedding models** - Nemotron is adequate for tiny corpus
4. **GNN embeddings** - Massive overkill for current scale
5. **Context compression** - Not hitting token limits yet
6. **HyDE query transformation** - Risky, adds latency

---

## Conclusion

This plan focuses on **high-impact, low-effort optimizations** that address the real bottlenecks: entity extraction quality and query understanding. By avoiding over-engineering for a tiny corpus, we can achieve meaningful improvements with minimal complexity.

**Key Principles:**
- Start simple, measure impact, iterate
- Focus on extraction quality, not retrieval complexity
- Avoid advanced techniques until corpus grows
- Data-driven decisions via evaluation framework

**Next Steps:**
1. Review and approve this plan
2. Set up evaluation framework (Priority 6) to establish baseline
3. Implement multi-pass extraction (Priority 1) - quick win
4. Test and measure impact before proceeding to other priorities
