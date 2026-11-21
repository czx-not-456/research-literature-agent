# 第三方组件与许可登记

日期：2026-11-16。以下是调研对象，**不是已集成依赖清单**。未安装任何候选项目，未拷贝业务实现。证据摘录/许可仅用于本地审查，来源见docs/pre-research/evidence/source-manifest.json；完整SBOM尚未建立。

| 项目 | 来源 | 主许可（已读） | 拟用途 | 状态/风险 |
|---|---|---|---|---|
| Open Notebook | https://github.com/lfnovo/open-notebook | MIT，Luis Novo | Web/资料库主体候选 | 未采用；依赖/权重另查 |
| GPT Researcher | https://github.com/assafelovic/gpt-researcher | Apache-2.0 | 报告/研究候选 | 未采用；PyMuPDF许可重点复核 |
| RAGFlow | https://github.com/infiniflow/ragflow | Apache-2.0 | 解析/检索候选 | 未采用；当前Go与原生/容器依赖另查 |
| PaperQA | https://github.com/Future-House/paper-qa | Apache-2.0 | 证据工具候选 | 未采用；默认pypdf插件与可选AGPL解析器分开 |
| Docling | https://github.com/docling-project/docling | MIT | 复杂PDF候选 | 未采用；模型权重和OCR后端另查 |
| AgentArts Python SDK | https://github.com/huaweicloud/agentarts-sdk-python | Apache-2.0 | Runtime/Gateway | 官方文档和源码已读，未安装/联调 |

额外MCP项目Epochal-dev/open-notebook-mcp、assafelovic/gptr-mcp仅由上游文档发现，未完成源码许可审计，不作为已批准依赖。GROBID和pypdf直接资料读取失败，不填写未经本次核实的许可。PyMuPDF AGPL/商业许可风险来自候选依赖路径，正式采用前须读具体版本许可文件及条款。

保留要求：复制/分发MIT代码保留版权和许可；Apache项目保留LICENSE、适用NOTICE、标示修改。模型权重/镜像/原生库逐项登记，不能只看主仓。API协议与论文版权另登记：
- Crossref：绝大部分元数据开放，部分摘要保留版权；免费public/polite有各自限流。
- arXiv：API条款、描述性元数据与每篇全文许可分开。
- OpenAlex：认证额度已核实，完整价格/许可原始页面访问受阻。
- Semantic Scholar：API协议+S2数据许可+论文第三方许可+署名义务，不能默认可任意商用。
- DeepSeek/百炼：本次只读官方能力/价格；数据保留政策与服务合同尚未审查。

完整源码版本、转依赖、模型文件校验、漏洞/许可扫描均留待确认方案后进行，当前不能宣称“依赖合规已完成”。

## 2026-11-17 计划修订

AgentArts SDK仅为辅助候选，原SDK Runtime优先建议撤销；许可登记和已读源码不证明平台工作流能力或账号权限。未新增依赖、安装或云资源。 当前路线见 [开发计划](DEVELOPMENT_PLAN.md)。

## 阶段二资料补查（2026-11-17）

补读官方SDK environment_variables.md 与 deploy.md，保留来源摘录；未安装/复制运行SDK，也未采用其示例Agent。验证脚本仅用Python标准库调用Crossref公开REST，未新增依赖。两条真实journal-article元数据只作连通性样本，不将类型或DOI当作论文质量保证。代金券及MaaS型号/价格尚未核实。


## 2026-11-21 文献库 MVP 实际采用

| 组件 | 版本与许可证 | 用途 |
| --- | --- | --- |
| [Flask](https://github.com/pallets/flask) | 3.1.3，BSD-3-Clause | 本地 Web 路由及模板，带 Werkzeug/Jinja 等依赖 |
| [pypdf](https://github.com/py-pdf/pypdf) | 6.21.4，BSD-3-Clause | PDF 页文本与文档属性 |
| [pypdfium2](https://github.com/pypdfium2-team/pypdfium2) | 5.15.2，安装元数据标注 BSD-3-Clause、Apache-2.0 和依赖许可 | 使用包含上游许可的 Python 分发包渲染单页 |
| [Pillow](https://github.com/python-pillow/Pillow) | 12.3.0，MIT-CMU | 生成页预览 PNG |
| [SQLite](https://sqlite.org/copyright.html) | Python 标准库绑定，SQLite 核心公有领域 | 本地持久化 |
| [ReportLab](https://www.reportlab.com/) | 4.5.1，BSD | 仅用于生成本地测试 PDF |

项目依赖声明保留各组件来源，未复制第三方项目源码。若以后将依赖随安装包或镜像分发，需保留对应 LICENSE、NOTICE，并按包含的原生依赖复核。
