## 项目概述
- **名称**: 双语术语可读性优化工作流
- **功能**: 对中英双语专业术语语料库进行「修改前 vs 修改后」的对比分析，将生僻英语词汇替换为东南亚非母语者更易理解的高频基础词汇，生成交互式对比网页并上传至对象存储
- **项目类型**: Python Workflow (LangGraph)
- **运行时**: Python 3.12 + FastAPI + LangGraph
- **包管理**: uv
- **部署类型**: service / workflow

## 目录结构
```
.
├── .coze                    # 项目配置
├── .preview                 # 预览端口配置
├── pyproject.toml           # Python 依赖声明
├── uv.lock                  # 依赖锁文件
├── config/                  # LLM 配置文件
│   └── simplify_terms_llm_cfg.json
├── scripts/                 # 部署与运行脚本
│   ├── setup.sh             # 依赖安装
│   ├── http_run.sh          # HTTP 服务启动（端口 5000）
│   ├── local_run.sh         # 本地运行
│   ├── pack.sh              # 依赖打包
│   └── load_env.py/sh       # 环境变量加载
├── src/
│   ├── main.py              # FastAPI 入口
│   ├── graphs/
│   │   ├── graph.py         # LangGraph 工作流定义
│   │   ├── state.py         # 状态定义
│   │   └── nodes/           # 工作流节点
│   │       ├── read_excel_node.py
│   │       ├── simplify_terms_node.py
│   │       ├── generate_html_node.py
│   │       └── upload_storage_node.py
│   ├── storage/             # 存储层（S3、数据库、内存）
│   ├── utils/               # 工具函数
├── static/
│   └── preview.html         # 预览界面
```

## 结构说明
本项目为单层结构，所有配置文件位于项目根目录。

## 运行与预览
- **运行方式**: `bash scripts/http_run.sh -p 5000` 启动 HTTP 服务
- **本地运行**: `bash scripts/local_run.sh -m flow` 运行完整工作流
- **预览**: 通过 FastAPI 根路由(/) serve 交互式预览界面，支持上传 Excel 文件并触发工作流
- **依赖安装**: `bash scripts/setup.sh`（使用 uv）