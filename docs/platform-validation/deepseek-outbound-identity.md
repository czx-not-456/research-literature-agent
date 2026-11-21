# DeepSeek 出站身份填写说明

日期：2026-11-18。依据：屏幕截图2026-11-18 154613.png、DeepSeek官方调用文档、华为云官方Agent Identity SDK指南与API Key示例。仅为填写指导，未代用户创建身份或读取密钥。

## 当前页面应先切换类型

截图选中“OAuth客户端”，显示自定义提供商、Discovery URL、客户端ID与客户端密钥。DeepSeek官方API使用API Key鉴权，当前任务应选旁边“API Key”类型。
OAuth客户端和IAM委托不是本次DeepSeek API Key接入所需的类型。不能为了通过必填校验虚构OAuth Client ID/Discovery URL。

## 字段填写

| 界面字段 | 填写/操作 |
|---|---|
| 身份名称 | 建议deepseek-api-key，作为平台自定义名称，不是账号ID或模型ID |
| 认证类型 | API Key |
| 切换后出现的API Key/密钥字段 | 填用户在DeepSeek官方平台创建的完整有效API Key原值；不加引号、换行或Bearer前缀 |
| 描述（若实际页面提供） | 可填“供AgentArts调用DeepSeek官方模型使用”，不含Key |
| 客户端ID、客户端密钥、Discovery URL | OAuth模式字段，不填写；切换API Key模式后应依据新表单配置，不把Key塞进OAuth客户端密钥 |
| OAuth提供商/Discovery自定义配置 | 本次无需配置，不虚构DeepSeek OAuth元数据URL |

截图尚未展示API Key标签下的完整表单，上表中“切换后出现”是条件性指导，不能当作已观察到具体控件。若有其他必填项或校验提示，再提供该区域截图并遮住任何已输入的Key。

## 关于Bearer前缀

DeepSeek官方最终HTTP请求要求Authorization: Bearer <API_KEY>。
API Key凭据存储的是原始Key；最终请求头如何组装由当前模型适配/头配置决定，不能把完整Authorization头塞进原始密钥框。
若新页面额外要求请求头配置，再按实际字段区分请求头名称Authorization、Bearer前缀和原始Key；不要在Key里加Bearer后又在前缀栏重复添加。
后续161220截图已显示供应商请求头配置：位置选标头、参数名称Authorization、前缀Bearer；身份里的Key保持原值。实际请求头组装仍待调用核验。

## 创建后的绑定

用户在平台直接填Key并创建身份；不要在聊天、文档、截图、Base_url或提示词中提供Key。
回到模型供应商配置，在实际“出站身份认证”选择处选刚创建的deepseek-api-key；如未显示，使用该页面实际提供的刷新或重新打开选项。
供应商Base_url继续为https://api.deepseek.com，模型API协议为标准OpenAI，模型名称按本轮建议deepseek-flash。身份名称与供应商名称、模型ID是不同对象。
保存身份与绑定不等于真实调用通过；保留实际创建/绑定状态或脱敏错误。此前Playground成功截图仍作为已有证据，不推断该次调用使用本次新身份。

## 官方依据

- https://api-docs.deepseek.com/ ：真实调用示例使用Authorization: Bearer及官方API Key。
- https://github.com/huaweicloud/agentarts-sdk-python/blob/main/docs/cn/sdk_user_guide/agent_identity_guide.md ：区分OAuth2、API Key、STS的凭据流程。
- https://github.com/huaweicloud/agentarts-sdk-python/blob/cba0fd67859941f5c7449b189dd96b57111f4079/examples/agent_identity/api_key_example.ipynb ：create_api_key_credential_provider(name=..., api_key=...)的API Key参数为原值；不执行示例的dummy值、密钥打印或跳过TLS配置。

没有为用户创建任何身份，没有新模型/API调用或费用；仍在阶段二。

新增供应商权限区域的具体填写见 [访问控制填写单](deepseek-provider-access-control.md)。出站身份deepseek-api-key已出现在下拉并被选中，尚无该供应商保存证据。
