Source: https://github.com/Future-House/paper-qa/blob/main/README.md
Retrieved: 2026-11-16
Snapshot: selected line-numbered excerpts; capped; upstream chars=60495

1: # PaperQA2
2: 
3: <!-- pyml disable-num-lines 6 line-length -->
4: 
5: [![GitHub](https://img.shields.io/badge/GitHub-black?logo=github&logoColor=white)](https://github.com/Future-House/paper-qa)
6: [![PyPI version](https://badge.fury.io/py/paper-qa.svg)](https://badge.fury.io/py/paper-qa)
7: [![tests](https://github.com/Future-House/paper-qa/actions/workflows/tests.yml/badge.svg)](https://github.com/Future-House/paper-qa)
8: ![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)
9: ![PyPI Python Versions](https://img.shields.io/pypi/pyversions/paper-qa)
10: 
11: PaperQA2 is a package for doing high-accuracy retrieval augmented generation (RAG) on PDFs, text files, Microsoft Office documents, and source code files,
12: with a focus on the scientific literature.
13: See our [recent 2024 paper](https://paper.wikicrow.ai)
14: to see examples of PaperQA2's superhuman performance in scientific tasks like
15: question answering, summarization, and contradiction detection.
16: 
17: <!--TOC-->
18: 
19: ---
20: 
21: **Table of Contents**
22: 
23: - [Quickstart](#quickstart)
24:   - [Example Output](#example-output)
25: - [What is PaperQA2](#what-is-paperqa2)
26:   - [PaperQA2 vs PaperQA](#paperqa2-vs-paperqa)
27:   - [PaperQA2 Goes CalVer in December 2025](#paperqa2-goes-calver-in-december-2025)
28:   - [What's New in Version 5 (aka PaperQA2)?](#whats-new-in-version-5-aka-paperqa2)
29:   - [What's New in December 2025?](#whats-new-in-december-2025)
30:   - [PaperQA2 Algorithm](#paperqa2-algorithm)
31: - [Installation](#installation)
32: - [CLI Usage](#cli-usage)
33:   - [Bundled Settings](#bundled-settings)
34:   - [Rate Limits](#rate-limits)
35: - [Library Usage](#library-usage)
36:   - [Agentic Adding/Querying Documents](#agentic-addingquerying-documents)
37:   - [Manual (No Agent) Adding/Querying Documents](#manual-no-agent-addingquerying-documents)
38:   - [Async](#async)
39:   - [Choosing Model](#choosing-model)
40:     - [Locally Hosted](#locally-hosted)
41:   - [Embedding Model](#embedding-model)
42:     - [Specifying the Embedding Model](#specifying-the-embedding-model)
43:     - [Local Embedding Models (Sentence Transformers)](#local-embedding-models-sentence-transformers)
44:   - [Adjusting number of sources](#adjusting-number-of-sources)
45:   - [Using Code or HTML](#using-code-or-html)
46:   - [Multimodal Support](#multimodal-support)
47:   - [Using External DB/Vector DB and Caching](#using-external-dbvector-db-and-caching)
48:   - [Creating Index](#creating-index)
49:     - [Manifest Files](#manifest-files)
50:   - [Reusing Index](#reusing-index)
51:   - [Using Clients Directly](#using-clients-directly)
52: - [Settings Cheatsheet](#settings-cheatsheet)
53: - [Where do I get papers?](#where-do-i-get-papers)
54: - [Callbacks](#callbacks)
55:   - [Caching Embeddings](#caching-embeddings)
56: - [Customizing Prompts](#customizing-prompts)
57:   - [Pre and Post Prompts](#pre-and-post-prompts)
58: - [FAQ](#faq)
59:   - [How come I get different results than your papers?](#how-come-i-get-different-results-than-your-papers)
60:   - [How is this different from LlamaIndex or LangChain?](#how-is-this-different-from-llamaindex-or-langchain)
62: - [Reproduction](#reproduction)
63: - [Citation](#citation)
64: 
65: ---
70: 
71: In this example we take a folder of research paper PDFs,
72: magically get their metadata - including citation counts with a retraction check,
73: then parse and cache PDFs into a full-text search index,
74: and finally answer the user question with an LLM agent.
75: 
78: mkdir my_papers
79: curl -o my_papers/PaperQA2.pdf https://arxiv.org/pdf/2409.13740
80: cd my_papers
81: pqa ask 'What is PaperQA2?'
90: > to construct neural network components, such as artificial neurons and associative memories,
91: > using a DNA-based system (Qian2011Neural pages 1-2, Qian2011Neural pages 15-16, Qian2011Neural pages 54-56).
92: > This research includes the implementation of a 3-bit XOR gate and a four-neuron Hopfield associative memory,
93: > showcasing the potential of DNA for neural network computation.
96: > Studies have applied convolutional neural networks (CNNs) to predict genomic features such as
97: > transcription factor binding and DNA accessibility (Eraslan2019Deep pages 4-5, Eraslan2019Deep pages 5-6).
98: > These models leverage DNA sequences as input data,
99: > effectively using neural networks to compute with DNA.
101: > they do highlight the use of neural networks in tasks related to protein sequences,
102: > such as predicting DNA-protein binding (Zeng2016Convolutional pages 1-2).
103: > However, the primary focus remains on DNA-based computation.
104: 
109: 
110: - A simple interface to get good answers with grounded responses containing in-text citations.
111: - State-of-the-art implementation including document metadata-awareness
112:   in embeddings and LLM-based re-ranking and contextual summarization (RCS).
113: - Support for agentic RAG, where a language agent can iteratively refine queries and answers.
114: - Automatic redundant fetching of paper metadata,
115:   including citation and journal quality data from multiple providers.
116: - A usable full-text search engine for a local repository of PDF/text files.
117: - A robust interface for customization, with default support for all [LiteLLM][LiteLLM providers] models.
118: 
125: 
126: PaperQA2 depends on some awesome libraries/APIs that make our repo possible.
127: Here are some in no particular order:
128: 
190: - A bundled set of configurations (read [this section here](#bundled-settings)))
191:   containing known-good hyperparameters
192: 
193: Note that `Docs` objects pickled from prior versions of `PaperQA` are incompatible with version 5,
194: and will need to be rebuilt.
195: Also, our minimum Python version was increased to Python 3.11.
196: 
197: ### What's New in December 2025?
202: - More and better readers
203:   - Two new _model-based_ PDF readers: [Docling](packages/paper-qa-docling)
204:     and [Nvidia nemotron-parse](packages/paper-qa-nemotron)
205:   - All PDF readers now can parse images and tables, report page numbers,
206:     support DPI
207:   - A reader for Microsoft Office data types
218:   and improved prompt templates
219: - Multiple fixes in metadata processing via Semantic Scholar and OpenAlex,
220:   and metadata processing
221:   (e.g. incorrectly inferring identical document IDs for main text and SI)
222: - Completed the deprecations accrued over the past year
247: install PaperQA2 (aka version 5) from [PyPI](https://pypi.org/project/paper-qa/).
248: Note version 5 requires Python 3.11+.
249: 
250: ```bash
257: PaperQA2 uses an LLM to operate,
258: so you'll need to either set an appropriate [API key environment variable][LiteLLM providers]
259: (i.e. `export OPENAI_API_KEY=sk-...`)
260: or set up an open source LLM server (i.e. using [llamafile](https://github.com/Mozilla-Ocho/llamafile).
261: Any LiteLLM compatible model can be configured to use with PaperQA2.
263: If you need to index a large set of papers (100+),
264: you will likely want an API key for both
265: [Crossref](https://www.crossref.org/documentation/metadata-plus/metadata-plus-keys/)
266: and [Semantic Scholar](https://www.semanticscholar.org/product/api#api-key),
267: which will allow you to avoid hitting public rate limits using these metadata services.
268: Those can be exported as `CROSSREF_API_KEY` and `SEMANTIC_SCHOLAR_API_KEY` variables.
269: 
270: ## CLI Usage
277: 
278: You will see PaperQA2 index your local PDF files,
279: gathering the necessary metadata for each of them
280: (using [Crossref](https://www.crossref.org/) and [Semantic Scholar](https://www.semanticscholar.org/)),
281: search over that index, then break the files into chunked evidence contexts,
390: 
391: ```python
392: from paperqa import Settings, ask
393: 
404: 
405: PaperQA2's full workflow can be accessed via Python directly:
406: 
407: ```python
408: from paperqa import Settings, ask
409: 
424: 
425: ```python
426: from paperqa import Settings, ask
427: 
436: 
437: ```python
438: from paperqa import Settings, agent_query
439: 
459: 
460: ```python
461: from paperqa import Docs, Settings
462: 
463: # valid extensions include .pdf, .txt, .md, .html, .docx, .xlsx, .pptx, and code files (e.g., .py, .ts, .yaml)
464: doc_paths = ("myfile.pdf", "myotherfile.pdf")
465: 
466: # Prepare the Docs object by adding a bunch of documents
483: PaperQA2 is written to be used asynchronously.
484: The synchronous API is just a wrapper around the async.
485: Here are the methods and their `async` equivalents:
486: 
495: The synchronous version just calls the async version in a loop.
496: Most modern python environments support `async` natively (including Jupyter notebooks!).
497: So you can do this in a Jupyter Not
[Snapshot excerpt truncated here; not a complete upstream file.]