# Subsystem: `src/converters` (Continent Level)

**Responsibility:** Document parsing, text extraction, structured resume parsing, and normalization into master knowledge graph inputs.

---

## 1. Overview & Responsibility

**[Documented]** `src/converters` handles extracting text from PDF resumes and raw text source files, structuring work experience, skills, and projects into normalized JSON and Markdown artifacts (`input/MASTER_RESUME.txt`).

**[Inferred]** This subsystem forms the top of the data ingestion pipeline, transforming unstructured raw artifacts into consistent representations before GraphRAG embedding and entity resolution.

---

## 2. Key Modules & Classes

| Module / Class | File | Responsibility |
|:---|:---|:---|
| [`PDFParser`](file:///C:/Users/mamat/Github/Prasad-Resumes-GraphRAG/src/converters/pdf_parser.py) | `src/converters/pdf_parser.py` | Extracts text and layout metadata from PDF files using pdfplumber / pypdf. |
| [`StructuredResumeParser`](file:///C:/Users/mamat/Github/Prasad-Resumes-GraphRAG/src/converters/resume_structured_parser.py) | `src/converters/resume_structured_parser.py` | Parses raw resume text into structured Pydantic `ResumeData` representations. |
| `input_converter` | `src/converters/input_converter.py` | Converts input files into GraphRAG-ready chunked text formats. |
| `resume_structurer` | `src/converters/resume_structurer.py` | Structures messy resume text into clean markdown sections. |

---

## 3. Data Flow & Dependencies

```mermaid
flowchart TD
    RawPDF["Raw PDF / Text Resumes"] --> Parser[PDFParser]
    Parser --> Structurer[StructuredResumeParser]
    Structurer --> Master["input/MASTER_RESUME.txt"]
    Master --> GraphRAG["GraphRAG Indexer"]
```
