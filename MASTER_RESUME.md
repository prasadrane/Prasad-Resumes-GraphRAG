# PRASAD RANE — MASTER RESUME & EXHAUSTIVE SOURCE OF TRUTH

> **Purpose:** This is the definitive master resume and comprehensive reference library containing every verified bullet variant, metric, story, and technical skill across Prasad Rane's professional career.

**Prasad Rane**  
📍 Lake Bluff, IL | 📞 513-967-9423 | ✉️ emailprasadrane@gmail.com | 🌐 [LinkedIn](https://linkedin.com/in/rane-prasad) | 💻 [Portfolio](https://prasadrane.vercel.app)  
**Work Authorization:** H-1B, approved I-140 petition (does not require H-1B lottery for transfer)

---

## 🎯 Executive & Specialized Professional Summaries

### Canonical Summary
Senior Software Engineer with **10+ years of experience** architecting, operating, and modernizing high-throughput distributed systems, cloud-native microservices, and AI-enabled platforms across enterprise and regulated environments. Deep technical mastery in **C# / .NET 8/9**, **ASP.NET Core**, **Angular (12–18)**, **AWS / Azure**, and **Python**. Proven track record in high-concurrency performance tuning (low-level thread profiling, `SemaphoreSlim` concurrency throttles), event-driven architectures (**Apache Kafka / AWS MSK**, **SQS/SNS**), AI/LLM orchestration (**Amazon Bedrock**, **Claude Sonnet**, **Prompt Engineering**), and enterprise observability (**Dynatrace**, **OpenTelemetry**, **Splunk**, **PagerDuty**). Strong cross-functional leader known for introducing organization-wide IaC governance standards, mentoring engineering teams, and turning legacy monoliths into cloud-native microservices.

### Domain-Specific Summary Variants
- **AI / LLM-Forward**: Senior Software Engineer with 10 years of full-stack experience architecting cloud-native systems on AWS, featuring production experience building an **Amazon Bedrock (Claude Sonnet)** AI orchestration chatbot that reduced loan lookup time by 70%. Deep expertise in **C#/.NET Core**, **Angular**, and event-driven architecture (**Kafka/MSK**), with a track record of leading legacy modernization, security remediation, and cross-team technical governance without formal authority.
- **Cloud & Reliability-Forward**: Senior Software Engineer with 10 years of experience designing and scaling distributed systems on **AWS (ECS Fargate, Lambda, DynamoDB)**. Led a full legacy VB.NET-to-cloud-native migration that cut infrastructure costs 40% and achieved 99.95% uptime, alongside deep observability and incident-response work that took a critical integration from 60% to 98% monitoring accuracy.
- **Platform & DevEx-Forward**: Senior Software Engineer with 10 years of experience across backend systems, cloud infrastructure, and developer tooling. Built a one-command local development environment that cut onboarding from two weeks to under a day, and established enterprise-wide Kafka governance standards adopted by five engineering teams through influence rather than mandate.
- **Security & Auth-Forward**: Senior Software Engineer with 10 years of experience, including leading an end-to-end migration from legacy session-based authentication to OAuth2/JWT across seven dependent teams with zero production disruption, resolving all three high-priority findings from a security audit and cutting authentication failures by 60%.

---

## 🛠️ Complete Technical Skills Inventory

- **Backend & APIs**: C#, .NET Core, .NET 6/8/9, ASP.NET Core, Web API, RESTful API design, microservices architecture, LINQ, ADO.NET, data access layer design, dependency injection, CQRS, Python (FastAPI), Java (working knowledge), Node.js (working knowledge)
- **Frontend Development**: Angular (12–18), component-based architecture, TypeScript, HTML5/CSS3, RxJS, NgRx, Jasmine
- **Cloud & Infrastructure (AWS Native)**: AWS ECS Fargate, AWS Lambda, Amazon Bedrock, DynamoDB, S3, SQS, SNS, Amazon MSK (Kafka), AWS IAM, CloudWatch, Terraform (Infrastructure as Code), Docker, Kubernetes (fundamentals)
- **AI / LLM Integration**: Amazon Bedrock (Claude Sonnet), Prompt Engineering, prompt guardrails / injection defense, intent-to-API orchestration, LLM-as-router pattern, natural language synthesis, structured JSON output schemas, RAG-adjacent workflow design, Claude Code, GitHub Copilot, GraphRAG
- **Data & Security**: SQL Server, MySQL, DynamoDB (composite key / single-table design), OAuth2, JWT (Authorization Code + PKCE, Client Credentials flows), token rotation/revocation strategy, RBAC, audit trail design, query execution plan analysis, index strategy, stored procedure optimization, T-SQL
- **Integration & Messaging**: Apache Kafka / AWS MSK, Schema Registry, Avro, event-driven architecture, SQS/SNS, third-party REST API integration, payment gateway integration, Black Knight (MSP) API/SDK
- **CI/CD & Observability**: GitHub Actions, CircleCI, Jenkins, Dynatrace, Splunk, OpenTelemetry, PagerDuty, CloudWatch, synthetic monitoring, Split.io (feature flags)
- **Testing & Performance Debugging**: xUnit, Moq, Jasmine, Playwright, TDD, shadow-mode validation testing, regression testing, `dotnet-counters`, `dotnet-dump`, WinDbg, ILSpy, `SemaphoreSlim` thread profiling
- **Methodologies**: Agile (Scrum/Kanban), TDD, System Design, influence-without-authority technical leadership, cross-functional stakeholder management

---

## 🏆 Certifications

- **AWS Certified Cloud Practitioner** — Amazon Web Services *(Issued: Apr 2026 | Expires: Apr 2029)* | [Credly Verification Badge](https://www.credly.com/badges/337a36b4-0285-460e-b115-2023040ba6b5)

---

## 💼 Exhaustive Experience & Bullet Library

### **Software Engineer / Senior Engineer** — *Rocket Mortgage*
📍 *Lake Bluff, IL* | 🗓️ *Jan 2023 – Jul 2025*

#### Story 1 — Observability & Fannie Mae Integration (Dynatrace)
- **Diagnosed** a root-cause monitoring gap on a Fannie Mae eligibility integration processing 300–400 daily loan applications, tracing false-positive health checks to a misconfigured Dynatrace synthetic monitor hitting an auth endpoint instead of business logic, **improving observability accuracy from 60% to 98%**.
- **Redesigned** the health-check target from `getAuthToken` to `/getVersions`, eliminating false-positive PagerDuty alerts and **reducing on-call alert noise by 80%**.
- **Authored** a 5-point "Observability by Design" checklist and embedded automated enforcement into GitHub Actions CI/CD, preventing the same anti-pattern across 3+ subsequent third-party integrations.
- **Influenced** Fannie Mae's Platform Engineering team during monthly technical syncs to expose a dedicated `/health` endpoint reflecting true business logic status, permanently adopted into their API spec.
- **Redefined** the team's SLI from infrastructure uptime to business transaction availability (SQS drain job success), aligning monitoring with actual customer impact.

#### Story 2 — Self-Service Product Configuration Engine
- **Architected** a self-service Product Configuration UI using **Angular 18, .NET Core 6, and DynamoDB**, reducing configuration change deployment time **from 14 days to 1 day (sub-15 minutes)** and enabling **47 business rule changes** in the first month without engineering involvement.
- **Resolved** a multi-stakeholder design deadlock by rapid-prototyping three distinct UI approaches (grid, wizard, rule builder) and synthesizing them into a hybrid model with ~80% stakeholder consensus.
- **Migrated** a normalized MySQL schema to a single-table **DynamoDB** design using composite primary keys (`productConfigId` + `loanType`), enabling efficient multi-variant queries without table scans.
- **Adopted CQRS** architecture to optimize for a heavily read-oriented access pattern, improving configuration load performance.
- **Built** a shadow-mode validation framework running parallel MySQL/DynamoDB reads for two weeks with zero divergence, enabling a zero-incident legacy database decommission six months post-launch.
- **Implemented** full audit trail and RBAC via DynamoDB Streams + Lambda and a new internal-IdP admin role, passing formal security review with no major findings.
- **Mentored** two associate engineers through PR review and architecture coaching; both became independent owners of the configuration service.

#### Story 3 — Hotlist Deprecation & Legacy Refactor
- **Led** the safe deprecation of a legacy "Hotlist" feature spanning four interconnected services with no documentation or clear ownership, achieving **zero production regressions**.
- **Designed** a phased removal strategy using **Split.io** feature flags, synthetic "Dead Man" traffic alerts, and direct stakeholder interviews (QA, product, underwriters) to confirm the code was truly unused before deletion.
- **Coordinated** with backend teams to trace and remove stale stored-procedure dependencies untouched for years, improving downstream API response times and reducing developer cognitive load.

#### Story 4 — VB.NET Modernization to AWS ECS Fargate
- **Led** the end-to-end modernization of a mission-critical legacy VB.NET underwriter application (50–100 daily users) to a cloud-native **.NET Core / AWS ECS Fargate** architecture within a hard 6-month Active Directory decommission deadline.
- **Reverse-engineered** an undocumented COM interop layer with no source-level documentation using **ILSpy** decompilation, producing a complete integration surface map (MSP/Black Knight API calls, internal DB queries) with zero prior team knowledge.
- **Replaced** fragile COM-wrapped MSP integration with Black Knight's official API/SDK, creating a unit-testable, maintainable boundary.
- **Implemented Infrastructure as Code** using **Terraform** and CI/CD pipelines via **GitHub Actions**, increasing deployment frequency from quarterly to weekly.
- **Executed** a zero-downtime database cutover using bulk migration + CDC dual-write, eliminating data-loss risk during the transition.
- **Reduced infrastructure costs by 40%** by shifting from always-on on-prem servers to Fargate's pay-per-use model with right-sized containers.
- **Achieved 99.95% uptime** and absorbed a 3x increase in user load without degradation; **cut support tickets by 70%** post-launch.

#### Story 5 — Mentoring & Onboarding Leadership
- **Mentored** a summer intern from initial codebase overwhelm to independently presenting complex implementation updates in sprint reviews, through structured, component-by-component onboarding on the Angular/.NET Product Configuration codebase.
- **Onboarded** a new teammate to on-call responsibilities under a compressed handoff window via live PagerDuty/Dynatrace incident walkthroughs, resulting in the teammate independently handling solo on-call rotations immediately after.

#### Story 6 — AI Chatbot on Amazon Bedrock (Claude Sonnet)
- **Built** a production AI-powered loan information chatbot using **Amazon Bedrock (Claude Sonnet)** in **Python**, reducing manual multi-system lookup workflows (3–4 minutes) to sub-2-second natural language responses — a **70% reduction in lookup time**.
- **Designed** a structured LLM-as-router prompt schema where the model classifies intent (`ClientData` / `ProductData` / `WorkoutDecision`) and returns strict JSON for downstream **API orchestration**, prioritizing accuracy and auditability over direct LLM data synthesis.
- **Engineered** multi-intent query handling, decomposing compound natural-language questions into parallel API call sequences with synthesized natural-language responses.
- **Implemented** prompt-injection guardrails to sanitize and constrain user input before reaching Bedrock, defending against adversarial prompt manipulation.
- **Built** a full audit trail logging every prompt/response pair to **S3** for compliance and continuous prompt-tuning analysis.

#### Story 7 — Enterprise Kafka Governance & Standards
- **Established** enterprise-wide **Kafka/AWS MSK** governance standards (topic naming, IAM least-privilege, Avro schema compatibility) adopted by **all 5 major event-driven engineering teams within 3 months** — achieved entirely through influence, with no formal authority over the teams involved.
- **Built** a coalition of 5 cross-team engineers via informal working sessions, iterating the governance document until it read as a shared team standard rather than a top-down mandate.
- **Embedded** `BACKWARD`-compatible schema validation directly into the CI pipeline via **Schema Registry** API calls, shifting breaking-change detection left from production to pull-request time.
- **Automated** governance enforcement into **Terraform** topic-provisioning modules and a CI/CD linter, making compliant behavior the path of least resistance.

#### Story 8 — Concurrency & High-Throughput Performance Tuning
- **Diagnosed and resolved** intermittent 10–15 second stalls in a high-volume transaction service (50,000+ daily transactions) with no error logs, using `dotnet-counters`, `dotnet-dump`, and **WinDbg** thread-dump analysis to identify a third-party library lock bottleneck.
- **Designed** a `SemaphoreSlim`-based throttling layer to isolate the vendor library bottleneck without modifying or replacing the licensed dependency, achieving **99.99% availability** under peak load.
- **Determined** the optimal concurrency limit through iterative load testing, balancing throughput against semaphore wait-time thresholds, and led a team brown-bag session on async/await concurrency pitfalls in .NET.

#### Story 9 — DevEx / One-Command Local Dev Environment
- **Built** a one-command local development environment using **Docker Compose** and a Bash/PowerShell CLI wrapper, **reducing new-developer setup time from 2 weeks to under 1 day** and eliminating setup-related support tickets entirely.
- **Solved** local secrets sprawl by integrating a dev-specific secrets vault directly into the CLI, removing credentials from config files.
- **Implemented** health-check-based service readiness ordering in Docker Compose (beyond simple `depends_on`), eliminating intermittent startup race-condition failures across a 10-service stack.

#### Story 10 — Strategic Mid-Sprint Pivot (Loan Modification Calculator)
- **Identified**, mid-demo, that a real-time linear-input loan modification calculator fundamentally mismatched underwriters' actual non-linear workflow, and **led a mid-sprint architectural pivot** to a batch worksheet model with **zero schedule slip** (delivered on day 42 of a 6-week sprint).
- **Redesigned** the system as a batch aggregation architecture (**.NET Core on AWS Lambda**, unordered frontend worksheet, single-computation backend), using `decimal` types throughout to avoid floating-point rounding risk in financial calculations.
- **Delivered** a feature that **saved underwriters 30 minutes per case**, while mentoring a junior engineer through ownership of the frontend worksheet component.

#### Story 11 — OAuth2/JWT Authentication Migration
- **Owned** the end-to-end migration from vulnerable session-based authentication to **OAuth2/JWT** across 7 dependent teams on a live loan-processing platform, **resolving all 3 high-priority findings** from a security audit with zero disruption to active workflows.
- **Designed** caller-appropriate grant type strategy: Authorization Code Flow + PKCE for browser-based users, Client Credentials for service-to-service calls.
- **Implemented** JWT validation middleware (`Microsoft.AspNetCore.Authentication.JwtBearer`) with full claim validation (`sub`, `aud`, `exp`, `iat`, `iss`, roles), signing-key rotation, and centralized **RBAC** policy enforcement.
- **Built** a dual-auth transition layer accepting legacy sessions and JWTs in parallel, letting each of 7 teams migrate on an independent timeline within a defined cutover window, reducing authentication failures by **60%**.

---

### **Software Developer** — *London Computer Systems*
📍 *Cincinnati, OH* | 🗓️ *Dec 2019 – Jan 2023*

#### Story 12 — SQL Server Database Optimization
- **Diagnosed and resolved** severe performance degradation in nightly rent-roll and occupancy reports (up to 45-second generation times causing HTTP timeouts) by analyzing **SQL Server** query execution plans.
- **Refactored** stored procedures from nested-loop subqueries to set-based joins using temp tables with primary keys, and added targeted non-clustered composite indexes on high-churn columns.
- **Reduced report generation latency from 45 seconds to under 3 seconds** and **cut server CPU utilization ~30%** under peak load, deferring a costly hardware upgrade.

#### Story 13 — Payment Gateway API Integration
- **Designed and implemented** a zero-downtime integration of third-party ACH/credit card payment gateway APIs into an existing **.NET Core** billing engine for a property management platform.
- **Built** defensive integration patterns including exponential-backoff retry policies and fallback handling for transient network failures, achieving **100% graceful handling** of transient gateway failures with no ledger corruption.
- **Reduced manual check processing by 25%** by enabling thousands of tenants to pay rent securely online.

#### Core SaaS Engineering
- Developed and maintained full-stack features for an enterprise property management platform using **.NET Framework/Core**, **SQL Server**, and **Angular/TypeScript**, delivering responsive UI components for thousands of users across regulated real-estate workflows.
- Collaborated across engineering, QA, and infrastructure teams through Agile ceremonies, code reviews, and on-call rotations, authoring incident runbooks that improved production stability.

---

### **Software Developer** — *EXFO Electro-Optical Engineering*
📍 *Pune, India* | 🗓️ *Mar 2015 – Jun 2018*

#### Story 14 — C# Sleep-Mode Memory Leak Resolution
- **Root-caused and resolved** a critical memory leak causing complete application freezes on optical test devices after sleep/resume transitions, using memory profiling and dump analysis alongside QA to establish reliable reproduction.
- **Implemented** OS power-event handling (`Microsoft.Win32.SystemEvents.PowerModeChanged`) with `CancellationTokenSource`-driven graceful abort of REST polling tasks on suspend, **eliminating 100% of resume-state memory leaks** with zero field-reported recurrence.

#### Story 15 — Offline-First REST API Device Sync
- **Designed and implemented** an asynchronous **C#/REST API** integration layer replacing a manual USB/email export workflow for field engineers, **reducing sync time to a single click**.
- **Built** offline-first local caching with automatic background retry on connectivity restoration, achieving **zero report data loss** across hundreds of field tests despite unstable field network conditions.

---

### **Software Developer** — *Tanish Infotech Solutions*
📍 *Pune, India* | 🗓️ *Mar 2014 – Feb 2015*

#### Story 16 — Full-Cycle SMB Application Delivery
- **Delivered** end-to-end custom business management software for SMB clients, from direct requirements gathering through **SQL Server** schema design, full-stack **.NET** development, on-prem/IIS deployment, and client training.
- **Replaced** manual spreadsheet-based billing and inventory processes, **reducing billing error rates to near zero** and saving clients up to 10 hours/week of manual labor.

---

## 🎓 Education

- **M.S. in Information Systems** — *University of Cincinnati, Cincinnati, OH* | **GPA: 3.87** (2019)
- **B.E. in Electronics & Telecommunication** — *University of Pune, Pune, India* (2013)

---

## 📌 Gap-Framing & Skill Triage Cheat Sheet

When tailoring a resume for specific job descriptions, use this cheat sheet to bridge skill requirements accurately:

| JD Requirement | Actual Experience | Strategic Framing Strategy |
| :--- | :--- | :--- |
| **React** | Angular (12–18), component architecture | Frame as transferable component-based frontend architecture. |
| **Azure** | AWS-native (ECS Fargate, Lambda, DynamoDB, Bedrock) | Position as cloud-agnostic distributed systems depth with fast ramp to Azure equivalents. |
| **Kubernetes** | AWS ECS Fargate | Position ECS Fargate as equivalent managed container orchestration experience. |
| **Java** | Working knowledge; C# primary | Frame as working/secondary language knowledge alongside deep C#. |
| **IAM Platforms (Okta/SailPoint)** | AWS IAM, OAuth2/JWT, AD/Entra migration | Bridge via AuthN/AuthZ architecture depth and security compliance. |
| **Entity Framework** | LINQ, ADO.NET, custom DAL design | Reference LINQ, ADO.NET, and custom data access layer design patterns. |
