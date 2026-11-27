# AgentArts 多步文献调研验收

## 目标与验收线

复用已通过网页问答的 `agent-huawei-cit`。AgentArts 接收一次公开科研主题，自行选择 Skill、检索期刊论文、从返回候选中选两篇、逐篇核验 DOI，并生成中文简报。任务输出包括已核验书目信息、基于题名或元数据的比较，以及需要全文补证的问题。

本轮工具由 Managed Agent 沙箱借助已挂载 Skill 运行，直接访问 Crossref 公共 HTTPS API。项目已有独立 Crossref MCP 网关的实测证据，Managed Agent 经该网关执行的证据另行验收。[Managed Agents Skill 说明](https://support.huaweicloud.com/managedagents-agentarts/agentarts_13_0011.html) · [运行环境](https://support.huaweicloud.com/managedagents-agentarts/agentarts_13_0013.html)

## 挂载与单次验收

1. 在西南-贵阳一打开「我的资产 → Skill → 导入 → 导入压缩包」，选 [literature-research.zip](literature-research.zip)。包内是 Skill 说明和一个 Python 标准库脚本。[官方导入步骤](https://support.huaweicloud.com/lowcode-agentarts/agentarts_05_0367.html)
2. 打开「Managed Agents → agent-huawei-cit → 编辑 → 工具与 Skill」。选择 `literature-research`，内置工具勾选 `bash` 和 `read_file`。保存后在详情确认 Skill 已关联，核对新版本和运行环境出网模式。若平台出现权限或购买拦截，保存脱敏提示用于确认。参数的实际显示与执行权限以账号页面为准。[内置工具说明](https://support.huaweicloud.com/managedagents-agentarts/agentarts_13_0007.html) · [更新配置和版本](https://support.huaweicloud.com/api-agentarts/UpdateCoreAgent.html)
3. 在项目根目录通过 PowerShell 执行一次探针。服务运行与否均可。终端支持隐藏输入华为云 IAM AK/SK，临时凭据另需配置同组 Security Token。探针输出不包含密钥、签名、原始日志或模型思考。

```powershell
.\.venv-library\Scripts\python.exe -B -X utf8 docs/platform-validation/scripts/probe_agent_workflow.py
```

看到 `status: passed` 时，核对 `steps` 中有成功的 `search` 和同一结果集导出的两条 `verify`。探针依据真实 InvokeChat 的 `chat.tool_call` 与 `chat.tool_result` 配对，通过调用 ID 和候选顺序复核。最终回答的两条 DOI、题名、年份、类型及链接必须与 DOI 核验事件中的元数据一致；比较与补证字段需有内容，比较的语义仍需人工检查。[InvokeChat 事件定义](https://support.huaweicloud.com/api-agentarts/InvokeChat.html)

若返回 `not_verified`，保留终端输出和平台请求 ID（如有）。可在 Playground 输入同类需求并查看该轮工具轨迹。若平台要求批准工具操作，应先确认待执行的是本包的脚本。同一轮任务建议先以 API 验收一次，实际运行时长与模型 Token 可能产生费用。[Skill 计费说明](https://support.huaweicloud.com/managedagents-agentarts/agentarts_13_0011.html)

## 2026-11-24 验证状态

| 检查项 | 结果 |
|---|---|
| 上传 ZIP 文件结构和源文件一致性 | 通过 |
| 从本机解压后的 Skill 调用公开 Crossref | 返回 3 篇期刊论文，并独立核验 DOI `10.21275/sr251104092705` 与 `10.36085/jsai.v9i1.9897` |
| 非法 DOI | 本地拒绝，返回 `invalid_doi` |
| SSE 轨迹及报告核对回归 | 32 项测试通过；错序、伪造年份和缺少调用证据无法通过 |
| 华为云 Skill 挂载、新版本和任务真实执行 | 待账号侧操作与正式输出 |
| 平台工具权限、沙箱实际联网及任务账单 | 待该次云端执行核实 |

本环境无法访问已登录的 AgentArts 控制台，也没有可用 IAM 凭据。云端状态保留待验收。本轮测试覆盖选文和书目证据；多篇全文的报告编排和系统级评估按后续安排执行。


## 首次账号侧实跑与复测

用户实际运行探针后收到请求 ID `630b25eb-9192-4ad0-b850-0526cfdb46e7`，结果为 `not_verified`、`steps: []`。旧探针只记录能识别且配对的脚本结果，因此这份输出不能区分平台没有发出工具调用、命令或输出格式未识别、脚本失败等情形。该次云端验收未通过，保留请求 ID 供复查。

新版探针增加 `diagnostics`，记录已收到的工具事件数、公开的工具名称、可识别脚本调用、未配对调用、终态及回答格式。兼容带目录切换的直接 Python 调用、stdout 包装及最后一段流式 JSON。诊断仅显示固定错误类别与请求 ID。适用的判读方式如下。

- `no_tool_call_event`：先核对当前 `Latest` 绑定版本的「工具与 Skill」是否已保存 `literature-research`、`bash` 和 `read_file`。也可对照该轮请求的对应运行时日志。
- `no_recognized_literature_script_call`：已有工具事件，检查该轮是否读取了 Skill 后执行了对应脚本。
- `script_or_path_not_found`、`python_not_available`、`permission_denied`：查看相应脚本路径、解释器和工具授权。收到 `permission_interrupt` 时核对该工具操作的审批提示。
- `fewer_than_two_verified_dois`：看 `steps` 中具体操作的失败码和未配对计数。完成两条 DOI 核验后，再用最终回答匹配项判定任务是否完整。

本地 35 项自动化测试通过。本次读到的输出来自旧探针。新版账号侧输出及完整工具轨迹仍待验证。[工具与流式事件定义](https://support.huaweicloud.com/api-agentarts/InvokeChat.html)

## 第二次账号侧试跑

请求 ID `b0e86eb1-b18b-4f52-aca6-2ba1d276d202` 返回 3 个 `chat.tool_call`、3 个 `chat.tool_result`，其中按工具名识别出两次 Bash。最终消息为 JSON，模型声明 `complete`。旧探针的识别结果为 0 条匹配 Skill 命令及 0 条核验 DOI。可确认平台发生了工具调用，是否执行了已挂载学术脚本、是否调用了 Crossref，以及 DOI 是否经实际核验，仍缺少工具参数和返回证据。

优先查看同一轮既有日志。在「Managed Agents → agent-huawei-cit → 日志」按请求 ID 查询；如果页面只能按时间定位，选择本轮试跑时间。如果能看到两个 Bash 调用，保留命令名、脚本名、退出或错误状态以及是否有 `LIT_RESEARCH`。平台记录是否保留完整 stdout 以实际账号界面为准。[Managed Agents 日志](https://support.huaweicloud.com/managedagents-agentarts/agentarts_13_0004.html)

当前探针新增 `diagnostics.bash_calls`，只显示命令类别、脚本与 Crossref 主机是否出现、操作标记、是否收到结构化结果和固定错误类别。也会显示 `session_id`（若 SSE 提供），便于定位日志。更新后的任务提示明确要求每次 Bash 只调用一次 Skill 的 search 或 verify；Skill 包和验收条件继续沿用。若已有日志缺少 Bash 细节，可运行一次新版探针，提供 `diagnostics.bash_calls`、`steps` 和请求 ID。36 项本机回归通过，账号侧第二次试跑仍为未通过。

## 第三次账号侧试跑与只读历史查询

请求 ID `255685b8-e227-40ea-b759-1502001b0a9b`，会话 ID `d0a51e66f9dd4b5ab884c503c3cf27ef`。共收到 6 条工具调用事件，其中 3 条 Bash。第 2 条 Bash 提及脚本名，三条均缺少可识别的标准输出，且未发现查询或 DOI 参数。现有证据只确认平台执行过工具、回答到达终态，无法确认该学术脚本或 Crossref 查询实际执行。

探针现可用官方 `ShowChatHistory` 从同一 Agent 按指定会话读取历史，再用原请求 ID 过滤并按时间复核。历史查询只发签名 GET，不发起新的模型对话。工具复查仅输出脱敏分类，例如 `shell_verb: find`，不打印命令原文、路径或内部推理。

```powershell
.\.venv-library\Scripts\python.exe -B -X utf8 docs/platform-validation/scripts/probe_agent_workflow.py --history d0a51e66f9dd4b5ab884c503c3cf27ef --request-id 255685b8-e227-40ea-b759-1502001b0a9b
```

查看 `source: session_history` 的 `history`、`diagnostics.bash_calls` 与 `steps`。当前读取历史的第一页。会话已超时、历史未保存、历史输出截断等情况仍可能缺少详情，应记录返回状态及保留的历史字段。38 项本机测试通过；历史 GET 的实网响应待本机 IAM 查询。[会话历史 API](https://support.huaweicloud.com/api-agentarts/ShowChatHistory.html) · [会话生命周期](https://support.huaweicloud.com/managedagents-agentarts/agentarts_13_0027.html)


## 历史查询终止与最小执行检查

用户使用仅查询模式复查会话 `d0a51e66f9dd4b5ab884c503c3cf27ef`，旧探针报告未识别到结束标记，未取得可用的工具详情。该结果无法定位历史未返回的原因。现在即使正常连接在 `done` 之前关闭，也保留已收到的事件、接受状态和消息计数，标记 `history_stream_incomplete`。不完整历史仍不能用于通过验收。

下一轮先测 Skill 能否启动。这个短任务只要求在云端找到已挂载脚本并执行它的 `--help`，暂不检索或生成简报。

```powershell
.\.venv-library\Scripts\python.exe -B -X utf8 docs/platform-validation/scripts/probe_agent_workflow.py --check-skill
```

只有配对的工具输出包含实际帮助信息，才显示 `skill_available`。失败时按 `diagnostics.failure_reason` 区分未发起 Bash、未观察到帮助命令、Python 不可用、路径找不到或权限拒绝等。检查通过后才继续定位检索与 DOI 核验。40 项本地测试通过，本机脚本已实际输出帮助；云端最小检查仍待账号侧执行。

## Skill 最小检查超时

账号侧运行 --check-skill 后超时，未收到可识别事件、请求 ID 或会话 ID，云端 Skill 是否启动仍待核实。旧探针的 HTTP 响应头与事件流读取共用 30 秒套接字超时，错误输出无法区分两处。

新版将最小检查的套接字等待时间设为 75 秒，事件流回答窗口设为 120 秒。超时输出 diagnostics.transport，包含实测耗时和 timeout_phase。

| timeout_phase | 含义 |
| --- | --- |
| waiting_for_response_headers | 客户端等待 HTTP 响应头时超时。 |
| waiting_for_stream_data | 客户端已收到 HTTP 响应头，随后读取事件流时超时。 |
| response_window_exceeded | 读取事件流时已超过回答时间窗口。 |

若有心跳，只在 diagnostics.events 中计数。对网关根路径发出一次无凭据 HEAD 请求，收到 HTTP 404，TLS 校验成功。对已签名的调用接口及云端 Skill 的验证仍待账号侧复跑。42 项本地测试通过，同时用测试替身核对了 CLI 的超时 JSON、退出码及单次调用行为。

## Skill 检查返回四次 Bash 探索调用

请求 b3b48231-7027-4e2f-8b21-3dc2fb3bfd59 收到四组 Bash 调用及结果事件，按顺序为 ls、find、find、cd，最后收到 chat.final。旧诊断的 missing_structured_stdout 表示未发现工作流期望的结构化输出。目录探索本来就可能返回普通文本，因此该标签无法确认 find 是否找到文件，或 Skill 是否已加载。轨迹中未观察到脚本 --help 调用，云端启动验收仍待完成。

华为云文档说明 Skill 按任务相关性加载，配置关联可在智能体详情的「工具与 Skill」查看，历史版本的 skills 和 allowed_tools 可分别核对。更新后的最小检查用学术检索、DOI 核验和简报场景匹配 Skill 描述，再要求只执行 --help。探针会把 find 输出中的脚本路径记为 skill_script_path_observed，仅保留分类。是否启动仍须以配对的 --help 工具输出为准。[Skill 加载与排查](https://support.huaweicloud.com/managedagents-agentarts/agentarts_13_0011.html) · [版本详情](https://support.huaweicloud.com/api-agentarts/ShowCoreAgentVersion.html)

先在西南-贵阳一核对 Managed Agents → agent-huawei-cit → 基本信息 → 工具与 Skill，并确认当前版本同时关联 literature-research 和 Bash。若页面未关联该 Skill，先从「我的资产 → Skill」确认已有项目包，再在智能体编辑页选取并保存。若已确认关联及版本，用更新后的 --check-skill 复跑一次。

## 已确认关联后的只读复查

用户确认当前运行版本已关联 literature-research 并启用 Bash。请求 00e26db9-7d55-4668-ba19-f8e1eedabf3d 收到两组工具调用及结果，一次 Bash ls 和一次旧探针归类为 other 的工具调用，最后收到 chat.final。已确认版本配置和 Bash 调用。仍未观察到脚本的 --help 执行。旧输出没有留下另一工具的名字或其结果中的文件名。

用以下命令只读复查既有会话：

```powershell
.\.venv-library\Scripts\python.exe -B -X utf8 docs/platform-validation/scripts/probe_agent_workflow.py --history e202e2bbc9954d1083d71145c444b51b --request-id 00e26db9-7d55-4668-ba19-f8e1eedabf3d --check-skill
```

该模式调用历史 GET，按原请求 ID 回放工具事件。优先查看 diagnostics.non_bash_calls、diagnostics.bash_calls 和 history.messages_reviewed。工具名取自协议的 name 字段，可用于定位的一组固定文件名仅记录是否出现。结果中的名称可能出现在错误文本，需结合配对状态和失败分类判断。若会话过期或接口未返回该请求的消息，现有输出无法还原未识别工具，须保留当前阶段状态。[ShowChatHistory](https://support.huaweicloud.com/api-agentarts/ShowChatHistory.html) · [InvokeChat](https://support.huaweicloud.com/api-agentarts/InvokeChat.html)

## 首次会话复查识别 skill_tool

会话历史返回 10 条 history.message，其中本次请求有 2 条工具调用、2 条工具结果、1 条最终响应。工具调用识别为 skill_tool 和 Bash ls。旧回放未配对两条结果，历史未收到官方定义的 done 标记。已确认调用过 skill_tool，仍待核对它的返回内容及脚本是否能启动。

官方记录按从新到旧发送，工具调用和结果使用 tool_call_id 关联。最小 Skill 检查回放先登记同一请求中的调用，再匹配结果。读取嵌套结果字段，并在必要时从外层取得调用 ID；仅在同一请求存在相同 ID 时补全省略的工具名。未收到 done 时继续保留未验收状态。全量本地回归 45 项通过。使用上一节的只读命令复查，查看 non_bash_calls、bash_calls 和 history.tool_result_fields。字段齐全并配对后，才可利用固定文件名提示判断下一处需要核实的配置。[ShowChatHistory 事件结构与字段](https://support.huaweicloud.com/api-agentarts/ShowChatHistory.html)

## 旧会话无消息，改用实时 Skill 检查

再次只读查询会话 e202e2bbc9954d1083d71145c444b51b 时，返回 0 条历史消息和 1 条其他事件，未收到 done。该响应中没有可重新配对的调用。会话数据受生命周期限制；这份响应没有提供足以确认原因的错误码。[会话超时说明](https://support.huaweicloud.com/agentarts_faq/agentarts_09_0081.html)

--check-skill 现在要求按 Skill 加载工具返回的目录或 SKILL.md 路径只执行一次 --help。若没有可用路径，返回枚举 skill_location_unavailable，停止猜测目录。探针直接读取本轮实时事件，记录非 Bash 工具的配对情况和工具状态错误；模型最终报告的停点保存在 agent_reported_outcome，只作诊断提示。唯一的启动通过依据仍是配对的 Bash 帮助输出。无需回查旧会话。

```powershell
.\.venv-library\Scripts\python.exe -B -X utf8 docs/platform-validation/scripts/probe_agent_workflow.py --check-skill
```

验收状态保留为待云端实测。若实时结果标为 skill_load_failed，查看 diagnostics.non_bash_calls 中的工具错误；若标为 skill_location_unavailable，需核对平台 Skill 详情中的脚本文件可见性及加载工具能否提供可用路径，再决定接入处理。仅在 skill_available 后继续 Crossref 检索和 DOI 核验。

## 最后一次实时检查与验收阻塞

请求 36234302-e8f0-4b40-a645-fd7564c08d18 完成流式响应。skill_tool 有配对结果，结果中出现 literature-research。该轮没有 Bash 调用，也没有脚本帮助输出。智能体自行报告 skill_load_failed，探针依据事件输出 no_bash_call_event。智能体报告可用于定位，现有工具摘要未提供具体平台错误码，Skill 加载停住的原因尚未证实。

按约定结束本轮排查。AgentArts 云端学术工具验收标记为阻塞，仍待验证脚本启动、Crossref 检索与两条 DOI 核验。用户已确认暂缓该项云端验收，并推进可独立验证的系统测试。[系统测试记录](../system-testing/acceptance-results.md)
