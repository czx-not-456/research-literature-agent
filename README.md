# 研读工作台 · 科研文献库

单用户文献库 MVP。可以建立课题，导入中英文 PDF，整理和搜索文献，按 PDF 页码查看原件与提取文本。

在项目根目录用 PowerShell 启动。已存在 `.venv-library` 时可以跳过创建环境。

```powershell
py -3 -m venv .venv-library
.\.venv-library\Scripts\python.exe -m pip install -r requirements.txt
.\.venv-library\Scripts\python.exe -m flask --app research_library run --host 127.0.0.1 --port 5000
```

打开 <http://127.0.0.1:5000/>。先创建课题，再用「导入 PDF」一次多选，或分几次将文件加到同一批待上传列表。上传前可以逐一移除。每批最多 10 份、合计 96 MiB，每份最多 24 MiB、300 页。上传结果会显示新增、重复和失败的数量。在课题标题旁点击「编辑名称」即可重命名。文献详情可修改元数据和分类。搜索会同时匹配文献信息与提取文本，命中原文时可以直接打开对应页。分类在文献详情中填写，随后出现在课题的筛选菜单。

文件和数据默认保存在 `instance/literature.sqlite3`。备份时先停止应用，再复制数据库文件。正常退出以使 SQLite 完成收尾。也可设置 `LITERATURE_DB` 指向独立数据库位置。请在本机回环地址运行此版本，联网部署需要另行设计访问控制。

扫描 PDF 可以保留并查看原件，但当前没有 OCR。自动识别的元数据需核对。缺失年份、作者或 DOI 可以留空，正文页码采用 PDF 的实际页面顺序。

已导入的 PDF 可在课题内打开「批量更新文献」，选择文献并预览，再应用空元数据补齐和自动矩阵候选更新。[使用与验收](docs/design/library-refresh.md)

## 文献问答

打开任一课题的「文献问答」。选择一篇或多篇文献，输入问题并点击「查找原文」。匹配结果可跳转到 PDF 对应页。

如需启用真正的 AgentArts 回答，先用 Ctrl+C 退出上面的服务，然后执行以下命令。默认配置对应西南-贵阳一的 `agent-huawei-cit`。

```powershell
.\.venv-library\Scripts\python.exe -m research_library --agentarts
```

在本机 PowerShell 按提示隐藏输入华为云 AK 和 SK。已通过进程环境配置 `HUAWEICLOUD_SDK_AK` 和 `HUAWEICLOUD_SDK_SK` 时会直接使用，临时凭据还需设置 `HUAWEICLOUD_SDK_SECURITY_TOKEN`。凭据只用于本机服务端签名。打开 <http://127.0.0.1:5000/>，选择「让 AgentArts 回答」。每次提交会向 AgentArts 发送问题和匹配到的摘录，可能产生调用费用。

可用公开论文《Attention Is All You Need》提问 `What is scaled dot product attention?`。本机回归中，相关内容位于 PDF 第 4 页。联网答复与实际用量待使用当前账号验收。[设计与详细验收](docs/design/literature-qa.md)

## 文献对比矩阵

在课题内打开「对比矩阵」，选择文献并点击「从 PDF 提取候选」。可核对引文、修改字段、按字段或是否有证据筛选，并导出 CSV。[功能与验收](docs/design/literature-matrix.md)

## 调研报告

在课题页点击「调研报告」，选择文献生成本地初稿。可以单独保存或重建章节，查看原文证据并下载 Markdown 和 Word。[报告使用与验收](docs/design/literature-report.md)

若 AgentArts 问答返回 HTTP 401，参照运行时域名、入站认证和本机 IAM 配置的核对步骤。[401 联调记录](docs/platform-validation/managed-chat-401.md)

## 在线学术检索

在课题页面点「在线检索」，可查询 Crossref 或 arXiv。勾选结果保存到课题文献库，再按需要上传原 PDF。[检索使用及验收](docs/design/academic-search.md)

运行集成测试：

```powershell
.\.venv-library\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv-library\Scripts\python.exe -B -X utf8 -m unittest discover -v
```

[本阶段设计与验收口径](docs/design/library-mvp.md)
