# ===== 小红书达人爬虫 - 统一入口 =====
# 一键运行全流程：搜索 → 采集主页 → 采集笔记 → 评估 → 启动 Web 面板

import os       # 操作系统模块
import sys      # 系统模块
import yaml     # YAML 配置文件解析
import subprocess  # 子进程模块（用于启动 Streamlit）
from loguru import logger  # 日志记录器

# 将项目根目录添加到 Python 路径
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))  # 获取当前文件所在目录的绝对路径
sys.path.insert(0, PROJECT_ROOT)  # 添加到 Python 模块搜索路径

from core.browser import BrowserManager        # 浏览器管理器
from core.client import XHSClient               # API 客户端
from core.rate_limiter import RateLimiter       # 限速器
from models.database import Database            # 数据库
from crawlers.search import SearchCrawler       # 搜索爬虫
from crawlers.user_profile import UserProfileCrawler  # 用户主页爬虫
from crawlers.note_detail import NoteDetailCrawler    # 笔记详情爬虫
from analysis.evaluator import Evaluator        # 达人评估器
from export.exporter import Exporter            # 数据导出器


def load_config() -> dict:
    """
    加载配置文件。
    从 config/settings.yaml 读取所有配置项。
    返回:
        配置字典
    """
    # 构建配置文件路径
    config_path = os.path.join(PROJECT_ROOT, "config", "settings.yaml")

    # 检查配置文件是否存在
    if not os.path.exists(config_path):
        logger.error(f"配置文件不存在: {config_path}")
        logger.info("请先编辑 config/settings.yaml 并填入你的 Cookie")
        sys.exit(1)  # 退出程序

    # 读取并解析 YAML 配置文件
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)  # 安全解析 YAML

    # 记录配置加载日志
    logger.info("配置文件加载成功 ✓")
    return config


def validate_config(config: dict):
    """
    校验配置文件的必要字段。
    参数:
        config: 配置字典
    """
    # 检查 Cookie 是否已填写
    if not config.get("cookie"):
        logger.error("❌ 请在 config/settings.yaml 中填入你的小红书 Cookie")
        logger.info("获取方式: 浏览器登录小红书 → F12 打开 DevTools → Application → Cookies")
        sys.exit(1)  # 退出程序

    # 检查关键词列表
    if not config.get("keywords"):
        logger.warning("未配置搜索关键词，将使用默认关键词")
        config["keywords"] = ["亚文化"]  # 设置默认值

    logger.info("配置校验通过 ✓")


def run_crawler(config: dict):
    """
    执行完整的爬虫流程。
    流程：启动浏览器 → 搜索达人 → 采集主页 → 采集笔记 → 关闭浏览器
    参数:
        config: 配置字典
    """
    # 初始化数据库
    db = Database(config.get("db_path", "data/db/xiaohongshu.db"))

    # 初始化限速器
    rate_limiter = RateLimiter(
        delay_min=config.get("delay_min", 5),      # 最小延迟
        delay_max=config.get("delay_max", 12),     # 最大延迟
        block_pause=config.get("block_pause", 60),  # 风控暂停时长
        max_retries=config.get("max_retries", 3)    # 最大重试次数
    )

    # 初始化浏览器管理器
    browser_manager = BrowserManager(
        cookie=config.get("cookie", ""),
        headless=config.get("headless", True),
        viewport_width=config.get("viewport_width", 1920),
        viewport_height=config.get("viewport_height", 1080)
    )

    try:
        # ===== 步骤 1: 启动浏览器 =====
        logger.info("=" * 50)
        logger.info("步骤 1/5: 启动浏览器")
        logger.info("=" * 50)
        browser_manager.start()

        # 获取页面实例
        page = browser_manager.get_page()
        # 创建 API 客户端
        client = XHSClient(page, rate_limiter)

        # ===== 步骤 2: 搜索达人 =====
        logger.info("=" * 50)
        logger.info("步骤 2/5: 搜索达人")
        logger.info("=" * 50)
        # 创建搜索爬虫
        search_crawler = SearchCrawler(
            client=client,
            keywords=config.get("keywords", ["亚文化"]),
            limit=config.get("limit", 50)
        )
        # 执行搜索，获取用户 ID 列表
        user_ids = search_crawler.search()

        # 如果没有找到达人，提前退出
        if not user_ids:
            logger.warning("未搜索到任何达人，请检查关键词和 Cookie 是否有效")
            return

        # ===== 步骤 3: 采集达人主页 =====
        logger.info("=" * 50)
        logger.info("步骤 3/5: 采集达人主页信息")
        logger.info("=" * 50)
        # 创建用户主页爬虫
        user_crawler = UserProfileCrawler(
            client=client,
            db=db,
            images_dir=config.get("images_dir", "data/images")
        )
        # 执行采集
        users = user_crawler.crawl(user_ids)

        # ===== 步骤 4: 采集达人笔记 =====
        logger.info("=" * 50)
        logger.info("步骤 4/5: 采集达人笔记详情")
        logger.info("=" * 50)
        # 创建笔记详情爬虫
        note_crawler = NoteDetailCrawler(
            client=client,
            db=db,
            notes_per_user=config.get("notes_per_user", 20),
            images_dir=config.get("images_dir", "data/images")
        )
        # 仅采集成功获取主页信息的达人的笔记
        successful_ids = [u["user_id"] for u in users]
        note_crawler.crawl(successful_ids)

        # ===== 步骤 5: 评估达人 =====
        logger.info("=" * 50)
        logger.info("步骤 5/5: 评估达人并生成评分")
        logger.info("=" * 50)
        evaluator = Evaluator(db)
        results = evaluator.evaluate_all()

        # 导出 Excel 报告
        exporter = Exporter(db, config.get("export_dir", "data/exports"))
        excel_path = exporter.export_excel()
        logger.info(f"Excel 报告已生成: {excel_path}")

        # 输出统计摘要
        logger.info("=" * 50)
        logger.info("🎉 爬取流程全部完成！")
        logger.info(f"  已采集达人: {len(users)}")
        logger.info(f"  已采集笔记: {db.get_note_count()}")
        logger.info(f"  S级推荐: {sum(1 for r in results if r['grade'] == 'S')}")
        logger.info(f"  A级推荐: {sum(1 for r in results if r['grade'] == 'A')}")
        logger.info(f"  Excel 报告: {excel_path}")
        logger.info("=" * 50)

    except KeyboardInterrupt:
        # 用户按 Ctrl+C 中断
        logger.info("用户中断爬取流程")
    except Exception as e:
        # 其他异常
        logger.error(f"爬取流程出错: {e}")
        import traceback
        traceback.print_exc()  # 打印完整错误堆栈
    finally:
        # 无论如何都关闭浏览器
        browser_manager.close()
        # 输出限速器统计
        logger.info(f"请求统计: {rate_limiter.get_stats()}")


def start_web():
    """
    启动 Streamlit Web 可视化面板。
    """
    # 构建 web/app.py 的绝对路径
    app_path = os.path.join(PROJECT_ROOT, "web", "app.py")
    logger.info(f"正在启动 Web 面板: {app_path}")
    # 使用 subprocess 启动 Streamlit
    subprocess.run([
        sys.executable, "-m", "streamlit", "run",  # python -m streamlit run
        app_path,                                    # 应用入口文件
        "--server.port", "8501",                    # 监听端口
        "--server.headless", "true",                # 无头模式（不自动打开浏览器）
        "--browser.gatherUsageStats", "false",      # 禁止收集使用统计
    ])


def main():
    """
    主函数 - 程序入口。
    支持两种模式：
    1. python main.py          → 执行完整爬虫流程 + 启动 Web 面板
    2. python main.py --web-only → 仅启动 Web 面板（查看已有数据）
    """
    # 打印欢迎信息
    print()
    print("=" * 50)
    print("  📕 小红书亚文化达人爬虫 & 评估系统")
    print("=" * 50)
    print()

    # 解析命令行参数
    web_only = "--web-only" in sys.argv  # 是否仅启动 Web 面板

    if web_only:
        # 仅启动 Web 面板模式
        logger.info("模式: 仅启动 Web 面板")
        start_web()
    else:
        # 完整流程模式
        logger.info("模式: 完整爬取流程")

        # 加载配置
        config = load_config()
        # 校验配置
        validate_config(config)
        # 执行爬虫
        run_crawler(config)

        # 爬取完成后，询问是否启动 Web 面板
        print()
        choice = input("是否启动 Web 可视化面板查看结果？(y/n): ").strip().lower()
        if choice in ["y", "yes", ""]:
            start_web()
        else:
            logger.info("程序结束。你可以随时运行 'python main.py --web-only' 查看数据")


# 程序入口点
if __name__ == "__main__":
    main()
