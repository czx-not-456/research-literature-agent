# GitHub 开源项目比较

> 2026-11-17 计划修订：当前阶段顺序及职责以 [开发计划](../../DEVELOPMENT_PLAN.md) 为准。新增阶段二先验证 AgentArts 平台工作流，详细设计/核心开发/完整联调/系统测试/正式部署分别为阶段三至七。平台必须完成核心智能体的构建、编排和部署；本报告原始调研事实保留 2026-11-16 日期，本次没有新增平台实测结论。

调研日期：2026-11-16。范围：阶段一；没有安装或运行候选项目，没有修改其源码。
结论依据为公开仓库实际 README、LICENSE、依赖清单、部署文件和选定源码，不以 Star 数评判。记录在 [证据索引](evidence/source-manifest.json) 及 evidence/ 下。默认分支会变化，快照仅代表本次读取；锁定 commit、完整 SBOM 与运行验收尚未完成。

## 结论

没有一个候选项目已被证明能直接覆盖全部 A–E。Open Notebook 最适合作为完整 Web 复用起点；PaperQA 适合隔离为科研证据工具；RAGFlow 有较强解析与位置数据基础，但当前分支部署、二次开发负担明显较高；GPT Researcher 强项是通用检索和报告，不等同于个人学术文献库。建议优先考虑方案 B，详见 [技术选型](technology-selection.md)，尚未确定最终方案。

## 判定标准

- “代码”：已找到实现入口或结构，不表示本机运行通过。
- “文档”：上游明确描述，尚未用本项目样本验证。
- “需补”：不能满足本项目验收，或本次未找到足够实现证据。
- “待测”：中英文、双栏、扫描件、效果与可靠性均须实测。
- “未发现”：限于所审查文件，不能推断全仓库绝对不存在。
- README 的未来方向、研究论文中的内部系统效果不算开源版本已交付能力。

## A–E 功能覆盖

| 能力 | Open Notebook | GPT Researcher | RAGFlow 当前 main | PaperQA 当前 main |
|---|---|---|---|---|
| 完整 Web | Next.js + FastAPI，代码/部署 | FastAPI + 简版前端/Next.js，代码 | Web + Go 服务，代码/部署 | Python SDK/CLI；未确认完整管理 Web |
| A 上传、管理 | sources、notebooks CRUD 与上传代码；学术字段需补 | 上传/删除代码；持久化与分类需补 | 文档上传、列表、预览、删除代码 | Docs 添加文件/URL；业务库需自建 |
| PDF 解析 | content-core 依赖与后台处理代码；OCR 为可选重组件 | 本地资料读取及 PyMuPDF/unstructured 依赖 | DeepDoc、原生解析和位置字段基础 | 可插拔 PDF 解析，默认 paper-qa-pypdf |
| 中文/英文 | 中文 UI 是文档声明；解析与问答质量待测 | 可提示中文；解析和领域质量待测 | 文档支持多格式；中文 OCR/双栏需测 | 不应把英文科研基准推广为中文通过 |
| 标题/作者/摘要/关键词/年/DOI | Source 通用内容对象，完整学术模型需补 | 完整学术模型需补 | 通用元数据配置，学术准确性待测 | citation/details 有提取流程，需验证、可人工改 |
| 单篇/多篇问答 | source_chat / chat / search；代码 | report chat 和研究接口；学术问答需改 | chat、dataset、chunk 检索接口 | Docs/aquery、gather_evidence 等代码 |
| B 十字段矩阵 | 需新增结构化存储、编辑、筛选、导出 | 同左 | 有知识编译等能力，不能等同十字段矩阵验收 | 证据工具可支撑提取；管理 UI 和存储需补 |
| C 引用与定位 | 有来源引用；精确页/片段/坐标需补证据模型 | URL/资料引用不能证明页码准确 | chunk positions 与预览基础；语义支持核验需补 | 文本块有 pages 范围；单页精确定位和语义核验需补 |
| C 直接支持/推断/无证据 | 需新增并测试 | 需新增并测试 | 需新增并测试 | 需新增并测试 |
| D 报告和导出 | 笔记/变换基础；章节版本、Word 需补 | 报告生成及 MD/Word/PDF 转换代码 | 知识编译不等于可编辑科研综述与 Word 验收 | 有答案综合；章节报告业务需补 |
| E 学术检索导入 | URL 导入≠学术 API 检索；需补 | arxiv/Tavily 等依赖与检索器；三源规范化需补 | 不把连接器、scholarly 依赖当成完整 E | paper_search 存在；README 说明部分检索基于用户文献索引 |
| API / MCP | REST 代码；MCP 为独立 Epochal 项目 | REST、WebSocket；MCP client；server 独立仓库 | REST、MCP handler 代码 | Python 接口；外包 HTTP/MCP 适配 |
| AgentArts | 推荐通过有边界的工具适配 | 需避免两套规划器重叠 | 可作为工具服务；不以原生 Agent 替代 AgentArts | 作为证据工具，避免直接接管全任务 |

原文片段与页码存在，不代表该片段确实支持生成的结论。引用标记存在，也不代表 DOI、作者和页码已核实。

## 逐项审查

### 1. Open Notebook

上游：https://github.com/lfnovo/open-notebook ，MIT，Copyright (c) 2024 Luis Novo。
实际读取：README.md、LICENSE、pyproject.toml、docker-compose.yml、api/routers/sources.py、api/routers/source_chat.py、open_notebook/domain/notebook.py、commands/source_commands.py、docs/1-INSTALLATION/from-source.md、docs/5-CONFIGURATION/mcp-integration.md。

- pyproject：1.15.1，Python >=3.11.5,<3.13；FastAPI、LangChain、LangGraph、content-core、Esperanto、SurrealDB。
- Compose：SurrealDB v2 + open_notebook 两服务；后者包含 UI、API、后台 worker，端口 8502/5055；数据库 8000 绑定本机。
- sources.py 包含上传前文件支持检查、去重、异步处理、查询及文件返回入口；source_chat.py 包含会话 CRUD 和消息流。
- Source 通用全文、资料关系与 insights 适合复用，但应增加受控的学术字段与原始字段来源；不能让模型生成的元数据成为无条件权威记录。
- README 明确把未来新输出格式、部分 MCP Agent 方向放在 Horizon；文档中的 MCP 来自 Epochal-dev/open-notebook-mcp，须单独审查许可、认证和传输协议。
- 资源建议：本机 16 GiB 可优先验证云模型方案；2–4 vCPU/4–8 GiB 仅是小库初始工程预算，未测得容量上限。启用 Docling/OCR 后另测内存与下载量。
- 云迁移：Linux x86_64 容器部署具备路径；OBS、数据库备份、访问控制需要改造。不能默认 SurrealDB 可直接迁移到华为云关系数据库。
- 风险：当前依赖使用较宽范围、镜像 floating tag；应锁定版本。默认无密码与公开示例加密密钥必须在部署前改掉。MIT 主许可不覆盖所有依赖、模型权重和第三方内容。

### 2. GPT Researcher

上游：https://github.com/assafelovic/gpt-researcher ，Apache-2.0。
实际读取：README.md、LICENSE、requirements.txt、docker-compose.yml、main.py、gpt_researcher/agent.py、backend/server/app.py、backend/utils.py。主要材料从 master 获取；元数据显示默认分支 main；另读取 main 的 backend/server/app.py 核对入口，尚未逐文件比较两分支差异，正式复用须统一固定 commit。

- Python FastAPI + LangChain/LangGraph/LiteLLM；Docker 支持后端和 Next.js 前端。
- GPTResearcher 类有 conduct_research / write_report 流程，web/local/hybrid 资料源与 MCP 参数。
- backend/server/app.py 有真实 upload/delete、研究与报告接口、WebSocket；同时明确注释部分报告 API “no database persistence”。不能把交互页面当作稳定的文献库持久化。
- backend/utils.py 有 Markdown、Word、PDF 输出代码；尚未验证中文字体、复杂表格、章节局部重新生成和格式保持。
- requirements 含 pymupdf、unstructured、md2pdf、浏览器相关组件；运行成本还包括搜索服务，README 的单次成本估计不能作为本项目报价。
- MCP client 与 server 区分：server 上游指向独立 gptr-mcp；不等于任何云平台可直接使用本地 stdio。
- 适用：通用深度研究/报告工具；作为项目主干会增加文献库、矩阵、证据锚点和章节版本的开发量。
- 许可风险：Apache-2.0 主项目 + PyMuPDF AGPL/商业许可路径需重点审查。不得因主项目宽松就认为整个依赖树宽松。可评估替换解析器，替换效果须测。

### 3. RAGFlow

上游：https://github.com/infiniflow/ragflow ，Apache-2.0。
实际读取：README.md、LICENSE、go.mod、pyproject.toml、docker/docker-compose.yml、docker/docker-compose-base.yml、internal/handler/document.go、internal/handler/chunk.go 及 internal/ 目录。

- 本次 main 是 Go 1.27 服务、CGO/原生静态库与 DeepDoc CPU 推理路径，保留 Python 依赖配置（>=3.13,<3.14）及 Web。不能用旧版“Python 后端”概括。
- README 本次写明源码构建涉及 Go 1.27、Clang/LLD 20、CMake >=4.0、PCRE2，另下载 pdfium/pdf_oxide/office_oxide/onnxruntime 与模型资源。
- 推荐起始配置为 4 CPU、16 GB RAM、50 GB 可用磁盘，这是上游建议而非本机实测；本机总内存接近该值，Windows 和开发工具还要占用，因此不建议本机首选。
- Compose 的 profile 支持多种文档引擎与存储后端；它们是可选项，不能把所有列出的数据库都算成必须同时启动。
- document.go 有上传、预览、元数据过滤、删除；chunk.go 接受 positions。具备证据位置基础，但仍需证明解析输出、检索、回答和 UI 位置链路一致。
- 内置 Agent/MCP 和知识编译方向范围较广，与 AgentArts 叠加容易重复规划。建议只做隔离解析/检索服务评估。
- 许可需逐项检查原生库、镜像、搜索/对象存储版本；未完成全依赖扫描，不能给出“可无风险商用”的结论。

### 4. PaperQA（用户称 PaperQA2）

上游：https://github.com/Future-House/paper-qa ，Apache-2.0。
实际读取：README.md、LICENSE、pyproject.toml、src/paperqa/readers.py、src/paperqa/docs.py、src/paperqa/agents/tools.py。

- Python >=3.11,<3.15；LiteLLM、fhaviary、fhlmi、Tantivy、NumPy、Pydantic；默认 paper-qa-pypdf，可选 docling/pymupdf/nemotron 等插件。
- readers.py 的 resolve_page_range 使用 1-based 页码转内部范围，_make_chunk 保存 “pages x-y”。范围引用不等于准确单页；要保存原始页号与块映射。
- tools.py 有 paper_search、gather_evidence、gen_answer；可复用为受控分析工具，不让它绕过 AgentArts 主流程。
- docs.py 可在缺失 citation 时从模型抽取，并有 Unknown/文件名/当前年回退路径；此路径不满足本项目“不得编造年份”等约束，必须拦截为待核实、保留原始来源。
- README 特别说明 FutureHouse 内部有无法公开共享的论文 API/许可，公开版能力与论文实验系统不完全一致；必须使用用户合法提供或开放许可论文。
- 没有本次核实的完整 Web 文献管理系统。持久化业务、分类、矩阵、报告编辑、导出均需开发。
- 默认轻量解析不能保证扫描件、中文双栏质量；可选解析器按样本启用。
- LiteLLM 配置中明确排除一个遭攻击的版本，说明供应链锁定与审计有现实必要；该上游注释不是本项目完成安全扫描的证据。

## 其他候选和组件

GitHub 补充检索词：AgentArts、scientific literature review local PDF web。后一个查询返回 literature-capture，尚未审查，不能作为已合格候选。没有仅凭检索结果推荐小型项目。

重点补充审查 Docling：https://github.com/docling-project/docling 。已读 README、LICENSE、pyproject.toml 与 docling/document_converter.py；MIT，当前 pyproject 中 docling-slim 2.150.1。提供统一解析、页面范围、可配置后端及进度回调，可作复杂 PDF 解析模块；不是完整 Web 文献库。OCR/表格模型、下载权重和加速器支持要独立核验。本次未安装或跑中文样本，不承诺解析准确率。

华为云官方 AgentArts SDK 另见技术选型文档，Apache-2.0；只读核查，未安装、部署。

GROBID、pypdf 的直接 GitHub 文件读取未成功；仅列为后续候选，不作为本次已核实许可或可运行组件。

## 维护与部署判定

| 项目 | 本次元数据 pushed_at（UTC） | 判定 |
|---|---|---|
| Open Notebook | 2026-11-15 21:44:06 | 未归档，近期更新 |
| GPT Researcher | 2026-11-12 19:34:46 | 未归档，分支需统一 |
| RAGFlow | 2026-11-16 13:23:11 | 未归档，当前架构变化较大 |
| PaperQA | 2026-11-09 20:37:05 | 未归档，科研 SDK 持续维护 |
| Docling | 2026-11-16 12:59:06 | 未归档，解析组件持续维护 |

近期 push 仅说明更新发生，不能代替 issue 响应、发布稳定性、回归结果和长期维护保证。本次尚未统计 issue 解决周期或完整运行 CI。

## 进入实施前的最小验证建议（未执行）

固定版本后，用各 3 篇中英文文本 PDF、2 篇双栏和2份合法扫描件验证页号/原文映射、元数据缺失处理、同一证据多次检索一致性。Open Notebook 与 PaperQA 先分服务验证，避免依赖冲突。Word 导出须实开、逐页检查，不能以返回路径代替导出成功。所有指标到阶段六建立人工参考答案后再报告。
