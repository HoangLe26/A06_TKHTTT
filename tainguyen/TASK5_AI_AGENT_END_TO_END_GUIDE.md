# AI Agent Implementation Guide — Assignment 06, Task 5
## Multimodal Search System for E-Commerce

> Purpose: This file is an end-to-end execution guide for an AI coding agent.  
> Scope: Implement **Task 5 — Python Implementation** so that the code mirrors the three-layer architecture and is ready for Task 6 demonstration.  
> Source of truth: the provided Assignment 06 specification.  
> The agent is authorized to inspect, create, edit, refactor, run, and test project files needed to complete this task.

---

## 1. Mission

Build a working Python prototype for the **Multimodal Search System for E-Commerce**.

The prototype must implement all five Task 5 requirements:

1. **Product repository**
2. **Text search**
3. **Simulated voice search**
4. **Image-similarity search**
5. **Result ranking**

The implementation must preserve the assignment's central flow:

```text
Different Inputs
    ↓
Common Query Representation
    ↓
Retrieval
    ↓
Ranking
    ↓
Results
```

The implementation should also mirror the architecture modeled in Visual Paradigm:

```text
Presentation Layer
        ↓
Application / Intelligence Layer
        ↓
Data Layer
```

A UI/presentation class must not directly read the product database/data file if the same operation belongs in the repository.

---

## 2. Agent Permissions

The AI Agent is explicitly allowed to perform all actions necessary inside the project workspace, including:

- Read all existing project files.
- Inspect current source code and directory structure.
- Create missing directories and files.
- Edit or replace incomplete source files.
- Refactor code when required for architectural consistency.
- Create `__init__.py` files when useful.
- Create or modify JSON data files.
- Add sample image files only when needed for the prototype/demo.
- Install or declare required Python packages when the environment permits.
- Run Python scripts.
- Run tests and debugging commands.
- Fix syntax, import, path, runtime, or logic errors.
- Validate outputs against the assignment requirements.
- Create/update `README.md` if appropriate.
- Preserve user-created files that are unrelated to Task 5.
- Do not delete major existing work unless it is clearly obsolete and a safer replacement is created.

Before modifying an existing implementation, inspect it first and reuse correct work whenever possible.

---

## 3. Requirements Extracted From the Assignment

### 3.1 Required Python implementation

Task 5 requires:

```text
• product repository
• text search
• simulated voice search
• image-similarity search
• result ranking
```

### 3.2 Product repository

The assignment provides `data/product_repository.py` as the repository example and requires the student to add **at least 10 products**.

A product should have enough searchable information for the prototype, such as:

```text
id
name
category
color
price
stock
```

For image search, a product also needs an embedding either:

- stored directly with the product, or
- stored in `VectorIndex`.

### 3.3 Query representation

The assignment expects `QueryService` to convert different modalities into a common query object.

Expected conceptual forms:

```python
{
    "type": "text",
    "query": "black running shoes"
}
```

```python
{
    "type": "voice",
    "query": "find black running shoes"
}
```

```python
{
    "type": "image",
    "embedding": [...]
}
```

### 3.4 Text search

The basic required implementation may use **keyword matching**.

The assignment example builds searchable text from:

```text
product name + category + color
```

Then it:

1. lowercases the query,
2. splits the query into words,
3. counts matching words,
4. keeps products whose score is greater than zero.

Do not unnecessarily replace this with a complex NLP model.

### 3.5 Simulated voice search

Real speech recognition is **not required** for the basic prototype.

The required simulation is:

```text
voice/audio input
    ↓
SpeechService.transcribe(...)
    ↓
already-transcribed text
    ↓
text retrieval
```

Example:

```python
speech_service.transcribe("find black running shoes")
```

may simply return:

```text
find black running shoes
```

The report/demo must clearly state that speech-to-text is simulated.

### 3.6 Image similarity

The basic prototype is allowed to use **artificial feature vectors**.

Image similarity must use **cosine similarity** or an equivalent implementation consistent with the assignment:

```text
similarity(a,b) = dot(a,b) / (||a|| * ||b||)
```

Products with higher similarity scores should rank higher.

Do not require a real CNN/CLIP model unless the existing project already has one and it works reliably.

### 3.7 Ranking

Retrieval and ranking must remain conceptually separate:

```text
Retrieval → candidate products
Ranking   → ordered candidate products
```

`RankingService` should therefore be a distinct component/file and should order candidates by score from highest to lowest.

---

## 4. Recommended Project Structure

The assignment shows the following recommended structure conceptually:

```text
assignment05/
│
├── main.py
│
├── presentation/
│   └── search_ui.py
│
├── application/
│   ├── query_service.py
│   ├── speech_service.py
│   ├── image_service.py
│   ├── search_service.py
│   └── ranking_service.py
│
├── data/
│   ├── product_repository.py
│   ├── order_repository.py
│   └── vector_index.py
│
└── data/
    ├── products.json
    └── images/
```

The handout visually repeats the folder name `data/`. A real filesystem cannot have two separate sibling folders with the same name. For implementation, normalize it to **one `data/` folder**:

```text
assignment06/
│
├── main.py
│
├── presentation/
│   ├── __init__.py
│   └── search_ui.py
│
├── application/
│   ├── __init__.py
│   ├── query_service.py
│   ├── speech_service.py
│   ├── image_service.py
│   ├── search_service.py
│   └── ranking_service.py
│
├── data/
│   ├── __init__.py
│   ├── product_repository.py
│   ├── order_repository.py
│   ├── vector_index.py
│   ├── products.json
│   └── images/
│
├── requirements.txt
└── README.md
```

Notes:

- The PDF labels the directory `assignment05/` even though the document cover says **Assignment 06**. Use the current project/assignment naming convention unless the instructor explicitly requires `assignment05`.
- `order_repository.py` is present in the recommended architecture, but order search is not one of the five mandatory Task 5 implementation bullets. It may be implemented minimally or left ready for later extension.
- `vector_index.py` is useful for keeping image embeddings in the Data Layer and making the Python structure match the UML more closely.

---

## 5. Architecture Mapping

The code should reflect this mapping.

### Presentation Layer

```text
presentation/search_ui.py
```

Responsibilities:

- accept text input,
- accept simulated voice input,
- accept image query/embedding input,
- call Application Layer services,
- display returned results and scores.

It must not directly access JSON/database storage.

### Application / Intelligence Layer

```text
application/query_service.py
application/speech_service.py
application/image_service.py
application/search_service.py
application/ranking_service.py
```

Responsibilities:

- normalize/create query objects,
- simulate speech-to-text,
- compute image similarity,
- retrieve candidates,
- rank results.

### Data Layer

```text
data/product_repository.py
data/vector_index.py
data/products.json
data/images/
```

Responsibilities:

- load/store product information,
- provide product records,
- provide product image embeddings/vector data.

---

## 6. Required Files and Detailed Responsibilities

### 6.1 `data/products.json`

Create at least **10 products**.

Recommended schema:

```json
[
  {
    "id": 1,
    "name": "Nike Running Shoes",
    "category": "shoes",
    "color": "black",
    "price": 120,
    "stock": 10
  }
]
```

Requirements:

- Unique `id`.
- At least 10 records.
- Multiple categories/colors so text retrieval can be demonstrated.
- Include several shoe products so assignment example queries work.
- Include some non-shoe products so ranking differences are visible.

Suggested products:

```text
Nike Running Shoes
Adidas Running Shoes
Black Leather Bag
Blue Sports Shoes
Nike Casual Shoes
Red T-Shirt
Black Hoodie
Brown Backpack
White Sneakers
Sports Cap
```

The agent may improve this list while preserving at least 10 products.

---

### 6.2 `data/product_repository.py`

Implement a `ProductRepository` class.

Minimum interface:

```python
class ProductRepository:
    def __init__(self, ...):
        ...

    def all_products(self):
        ...
```

Preferred behavior:

- Load `products.json`.
- Resolve file paths relative to the Python file/project rather than depending on the terminal's current directory.
- Validate that loaded data is a list.
- Return product data without exposing unnecessary storage details.

Optional useful methods:

```python
find_by_id(product_id)
```

Do not put search/ranking business logic in the repository.

---

### 6.3 `data/vector_index.py`

Implement a small in-memory vector index for image search.

A simple structure is sufficient:

```python
{
    1: [0.9, 0.1, 0.2],
    2: [0.2, 0.8, 0.1],
    ...
}
```

Minimum interface may include:

```python
class VectorIndex:
    def all_embeddings(self):
        ...

    def get_embedding(self, product_id):
        ...
```

Requirements:

- Include an embedding for every product used in image search.
- All vectors must have the same dimension.
- Artificial vectors are valid for the basic prototype.

The agent may alternatively store embeddings with products if necessary, but `VectorIndex` is preferred because it matches the assignment's Data Layer architecture.

---

### 6.4 `application/query_service.py`

Implement:

```python
class QueryService:
    def text_query(self, text):
        ...

    def voice_query(self, text):
        ...

    def image_query(self, embedding):
        ...
```

Expected outputs:

```python
{"type": "text", "query": text}
{"type": "voice", "query": text}
{"type": "image", "embedding": embedding}
```

Validation:

- Text/voice query should reject or safely handle `None`.
- Image embedding should be convertible to a numeric vector.

Keep this component simple.

---

### 6.5 `application/speech_service.py`

Implement simulated voice recognition:

```python
class SpeechService:
    def transcribe(self, audio_input):
        return audio_input
```

A small amount of validation is acceptable, but do not turn this into real speech recognition unless explicitly requested later.

Required meaning:

```text
"audio_input" in this prototype represents already-transcribed speech text.
```

Add an explanatory comment/docstring because the assignment explicitly expects the student to explain the simulation.

---

### 6.6 `application/image_service.py`

Implement image/vector similarity.

Required capability:

```python
cosine_similarity(query_embedding, product_embedding)
```

Use NumPy unless there is a strong reason not to.

Expected behavior:

```python
numerator = np.dot(a, b)
denominator = np.linalg.norm(a) * np.linalg.norm(b)

if denominator == 0:
    return 0.0

return numerator / denominator
```

Also validate vector dimensions and numeric data.

Possible class:

```python
class ImageService:
    def cosine_similarity(self, a, b):
        ...
```

Do not perform ranking inside this service; it should calculate similarity scores.

---

### 6.7 `application/search_service.py`

This is the main retrieval component.

Recommended constructor:

```python
class SearchService:
    def __init__(self, product_repository, vector_index, image_service):
        ...
```

Required capabilities:

```python
search_text(query_text)
search_image(query_embedding)
search(query_object)
```

#### Text retrieval algorithm

Implement approximately:

```text
query = lowercase(query)
words = query.split()

for product:
    searchable_text =
        product["name"] +
        product["category"] +
        product["color"]

    score = number of query words found in searchable_text

    if score > 0:
        add (product, score) to candidates
```

Important:

- `SearchService` retrieves candidates.
- Avoid final sorting here if ranking is delegated to `RankingService`.
- This is a deliberate improvement over blindly copying the example because the assignment requires a separate Ranking Service in the architecture and Task 5 explicitly mentions result ranking.

#### Voice retrieval

Voice queries should reuse text retrieval after transcription/query conversion.

Do **not** duplicate the keyword matching algorithm in `SpeechService`.

#### Image retrieval

For every product embedding in `VectorIndex`:

1. calculate cosine similarity,
2. map `product_id` back to a product,
3. produce candidate tuple/object:

```python
(product, score)
```

Do not sort here if `RankingService` is responsible for final ordering.

---

### 6.8 `application/ranking_service.py`

Implement a separate ranking component.

Minimum interface:

```python
class RankingService:
    def rank(self, candidates):
        return sorted(
            candidates,
            key=lambda item: item[1],
            reverse=True
        )
```

Input candidate structure:

```python
(product, score)
```

Output:

```text
same candidates sorted by descending score
```

Optional:

```python
rank(candidates, top_k=None)
```

Ranking must be visibly separate from retrieval.

---

### 6.9 `presentation/search_ui.py`

This file is part of the assignment's recommended Python structure and should exist.

Implement a lightweight console presentation layer.

Recommended API:

```python
class SearchUI:
    def __init__(
        self,
        query_service,
        speech_service,
        search_service,
        ranking_service
    ):
        ...

    def search_text(self, text):
        ...

    def search_voice(self, voice_text):
        ...

    def search_image(self, embedding):
        ...

    def display_results(self, results):
        ...
```

Required flows:

#### Text

```text
SearchUI
→ QueryService.text_query
→ SearchService.search
→ RankingService.rank
→ SearchUI.display_results
```

#### Voice

```text
SearchUI
→ SpeechService.transcribe
→ QueryService.voice_query
→ SearchService.search
→ RankingService.rank
→ SearchUI.display_results
```

#### Image

```text
SearchUI
→ QueryService.image_query
→ SearchService.search
→ RankingService.rank
→ SearchUI.display_results
```

Output should show at least:

```text
product name
score
```

Prefer also:

```text
category
color
price
stock
```

The presentation layer must not directly open `products.json`.

---

### 6.10 `main.py`

`main.py` should act as the composition root.

It should:

1. Create Data Layer objects.
2. Create Application Layer services.
3. Inject dependencies.
4. Create `SearchUI`.
5. Run example queries.

Recommended dependency setup:

```text
ProductRepository
VectorIndex
ImageService
    ↓
SearchService

QueryService
SpeechService
SearchService
RankingService
    ↓
SearchUI
```

Do not place the entire application logic directly in `main.py`.

---

## 7. Required Demo Scenarios

Although Task 6 is separate, Task 5 should be implemented so these three demonstrations work immediately.

### Demo A — Text Query

Input:

```text
black shoes
```

Required display:

```text
Input
Processing mode: Text
Returned products
Ranking score
```

Expected behavior:

- black shoe products should rank highly,
- partial matches may still appear with lower scores.

### Demo B — Simulated Voice Query

Input:

```text
find running shoes
```

Required processing:

```text
voice text
→ SpeechService.transcribe()
→ QueryService.voice_query()
→ text retrieval
→ ranking
```

Display both:

```text
Voice input
Transcribed text
```

The two strings may be identical because speech recognition is simulated.

### Demo C — Image Query

Use an artificial query embedding such as:

```python
[0.90, 0.10, 0.20]
```

Required processing:

```text
embedding
→ cosine similarity
→ product candidates
→ ranking
```

Display:

```text
product name
similarity score
```

The product whose vector is most similar should appear first.

---

## 8. Recommended Console Output

A clean successful run can look like:

```text
=== E-Commerce Search Demo ===

=== TEXT SEARCH ===
Input: black shoes
1. Nike Running Shoes
   category: shoes
   color: black
   price: 120
   score: 2.0000

2. Blue Sports Shoes
   ...
   score: 1.0000

=== VOICE SEARCH ===
Voice input: find running shoes
Transcribed text: find running shoes

1. Nike Running Shoes
   score: 2.0000

2. Adidas Running Shoes
   score: 2.0000

=== IMAGE SEARCH ===
Query embedding: [0.9, 0.1, 0.2]

1. Nike Running Shoes
   similarity: 0.99...

2. ...
```

Exact rankings depend on the chosen dataset/embeddings.

---

## 9. Dependencies

For the basic version, keep dependencies minimal.

Recommended `requirements.txt`:

```text
numpy
```

Do not introduce TensorFlow, PyTorch, OpenCV, speech-recognition packages, vector databases, or web frameworks unless the user explicitly asks for advanced work.

---

## 10. Robust Path Handling

The project must run from its root with:

```bash
python main.py
```

Avoid code such as:

```python
open("data/products.json")
```

when it may fail from another working directory.

Prefer:

```python
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
```

or equivalent reliable path resolution.

---

## 11. Error Handling

Handle common failures cleanly:

### Product JSON missing

Raise a useful error:

```text
Product data file not found: ...
```

### Invalid JSON

Raise or print a clear message.

### Empty text query

Return no candidates or a controlled validation message.

### Invalid image vector

Handle:

- empty vector,
- non-numeric values,
- dimension mismatch,
- zero vector.

### Missing product embedding

Skip that product safely or provide a useful diagnostic.

Do not silently crash.

---

## 12. Verification Checklist

The agent must verify all items before considering Task 5 complete.

### Structure

- [ ] `main.py` exists.
- [ ] `presentation/search_ui.py` exists.
- [ ] `application/query_service.py` exists.
- [ ] `application/speech_service.py` exists.
- [ ] `application/image_service.py` exists.
- [ ] `application/search_service.py` exists.
- [ ] `application/ranking_service.py` exists.
- [ ] `data/product_repository.py` exists.
- [ ] `data/vector_index.py` exists or equivalent embedding storage is justified.
- [ ] `data/products.json` exists.
- [ ] At least 10 products exist.
- [ ] `data/images/` exists if image samples are part of the project package.

### Architecture

- [ ] Presentation does not directly access product JSON/database.
- [ ] Query creation is in `QueryService`.
- [ ] Voice simulation is in `SpeechService`.
- [ ] Image similarity logic is in `ImageService`.
- [ ] Retrieval is in `SearchService`.
- [ ] Ranking is in `RankingService`.
- [ ] Product data access is in `ProductRepository`.

### Functional behavior

- [ ] Text search works.
- [ ] Voice search works using simulated transcription.
- [ ] Image similarity works.
- [ ] Ranking is descending by score.
- [ ] No-results case works.
- [ ] Zero-vector cosine similarity does not crash.

### Demo readiness

- [ ] One text query produces results.
- [ ] One voice query produces results.
- [ ] One image query produces results.
- [ ] Each demo shows the input.
- [ ] Each demo shows returned products.
- [ ] Each demo shows ranking/similarity scores.

---

## 13. Tests the Agent Must Run

At minimum, execute these checks.

### Test 1 — Imports

```bash
python main.py
```

Expected:

- no import errors,
- no missing package errors,
- no path errors.

### Test 2 — Product count

Verify:

```text
len(repository.all_products()) >= 10
```

### Test 3 — Text search

Query:

```text
black shoes
```

Verify:

- result list is not empty,
- scores are numeric,
- ranked scores are non-increasing.

### Test 4 — Voice simulation

Input:

```text
find running shoes
```

Verify:

```text
transcribed text == input text
```

Then confirm search results exist.

### Test 5 — Image similarity

Use a query vector close to one product's embedding.

Verify:

- similarities are numeric,
- no division-by-zero error,
- most similar product is ranked first.

### Test 6 — Empty text

Input:

```text
""
```

Expected:

- controlled empty result,
- no crash.

### Test 7 — Zero image vector

Input:

```python
[0.0, 0.0, 0.0]
```

Expected:

- similarity returns `0.0`,
- no crash.

---

## 14. Optional Automated Tests

If time permits, create:

```text
tests/
├── test_product_repository.py
├── test_search_service.py
├── test_image_service.py
└── test_ranking_service.py
```

Use `pytest`.

Suggested assertions:

```python
assert len(products) >= 10
assert results
assert scores == sorted(scores, reverse=True)
assert image_service.cosine_similarity(zero, x) == 0.0
```

Do not let test infrastructure become more complicated than the assignment itself.

---

## 15. README Requirements

The final submission requires a README. Create/update `README.md` with:

```text
Project title
Python version
Required packages
Installation
How to run
Project directory structure
Example commands
Example queries
Explanation of simulated voice search
Explanation of artificial image embeddings
Known limitations
```

Recommended run instructions:

```bash
python -m pip install -r requirements.txt
python main.py
```

---

## 16. Limitations to State Clearly

The agent should document the following limitations where applicable:

- Speech-to-text is simulated.
- Image embeddings are artificial vectors.
- Text search is keyword-based, not semantic.
- Dataset is small and local.
- Ranking is simple score sorting.
- No production database is required.
- No authentication or real e-commerce backend is required.
- Real image models/vector databases are optional advanced work.

These are acceptable because the assignment explicitly asks students to start with a simple prototype.

---

## 17. Do Not Over-Engineer

The base assignment does **not** require:

```text
real microphone recording
Whisper
Google Speech API
CNN
CLIP
FAISS
Pinecone
PostgreSQL
Flask
Django
FastAPI
React
web UI
cloud deployment
```

Those belong to optional/advanced extensions unless already present and stable.

Priority order:

```text
Correct architecture
→ Required Task 5 features
→ Reliable execution
→ Clear demo
→ Clean code
→ Optional extensions
```

---

## 18. Implementation Order for the Agent

Follow this exact order unless the existing project makes another order clearly safer.

### Phase 1 — Inspect

1. List project files.
2. Read existing Python code.
3. Identify files already implementing required features.
4. Preserve correct work.
5. Identify missing components.

### Phase 2 — Normalize structure

Create/fix:

```text
presentation/
application/
data/
```

Add `__init__.py` as appropriate.

### Phase 3 — Data Layer

1. Build/fix `products.json`.
2. Ensure at least 10 products.
3. Implement `ProductRepository`.
4. Implement `VectorIndex`.

### Phase 4 — Application Layer

Implement/fix in this order:

```text
QueryService
SpeechService
ImageService
SearchService
RankingService
```

### Phase 5 — Presentation Layer

Implement `SearchUI`.

### Phase 6 — Composition

Implement/fix `main.py`.

### Phase 7 — Execute and debug

Run:

```bash
python main.py
```

Fix all errors until the required three search modes work.

### Phase 8 — Verify acceptance criteria

Run the checklist and tests in this guide.

### Phase 9 — Documentation

Create/update:

```text
README.md
requirements.txt
```

### Phase 10 — Final report to user

The agent should report:

```text
Files created
Files modified
Architecture implemented
Queries tested
Actual outputs
Any remaining limitations
How to run the project
```

Do not merely say "done"; provide evidence of successful execution.

---

## 19. Acceptance Criteria

Task 5 is complete only when all of the following are true:

1. The project runs successfully with Python.
2. There are at least 10 products.
3. Text query retrieval works.
4. Voice search is simulated and reuses text retrieval.
5. Image search calculates cosine similarity.
6. Product candidates receive numeric scores.
7. `RankingService` orders candidates from highest to lowest score.
8. The code follows Presentation → Application → Data.
9. `SearchUI` exists and does not directly access product storage.
10. The code is ready to demonstrate text, voice, and image queries.
11. The output makes ranking scores visible.
12. Basic invalid/empty inputs do not crash the program.
13. README/run instructions are accurate.

---

## 20. Definition of Done

A strong final state should resemble:

```text
assignment06/
│
├── main.py
├── requirements.txt
├── README.md
│
├── presentation/
│   ├── __init__.py
│   └── search_ui.py
│
├── application/
│   ├── __init__.py
│   ├── query_service.py
│   ├── speech_service.py
│   ├── image_service.py
│   ├── search_service.py
│   └── ranking_service.py
│
├── data/
│   ├── __init__.py
│   ├── product_repository.py
│   ├── order_repository.py
│   ├── vector_index.py
│   ├── products.json
│   └── images/
│
└── tests/                  # optional but recommended
    └── ...
```

And running:

```bash
python main.py
```

must visibly demonstrate a functional multimodal search prototype.

---

# Final Instruction to the AI Agent

Work autonomously and complete the implementation end to end.

Do not stop after creating skeleton files.  
Do not leave placeholder methods when a simple working implementation can be provided.  
Do not introduce unnecessary production infrastructure.  
Use the assignment document as the source of truth.  
Keep the implementation consistent with the UML architecture.  
Run the code, inspect the actual output, fix errors, and verify every mandatory Task 5 requirement before finishing.
