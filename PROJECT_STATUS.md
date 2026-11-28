# 项目状态

## 2026-11-28 矩阵全字段评测与 arXiv 复验

用户已确认旧文献库批量更新。全字段评测扩至八篇真实论文与 66 个标注。候选命中由 22 项提高到 31 项，复测 45 条候选均可逐字定位。arXiv 实网成功导入一条，53 项自动化测试通过。矩阵语义仍有缺口，AgentArts 云端验收继续暂缓。本轮等待用户确认。[本轮验收](docs/system-testing/matrix-benchmark-results.md)

## 旧文献库批量更新

已交付课题内的更新预览与确认应用。支持补齐可核对的空元数据、刷新自动候选和保护手工修改，52 项测试通过。用两篇公开论文重建旧记录，实跑验证了年份补齐与矩阵证据页刷新。AgentArts 云端验收按约定暂缓，等待本轮交付确认。[使用与验收](docs/design/library-refresh.md)

## 本地元数据与矩阵质量复测

四篇真实论文的核心字段从 8/16 提升到 14/16，九个指定矩阵字段从 3/9 提升到 9/9。49 项自动化测试通过，上一轮 Web 导入、引用和报告的端到端复测通过。两篇英文 PDF 的 DOI 缺少文件内证据，继续留空。暂缓 AgentArts 云端验收，等待本轮交付确认。[本地质量复测](docs/system-testing/quality-results.md)

## 2026-11-27 独立系统测试

用户确认暂缓 AgentArts 云端工具验收并开展独立系统测试。已跑通真实双语论文解析、证据回跳、报告编辑和 Word/Markdown 导出，修复短语排序与 Word 排版，47 项回归通过。元数据漏项、arXiv 限流及云端验收仍有缺口。已交付本轮结果，等待确认下一步。[系统测试记录](docs/system-testing/acceptance-results.md)

## 2026-11-24 AgentArts 多步文献调研

在线检索获用户确认。进入 AgentArts 自主科研任务验收。已准备可导入 Skill 与 InvokeChat 轨迹核验探针，32 项回归及本机真实 Crossref 检索、两条 DOI 核验通过。待已登录账号挂载并运行一次云端任务。

用户已确认当前运行版本关联 literature-research 并启用 Bash。最后一次实时检查有 skill_tool 配对结果，未发起 Bash，智能体报告 skill_load_failed。具体原因待平台证据核实。云端自主学术工具验收标记为阻塞，本轮排查结束。用户已确认暂缓该项云端验收并推进独立系统测试。[验证记录](docs/platform-validation/managed-research-workflow.md)

[工作流核验](docs/platform-validation/managed-research-workflow.md)


## 2026-11-23 在线学术检索

用户截图确认网页版 AgentArts 问答成功，显示核对通过的 PDF 第 2 页摘录及模型推断。在线检索与导入已交付，29 项回归和三组真实 API 的网页导入实测通过。平台自主工具编排待验收。[在线检索验收](docs/design/academic-search.md)


## 2026-11-23 调研报告

完成本地初稿、章节编辑与单节重建、原文证据及 Word/Markdown 下载，25 项自动化测试通过。用户提供的 AgentArts 401 截图已复核，增加脱敏诊断，待账号侧恢复云端联调。本次交付后等待试用确认。[报告验收](docs/design/literature-report.md) · [401 记录](docs/platform-validation/managed-chat-401.md)


## 2026-11-22 文献对比矩阵

已交付十字段矩阵、按 PDF 页保存的原文候选、人工修订及证据校验、字段筛选和 CSV 导出。21 项测试通过，两篇公开论文的 16 个候选引文均可在对应页文本定位。待用户确认矩阵；AgentArts 云端问答仍待账号联调。[本轮验收](docs/design/literature-matrix.md)

## 2026-11-22 文献库使用反馈修正

课题支持批量导入、分次追加和逐份移除待上传 PDF，标题旁可重命名。18 项自动化测试通过，已在隔离 Chrome 验证多选、追加、移除、实际导入与重命名。

## 2026-11-22 文献问答与页级核验

文献库 MVP 已获用户试用确认。本轮已交付单篇和多篇文献问答入口、本地原文检索、引文核对和页码跳转、AgentArts 官方 API 客户端。15 项自动化测试通过，公开论文第 4 页定位及 Chrome 表单验证通过。当前待用账号 IAM 凭据完成一次 Web 到现有 Managed Agent 的正式调用；Agent 自主工具调用仍待联调。当前阶段交付后等待确认。[设计与验收记录](docs/design/literature-qa.md)


## 2026-11-21 文献库 MVP 已交付

合并阶段已实现本地课题和文献管理、中英文 PDF 解析、元数据编辑与分类、全文搜索、页级原文预览和 JSON 来源接口。六项集成测试通过。使用真实公开论文回归字体版式标题和脚注边界，并在 Chrome 核验桌面阅读与窄屏文献库。正式文献库从空库启动。AgentArts 剩余验证暂停，待用户审阅本阶段后决定后续工作。

- [本地启动与使用](README.md)
- [设计与验收](docs/design/library-mvp.md)
- [实测证据](docs/design/evidence/verification.json)

> 下方记录保留 AgentArts 验证等先前进展。

更新：2026-11-18。当前有效路线见 [开发计划](DEVELOPMENT_PLAN.md)。

阶段二已获授权并进行中。先前Agent有Playground成功证据；当前新建agent-huawei-cit详情已确认，但尚无该Agent调用结果；真实文献工具编排、对外API与发布记录尚未验证。阶段三及之后未授权，正式技术方案和业务模型选型未定案。

| 阶段 | 状态 |
|---|---|
| 一：开源调研与候选选型 | 已交付调研，候选方案待确认 |
| 二：AgentArts最小可行验证 | 部分成功：Agent创建/Playground文本调用；工具/API待验证 |
| 三：需求细化与系统设计 | 未开始、未授权 |
| 四：核心业务功能开发 | 未开始、未授权 |
| 五：完整科研工作流与联调 | 未开始、未授权 |
| 六：系统测试与质量优化 | 未开始、未授权 |
| 七：比赛展示与正式部署 | 未开始、未授权 |

## 当前已取得证据

- 用户确认DeepSeek官方来源，先前核查官方Flash API ID并提供接入填写单；截图未展示最终所选模型，不能将建议当实际配置。
- 最新截图显示AgentArts、西南-贵阳一、agent-tg2vc3r0及成功问答，页面时间11月18日11:02。Agent名称/显示标识不等于官方API所需UUID。
- 先前Crossref本地真实查询成功；仍不是平台调用文献工具的证据。

## 当前需要推进

- 智能体详情/编辑页的模型、提示词、环境、工具与Skill配置；对外调用/API说明入口（如有）。
- 本次输入45877、输出11、总计45888的计量范围、上下文、轮次与实际费用；截图显示深度思考，但不足以解释计数或认定具体模型。
- 根据实际平台接入契约完成真实文献工具绑定、执行轨迹、官方API与失败路径；暂不重复简单问答或批量论文。

本次助手仅审查用户成功截图并更新记录，未代用户发起模型/API调用或购买资源。当前浏览器工具此前因Windows沙箱错误不可连接，继续采用用户操作+脱敏证据验证；不索要密钥或思考正文。

详情见 [阶段二验收](docs/platform-validation/acceptance-results.md) 与 [本次成功及下一步](docs/platform-validation/playground-success-and-next-validation.md)。旧状态保存在 [历史归档](docs/platform-validation/history/PROJECT_STATUS-before-playground-success.md)，不能作为当前未创建判断。

初赛仍以真实平台构建运行及Demo视频为重点，不要求提前提供公网Demo链接；每阶段交付后等待明确确认，阶段二目前未完成。

当前目标已切换agent-huawei-cit：deepseek-flash与environment-huawei-cit已绑定，内置工具/Skills均0。旧Playground成功属于另一Agent，不迁移结果与用量。下一步核实工具/Skill接入选项及官方API调用信息，见 [具体操作](docs/platform-validation/agent-huawei-cit-next-steps.md)。


### 2026-11-20 最新阶段二状态

AgentArts 网关和 Crossref Target 已创建，网关控制台实测检索成功并返回两条带 DOI 的文献记录。当前待验证的是 `agent-huawei-cit` 的工具接入与实际调用，以及官方 Agent API。[阶段二验收](docs/platform-validation/acceptance-results.md)


### 网关外部 IAM 验证更新

本机 V11 签名已通过 IAM 进入 MCP 网关，并成功列出 Crossref 工具。云端 Agent 的工具调用和外部 Agent API 仍是阶段二验收项。[阶段二验收](docs/platform-validation/acceptance-results.md)


### 外部网关检索已实测通过

V11 外部客户端已执行真实查询，返回两条带题名、DOI 和链接的 Crossref 登记记录。阶段二转入云端运行时部署前检查。实际智能体工具编排及外部 Agent API 尚待验证。[验收记录](docs/platform-validation/acceptance-results.md)


### 阶段二本地运行时镜像就绪

`literature-runtime-probe:0.1.0` 已构建并通过本地容器烟测。下一步核对西南-贵阳一的私有 SWR 仓库及云端运行时身份，验证云端到 MCP 网关的完整链路。[验收记录](docs/platform-validation/acceptance-results.md)


### 运行时验证镜像已上传 SWR

本机验收过的验证镜像已推送至西南-贵阳一 SWR，远端标签与摘要核对通过。阶段二下一步确认 STS 凭据提供商与运行时委托，再提交云端托管验证。[验收记录](docs/platform-validation/acceptance-results.md)


### 阶段二运行时委托版镜像已就绪

0.1.1 已上传到既有私有 SWR，默认用运行时委托的临时凭据。下一步托管单独的验证实例并验证官方运行时 API、临时身份和真实 Crossref 返回。[阶段二验收](docs/platform-validation/acceptance-results.md)
