# ===== 关键词搜索爬虫模块 =====
# 通过导航到小红书搜索页面，拦截 API 响应来收集达人用户 ID

from loguru import logger          # 日志记录器
from core.client import XHSClient  # 小红书 API 客户端


class SearchCrawler:
    """
    搜索爬虫。
    功能：
    1. 依次搜索多个关键词（导航到搜索结果页）
    2. 从搜索结果中提取用户 ID
    3. 自动去重，直到收集够目标数量
    """

    def __init__(self, client: XHSClient, keywords: list, limit: int = 50):
        """
        初始化搜索爬虫。
        参数:
            client: XHS API 客户端实例
            keywords: 搜索关键词列表（如 ["亚文化", "cosplay", ...]）
            limit: 需要收集的达人数量上限
        """
        self.client = client    # API 客户端
        self.keywords = keywords  # 关键词列表
        self.limit = limit      # 目标数量
        self.user_ids = set()   # 已收集的用户 ID 集合（自动去重）

    def search(self) -> list:
        """
        执行搜索流程，收集达人用户 ID 列表。
        流程：遍历关键词 → 搜索笔记 → 从笔记中提取作者 ID → 去重 → 达到上限停止
        返回:
            去重后的用户 ID 列表
        """
        # 记录搜索开始日志
        logger.info(f"开始搜索达人，目标数量: {self.limit}，关键词: {self.keywords}")

        # 遍历每个关键词进行搜索
        for keyword in self.keywords:
            # 如果已收集够目标数量，提前终止
            if len(self.user_ids) >= self.limit:
                logger.info(f"已达到目标数量 {self.limit}，停止搜索")
                break

            # 记录当前搜索的关键词
            logger.info(f"搜索关键词: 「{keyword}」(当前已收集 {len(self.user_ids)} 人)")

            # 方式 1：搜索笔记，从笔记作者中提取达人 ID
            self._search_notes_by_keyword(keyword)

            # 方式 2：搜索用户，直接获取达人 ID
            if len(self.user_ids) < self.limit:
                self._search_users_by_keyword(keyword)

        # 将集合转为列表
        result = list(self.user_ids)
        # 如果超过上限，只取前 limit 个
        result = result[:self.limit]
        # 记录搜索完成日志
        logger.info(f"搜索完成，共收集 {len(result)} 位达人 ID")
        # 返回结果
        return result

    def _search_notes_by_keyword(self, keyword: str):
        """
        通过搜索笔记来发现达人。
        导航到搜索结果页面，拦截 API 响应，从笔记中提取作者 ID。
        参数:
            keyword: 搜索关键词
        """
    def _search_notes_by_keyword(self, keyword: str) -> list:
        """
        通过搜索笔记来获取达人。
        """
        logger.debug(f"搜索笔记 - 关键词: {keyword}")
        note_items = []

        try:
            # 调用新版客户端：直接发送带签名的 POST 请求
            result = self.client.search_notes(keyword)

            if not result:
                logger.warning(f"搜索笔记无结果: {keyword}")
                return note_items

            # API 响应结构: {"data": {"items": [{"id": "...", "note_card": {...}}, ...]}}
            data = result.get("data", {})
            items = data.get("items", [])

            logger.debug(f"获取到 {len(items)} 条笔记结果")

            # 遍历结果提取数据
            for item in items:
                # 兼容不同的数据结构
                note_card = item.get("note_card", item)
                user_info = note_card.get("user", {})

                user_id = user_info.get("user_id", "") or user_info.get("id", "")
                nickname = user_info.get("nickname", "") or user_info.get("name", "")

                if user_id and nickname:
                    note_items.append({
                        "user_id": user_id,
                        "nickname": nickname,
                        "cover": user_info.get("avatar", ""),
                        "source": f"note_keyword: {keyword}"
                    })

        except Exception as e:
            logger.error(f"搜索笔记异常: {e}")

        return note_items

    def _search_users_by_keyword(self, keyword: str) -> list:
        """
        通过直接搜索用户来获取达人。
        """
        logger.debug(f"搜索用户 - 关键词: {keyword}")
        user_items = []

        try:
            # 调用新版客户端：直接发送带签名的 POST 请求
            result = self.client.search_users(keyword)

            if not result:
                logger.warning(f"搜索用户无结果: {keyword}")
                return user_items

            # API 响应结构: {"data": {"users": [{"id": "...", "name": "...", "desc": "..."}, ...]}}
            data = result.get("data", {})
            users = data.get("users", data.get("items", []))

            logger.debug(f"获取到 {len(users)} 个用户结果")

            for user in users:
                user_id = user.get("id", "") or user.get("user_id", "")
                nickname = user.get("name", "") or user.get("nickname", "")

                if user_id and nickname:
                    user_items.append({
                        "user_id": user_id,
                        "nickname": nickname,
                        "desc": user.get("desc", ""),
                        "cover": user.get("image", "") or user.get("avatar", ""),
                        "source": f"user_keyword: {keyword}"
                    })

        except Exception as e:
            logger.error(f"搜索用户异常: {e}")

        return user_items
