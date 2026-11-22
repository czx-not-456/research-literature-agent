# 文献问答与页级核验

## 使用范围

从课题文献库进入「文献问答」，或者从文献详情点击「问这篇论文」。每次选 1 至 6 篇同课题文献，填写最多 500 个字符的问题。普通启动即可「查找原文」；启用 IAM 配置后，可选择「让 AgentArts 回答」。本机查找使用已提取的 PDF 页文本，扫描页需要先有可提取文本。

本地检索采用英文词、中英文标点边界、中文二元词组，以及对连续英文技术词组的排序加权。先提供各匹配文献的代表片段，再补充相关片段，最多 8 段，每段最多 720 个字符。这里的召回属于字词匹配，对概念改写或跨语种提问只有有限覆盖。未匹配到原文时可使用论文中的原词重新提问。

本地后端发出问题及带内部编号的原文摘录，不发送整个 PDF 或文献库。每次请求使用新的会话号。AgentArts 根据摘录生成结构化回答。后端以本地保存的标题和 PDF 物理页码生成链接，只接受能在已发送摘录中逐字定位的引文，核对时允许空白差异并显示本地原文。

- **原文摘录 · 已核对**表示回答文字与核实的原文一致。
- **模型推断**表示模型给出了可定位的引文，但归纳、解释或翻译仍需读者核对语义。
- **缺乏证据**表示没有通过本地核对的引文，页面省略该条结论的文本。

## AgentArts 接入

Web 后端使用现有西南-贵阳一 Managed Agent `agent-huawei-cit`，通过控制台中已有运行时访问域名发起官方 `InvokeChat` 调用。请求方法是 `POST /runtimes/managed-agent-huawei-cit/invocations/v1/chat/completions`，请求体包含 `query`，请求头携带会话 ID 和 IAM V11 签名。响应使用 SSE；只有收到成功终态的回答才进入本地核验。网络或鉴权失败时保留本地片段并显示失败原因。当前路径由本机选取候选原文，再由平台回答。平台自主调用检索或核验工具的轨迹仍待验证。

- [Managed Agent 对话接口 · InvokeChat](https://support.huaweicloud.com/api-agentarts/InvokeChat.html)
- [华为云运行时 IAM V11 调用说明](https://support.huaweicloud.com/bestpractice-agentarts/agentarts_06_0063.html)
- [既有运行时控制台记录](../platform-validation/evidence/runtime-console-review.json)

## 本机验收结果

Windows 本地共通过 15 项自动化测试，包括原有的 6 项文献库用例。新增用例覆盖中英文 PDF、单双文献入口、课题隔离、技术术语排序、无证据与无配置、伪造引文和页码、网络失败回退、IAM 签名一致性及官方形态的 SSE 解析。传输和模型输出测试使用固定用例，云端结果尚待验证。

公开论文《Attention Is All You Need》回归使用问题 `What is scaled dot product attention?`。原始排序将首页一次术语提及排在正文之前；修正后返回第 4、1 页，第 4 页的来源接口文本与 PDF 预览均通过检查。Chrome 在 1280 和 412 像素窗口宽度下检查了问答表单、文献预选和未配置时的云端按钮状态。所有测试数据写入隔离库。[公开论文原件](https://arxiv.org/pdf/1706.03762)

## 云端验收待办

在本机启动 AgentArts 模式，使用一篇允许发送摘录的公开论文提交一个问题。记录官方 API 成功、回答可核验、至少一个引文跳转到实际 PDF 页面，以及平台用量。控制台的旧 Playground 和单独的 Crossref MCP 成功各有独立记录。本轮未提交新的云请求，实际账单、该 Agent 的 InvokeChat 结果和平台自主工具调用仍待验证。[本地启动说明](../../README.md)
