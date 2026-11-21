Source: https://github.com/lfnovo/open-notebook/blob/main/README.md
Retrieved: 2026-11-16
Snapshot: selected line-numbered excerpts; capped; upstream chars=21035

1: <a id="readme-top"></a>
2: 
3: <!-- [![Contributors][contributors-shield]][contributors-url] -->
4: [![Forks][forks-shield]][forks-url]
5: [![Stargazers][stars-shield]][stars-url]
6: [![Issues][issues-shield]][issues-url]
7: [![MIT License][license-shield]][license-url]
8: <!-- [![LinkedIn][linkedin-shield]][linkedin-url] -->
9: 
10: 
11: <!-- PROJECT LOGO -->
12: <br />
13: <div align="center">
14:   <a href="https://github.com/lfnovo/open-notebook">
15:     <img src="docs/assets/hero.svg" alt="Logo">
16:   </a>
17: 
18:   <h3 align="center">Open Notebook</h3>
19: 
20:   <p align="center">
21:     An open source, privacy-focused alternative to Google's Notebook LM!
22:     <br /><strong>Join our <a href="https://discord.gg/37XJPXfz2w">Discord server</a> for help, to share workflow ideas, and suggest features!</strong>
23:     <br />
24:     <a href="https://www.open-notebook.ai"><strong>Checkout our website »</strong></a>
25:     <br />
26:     Follow <a href="https://x.com/lfnovo">@lfnovo on X</a> for updates
27:     <br />
28:     <br />
29:     <a href="docs/0-START-HERE/index.md">📚 Get Started</a>
30:     ·
31:     <a href="docs/3-USER-GUIDE/index.md">📖 User Guide</a>
32:     ·
33:     <a href="docs/2-CORE-CONCEPTS/index.md">✨ Features</a>
34:     ·
35:     <a href="docs/1-INSTALLATION/index.md">🚀 Deploy</a>
36:   </p>
37: </div>
38: 
39: <p align="center">
40: <a href="https://trendshift.io/repositories/14536" target="_blank"><img src="https://trendshift.io/api/badge/repositories/14536" alt="lfnovo%2Fopen-notebook | Trendshift" style="width: 250px; height: 55px;" width="250" height="55"/></a>
41: </p>
42: 
43: <div align="center">
44:   <!-- Keep these links. Translations come from zdoc.app, which follows the current README automatically. Arabic and Turkish are hand-maintained under docs/i18n/ only because zdoc.app does not serve them; new languages are not added by hand (#1550). -->
45:   <a href="docs/i18n/ar/README.md" dir="rtl">العربية</a> |
46:   <a href="https://zdoc.app/de/lfnovo/open-notebook">Deutsch</a> | 
47:   <a href="https://zdoc.app/es/lfnovo/open-notebook">Español</a> | 
48:   <a href="https://zdoc.app/fr/lfnovo/open-notebook">français</a> | 
49:   <a href="https://zdoc.app/ja/lfnovo/open-notebook">日本語</a> | 
50:   <a href="https://zdoc.app/ko/lfnovo/open-notebook">한국어</a> | 
51:   <a href="https://zdoc.app/pt/lfnovo/open-notebook">Português</a> | 
52:   <a href="https://zdoc.app/ru/lfnovo/open-notebook">Русский</a> | 
53:   <a href="docs/i18n/tr/README.md">Türkçe</a> |
54:   <a href="https://zdoc.app/zh/lfnovo/open-notebook">中文</a>
55: </div>
56: 
57: ## A private, multi-model, 100% local, full-featured alternative to Notebook LM
58: 
59: ![New Notebook](docs/assets/asset_list.png)
60: 
65: - 🤖 **Choose your AI models** - 20+ providers including OpenAI, Anthropic, Google, Mistral, Ollama and any OpenAI-compatible server (LM Studio, vLLM)
66: - 📚 **Organize multi-modal content** - PDFs, videos, audio, web pages, and more
67: - 🎙️ **Generate professional podcasts** - Advanced multi-speaker podcast generation
68: - 🔍 **Search intelligently** - Full-text and vector search across all your content
83: | **Content Transformations** | Custom and built-in | Limited options | Unlimited processing power |
84: | **API Access** | Full REST API | No API | Complete automation |
85: | **Deployment** | Docker, cloud, or local | Google hosted only | Deploy anywhere |
86: | **Citations** | Answers cite the sources, notes and insights they used | Comprehensive with sources | Research integrity |
87: | **Customization** | Open source, fully customizable | Closed system | Unlimited extensibility |
88: | **Cost** | Pay only for AI usage | Free tier + Monthly subscription | Transparent and controllable |
98: 
99: [![Python][Python]][Python-url] [![Next.js][Next.js]][Next-url] [![React][React]][React-url] [![SurrealDB][SurrealDB]][SurrealDB-url] [![LangChain][LangChain]][LangChain-url]
100: 
101: ## 🚀 Quick Start
104: - [Docker Desktop](https://www.docker.com/products/docker-desktop/) (macOS, Windows) or Docker Engine with the Compose plugin (Linux)
105: - An API key from an AI provider, or a local model server such as Ollama. You add it in the UI, not in config files.
106: 
107: ### Step 1: Download docker-compose.yml
112: 
113: This is the official [docker-compose.yml](docker-compose.yml) from this repository. It runs two services: `surrealdb` (the database) and `open_notebook` (UI, API and background worker).
114: 
115: ### Step 2: Set your encryption key
116: Create a `.env` file next to `docker-compose.yml` and set `OPEN_NOTEBOOK_ENCRYPTION_KEY` to a long random secret you generate yourself (for example with `openssl rand -hex 32`; [other options](docs/1-INSTALLATION/docker-compose.md#step-2-set-your-encryption-key)). The shipped compose file reads it from `.env`. Editing that line in `docker-compose.yml` is a valid alternative. It encrypts the API keys you store; keep it. When neither is set, the file falls back to `change-me-to-a-secret-string` only for installs that used that placeholder. If an existing install has a custom key in its old compose file, copy that exact key into `.env` before replacing the file; do not generate a new one. That fallback is public. Replace it before you save provider keys.
117: 
118: > **Shared network or server?** The UI (`8502`) and API (`5055`) are published on all network interfaces and there is no password by default. If other devices can reach this machine, change those two port lines to `"127.0.0.1:8502:8502"` and `"127.0.0.1:5055:5055"`, or set `OPEN_NOTEBOOK_PASSWORD` in the same `.env` file, before starting.
119: 
120: ### Step 3: Start services
129: 2. Find your provider (OpenAI, Anthropic, Google, etc.) and click **Add Configuration**.
130: 3. Enter a name and your API key (local providers such as Ollama need a **Base URL** instead), then click **Add Configuration**.
131: 4. Click **Test** on the new configuration to check the connection.
132: 5. Click **Models**, choose a **Model Type**, tick the models to add and click **Add**. Add at least one **Language** model and one **Embedding** model.
136: 
137: > **Need an API key?** Get one from:
138: > [OpenAI](https://platform.openai.com/api-keys) · [Anthropic](https://console.anthropic.com/settings/keys) · [Google](https://aistudio.google.com/app/apikey) · [Groq](https://console.groq.com/keys)
139: >
140: > Anthropic and Groq have no embedding models; pair them with a provider that does (see the [matrix](#provider-support-matrix)).
147: 
148: - **[Local AI with Ollama](docs/0-START-HERE/quick-start-local.md)** - Run models locally without API costs
149: - **[Docker Compose guide](docs/1-INSTALLATION/docker-compose.md)** - Settings, backups, updates, remote access
150: - **[From Source (Developers)](docs/1-INSTALLATION/from-source.md)** - For development and contributions
165: 
166: [![Star History Chart](https://star-history.dera.page/svg?repos=lfnovo/open-notebook&type=date&legend=top-left)](https://star-history.dera.page/#lfnovo/open-notebook&type=date&legend=top-left)
167: 
168: 
181: | xAI          | ✅          | ❌               | ❌             | ✅             |
182: | OpenRouter   | ✅          | ✅               | ✅             | ✅             |
183: | DashScope (Qwen) | ✅          | ❌               | ❌             | ❌             |
184: | MiniMax      | ✅          | ❌               | ❌             | ✅             |
191: | ElevenLabs   | ❌          | ❌               | ✅             | ✅             |
192: | Deepgram     | ❌          | ❌               | ✅             | ✅             |
193: | Ollama       | ✅          | ✅               | ❌             | ❌             |
194: | oMLX         | ✅          | ✅               | ❌             | ❌             |
206: - **🎯 Multi-Notebook Organization**: Manage multiple research projects seamlessly
207: - **📚 Universal Content Support**: PDFs, videos, audio, web pages, Office docs, and more
208: - **🤖 Multi-Model AI Support**: 20+ providers including OpenAI, Anthropic, Ollama, Google, LM Studio, and more
209: - **🎙️ Professional Podcast Generation**: Advanced multi-speaker podcasts with Episode Profiles
216: - **🔧 Content Transformations**: Powerful customizable actions to summarize and extract insights
217: - **🌐 Comprehensive REST API**: Full programmatic access for custom integrations [![API Docs](https://img.shields.io/badge/API-Documentation-blue?style=flat-square)](http://localhost:5055/docs)
218: - **🔐 Optional Password Protection**: Secure public deployments with authentication
219: - **📊 Fine-Grained Context Control**: Choose exactly what to share with AI models
220: - **📎 Citations**: Get answers with proper source citations
221: 
222: 
247: - **[🔌 MCP Integration](docs/5-CONFIGURATION/mcp-integration.md)** - Connect with Claude Desktop, VS Code and other MCP clients
248: - **[🔧 REST API Reference](docs/7-DEVELOPMENT/api-reference.md)** - Complete API documentation
249: - **[🔐 Security](docs/5-CONFIGURATION/security.md)** - Password protection and privacy
250: - **[🚀 Deployment](docs/1-INSTALLATION/index.md)** - Complete deployment guides for all scenarios
257: 
258: Right now the focus is on making the core experience (sources, chat, search, notes, podcasts) solid across every provider and deployment, before adding new product surfaces. The bigger directions under consideration, such as multi-user support, new output formats and agents operating Open Notebook through MCP, are described in the **Horizon** section of [VISION.md](VISION.md#horizon). They are directions, not dated promises.
259: 
260: Explore [GitHub Discussions](https://github.com/lfnovo/open-notebook/discussions/categories/ideas) for proposed features and product ideas, and [open Issues](https://github.com/lfnovo/open-notebook/issues) for known bugs and approved work. Recent changes are in the [CHANGELOG](CHANGELOG.md).
286: 
287: **Current Tech Stack**: Python, FastAPI, Next.js, React, SurrealDB
288: 
289: See our [Contributing Guide](CONTRIBUTING.md) for detailed information on how to get started, including our guidelines for [AI-assisted contributions](docs/7-DEVELOPMENT/contributing.md#ai-assisted-and-agent-generated-prs). To understand what we're building (and what we'll say no to), read [VISION.md](VISION.md).
293: 
294: ## 📄 License
295: 
296: Open Notebook is MIT licensed. See the [LICENSE](LICENSE) file for details.
297: 
298: 
318: [issues-url]: https://github.com/lfnovo/open-notebook/issues
319: [license-shield]: https://img.shields.io/github/license/lfnovo/open-notebook.svg?style=for-the-badge
320: [license-url]: https://github.com/lfnovo/open-notebook/blob/main/LICENSE
321: [linkedin-shield]: https://img.shields.io/badge/-LinkedIn-black.svg?style=for-the-badge&logo=linkedin&colorB=555
322: [linkedin-url]: https://linkedin.com/in/lfnovo
326: [React-url]: https://reactjs.org/
327: [Python]: https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white
328: [Python-url]: https://www.python.org/
329: [LangChain]: https://img.shields.io/badge/LangChain-3A3A3A?style=for-the-badge&logo=chainlink&logoColor=white
330: [LangChain-url]: https://www.langchain.com/
331: [SurrealDB]: https://img.shields.io/badge/SurrealDB-FF5E00?style=for-the-badge&logo=databricks&logoColor=white
332: [SurrealDB-url]: https://surrealdb.com/
333: 