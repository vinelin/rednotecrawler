# ===== 笔记详情爬虫模块 =====
# 通过导航到用户主页，拦截 API 响应采集笔记数据，并下载封面图

import os       # 操作系统模块，用于路径操作
import httpx    # HTTP 客户端，用于下载图片
from loguru import logger          # 日志记录器
from core.client import XHSClient  # 小红书 API 客户端
from models.database import Database  # 数据库操作类


class NoteDetailCrawler:
    """
    笔记详情爬虫。
    功能：
    1. 导航到达人主页，拦截笔记列表 API 响应
    2. 采集每篇笔记的互动数据
    3. 下载封面图到本地
    """

    def __init__(self, client: XHSClient, db: Database,
                 notes_per_user: int = 20, images_dir: str = "data/images"):
        """
        初始化笔记详情爬虫。
        参数:
            client: XHS API 客户端实例
            db: 数据库实例
            notes_per_user: 每个达人采集的最近笔记数量
            images_dir: 图片保存根目录
        """
        self.client = client                # API 客户端
        self.db = db                        # 数据库
        self.notes_per_user = notes_per_user  # 每人采集笔记数
        # 获取项目根目录
        self.project_root = os.path.dirname(os.path.dirname(__file__))
        # 构建封面图保存目录
        self.covers_dir = os.path.join(self.project_root, images_dir, "covers")
        # 确保目录存在
        os.makedirs(self.covers_dir, exist_ok=True)

    def crawl(self, user_ids: list) -> dict:
        """
        批量采集达人的笔记详情。
        参数:
            user_ids: 用户 ID 列表
        返回:
            字典，key=user_id, value=该达人的笔记数据列表
        """
        # 记录开始日志
        logger.info(f"开始采集 {len(user_ids)} 位达人的笔记数据...")
        # 存储结果：{user_id: [note_data, ...]}
        all_notes = {}
        # 遍历每个用户
        for index, user_id in enumerate(user_ids, 1):
            # 输出进度日志
            logger.info(f"[{index}/{len(user_ids)}] 正在采集达人 {user_id} 的笔记...")
            # 采集该用户的笔记
            notes = self._crawl_user_notes(user_id)
            # 保存结果
            all_notes[user_id] = notes
            # 记录本次采集数量
            logger.info(f"  ✓ 采集到 {len(notes)} 篇笔记")

        # 统计总笔记数
        total = sum(len(notes) for notes in all_notes.values())
        logger.info(f"笔记采集完成: 共 {total} 篇")
        return all_notes

    def _crawl_user_notes(self, user_id: str) -> list:
        """
        采集单个达人的笔记列表。
        调用客户端获取用户主页笔记分页 API。
        参数:
            user_id: 用户 ID
        返回:
            笔记数据字典列表
        """
        # 存储该用户的所有笔记数据
        notes = []

        try:
            # 调用客户端获取用户笔记
            result = self.client.get_user_notes(user_id)

            if not result:
                logger.warning(f"获取用户笔记列表失败: {user_id}")
                return notes

            # 获取数据部分
            data = result.get("data", {})
            note_list = data.get("notes", [])

            logger.debug(f"API 返回 {len(note_list)} 篇笔记")

            # 遍历笔记列表
            for note_item in note_list:
                if len(notes) >= self.notes_per_user:
                    break

                note_data = self._parse_note(user_id, note_item)
                if note_data:
                    self.db.save_note(note_data)
                    notes.append(note_data)

        except Exception as e:
            logger.error(f"采集用户 {user_id} 笔记时出错: {e}")

        return notes

    def _parse_note(self, user_id: str, note_item: dict) -> dict:
        """
        解析单篇笔记的数据。
        参数:
            user_id: 所属用户 ID
            note_item: API 返回的笔记原始数据
        返回:
            解析后的笔记数据字典，失败返回 None
        """
        try:
            # 获取笔记 ID
            note_id = note_item.get("note_id", "") or note_item.get("id", "")
            if not note_id:
                return None

            # 获取互动数据（点赞等信息在 API 中通常扁平化了，或在 interact_info 里）
            interact_info = note_item.get("interact_info", note_item)

            # 动态判断并安全转换为数字
            liked = self._safe_int(interact_info.get("liked_count", note_item.get("liked_count", 0)))
            collected = self._safe_int(interact_info.get("collected_count", note_item.get("collected_count", 0)))
            comment = self._safe_int(interact_info.get("comment_count", note_item.get("comment_count", 0)))
            share = self._safe_int(interact_info.get("share_count", note_item.get("share_count", 0)))

            # 获取封面 URL
            cover = note_item.get("cover", {})
            cover_url = cover.get("url_default", "") or cover.get("url", "")
            
            # 判断笔记类型
            note_type_value = note_item.get("type", "")
            note_type = "video" if note_type_value == "video" else "normal"

            # 下载封面图
            cover_local = self._download_cover(note_id, cover_url)

            # 构建存储结构
            note_data = {
                "note_id": note_id,
                "user_id": user_id,
                "title": note_item.get("display_title", note_item.get("title", "")),
                "note_type": note_type,
                "liked_count": liked,
                "collected_count": collected,
                "comment_count": comment,
                "share_count": share,
                "cover_image": cover_url,
                "cover_local": cover_local,
                "tags": "",  # 列表 API 通常不返回完整标签，默认空
                "create_time": str(note_item.get("time", "")),
                "is_ad": False, # 初步判断，更精确的需要请求单篇详情
            }

            return note_data

        except Exception as e:
            logger.error(f"解析笔记数据出错: {e}")
            return None

    def _safe_int(self, value) -> int:
        """
        安全地将值转为整数。
        参数:
            value: 可能是 int、str 或其他类型
        返回:
            整数值
        """
        try:
            return int(value)
        except (ValueError, TypeError):
            return 0

    def _download_cover(self, note_id: str, cover_url: str) -> str:
        """
        下载笔记封面图到本地。
        参数:
            note_id: 笔记 ID（用作文件名）
            cover_url: 封面图 URL
        返回:
            本地保存路径，下载失败返回空字符串
        """
        # 如果没有封面 URL，跳过
        if not cover_url:
            return ""

        try:
            # 构建本地保存路径
            local_path = os.path.join(self.covers_dir, f"{note_id}.jpg")

            # 文件已存在则跳过
            if os.path.exists(local_path):
                return local_path

            # 使用 httpx 下载图片
            with httpx.Client(timeout=15) as http_client:  # 15 秒超时
                response = http_client.get(cover_url)       # 发送请求
                if response.status_code == 200:
                    # 写入文件
                    with open(local_path, "wb") as f:
                        f.write(response.content)
                    return local_path
                else:
                    logger.warning(f"封面下载失败 (HTTP {response.status_code}): {note_id}")
                    return ""

        except Exception as e:
            logger.warning(f"封面下载异常: {note_id} - {e}")
            return ""
