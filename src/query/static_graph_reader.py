"""
static_graph_reader.py — Fast static Parquet/JSON reader and dynamic resume query engine.
Reads graph entities directly from pre-computed output parquet/json files or full MASTER_RESUME.txt.
"""

import os
import re
import json
from pathlib import Path
from typing import List, Dict, Any

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
OUTPUT_DIR = ROOT_DIR / "output"

def read_precomputed_entities() -> List[Dict[str, Any]]:
    """Read pre-computed entities from output graph artifacts or full MASTER_RESUME.txt."""
    json_path = OUTPUT_DIR / "graph_entities.json"
    if json_path.exists():
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    
    master_resume = ROOT_DIR / "input" / "MASTER_RESUME.txt"
    if master_resume.exists():
        try:
            with open(master_resume, "r", encoding="utf-8") as f:
                text = f.read()
                sections = text.split("\n## ")
                entities = []
                for sec in sections:
                    lines = sec.strip().split("\n")
                    header = lines[0].replace("#", "").strip() if lines else "General"
                    content = "\n".join(lines[1:]).strip() if len(lines) > 1 else sec
                    entities.append({"title": header, "content": content})
                return entities
        except Exception:
            pass
            
    return []

def search_static_graph(query_keywords: List[str]) -> List[str]:
    """Execute fast keyword match over static pre-computed entities in < 1 second."""
    entities = read_precomputed_entities()
    if not entities or not query_keywords:
        return []
        
    matched = []
    lower_kws = [kw.lower() for kw in query_keywords]
    for entity in entities:
        text = str(entity.get("content", "")) + " " + str(entity.get("title", ""))
        if any(kw in text.lower() for kw in lower_kws):
            matched.append(text[:300])
            
    return matched[:10]

def search_static_resume(query: str, mode: str = "local") -> str:
    """
    Perform content-aware query synthesis against Prasad Rane's master resume.
    Differentiates between 'local' (granular entity facts) and 'global' (executive career synthesis) modes.
    """
    q_lower = query.lower().strip()
    is_global = (mode == "global")
    
    # 1. Company / Employer History Query
    if any(k in q_lower for k in ["company", "companies", "worked for", "work for", "employer", "history", "where has"]):
        if is_global:
            return (
                "### **[Global Summary] Prasad Rane's Career Trajectory & Employers**\n\n"
                "- **10+ Year Career Progression**: Prasad's career spans software engineering roles across 4 major tech organizations, evolving from SMB client applications to enterprise mortgage cloud platforms.\n\n"
                "- **Enterprise FinTech (Rocket Mortgage, 2023–2025)**: Led cloud modernization to AWS ECS Fargate, GenAI Amazon Bedrock integration, and cross-team Kafka governance.\n\n"
                "- **SaaS & Property Management (London Computer Systems, 2019–2023)**: Engineered core billing APIs and optimized high-churn SQL Server database architectures.\n\n"
                "- **Optical Hardware & Field Systems (EXFO, 2015–2018)**: Built offline-first C# REST sync layers and resolved low-level OS power event memory leaks.\n\n"
                "- **Full-Stack Development (Tanish Infotech, 2014–2015)**: Delivered end-to-end custom business software and SQL database solutions."
            )
        else:
            return (
                "### **[Local Context] Prasad Rane's Professional Experience & Companies**\n\n"
                "- **Rocket Mortgage** (*Software Engineer / Senior Engineer* | Lake Bluff, IL | Jan 2023 – Jul 2025)\n"
                "  Architected AWS ECS Fargate microservices, Amazon Bedrock (Claude Sonnet) AI chatbots, Kafka/MSK governance standards, and .NET Core / Angular configuration engines.\n\n"
                "- **London Computer Systems** (*Software Developer* | Cincinnati, OH | Dec 2019 – Jan 2023)\n"
                "  Optimized SQL Server query plans reducing report generation latency from 45s to <3s; integrated ACH/credit card payment APIs into .NET Core billing engine.\n\n"
                "- **EXFO Electro-Optical Engineering** (*Software Developer* | Pune, India | Mar 2015 – Jun 2018)\n"
                "  Resolved OS power-event C# memory leaks on test devices and built offline-first REST API sync layers for field engineers.\n\n"
                "- **Tanish Infotech Solutions** (*Software Developer* | Pune, India | Mar 2014 – Feb 2015)\n"
                "  Delivered full-stack .NET and SQL Server custom business management applications for SMB clients."
            )

    # 2. AWS / Cloud / AI Experience Query
    if any(k in q_lower for k in ["aws", "cloud", "lambda", "ecs", "fargate", "bedrock", "dynamodb", "s3", "sqs", "sns", "kafka", "msk", "terraform"]):
        if is_global:
            return (
                "### **[Global Summary] Cloud & AI Architecture Strategy**\n\n"
                "- **Executive Overview**: Prasad's cloud expertise focuses on resilient distributed architectures on AWS, combining containerized microservices (ECS Fargate, Docker, Terraform), event-driven streaming (Apache Kafka/MSK, SQS/SNS), and cutting-edge GenAI (Amazon Bedrock / Claude Sonnet).\n\n"
                "- **Business Impact**: Shifting legacy monoliths to AWS pay-per-use container models delivered a **40% cost reduction** with 99.95% uptime, while GenAI prompt-orchestration reduced workflow latency by **70%**.\n\n"
                "- **Governance & Standards**: Established organization-wide Kafka schema compatibility standards adopted across 5 major engineering teams without formal authority."
            )
        else:
            return (
                "### **[Local Context] Prasad Rane's AWS & Cloud Infrastructure Stack**\n\n"
                "- **AWS Container Orchestration**: Deployed cloud-native microservices on **AWS ECS Fargate** with **Docker** and **Terraform IaC**, cutting infrastructure costs by 40% and achieving 99.95% uptime.\n\n"
                "- **AI / LLM Integration (Amazon Bedrock)**: Built an AI loan information chatbot using **Amazon Bedrock (Claude Sonnet)** in Python, implementing LLM-as-router schemas that reduced manual lookup time by **70%** (sub-2-second responses).\n\n"
                "- **Event-Driven Messaging**: Established enterprise-wide **Apache Kafka / AWS MSK** governance standards adopted by 5 engineering teams; utilized **SQS & SNS** for asynchronous decoupling.\n\n"
                "- **Serverless & NoSQL Data**: Built high-throughput serverless endpoints using **AWS Lambda** and optimized single-table **DynamoDB** designs with composite keys."
            )

    # 3. Python, C#, .NET & Microservices Stack Query
    if any(k in q_lower for k in ["python", "microservices", "c#", ".net", "angular", "fastapi", "stack", "technology", "technologies"]):
        if is_global:
            return (
                "### **[Global Summary] Software Engineering Mastery & Tech Stack**\n\n"
                "- **Core Technology Foundations**: Deep technical depth in **C# / .NET 8/9**, ASP.NET Core, Angular (12–18), Python (FastAPI), and SQL/NoSQL databases.\n\n"
                "- **Architectural Philosophy**: Focuses on clean microservices boundaries, CQRS patterns, high-concurrency performance tuning (`SemaphoreSlim` thread profiling), and developer experience (DevEx) tooling.\n\n"
                "- **Quality & DevEx**: Reduced developer setup time from 2 weeks to under 1 day via single-command Docker Compose local development environments."
            )
        else:
            return (
                "### **[Local Context] Prasad Rane's Core Engineering Stack**\n\n"
                "- **Backend Languages & Frameworks**: C# / .NET 8/9, ASP.NET Core, Python (FastAPI), RESTful API design, CQRS architecture, LINQ, ADO.NET.\n\n"
                "- **Frontend Engineering**: Angular (12–18), TypeScript, component-based UI, RxJS, NgRx, Jasmine.\n\n"
                "- **Microservices & DevEx**: Built Docker Compose single-command local development environments reducing developer setup time from 2 weeks to under 1 day; architected decoupled REST microservices."
            )

    # 4. Technical Achievements / Metrics Query
    if any(k in q_lower for k in ["achievement", "achievements", "metric", "metrics", "impact", "accomplishment"]):
        if is_global:
            return (
                "### **[Global Summary] Executive Technical Achievements**\n\n"
                "- **AI Innovation**: Pioneered Amazon Bedrock (Claude Sonnet) loan lookup engine yielding 70% operational time savings.\n\n"
                "- **Cloud Modernization**: Successfully executed legacy VB.NET to AWS ECS Fargate migration cutting costs 40% with 99.95% availability.\n\n"
                "- **Database & Query Performance**: Delivered 15x query latency improvements (45s to sub-3s) on SQL Server enterprise reporting.\n\n"
                "- **Developer Acceleration**: Built single-command Docker local environments slashing developer onboarding from 2 weeks to <1 day."
            )
        else:
            return (
                "### **[Local Context] Prasad Rane's Key Technical Achievements**\n\n"
                "- **70% Lookup Time Reduction**: Built Amazon Bedrock (Claude Sonnet) AI loan chatbot reducing 3–4 minute manual lookups to sub-2-second natural language answers.\n\n"
                "- **40% Cost Cut & 99.95% Uptime**: Modernized legacy VB.NET underwriter app to AWS ECS Fargate and Terraform IaC within a strict 6-month deadline.\n\n"
                "- **45s to Sub-3s DB Latency**: Refactored SQL Server stored procedures and added targeted non-clustered composite indexes.\n\n"
                "- **2 Weeks to <1 Day Dev Setup**: Engineered single-command Docker Compose local development environment with dev secrets vault integration.\n\n"
                "- **14 Days to Sub-15 Min Deployments**: Architected Angular 18 + .NET Core 6 self-service Product Configuration UI with single-table DynamoDB design."
            )

    # 5. Fallback keyword search over MASTER_RESUME sections
    entities = read_precomputed_entities()
    relevant_bullets = []
    keywords = [w for w in re.findall(r"\w+", q_lower) if len(w) > 3 and w not in ["what", "which", "does", "have", "used", "with", "from"]]
    
    if entities and keywords:
        for ent in entities:
            title = ent.get("title", "")
            content = ent.get("content", "")
            for line in content.split("\n"):
                line_str = line.strip()
                if any(kw in line_str.lower() for kw in keywords) and len(line_str) > 20:
                    clean_line = re.sub(r"^[\s\*\-•]+", "", line_str)
                    relevant_bullets.append(f"- {clean_line}")
                    if len(relevant_bullets) >= 5:
                        break

    if relevant_bullets:
        bullet_text = "\n\n".join(relevant_bullets)
        mode_title = "Global Summary" if is_global else "Local Context"
        return f"### **[{mode_title}] GraphRAG Information for '{query}'**\n\n{bullet_text}"

    # General Fallback
    if is_global:
        return (
            "### **[Global Summary] Prasad Rane's Strategic Overview**\n\n"
            "- **Senior Software Engineer**: 10+ years leading cloud, distributed systems, and AI platforms.\n\n"
            "- **Strategic Focus**: Legacy modernization, cloud cost optimization, event-driven streaming, and AI orchestration.\n\n"
            "- **Proven Track Record**: High-concurrency performance tuning, cross-team IaC governance, and engineering mentorship."
        )
    else:
        return (
            "### **[Local Context] Prasad Rane's Knowledge Summary**\n\n"
            "- **Software Engineering Mastery**: 10+ years architecting cloud-native distributed systems, .NET Core/C#, Angular, Python, and AWS microservices.\n\n"
            "- **Key Employers**: Rocket Mortgage, London Computer Systems, EXFO Electro-Optical Engineering, Tanish Infotech Solutions.\n\n"
            "- **Cloud & AI Focus**: Production experience with AWS ECS Fargate, Amazon Bedrock (Claude Sonnet), Kafka/MSK, DynamoDB, and Terraform IaC."
        )
