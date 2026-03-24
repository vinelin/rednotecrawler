# ===== 日志工具模块 =====
# 基于 loguru 库，提供统一的日志输出（控制台 + 文件）

import sys  # 系统模块，用于获取标准输出流
import os   # 操作系统模块，用于文件路径操作
from loguru import logger  # 导入 loguru 的 logger 实例


def setup_logger():
    """
    配置并初始化日志系统。
    - 控制台输出：彩色格式，INFO 级别
    - 文件输出：保存到 logs/ 目录，按天轮转，保留 7 天
    """
    # 移除 loguru 默认的日志处理器（避免重复输出）
    logger.remove()

    # 定义日志格式模板
    # {time} = 时间戳, {level} = 日志级别, {message} = 日志内容
    # {name}:{function}:{line} = 文件名:函数名:行号
    log_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "  # 绿色时间戳
        "<level>{level: <8}</level> | "                   # 带颜色的级别标签
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:"    # 青色的文件名和函数名
        "<cyan>{line}</cyan> - "                          # 青色的行号
        "<level>{message}</level>"                        # 带颜色的日志内容
    )

    # 添加控制台处理器：输出到标准输出流，INFO 级别及以上
    logger.add(
        sys.stdout,          # 输出目标：控制台
        format=log_format,   # 使用自定义格式
        level="INFO",        # 最低输出级别
        colorize=True        # 启用彩色输出
    )

    # 确保日志目录存在
    log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")  # 项目根目录/logs
    os.makedirs(log_dir, exist_ok=True)  # 目录不存在则创建

    # 添加文件处理器：输出到日志文件，按天轮转
    logger.add(
        os.path.join(log_dir, "crawler_{time:YYYY-MM-DD}.log"),  # 日志文件路径，按日期命名
        format=log_format,   # 使用自定义格式
        level="DEBUG",       # 文件记录 DEBUG 及以上所有级别
        rotation="00:00",    # 每天午夜轮转新文件
        retention="7 days",  # 日志文件保留 7 天
        encoding="utf-8",    # 使用 UTF-8 编码（支持中文）
        enqueue=True         # 异步写入，避免阻塞主线程
    )

    # 返回配置好的 logger 实例
    return logger


# 模块加载时自动初始化日志系统
setup_logger()
