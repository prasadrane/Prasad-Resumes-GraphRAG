"""
SME Tech Ontology & Skill Hierarchy.

Provides domain taxonomy, synonym normalization, parent/child skill expansion,
and technology relatedness evaluation for ATS keyword matching and resume generation.
"""

from typing import Dict, List, Set, Optional, Union


class SMEOntology:
    """Subject Matter Expert (SME) Technology Ontology and Skill Hierarchy."""

    # Synonym and alias normalization mapping (lowercase source -> canonical lowercase target)
    SYNONYM_MAP: Dict[str, str] = {
        # Cloud & Containers
        "k8s": "kubernetes",
        "k8s / kubernetes": "kubernetes",
        "kube": "kubernetes",
        "aws cloud": "aws",
        "amazon web services": "aws",
        "gcp": "google cloud",
        "google cloud platform": "google cloud",
        "azure cloud": "azure",
        "microsoft azure": "azure",
        "tf": "terraform",
        "iac": "infrastructure as code",
        "serverless architecture": "serverless",
        "aws lambda": "lambda",
        "aws ecs": "ecs",
        "aws fargate": "fargate",
        # AI / ML / Data
        "py-torch": "pytorch",
        "torch": "pytorch",
        "tf-keras": "keras",
        "tensorflow.js": "tensorflow",
        "llm": "llms",
        "large language models": "llms",
        "large language model": "llms",
        "nlp": "nlp",
        "natural language processing": "nlp",
        "rag": "rag",
        "retrieval augmented generation": "rag",
        "retrieval-augmented generation": "rag",
        "graph-rag": "graphrag",
        "graph rag": "graphrag",
        "msft graphrag": "graphrag",
        "microsoft graphrag": "graphrag",
        "lang-chain": "langchain",
        "lance-db": "lancedb",
        "vector db": "vector databases",
        "vector dbs": "vector databases",
        "vector database": "vector databases",
        "vectordb": "vector databases",
        "neo 4j": "neo4j",
        "neo-4j": "neo4j",
        "ml": "machine learning",
        "dl": "deep learning",
        "genai": "generative ai",
        "gen-ai": "generative ai",
        # Backend & Architecture
        "rest": "restful apis",
        "rest api": "restful apis",
        "rest apis": "restful apis",
        "restful api": "restful apis",
        "restful web services": "restful apis",
        "eda": "event-driven architecture",
        "event driven architecture": "event-driven architecture",
        "event streaming": "event streaming",
        "message streaming": "event streaming",
        "msg streaming": "event streaming",
        "fast-api": "fastapi",
        "node": "node.js",
        "nodejs": "node.js",
        "node js": "node.js",
        "node.js": "node.js",
        "react": "react",
        "react.js": "react",
        "reactjs": "react",
        "golang": "go",
        "go lang": "go",
        "spring-boot": "spring boot",
        "springboot": "spring boot",
        "asp.net core": "asp.net",
        "dotnet": "asp.net",
        ".net": "asp.net",
        ".net core": "asp.net",
        # Databases & Caching
        "postgres": "postgresql",
        "pgsql": "postgresql",
        "mongo": "mongodb",
        "dynamo": "dynamodb",
        "elastic search": "elasticsearch",
        # DevOps & Observability
        "ci cd": "ci/cd",
        "cicd": "ci/cd",
        "ci / cd": "ci/cd",
        "gh actions": "github actions",
        "gh-actions": "github actions",
        "oauth 2.0": "oauth2",
        "oauth 2": "oauth2",
        "oauth": "oauth2",
        "json web token": "jwt",
        "json web tokens": "jwt",
    }

    # Taxonomy: Skill -> Parent Domain Categories
    SKILL_TAXONOMY: Dict[str, List[str]] = {
        # Cloud & Infrastructure
        "aws": ["Cloud & Infrastructure", "Cloud Computing", "AWS Cloud"],
        "azure": ["Cloud & Infrastructure", "Cloud Computing", "Azure Cloud"],
        "google cloud": ["Cloud & Infrastructure", "Cloud Computing", "GCP Cloud"],
        "docker": ["Containers", "Cloud & Infrastructure", "DevOps"],
        "kubernetes": ["Container Orchestration", "Cloud & Infrastructure", "DevOps", "Containers"],
        "terraform": ["Infrastructure as Code", "Cloud & Infrastructure", "DevOps"],
        "serverless": ["Cloud & Infrastructure", "Serverless Compute", "Cloud Architecture"],
        "ecs": ["Container Orchestration", "AWS Cloud", "Containers", "Cloud & Infrastructure"],
        "fargate": ["Container Orchestration", "Serverless Compute", "AWS Cloud", "Containers"],
        "lambda": ["Serverless Compute", "AWS Cloud", "Cloud & Infrastructure", "Event-Driven Architecture"],
        # AI / ML / Data
        "pytorch": ["Deep Learning Frameworks", "Machine Learning", "AI/ML"],
        "tensorflow": ["Deep Learning Frameworks", "Machine Learning", "AI/ML"],
        "keras": ["Deep Learning Frameworks", "Machine Learning", "AI/ML"],
        "deep learning": ["Machine Learning", "AI/ML", "Artificial Intelligence"],
        "machine learning": ["AI/ML", "Data Science", "Artificial Intelligence"],
        "llms": ["AI/ML", "Natural Language Processing", "Generative AI"],
        "nlp": ["AI/ML", "Natural Language Processing", "Machine Learning"],
        "graphrag": ["AI/ML", "RAG", "Knowledge Graphs", "Generative AI", "Information Retrieval"],
        "langchain": ["AI/ML", "LLM Frameworks", "Generative AI", "RAG"],
        "rag": ["AI/ML", "Information Retrieval", "Generative AI", "Search"],
        "lancedb": ["Databases & Caching", "Vector Databases", "AI/ML", "Vector Search"],
        "neo4j": ["Databases & Caching", "Graph Databases", "Knowledge Graphs"],
        "vector databases": ["Databases & Caching", "AI/ML", "Vector Search", "Information Retrieval"],
        # Backend & Architecture
        "microservices": ["Backend & Architecture", "Distributed Systems", "Cloud Architecture"],
        "event-driven architecture": ["Backend & Architecture", "Distributed Systems", "Message Streaming"],
        "restful apis": ["Backend & Architecture", "RESTful APIs", "API Design", "Web Services"],
        "graphql": ["Backend & Architecture", "API Design", "Query Languages"],
        "fastapi": ["RESTful APIs", "Backend Frameworks", "Microservices"],
        "flask": ["RESTful APIs", "Backend Frameworks", "Microservices"],
        "django": ["RESTful APIs", "Backend Frameworks", "Web Frameworks"],
        "node.js": ["Backend Frameworks", "JavaScript Runtime", "Microservices"],
        "spring boot": ["RESTful APIs", "Backend Frameworks", "Microservices"],
        "asp.net": ["RESTful APIs", "Backend Frameworks", "Microservices"],
        "go": ["Programming Languages", "Systems Programming"],
        "python": ["Programming Languages"],
        "react": ["Frontend Development", "UI Frameworks", "Web Development"],
        # Messaging & Streaming
        "kafka": ["Event-Driven Architecture", "Message Streaming", "Distributed Systems", "Data Ingestion"],
        "rabbitmq": ["Event-Driven Architecture", "Message Streaming", "Distributed Systems"],
        "kinesis": ["Event-Driven Architecture", "Message Streaming", "AWS Cloud", "Distributed Systems"],
        "event streaming": ["Event-Driven Architecture", "Message Streaming", "Distributed Systems"],
        # Databases & Caching
        "postgresql": ["Databases & Caching", "Relational Databases", "SQL Databases"],
        "mysql": ["Databases & Caching", "Relational Databases", "SQL Databases"],
        "dynamodb": ["Databases & Caching", "NoSQL Databases", "AWS Cloud", "Document Databases"],
        "mongodb": ["Databases & Caching", "NoSQL Databases", "Document Databases"],
        "redis": ["Databases & Caching", "In-Memory Caching", "NoSQL Databases", "Key-Value Stores"],
        "cassandra": ["Databases & Caching", "NoSQL Databases", "Distributed Databases", "Columnar Databases"],
        # DevOps & Observability
        "ci/cd": ["DevOps & CI/CD", "Continuous Integration", "Software Delivery"],
        "github actions": ["DevOps & CI/CD", "CI/CD", "Automation"],
        "jenkins": ["DevOps & CI/CD", "CI/CD", "Automation"],
        "oauth2": ["Security & Identity", "Authentication & Authorization"],
        "jwt": ["Security & Identity", "Authentication & Authorization"],
        "splunk": ["Observability & Monitoring", "Log Analysis", "DevOps"],
        "dynatrace": ["Observability & Monitoring", "APM & Tracing", "DevOps"],
        "datadog": ["Observability & Monitoring", "APM & Tracing", "DevOps"],
    }

    # Explicit Category-to-Children / Domain expansion map
    CATEGORY_CHILDREN_MAP: Dict[str, List[str]] = {
        "deep learning": ["pytorch", "tensorflow", "keras", "deep learning"],
        "deep learning frameworks": ["pytorch", "tensorflow", "keras"],
        "machine learning": ["pytorch", "tensorflow", "keras", "deep learning", "machine learning", "nlp", "llms"],
        "ai/ml": ["pytorch", "tensorflow", "keras", "deep learning", "machine learning", "llms", "nlp", "graphrag", "langchain", "rag", "lancedb", "vector databases"],
        "llms": ["langchain", "graphrag", "rag", "llms"],
        "generative ai": ["llms", "graphrag", "langchain", "rag"],
        "natural language processing": ["nlp", "llms", "graphrag"],
        "rag": ["graphrag", "langchain", "rag", "lancedb", "vector databases"],
        "vector databases": ["lancedb", "vector databases"],
        "vector search": ["lancedb", "vector databases"],
        "knowledge graphs": ["graphrag", "neo4j"],
        "event-driven architecture": ["kafka", "rabbitmq", "kinesis", "lambda", "event streaming"],
        "message streaming": ["kafka", "rabbitmq", "kinesis", "event streaming"],
        "event streaming": ["kafka", "rabbitmq", "kinesis", "event-driven architecture"],
        "container orchestration": ["kubernetes", "fargate", "ecs", "docker"],
        "containers": ["docker", "kubernetes", "ecs", "fargate"],
        "serverless compute": ["fargate", "lambda", "serverless"],
        "aws cloud": ["aws", "ecs", "fargate", "lambda", "dynamodb", "kinesis"],
        "cloud & infrastructure": ["aws", "azure", "google cloud", "docker", "kubernetes", "terraform", "serverless", "ecs", "fargate", "lambda"],
        "restful apis": ["fastapi", "flask", "django", "spring boot", "asp.net", "restful apis"],
        "backend frameworks": ["fastapi", "flask", "django", "spring boot", "asp.net", "node.js"],
        "microservices": ["fastapi", "flask", "spring boot", "asp.net", "microservices", "docker", "kubernetes"],
        "relational databases": ["postgresql", "mysql"],
        "nosql databases": ["dynamodb", "mongodb", "redis", "cassandra"],
        "databases & caching": ["postgresql", "mysql", "dynamodb", "mongodb", "redis", "cassandra", "lancedb", "neo4j"],
        "in-memory caching": ["redis"],
        "devops": ["docker", "kubernetes", "terraform", "ci/cd", "github actions", "jenkins"],
        "ci/cd": ["github actions", "jenkins", "ci/cd"],
        "security & identity": ["oauth2", "jwt"],
        "observability & monitoring": ["splunk", "dynatrace", "datadog"],
    }

    def normalize_term(self, term: Optional[str]) -> str:
        """
        Normalize technology term by stripping whitespace, converting to lowercase,
        and mapping known aliases/synonyms to canonical terms.
        """
        if term is None:
            return ""
        
        cleaned = term.strip().lower()
        if not cleaned:
            return ""
        
        # Check direct match in synonym map
        if cleaned in self.SYNONYM_MAP:
            return self.SYNONYM_MAP[cleaned]
        
        # Check punctuation-simplified match (e.g. py-torch -> pytorch)
        no_hyphens = cleaned.replace("-", "")
        if no_hyphens in self.SYNONYM_MAP:
            return self.SYNONYM_MAP[no_hyphens]
            
        no_dots = cleaned.replace(".", "")
        if no_dots in self.SYNONYM_MAP:
            return self.SYNONYM_MAP[no_dots]
            
        # Check taxonomy direct canonical entries
        if cleaned in self.SKILL_TAXONOMY:
            return cleaned
            
        return cleaned

    def get_parent_categories(self, term: Optional[str]) -> List[str]:
        """
        Return parent domain categories for a given technology term.
        Returns empty list if the term is unknown or empty.
        """
        norm_term = self.normalize_term(term)
        if not norm_term:
            return []

        # Direct taxonomy lookup
        if norm_term in self.SKILL_TAXONOMY:
            return list(self.SKILL_TAXONOMY[norm_term])

        # Check if term is a known category itself
        categories = []
        for cat_name in self.CATEGORY_CHILDREN_MAP:
            if norm_term == cat_name or norm_term in cat_name:
                categories.append(cat_name.title())

        return categories

    def get_child_skills(self, term_or_category: Optional[str]) -> List[str]:
        """
        Return child skills associated with a high-level category or skill.
        """
        norm = self.normalize_term(term_or_category)
        if not norm:
            return []

        results: Set[str] = set()

        # Check direct category children map
        if norm in self.CATEGORY_CHILDREN_MAP:
            for child in self.CATEGORY_CHILDREN_MAP[norm]:
                results.add(child)

        # Inverted search over SKILL_TAXONOMY
        for skill, parents in self.SKILL_TAXONOMY.items():
            for parent in parents:
                if norm == parent.lower() or norm in parent.lower():
                    results.add(skill)

        # If it's a known skill in taxonomy, include itself
        if norm in self.SKILL_TAXONOMY:
            results.add(norm)

        return sorted(list(results))

    def expand_query_terms(self, terms: Union[List[str], Set[str]]) -> List[str]:
        """
        Expand a list of query terms into related child skills, synonyms, and parent concepts.
        Preserves ordering with deduplication.
        """
        if not terms:
            return []

        expanded: List[str] = []
        seen: Set[str] = set()

        def add_item(item: str):
            clean = item.strip().lower()
            if clean and clean not in seen:
                seen.add(clean)
                expanded.append(clean)

        for raw_term in terms:
            if not raw_term or not raw_term.strip():
                continue
            
            raw_clean = raw_term.strip().lower()
            norm = self.normalize_term(raw_term)

            # Add original and normalized term
            add_item(raw_clean)
            if norm:
                add_item(norm)

            # Expand child skills if term is a high-level domain / category
            child_skills = self.get_child_skills(raw_clean)
            for child in child_skills:
                add_item(child)

            if norm and norm != raw_clean:
                for child in self.get_child_skills(norm):
                    add_item(child)

        return expanded

    def semantic_distance(self, term_a: Optional[str], term_b: Optional[str], max_hops: int = 3) -> float:
        """
        Calculate semantic graph distance between two technology terms.
        0.0 = identical/synonyms
        1.0 = direct parent-child
        2.0 = siblings in same domain or 2-hop hierarchy
        inf = unrelated / unreachable within max_hops
        """
        norm_a = self.normalize_term(term_a)
        norm_b = self.normalize_term(term_b)

        if not norm_a or not norm_b:
            return float("inf")

        if norm_a == norm_b:
            return 0.0

        # Direct parent-child (1 hop)
        children_a = set(self.get_child_skills(norm_a))
        if norm_b in children_a:
            return 1.0

        children_b = set(self.get_child_skills(norm_b))
        if norm_a in children_b:
            return 1.0

        # Check shared parent categories (2 hops via common parent)
        parents_a = {p.lower() for p in self.get_parent_categories(norm_a)}
        parents_b = {p.lower() for p in self.get_parent_categories(norm_b)}
        generic_categories = {"programming languages", "data science", "systems programming"}
        shared_parents = (parents_a - generic_categories).intersection(parents_b - generic_categories)
        if shared_parents:
            return 2.0

        # Multi-hop transitive expansion
        if max_hops >= 3:
            for child in children_a:
                child_parents = {p.lower() for p in self.get_parent_categories(child)} - generic_categories
                if child_parents.intersection(parents_b - generic_categories):
                    return 3.0

        return float("inf")

    def are_related(self, term_a: Optional[str], term_b: Optional[str], max_hops: int = 2) -> bool:
        """
        Evaluate whether two technology terms are related through exact match,
        parent-child hierarchy, or shared domain categories within max_hops.
        """
        dist = self.semantic_distance(term_a, term_b, max_hops=max_hops)
        return dist <= float(max_hops)

    # Class-level / Static convenience wrappers
    @classmethod
    def normalize(cls, term: Optional[str]) -> str:
        return cls().normalize_term(term)

    @classmethod
    def get_categories(cls, term: Optional[str]) -> List[str]:
        return cls().get_parent_categories(term)

    @classmethod
    def get_children(cls, term: Optional[str]) -> List[str]:
        return cls().get_child_skills(term)

    @classmethod
    def expand(cls, terms: Union[List[str], Set[str]]) -> List[str]:
        return cls().expand_query_terms(terms)

    @classmethod
    def related(cls, term_a: Optional[str], term_b: Optional[str], max_hops: int = 2) -> bool:
        return cls().are_related(term_a, term_b, max_hops=max_hops)

    @classmethod
    def distance(cls, term_a: Optional[str], term_b: Optional[str], max_hops: int = 3) -> float:
        return cls().semantic_distance(term_a, term_b, max_hops=max_hops)
