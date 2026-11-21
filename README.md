# 研读工作台 · 科研文献库

单用户文献库 MVP。可以建立课题，导入中英文 PDF，整理和搜索文献，按 PDF 页码查看原件与提取文本。

在项目根目录用 PowerShell 启动。已存在 `.venv-library` 时可以跳过创建环境。

```powershell
py -3 -m venv .venv-library
.\.venv-library\Scripts\python.exe -m pip install -r requirements.txt
.\.venv-library\Scripts\python.exe -m flask --app research_library run --host 127.0.0.1 --port 5000
```

打开 <http://127.0.0.1:5000/>。先创建课题，然后导入 PDF。每份最多 24 MiB、300 页。文献详情可修改元数据和分类。搜索会同时匹配文献信息与提取文本，命中原文时可以直接打开对应页。分类在文献详情中填写，随后出现在课题的筛选菜单。

文件和数据默认保存在 `instance/literature.sqlite3`。备份时先停止应用，再复制数据库文件。正常退出以使 SQLite 完成收尾。也可设置 `LITERATURE_DB` 指向独立数据库位置。请在本机回环地址运行此版本，联网部署需要另行设计访问控制。

扫描 PDF 可以保留并查看原件，但当前没有 OCR。自动识别的元数据需核对。缺失年份、作者或 DOI 可以留空，正文页码采用 PDF 的实际页面顺序。

运行集成测试：

```powershell
.\.venv-library\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv-library\Scripts\python.exe -B -X utf8 -m unittest discover -v
```

[本阶段设计与验收口径](docs/design/library-mvp.md)
