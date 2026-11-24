# AgentArts 文件问答 HTTP 401

## 11 月 23 日用户侧成功复测

网页版返回离线黑盒优化的 AgentArts 回答，显示核对的 PDF 第 2 页摘录、模型推断和缺乏证据标签。该次请求成功，旧 401 根因仍未确认。平台自主调用外部工具尚待验收。[用户截图](<../../屏幕截图 2026-11-23 144921.png>)

## 当前结果

2026-11-23 的用户截图显示界面能够检索选定论文页文本并返回两段候选原文，点击「让 AgentArts 回答」后，Web 后端收到 HTTP 401。截图未提供华为云错误码、请求 ID 或具体错误描述，暂时无法区分运行时访问域名、入站认证方式、IAM 密钥状态、临时凭据或签名时间问题。

本轮核对 Managed Agent 官方调用路径、既有运行时记录和 V11 签名范围。当前客户端使用运行时 `managed-agent-huawei-cit`、西南-贵阳一及 IAM V11。官方 SDK 的签名范围使用 `apic`。单独的 Crossref MCP 网关曾用 V11 调通；两个访问入口各自验证，当前 Managed Agent 对话接口仍返回 401。

新版本显示平台错误码、请求 ID 和固定的过期提示（在平台返回相应字段时），保留本地匹配的原文。显示内容经过白名单筛选，不回传响应正文、Authorization 或密钥。本轮测试使用本地夹具，未使用账号凭据发起云请求。

## 已核对的账号配置

2026-11-23 的截图和控制台复制地址共同确认，西南-贵阳一的 `managed-agent-huawei-cit` 使用 `defaultgw`，`Latest` 绑定 v2，v2 入站为 IAM。实际访问域名与应用默认网关一致。截图还显示运行时委托 `DefaultAgentArtsRuntimeAgency` 和日志记录已开启。

控制台复制的是通用运行时调用地址 `/runtimes/managed-agent-huawei-cit/invocations?endpoint=Latest`。文献问答用的官方 Managed Agent 对话接口路径为 `/runtimes/managed-agent-huawei-cit/invocations/v1/chat/completions`，其公开接口参数未列出 `endpoint`。现有客户端路径符合 InvokeChat 文档，启动选项 `--endpoint` 接受 HTTPS 网关域名。未取得新版客户端重试后的平台错误码或请求 ID，现有 401 的具体子原因仍待验证。[ExecuteRuntime](https://support.huaweicloud.com/api-agentarts/InvokeRuntime1.html) · [InvokeChat](https://support.huaweicloud.com/api-agentarts/InvokeChat.html)

## 恢复联调

1. 在西南-贵阳一打开「智能体运行时 → managed-agent-huawei-cit → 访问方式」，核对当前版本的访问域名及「权限与访问控制」中的入站认证。按运行时的 HTTPS 访问域名启动，可用 `--endpoint` 覆盖本地默认值。
2. IAM 入站使用该云资源所属账号或获授权 IAM 身份的有效 AK/SK。使用临时凭据时，完整提供同一组 AK、SK 和 `HUAWEICLOUD_SDK_SECURITY_TOKEN`。启动时已有环境变量会优先于本机隐藏输入。DeepSeek Key 属于 AgentArts 访问模型的出站配置。
3. 若提示签名时间超出有效窗口，使用 Windows「设置 → 时间和语言 → 日期和时间 → 立即同步」，然后重试。若提示令牌过期，刷新临时凭据。
4. 重启本机服务后，用公开论文复测一次。只记录页面显示的 HTTP 状态、平台错误码和请求 ID。实际账单、托管智能体问答和平台自主工具调用待分别验证。

[Managed Agent InvokeChat](https://support.huaweicloud.com/api-agentarts/InvokeChat.html) · [入站认证](https://support.huaweicloud.com/highcode-agentarts/agentarts_10_227.html) · [401 与签名时间说明](https://support.huaweicloud.com/bestpractice-agentarts/agentarts_06_0023.html)
