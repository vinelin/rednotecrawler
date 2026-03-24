# ===== Playwright 浏览器管理模块 =====
# 负责启动浏览器、注入反检测脚本、管理 Cookie 登录态

import os           # 操作系统模块，用于路径操作
import json         # JSON 模块，用于解析 Cookie 字符串
from playwright.sync_api import sync_playwright, Page, Browser, BrowserContext  # Playwright 核心类
from loguru import logger  # 日志记录器


class BrowserManager:
    """
    浏览器管理器。
    功能：
    1. 启动 Chromium 浏览器（支持有头/无头模式）
    2. 注入 stealth.min.js 反检测脚本
    3. 从 Cookie 字符串注入登录态
    4. 提供页面实例供爬虫模块使用
    """

    # 小红书主站域名
    BASE_URL = "https://www.xiaohongshu.com"

    def __init__(self, cookie: str, headless: bool = True,
                 viewport_width: int = 1920, viewport_height: int = 1080):
        """
        初始化浏览器管理器。
        参数:
            cookie: 从浏览器复制的完整 Cookie 字符串
            headless: 是否使用无头模式（True=不显示浏览器窗口）
            viewport_width: 浏览器视口宽度
            viewport_height: 浏览器视口高度
        """
        self.cookie = cookie              # Cookie 字符串
        self.headless = headless          # 无头模式开关
        self.viewport_width = viewport_width    # 视口宽度
        self.viewport_height = viewport_height  # 视口高度
        self.playwright = None            # Playwright 实例（延迟初始化）
        self.browser: Browser = None      # 浏览器实例
        self.context: BrowserContext = None  # 浏览器上下文（隔离的会话）
        self.page: Page = None            # 页面实例

    def _parse_cookie_string(self, cookie_str: str) -> list[dict]:
        """
        将浏览器复制的 Cookie 字符串解析为 Playwright 格式的 Cookie 列表。
        输入格式: "key1=value1; key2=value2; ..."
        输出格式: [{"name": "key1", "value": "value1", "domain": ".xiaohongshu.com", ...}, ...]
        
        参数:
            cookie_str: 原始 Cookie 字符串
        返回:
            Playwright 格式的 Cookie 字典列表
        """
        # 初始化结果列表
        cookies = []
        # 按分号分割 Cookie 字符串，逐个处理
        for item in cookie_str.split(";"):
            # 去除首尾空格
            item = item.strip()
            # 跳过空字符串
            if not item:
                continue
            # 按第一个等号分割键值对（值中可能包含等号）
            if "=" in item:
                name, value = item.split("=", 1)  # 最多分割 1 次
                # 构建 Playwright 格式的 Cookie 字典
                cookies.append({
                    "name": name.strip(),           # Cookie 名称
                    "value": value.strip(),          # Cookie 值
                    "domain": ".xiaohongshu.com",    # 作用域名
                    "path": "/",                     # 作用路径
                })
        # 返回解析后的 Cookie 列表
        return cookies

    def start(self):
        """
        启动浏览器并完成初始化。
        流程：启动 Playwright → 创建浏览器 → 注入反检测脚本 → 注入 Cookie → 访问首页
        优先使用 Playwright 自带 Chromium，如果没安装则回退到系统已安装的 Chrome。
        """
        # 记录启动日志
        logger.info("正在启动浏览器...")

        # 启动 Playwright 运行时
        self.playwright = sync_playwright().start()

        # 浏览器启动参数
        launch_args = [
            "--disable-blink-features=AutomationControlled",  # 禁用自动化检测标志
            "--no-sandbox",                                    # 禁用沙盒（提升兼容性）
        ]

        try:
            # 优先尝试启动 Playwright 自带的 Chromium
            self.browser = self.playwright.chromium.launch(
                headless=self.headless,  # 是否无头模式
                args=launch_args
            )
            logger.info("使用 Playwright 内置 Chromium")
        except Exception as e:
            # Playwright Chromium 未安装（下载失败时会走到这里）
            logger.warning(f"Playwright Chromium 未安装: {e}")
            logger.info("回退到系统已安装的 Chrome 浏览器...")
            try:
                # 使用 channel="chrome" 启动系统 Chrome
                self.browser = self.playwright.chromium.launch(
                    channel="chrome",        # 使用系统 Chrome
                    headless=self.headless,
                    args=launch_args
                )
                logger.info("使用系统 Chrome 浏览器 ✓")
            except Exception as e2:
                # Chrome 也找不到，尝试 Edge
                logger.warning(f"系统 Chrome 未找到: {e2}")
                logger.info("尝试使用 Microsoft Edge...")
                self.browser = self.playwright.chromium.launch(
                    channel="msedge",        # 使用系统 Edge
                    headless=self.headless,
                    args=launch_args
                )
                logger.info("使用 Microsoft Edge 浏览器 ✓")

        # 创建浏览器上下文（相当于一个隔离的浏览器会话）
        self.context = self.browser.new_context(
            viewport={                              # 设置视口大小
                "width": self.viewport_width,
                "height": self.viewport_height
            },
            user_agent=(                            # 设置 User-Agent 伪装为正常 Chrome 浏览器
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        )

        # ----- 注入 stealth.min.js 反检测脚本 -----
        # 该脚本会在每个页面加载前执行，隐藏 Playwright 的自动化特征
        stealth_js_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),  # 项目根目录
            "scripts", "stealth.min.js"                   # 脚本路径
        )
        # 检查反检测脚本是否存在
        if os.path.exists(stealth_js_path):
            # 读取脚本内容
            with open(stealth_js_path, "r", encoding="utf-8") as f:
                stealth_js = f.read()
            # 注入到浏览器上下文（每个新页面都会自动执行）
            self.context.add_init_script(stealth_js)
            logger.info("已注入 stealth.min.js 反检测脚本")
        else:
            # 脚本不存在时输出警告
            logger.warning(f"未找到反检测脚本: {stealth_js_path}，跳过注入")

        # ----- 注入 Cookie 登录态 -----
        if self.cookie:
            # 解析 Cookie 字符串为 Playwright 格式
            cookies = self._parse_cookie_string(self.cookie)
            # 批量添加 Cookie 到浏览器上下文
            self.context.add_cookies(cookies)
            logger.info(f"已注入 {len(cookies)} 条 Cookie")
        else:
            # 没有提供 Cookie 时输出警告
            logger.warning("未提供 Cookie，将以未登录状态运行（功能受限）")

        # 创建新页面
        self.page = self.context.new_page()

        # 访问小红书首页，触发 Cookie 生效
        logger.info("正在访问小红书首页...")
        self.page.goto(self.BASE_URL, wait_until="domcontentloaded")  # 等待 DOM 加载完成

        # 等待页面稳定（给 JS 一些执行时间）
        self.page.wait_for_timeout(3000)  # 等待 3 秒

        logger.info("浏览器启动完成 ✓")

    def get_page(self) -> Page:
        """
        获取当前页面实例。
        返回:
            Playwright 的 Page 对象，供爬虫模块使用
        """
        return self.page

    def close(self):
        """
        关闭浏览器并释放资源。
        按顺序关闭：上下文 → 浏览器 → Playwright 运行时
        """
        logger.info("正在关闭浏览器...")
        try:
            # 关闭浏览器上下文
            if self.context:
                self.context.close()
            # 关闭浏览器
            if self.browser:
                self.browser.close()
            # 停止 Playwright 运行时
            if self.playwright:
                self.playwright.stop()
            logger.info("浏览器已关闭 ✓")
        except Exception as e:
            # 捕获关闭过程中的异常，避免程序崩溃
            logger.error(f"关闭浏览器时出错: {e}")

    def screenshot(self, filename: str = "screenshot.png"):
        """
        截取当前页面截图（调试用）。
        参数:
            filename: 截图保存的文件名
        """
        # 构建截图保存路径（保存在项目根目录的 screenshots 目录下）
        path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "screenshots", filename
        )
        # 确保截图目录存在
        os.makedirs(os.path.dirname(path), exist_ok=True)
        # 执行截图
        self.page.screenshot(path=path, full_page=True)  # full_page=True 截取完整页面
        logger.info(f"截图已保存: {path}")
