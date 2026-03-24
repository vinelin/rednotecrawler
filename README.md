# 📕 小红书亚文化达人爬虫 & 评估系统

自动采集小红书亚文化领域达人数据，多维度评分，Web 可视化面板展示。

## 功能

- 🔍 **关键词搜索**: 按亚文化关键词搜索达人（JK/Lolita/汉服/cosplay 等）
- 👤 **达人采集**: 头像、粉丝数、简介、认证等完整主页数据
- 📝 **笔记采集**: 近 20 篇笔记的互动数据、封面图、标签
- 📊 **智能评分**: 6 维度综合评分（互动率/内容质量/粉丝量级/领域匹配/更新频率/商业比例）
- 🏆 **合作推荐**: S/A/B/C/D 五级推荐等级
- 🖥️ **Web 面板**: Streamlit 仪表盘（排行榜/雷达图/笔记封面/一键导出）
- 📥 **Excel 导出**: 多 Sheet 报告（评分排行 + 达人列表 + 笔记明细）

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
playwright install chromium
```

### 2. 配置 Cookie

编辑 `config/settings.yaml`，填入你的小红书 Cookie:

```yaml
cookie: "你的完整Cookie字符串"
```

**获取方式**: 浏览器登录 xiaohongshu.com → F12 → Application → Cookies → 复制所有值

### 3. 运行

```bash
# 一键爬取 + 评估 + 启动面板
python main.py

# 仅查看已有数据
python main.py --web-only
```

## 项目结构

```
├── config/settings.yaml     # 配置文件
├── core/                    # 核心引擎（浏览器/客户端/限速）
├── crawlers/                # 爬虫模块（搜索/主页/笔记）
├── models/                  # 数据模型（Pydantic + SQLAlchemy）
├── analysis/                # 评估算法
├── export/                  # 数据导出
├── web/                     # Streamlit 面板
├── data/                    # 数据存储（数据库 + 图片）
└── main.py                  # 统一入口
```

## ⚠️ 免责声明

本项目仅供学习交流使用，请遵守小红书用户协议和相关法律法规。仅采集公开数据，请控制请求频率。使用者需自行承担法律风险。
