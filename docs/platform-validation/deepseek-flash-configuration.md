# DeepSeek 官方 Flash：AgentArts 最小验证填写单

日期：2026-11-17。用户确认API来自DeepSeek官方平台，并看到DeepSeek V4.1 Flash与V4.1 Pro。本轮采用Flash作为最小验证建议；正式业务模型选型不在本轮定案。供应商/服务尚未保存，未调用模型。

## 可直接准备的配置

| 界面字段 | 填写值 |
|---|---|
| 提供商名称 | deepseek-provider |
| 提供商描述（可选） | 官方DeepSeek接口，供AgentArts科研文献最小验证使用 |
| Base_url | https://api.deepseek.com |
| 模型服务名称 | deepseek-flash-probe |
| 模型服务描述（可选） | 短文本连通性与后续工具调用验证 |
| 模型名称 | deepseek-flash |
| API接口协议 | 标准OpenAI协议 |
| 模型类型 | 先仅勾选“文本对话/图像理解”合并项 |
| 鉴权凭据 | 官方DeepSeek API Key，由用户直接配置到平台实际鉴权入口 |

不要把https://platform.deepseek.com/usage填入Base_url；这是账号用量页面，不是推理API地址。
不要填完整/chat/completions路径；官方文档Base_url为上述根地址。AgentArts实际路径拼接待实测，报错后核对，不盲改。
页面合并类型不证明实际视觉能力已测，不勾选文本向量化/多模态对话/文本排序/实时语音。

## 显示名和API ID的核对结果

本次复核 [官方模型与价格页](https://api-docs.deepseek.com/quick_start/pricing/)：
- Flash API ID为deepseek-flash，页面版本DeepSeek-V4.1-Flash-1017，与用户Flash系列信息对应。
- 官方页本次仍列Pro API ID为deepseek-v4-pro、版本DeepSeek-V4-Pro-0813；与用户看到的“V4.1 Pro”存在显示/版本差异。未取得账号模型列表实测，不推断新版Pro的ID，更不能自行拼接deepseek-v4.1-pro。
- 本轮不使用Pro；该差异不阻断Flash接入。后续需要Pro时再对照账号实际API模型列表/调用示例。

本次访问记录：evidence/deepseek-confirmed-pricing-access.json；仅证明官方文档内容，不证明用户Key余额/模型权限或平台适配已通过。

## 具体操作顺序

1. 在供应商页填写提供商名称、Base_url与可选描述。
2. 在“添加模型服务”抽屉按表填写名称、模型ID、标准OpenAI协议及文本类型，点该抽屉“确定”，回到供应商表单检查服务行。
3. 按页面实际提供的鉴权方式配置官方Key。当前截图未展示完整凭据区域，不臆造控件名称；若没有找到凭据入口，仅提供相关界面截图并隐藏任何凭据。不要将Key写入Base_url、提示词、描述或聊天。
4. 完成平台实际提供的供应商保存步骤；回模型列表确认提供商与服务状态，再回创建智能体页刷新模型列表。配置保存/列表出现仅为配置阶段证据。
5. 若有真实“测试连接”或“测试模型”入口，只做一轮短文本调用；没有时先记录可见界面，不编造测试按钮，不另建本地Agent取代平台。

建议短文本输入：“请只用一句中文说明你已收到本次连通性测试，不检索文献，不调用外部工具。”
这只是测试输入，不是预设模型结果；必须记录实际返回内容/错误、耗时、usage（如有）。不声称此测试验证科研准确性或Agent工具能力。
若有输出限制，首轮建议设置较小上限（例如128个输出token），具体参数以该界面实际支持为准。若有兼容的额外参数入口，可按DeepSeek官方文档关闭思考模式；提示词不能替代请求级开关，不盲目填写不存在的选项。
本轮不上传论文、不批量调用、不自动循环重试。DeepSeek推理会消耗其账号额度；AgentArts相关资源费用另核查。

## 故障和后续验证边界

- 配置保存失败：保留实际校验或错误提示，不以截图上有模型名称声称已接通。
- 401/403：核查实际凭据、模型权限或平台出网鉴权，不能直接判定Key失效是唯一原因。
- 404：检查最终请求URL及接口/模型ID，不盲加v1、不替换为未核实端点。
- 400及工具阶段错误：检查实际响应及thinking/tool消息字段适配，不一概归为模型不支持工具。
- 429：记录限流/额度提示，停止自动重试并核实。
- 本次仅准备配置；AgentArts创建、编排、部署、官方API与真实文献工具调用仍须独立验收。

下一步所需反馈是保存后的列表状态、实际连接测试结果或脱敏错误。官方来源已确认，不再重复要求用户确认是否第三方API；MaaS是否开通不影响本轮使用已有DeepSeek的配置路线。

## 出站身份配置补充

用户提供的身份创建截图当前选中OAuth客户端。接入已确认的DeepSeek官方API应切换API Key，将原始Key直接保存到平台凭据，再在供应商出站认证处绑定；OAuth Client ID/Secret/Discovery URL不填写。完整步骤见 [出站身份指南](deepseek-outbound-identity.md)。API Key标签下具体字段尚未拍到，创建/绑定未代用户执行。

供应商权限区域现已可见，具体填写见 [访问控制填写单](deepseek-provider-access-control.md)：API Key认证、deepseek-api-key、标头、Authorization、Bearer、公网访问，标签可不加；原始Key只保存在身份中。
