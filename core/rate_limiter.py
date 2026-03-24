# ===== 请求限速与重试模块 =====
# 控制爬虫请求频率，防止触发小红书反爬机制

import time    # 时间模块，用于 sleep 暂停
import random  # 随机数模块，用于生成随机延迟
from loguru import logger  # 日志记录器


class RateLimiter:
    """
    请求限速器。
    功能：
    1. 每次请求前随机等待 delay_min ~ delay_max 秒
    2. 检测到风控时自动暂停指定时长
    3. 支持指数退避重试
    """

    def __init__(self, delay_min: float = 5, delay_max: float = 12,
                 block_pause: int = 60, max_retries: int = 3):
        """
        初始化限速器。
        参数:
            delay_min: 最小请求间隔（秒）
            delay_max: 最大请求间隔（秒）
            block_pause: 检测到风控时的暂停时长（秒）
            max_retries: 最大重试次数
        """
        self.delay_min = delay_min      # 最小延迟时间
        self.delay_max = delay_max      # 最大延迟时间
        self.block_pause = block_pause  # 风控暂停时长
        self.max_retries = max_retries  # 最大重试次数
        self.request_count = 0          # 请求计数器（统计总请求次数）
        self.last_request_time = 0      # 上次请求的时间戳

    def wait(self):
        """
        在发送请求前调用，执行随机延迟等待。
        延迟时间在 [delay_min, delay_max] 之间随机取值。
        """
        # 生成随机等待时长
        delay = random.uniform(self.delay_min, self.delay_max)
        # 记录日志，显示等待时长（保留1位小数）
        logger.debug(f"限速等待 {delay:.1f} 秒...")
        # 执行等待
        time.sleep(delay)
        # 更新上次请求时间为当前时间
        self.last_request_time = time.time()
        # 请求计数器加 1
        self.request_count += 1

    def on_blocked(self):
        """
        检测到被风控时调用（如收到 403 状态码或验证码页面）。
        暂停较长时间后再继续。
        """
        # 记录警告日志
        logger.warning(f"检测到风控！暂停 {self.block_pause} 秒后继续...")
        # 执行较长时间的暂停
        time.sleep(self.block_pause)
        # 记录恢复日志
        logger.info("风控暂停结束，恢复爬取")

    def should_retry(self, attempt: int) -> bool:
        """
        判断是否应该重试。
        参数:
            attempt: 当前尝试次数（从 0 开始）
        返回:
            True 表示应该重试，False 表示放弃
        """
        # 如果当前尝试次数未超过最大重试次数
        if attempt < self.max_retries:
            # 计算指数退避等待时间：2^attempt 秒（1秒, 2秒, 4秒...）
            backoff = 2 ** attempt
            # 记录重试日志
            logger.warning(f"第 {attempt + 1}/{self.max_retries} 次重试，等待 {backoff} 秒...")
            # 执行退避等待
            time.sleep(backoff)
            # 返回 True 表示继续重试
            return True
        # 超过最大重试次数，记录错误日志
        logger.error(f"已达到最大重试次数 ({self.max_retries})，放弃请求")
        # 返回 False 表示放弃
        return False

    def get_stats(self) -> dict:
        """
        获取限速器统计信息。
        返回:
            包含总请求数和运行时长的字典
        """
        return {
            "total_requests": self.request_count,  # 总请求次数
        }
