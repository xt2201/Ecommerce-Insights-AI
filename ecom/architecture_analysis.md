# Chat Graph Architecture Analysis

This document details the architecture of the [Chat](file:///home/thanhnx/ai_core_server/agents/chat/state/__init__.py#5-14) agent and its sub-graphs, based on the code in the `agents` directory.

## Overview

The architecture is a hierarchical composition of LangGraph graphs. The main entry point is the **Chat Graph**, which routes to specific capabilities like **Universal Search**. Universal Search further delegates to **Search Graph**, which orchestrates **Internal Search** and **Web Search**.

### Hierarchy
- **Chat Graph** (`agents/chat/graph`)
  - **Universal Search Graph** (`agents/universal_search/graph`)
    - **Search Graph** (`agents/search/graph`)
      - **Internal Search Graph** (`agents/internal_search/graph`)
      - **Web Search Graph** (`agents/web_search/graph`)

---

## Architecture Diagram

```mermaid
graph TD
    %% Chat Agent
    subgraph Chat_Agent [Chat Agent]
        direction TB
        C_Start((START)) --> C_ContextAnalysis[Context Analysis]
        C_ContextAnalysis -->|Command=CHAT| C_Chat[Chat Node]
        C_ContextAnalysis -->|Command=SEARCH| C_UniversalSearch[Universal Search Graph]
        C_Chat --> C_End((END))
        C_UniversalSearch --> C_End
    end

    %% Universal Search Agent
    subgraph Universal_Search_Agent [Universal Search Agent]
        direction TB
        US_Start((START)) --> US_Decomposer[Decomposer]
        US_Decomposer --> US_Orchestrator[Orchestrator]
        US_Orchestrator -->|Ready| US_Search[Search Node]
        US_Orchestrator -->|Ready| US_Answer[Answer Node]
        US_Orchestrator -->|Done| US_Synthesize[Synthesize Final Answer]
        US_Search --> US_Updater[Updater]
        US_Answer --> US_Updater
        US_Updater --> US_Orchestrator
        US_Synthesize --> US_End((END))
    end

    %% Search Agent
    subgraph Search_Agent [Search Agent]
        direction TB
        S_Start((START)) -->|Internal| S_InternalSearch[Internal Search Graph]
        S_Start -->|Web| S_WebSearch[Web Search Graph]
        S_InternalSearch --> S_Compose[Compose Final Answer]
        S_WebSearch --> S_Compose
        S_Compose --> S_End((END))
    end

    %% Internal Search Agent
    subgraph Internal_Search_Agent [Internal Search Agent]
        direction TB
        IS_Start((START)) --> IS_EntityAnalysis[Entity Analysis]
        IS_EntityAnalysis --> IS_Planner[Search Planner]
        IS_Planner -->|SQL| IS_SearchSQL[Search SQL]
        IS_Planner -->|Semantic| IS_SQLPrefilter[SQL Prefilter]
        IS_Planner -->|Both| IS_ExecBoth[Execute Both]
        IS_ExecBoth --> IS_SearchSQL
        IS_ExecBoth --> IS_SQLPrefilter
        IS_SQLPrefilter --> IS_SearchSemantic[Search Semantic]
        IS_SearchSQL --> IS_Synthesize[Synthesize Results]
        IS_SearchSemantic --> IS_Synthesize
        IS_Synthesize --> IS_End((END))
    end

    %% Web Search Agent
    subgraph Web_Search_Agent [Web Search Agent]
        direction TB
        WS_Start((START)) --> WS_QueryGen[Query Generator]
        WS_QueryGen --> WS_Search[Web Search Executor]
        WS_Search --> WS_Ranker[Ranker & Filter]
        WS_Ranker --> WS_AnswerGen[Answer Generator]
        WS_AnswerGen --> WS_Validator[Answer Validator]
        WS_Validator -->|Refine| WS_QueryGen
        WS_Validator -->|End| WS_End((END))
    end

    %% Links
    C_UniversalSearch -.-> US_Start
    US_Search -.-> S_Start
    S_InternalSearch -.-> IS_Start
    S_WebSearch -.-> WS_Start

    %% Tools Annotation
    IS_SearchSQL -.- Tool_SQL[Tool: generate_sql]
    IS_SearchSemantic -.- Tool_VTS[Tool: semantic_search]
    WS_Search -.- Tool_Web[Tool: WebSearchTool / FireCrawl]
    
    style Tool_SQL fill:#f9f,stroke:#333,stroke-width:2px
    style Tool_VTS fill:#f9f,stroke:#333,stroke-width:2px
    style Tool_Web fill:#f9f,stroke:#333,stroke-width:2px
```

---

## 1. Chat Graph
**Location**: `agents/chat/graph/__init__.py`
**State**: `ChatState`
**Tools**: None (Pure LLM orchestration)

**Nodes**:
- `context_analysis`: Analyzes user input to determine `relevant_query` and `command`.
- `chat`: Handles general conversation.
- `universal_search_graph`: Sub-graph for "SEARCH" command.

---

## 2. Universal Search Graph
**Location**: `agents/universal_search/graph/__init__.py`
**State**: `UniversalSearchState`
**Tools**: None (Orchestration & LLM)

**Nodes**:
- `decomposer`: Breaks down query into `SubQuery` list.
- `orchestrator`: Manages subquery execution flow.
- `search`: Executes "search" intent subqueries via `Search Graph`.
- `answer`: Executes "answer" intent subqueries using LLM.
- `updater`: Updates state with results.
- `synthesize_final_answer`: Aggregates results.

---

## 3. Search Graph
**Location**: `agents/search/graph/__init__.py`
**State**: `SearchState`
**Tools**: None (Router)

**Nodes**:
- `internal_search_graph`: Routes to Internal Search.
- `web_search_graph`: Routes to Web Search.
- `compose_final_answer`: Formats final result.

---

## 4. Internal Search Graph
**Location**: `agents/internal_search/graph/__init__.py`
**State**: `InternalSearchState`

**Nodes & Tools**:
- `entity_analysis`: Extracts entities.
- `search_planner`: Decides strategy (`sql`, `semantic`, `both`).
- `sql_prefilter`:
  - **Tool**: `generate_sql` (via LLM structured output).
  - **Function**: Generates SQL WHERE clauses to filter semantic search.
- `search_sql`:
  - **Tool**: `generate_sql` (from `tools.sql.tools`).
  - **Function**: Generates and executes SQL queries against the database.
- `search_semantic`:
  - **Tool**: `semantic_search` (from `tools.vts.tools`).
  - **Function**: Performs vector search on the knowledge base.
- `synthesize_search_results`: Combines SQL and Semantic results.

---

## 5. Web Search Graph
**Location**: `agents/web_search/graph/__init__.py`
**State**: `WebSearchState`

**Nodes & Tools**:
- `query_generator`: Generates optimized search queries.
- `web_search`:
  - **Tool**: `WebSearchTool` (wraps FireCrawl service).
  - **Function**: Performs web search and scrapes content.
- `ranker_filter`: Ranks results by relevance and recency; filters duplicates.
- `answer_generator`: Synthesizes answer from web results.
- `answer_validator`: Checks answer quality; triggers refinement if needed.
