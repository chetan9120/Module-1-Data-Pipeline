# Zepto Support Assistant (`/support_assistant`)

A small, fully offline-gradable RAG service: 8 Zepto policy documents embedded
locally and stored in ChromaDB, a LangGraph-orchestrated intent router that
retrieves grounded context, a Pydantic-enforced structured output, and a
FastAPI wrapper. All LLM calls are gated behind `MOCK_LLM` (default: mock,
graded baseline — no signup, no API key, no network call to any LLM
provider).

## Project layout

```
support_assistant/
├── docs/doc_01.txt ... doc_08.txt   # the 8-document corpus (verbatim)
├── ingest.py                        # chunking + embedding + ChromaDB storage/retrieval
├── prompts.py                       # structured prompt template (role/context/task/format/length)
├── llm_client.py                    # optional real-LLM client (Groq free tier), only used if MOCK_LLM=0
├── graph.py                         # LangGraph StateGraph: classify_intent, retrieve_and_answer, direct_answer
├── schemas.py                       # Pydantic AskRequest / AskResponse models
├── main.py                          # FastAPI app, POST /ask
├── requirements.txt
├── Dockerfile
└── README.md
```

## Running locally

```bash
cd support_assistant
pip install -r requirements.txt
uvicorn main:app --reload
# MOCK_LLM defaults to 1 (mock/graded baseline) — no env var needed.
```

The first request (or `python ingest.py`) builds the ChromaDB collection by
embedding the 8 corpus documents with `sentence-transformers/all-MiniLM-L6-v2`
into a persistent store at `support_assistant/chroma_db/`.

## Running with Docker (required, graded baseline)

```bash
docker build -t zepto-support-assistant .
docker run -p 7860:7860 zepto-support-assistant
# serves POST http://localhost:7860/ask, MOCK_LLM=1 by default
```

## Optional, ungraded extension: real LLM

```bash
docker run -p 7860:7860 -e MOCK_LLM=0 -e GROQ_API_KEY=your_key zepto-support-assistant
```
Uses Groq's free tier (`console.groq.com`, no credit card required) via
`llm_client.py`. Never hardcode the key — pass it as an env var / Space
secret. This is entirely optional; the graded submission is evaluated with
`MOCK_LLM` left at its default.

## Architecture: the RAG pipeline, stage by stage

**1. Ingestion** — `ingest.load_chunks()` reads the 8 files under `docs/`.
Each file is already a single short, topically atomic policy paragraph, so
chunking is one chunk per document (no further splitting needed) — chunk IDs
are the filenames without extension (`doc_01` … `doc_08`).

**2. Embedding** — `ingest.get_embedder()` loads
`sentence-transformers/all-MiniLM-L6-v2` locally (no API key, one-time model
download only). `ingest.get_or_build_collection()` embeds all 8 chunks and
stores them, together with their raw text and IDs, in a persistent ChromaDB
collection named `zepto_policies` (`chroma_db/` on disk).

**3. Retrieval** — `ingest.query_top_k(query, k=3)` embeds the incoming query
with the same model and asks the `zepto_policies` ChromaDB collection for the
top-3 chunks by cosine similarity. This is called from the `retrieve_and_answer`
node in `graph.py`, and — per the spec — **runs for real in both `MOCK_LLM`
modes**, since it needs no API key and no LLM network call.

**4. Generation** — happens inside two of the three LangGraph nodes in
`graph.py`:
- `retrieve_and_answer` (for `policy_question` queries): in the default mock
  mode it returns a canned `f"Based on the retrieved context: {top_chunk_snippet}"`
  string built from the top retrieved chunk — no LLM call. In the optional
  `MOCK_LLM=0` mode it instead renders `prompts.render_answer_prompt(query,
  context)` (the role–context–task–format–length template with the negative
  constraint and few-shot example) and calls the LLM via `llm_client.call_llm`.
- `direct_answer` (for `general_question` queries, no retrieval): mock mode
  returns a fixed string; the optional real-LLM mode renders
  `prompts.render_direct_prompt(query)` and calls the LLM.

**Routing** — `classify_intent` (mock mode: keyword heuristic over
`delivery / return / refund / membership / tracking / cancel / gift card /
support hours`; optional real-LLM mode: LLM classification) sets `state["intent"]`,
and a LangGraph conditional edge (`route_after_classify`) sends the query to
`retrieve_and_answer` or `direct_answer` accordingly. This routing logic
itself does not depend on `MOCK_LLM` — only the generation step inside each
node does.

**Structured output** — `schemas.AskResponse` (`answer: str`, `sources:
list[str]`, `confidence: float 0-1`) is what `POST /ask` returns. In mock
mode it's populated deterministically in code (`sources` = retrieved chunk
IDs or `[]`, `confidence = 1.0`). In the optional real-LLM mode,
`graph._call_llm_structured()` parses the LLM's JSON output against this
same Pydantic model and retries up to 2 additional times with a corrective
instruction if validation fails, before returning a clearly marked
`[error] ...` response.

```
docs/*.txt --load_chunks()--> chunks --get_embedder()--> embeddings
    --collection.add()--> ChromaDB "zepto_policies"

query --classify_intent--> policy_question ---> retrieve_and_answer
                                                    (query_top_k -> ChromaDB,
                                                     then mock/LLM generation)
                        --> general_question ---> direct_answer
                                                    (mock/LLM generation)
    --> AskResponse (answer, sources, confidence) --> FastAPI POST /ask
```

**What changes between MOCK_LLM states:** ingestion, embedding, and
retrieval are identical in both states (they never call an LLM). Only the
final generation step inside `retrieve_and_answer` / `direct_answer`
(and the `classify_intent` classification) switches from deterministic,
rule-based/canned code (`MOCK_LLM` unset or `1`) to an actual network call to
a free-tier LLM API with schema-validated, retrying structured output
(`MOCK_LLM=0`).

## Example calls (recorded with `MOCK_LLM` at its default)

**Call 1 — routes to `retrieve_and_answer` (contains "delivery"):**

Request:
```json
POST /ask
{"query": "Is standard delivery free on small orders?"}
```

Response:
```json
{
  "answer": "Based on the retrieved context: Zepto delivers grocery and household essentials to serviceable pin codes within 10 to 30 minutes of order confirmation, depending on the customer's delivery zone and current order volume. Standard del",
  "sources": ["doc_01", "doc_05", "doc_02"],
  "confidence": 1.0
}
```
(Top retrieved chunk is `doc_01`, the Delivery Policy document — matches the question asked.)

**Call 2 — routes to `direct_answer` (no policy keyword):**

Request:
```json
POST /ask
{"query": "What is the capital of France?"}
```

Response:
```json
{
  "answer": "I can only answer questions about Zepto policies right now.",
  "sources": [],
  "confidence": 1.0
}
```

Both calls were served locally via `uvicorn main:app` (`MOCK_LLM` left
unset — mock/graded baseline, no LLM API call made for either request), with
the real `all-MiniLM-L6-v2` embeddings and a live ChromaDB collection, and
captured via `Invoke-RestMethod ... | ConvertTo-Json` on Windows/PowerShell.

## Optional extensions attempted

Neither the `MOCK_LLM=0` real-LLM path nor the Hugging Face Spaces deployment
was exercised for this submission — both are implemented in code
(`llm_client.py`, the `MOCK_LLM=0` branches in `graph.py`, and the Dockerfile)
but are ungraded, optional stretches on top of the required mock baseline.
