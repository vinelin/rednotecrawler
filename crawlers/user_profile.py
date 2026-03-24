# ===== 用户主页爬虫模块 =====
# 通过导航到用户主页，拦截 API 响应采集达人信息，并下载头像

import os       # 操作系统模块，用于路径操作
import httpx    # HTTP 客户端，用于下载图片
from loguru import logger          # 日志记录器
from core.client import XHSClient  # 小红书 API 客户端
from models.database import Database  # 数据库操作类


class UserProfileCrawler:
    """
    用户主页爬虫。
    功能：
    1. 导航到用户主页，拦截 API 响应获取信息
    2. 解析并保存达人基本资料
    3. 下载头像图片到本地
    """

    def __init__(self, client: XHSClient, db: Database, images_dir: str = "data/images"):
        """
        初始化用户主页爬虫。
        参数:
            client: XHS API 客户端实例
            db: 数据库实例
            images_dir: 图片保存根目录
        """
        self.client = client      # API 客户端
        self.db = db              # 数据库
        self.images_dir = images_dir  # 图片保存目录
        # 获取项目根目录的绝对路径
        self.project_root = os.path.dirname(os.path.dirname(__file__))
        # 构建头像保存目录的绝对路径
        self.avatar_dir = os.path.join(self.project_root, images_dir, "avatars")
        # 确保头像目录存在
        os.makedirs(self.avatar_dir, exist_ok=True)

    def crawl(self, user_ids: list) -> list:
        """
        批量采集达人主页信息。
        参数:
            user_ids: 用户 ID 列表
        返回:
            成功采集的用户数据字典列表
        """
        # 记录开始日志
        logger.info(f"开始采集 {len(user_ids)} 位达人主页信息...")
        # 存储成功采集的用户数据
        results = []
        # 遍历每个用户 ID
        for index, user_id in enumerate(user_ids, 1):
            # 输出进度日志
            logger.info(f"[{index}/{len(user_ids)}] 正在采集达人: {user_id}")
            # 采集单个用户信息
            user_data = self._crawl_single_user(user_id)
            # 如果采集成功
            if user_data:
                # 保存到数据库
                self.db.save_user(user_data)
                # 添加到结果列表
                results.append(user_data)
                # 记录成功日志
                logger.info(f"  ✓ {user_data.get('nickname', '未知')} - "
                           f"粉丝: {user_data.get('fans_count', 0)}")
            else:
                # 采集失败日志
                logger.warning(f"  ✗ 采集失败: {user_id}")

        # 记录完成日志
        logger.info(f"达人主页采集完成: 成功 {len(results)}/{len(user_ids)}")
        return results

    def _crawl_single_user(self, user_id: str) -> dict:
        """
        采集单个达人的主页信息。
        通过导航到用户主页，拦截 otherinfo API 响应获取数据。
        参数:
            user_id: 用户 ID
        返回:
            解析后的用户数据字典，失败返回 None
        """
        try:
            # 调用客户端获取用户信息（会导航到用户主页并拦截响应）
            result = self.client.get_user_info(user_id)

            # 检查响应是否有效
            if not result:
                logger.warning(f"获取用户信息失败: {user_id}")
                # 尝试从页面 DOM 中提取基本信息作为备用
                return self._crawl_from_dom(user_id)

            # 提取 data 字段
            data = result.get("data", result)

            # 基本信息可能在 basic_info 字段中，也可能直接在 data 中
            basic_info = data.get("basic_info", data)

            # 互动数据在 interactions 列表中
            interactions = data.get("interactions", [])

            # 标签在 tags 列表中
            tags_list = data.get("tags", [])

            # 解析互动数据（粉丝数、关注数、获赞数等）
            fans_count = 0       # 粉丝数
            following_count = 0  # 关注数
            liked_count = 0      # 获赞与收藏数
            # 遍历互动数据列表
            for interaction in interactions:
                # 获取互动类型名称
                name = interaction.get("name", "")
                # 获取互动数量
                count = interaction.get("count", "0")
                # 将字符串数量转为整数
                count = self._parse_count(count)
                # 根据类型填充对应字段
                if "粉丝" in name:
                    fans_count = count
                elif "关注" in name:
                    following_count = count
                elif "赞" in name or "收藏" in name:
                    liked_count = count

            # 解析用户标签
            tags_str = ",".join([tag.get("name", "") for tag in tags_list if tag.get("name")])

            # 获取头像 URL
            avatar_url = basic_info.get("imageb", basic_info.get("image", ""))

            # 下载头像到本地
            avatar_local = self._download_avatar(user_id, avatar_url)

            # 构建用户数据字典
            user_data = {
                "user_id": user_id,                                             # 用户 ID
                "nickname": basic_info.get("nickname", ""),                     # 昵称
                "avatar": avatar_url,                                           # 头像 URL
                "desc": basic_info.get("desc", ""),                             # 个人简介
                "gender": basic_info.get("gender", 0),                          # 性别
                "ip_location": basic_info.get("ip_location", ""),               # IP 属地
                "fans_count": fans_count,                                       # 粉丝数
                "following_count": following_count,                             # 关注数
                "notes_count": data.get("note_count", 0),                       # 笔记数
                "liked_count": liked_count,                                     # 获赞收藏
                "verified": bool(basic_info.get("red_official_verify_type", 0)), # 是否认证
                "verified_type": str(basic_info.get("red_official_verify_type", "")),  # 认证类型
                "tags": tags_str,                                               # 标签
                "level": str(basic_info.get("level_info", {}).get("level", "")),  # 等级
                "avatar_local": avatar_local,                                   # 头像本地路径
            }

            return user_data

        except Exception as e:
            # 捕获所有异常，避免单个用户失败导致整体中断
            logger.error(f"采集用户 {user_id} 时出错: {e}")
            return None

    def _crawl_from_dom(self, user_id: str) -> dict:
        """
        从页面 DOM 中提取用户基本信息（API 拦截失败时的备用方案）。
        参数:
            user_id: 用户 ID
        返回:
            用户数据字典，失败返回 None
        """
        try:
            logger.debug(f"尝试从 DOM 提取用户信息: {user_id}")

            # 从 DOM 中提取昵称
            nickname_list = self.client.extract_from_dom(".user-name", "textContent")
            nickname = nickname_list[0].strip() if nickname_list else ""

            # 从 DOM 中提取个人简介
            desc_list = self.client.extract_from_dom(".user-desc", "textContent")
            desc = desc_list[0].strip() if desc_list else ""

            # 如果连昵称都提取不到，放弃
            if not nickname:
                logger.warning(f"DOM 提取也失败: {user_id}")
                return None

            # 构建基础用户数据
            user_data = {
                "user_id": user_id,
                "nickname": nickname,
                "desc": desc,
                "fans_count": 0,
                "following_count": 0,
                "notes_count": 0,
                "liked_count": 0,
            }

            logger.debug(f"从 DOM 提取成功: {nickname}")
            return user_data

        except Exception as e:
            logger.error(f"DOM 提取失败: {user_id} - {e}")
            return None

    def _download_avatar(self, user_id: str, avatar_url: str) -> str:
        """
        下载用户头像到本地。
        参数:
            user_id: 用户 ID（用作文件名）
            avatar_url: 头像图片 URL
        返回:
            本地保存路径，下载失败返回空字符串
        """
        # 如果没有头像 URL，跳过下载
        if not avatar_url:
            return ""

        try:
            # 构建本地保存路径
            local_path = os.path.join(self.avatar_dir, f"{user_id}.jpg")

            # 如果文件已存在，跳过下载（避免重复下载）
            if os.path.exists(local_path):
                logger.debug(f"头像已存在，跳过下载: {user_id}")
                return local_path

            # 使用 httpx 下载图片
            with httpx.Client(timeout=15) as http_client:  # 设置 15 秒超时
                response = http_client.get(avatar_url)     # 发送 GET 请求
                # 检查 HTTP 状态码
                if response.status_code == 200:
                    # 写入文件
                    with open(local_path, "wb") as f:       # 二进制写入模式
                        f.write(response.content)           # 写入图片字节数据
                    logger.debug(f"头像下载成功: {user_id}")
                    return local_path
                else:
                    # HTTP 请求失败
                    logger.warning(f"头像下载失败 (HTTP {response.status_code}): {user_id}")
                    return ""

        except Exception as e:
            # 下载过程中出错
            logger.warning(f"头像下载异常: {user_id} - {e}")
            return ""

    def _parse_count(self, count_str) -> int:
        """
        解析数量字符串为整数。
        小红书 API 返回的数量可能是字符串格式，如 "1.2万"、"100"。
        参数:
            count_str: 数量字符串或数字
        返回:
            整数值
        """
        # 如果已经是整数，直接返回
        if isinstance(count_str, int):
            return count_str
        # 转为字符串处理
        count_str = str(count_str).strip()
        try:
            # 处理带"万"后缀的数量
            if "万" in count_str:
                return int(float(count_str.replace("万", "")) * 10000)
            # 处理带"亿"后缀的数量
            elif "亿" in count_str:
                return int(float(count_str.replace("亿", "")) * 100000000)
            else:
                # 普通数字，直接转换
                return int(float(count_str))
        except (ValueError, TypeError):
            # 转换失败，返回 0
            return 0
