# ===== HTTP 客户端模块 =====
# 借鉴 MediaCrawler 的签名机制，通过 Playwright 注入脚本计算 X-s/X-t，
# 然后使用 httpx 发送真实的 API 请求。

import json
import time
import httpx
from playwright.sync_api import Page
from loguru import logger
from core.rate_limiter import RateLimiter

class XHSClient:
    """
    小红书 API 客户端。
    核心策略：
    - 在现有的 Playwright 页面中执行 JS 计算签名 (X-s, X-t)
    - 使用 httpx 带上生成的签名和用户的 Cookie 发送真实的 API 请求
    """

    # API 基础路径
    HOST = "https://edith.xiaohongshu.com"
    WEB_HOST = "https://www.xiaohongshu.com"

    def __init__(self, page: Page, rate_limiter: RateLimiter, cookie_str: str):
        self.page = page
        self.rate_limiter = rate_limiter
        self.cookie_str = cookie_str
        self.headers = {
            "accept": "application/json, text/plain, */*",
            "content-type": "application/json;charset=UTF-8",
            "origin": "https://www.xiaohongshu.com",
            "referer": "https://www.xiaohongshu.com/",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Cookie": cookie_str
        }
        
        # 提取 a1 cookie 值（加密所需）
        self.a1 = ""
        for item in cookie_str.split(";"):
            item = item.strip()
            if item.startswith("a1="):
                self.a1 = item[3:]
                break

    def _get_sign(self, uri: str, data: dict = None) -> dict:
        """
        通过浏览器上下文计算请求签名。
        """
        try:
            # 确保页面已加载完毕
            if self.page.url == "about:blank":
                self.page.goto(self.WEB_HOST, wait_until="domcontentloaded")
                self.page.wait_for_timeout(2000)

            js_code = f"""
            () => {{
                if (!window._webmsxyw) return null;
                const uri = "{uri}";
                const data = {json.dumps(data) if data else "undefined"};
                return window._webmsxyw(uri, data);
            }}
            """
            signs = self.page.evaluate(js_code)
            if not signs:
                # 尝试点击一下页面触发加载
                self.page.evaluate("window.scrollTo(0, 100)")
                self.page.wait_for_timeout(1000)
                signs = self.page.evaluate(js_code)
            
            return signs or {"X-s": "", "X-t": ""}
        except Exception as e:
            logger.error(f"签名计算失败: {e}")
            return {"X-s": "", "X-t": ""}

    def _post(self, uri: str, data: dict) -> dict:
        """发送带签名的 POST 请求"""
        self.rate_limiter.wait()
        
        signs = self._get_sign(uri, data)
        headers = self.headers.copy()
        if signs and "X-s" in signs:
            headers["x-s"] = signs["X-s"]
            headers["x-t"] = str(signs["X-t"])
            
        url = f"{self.HOST}{uri}"
        logger.debug(f"POST {url}")
        
        try:
            with httpx.Client(timeout=15) as client:
                resp = client.post(url, headers=headers, json=data)
                
                if resp.status_code == 200:
                    result = resp.json()
                    if result.get("success"):
                        return result
                    else:
                        logger.warning(f"API 业务错误: {result.get('msg', '')} ({result.get('code', '')})")
                        return {}
                else:
                    logger.warning(f"HTTP 错误: {resp.status_code}")
                    return {}
        except Exception as e:
            logger.error(f"POST 请求异常: {e}")
            return {}

    def _get(self, uri: str, params: dict = None) -> dict:
        """发送带签名的 GET 请求"""
        self.rate_limiter.wait()
        
        # 将 params 拼接到 URI (计算签名需要的格式)
        sign_uri = uri
        if params:
            import urllib.parse
            query_str = urllib.parse.urlencode(params)
            sign_uri = f"{uri}?{query_str}"
            
        signs = self._get_sign(sign_uri)
        headers = self.headers.copy()
        if signs and "X-s" in signs:
            headers["x-s"] = signs["X-s"]
            headers["x-t"] = str(signs["X-t"])
            
        url = f"{self.HOST}{sign_uri}"
        logger.debug(f"GET {url}")
        
        try:
            with httpx.Client(timeout=15) as client:
                resp = client.get(url, headers=headers)
                if resp.status_code == 200:
                    result = resp.json()
                    if result.get("success"):
                        return result
                    return {}
                return {}
        except Exception as e:
            logger.error(f"GET 请求异常: {e}")
            return {}

    def search_notes(self, keyword: str, page: int = 1) -> dict:
        """根据关键词搜索笔记"""
        uri = "/api/sns/web/v1/search/notes"
        data = {
            "keyword": keyword,
            "page": page,
            "page_size": 20,
            "search_id": f"{int(time.time() * 1000)}",
            "sort": "general",
            "note_type": 0
        }
        return self._post(uri, data)

    def search_users(self, keyword: str) -> dict:
        """根据关键词搜索用户"""
        uri = "/api/sns/web/v1/search/user"
        data = {
            "keyword": keyword,
            "page": 1,
            "page_size": 20,
            "search_id": f"{int(time.time() * 1000)}",
            "search_user_type": 1
        }
        return self._post(uri, data)

    def get_user_info(self, user_id: str) -> dict:
        uri = "/api/sns/web/v1/user/otherinfo"
        params = {"target_user_id": user_id}
        return self._get(uri, params)

    def get_user_notes(self, user_id: str, cursor: str = "") -> dict:
        uri = "/api/sns/web/v1/user_posted"
        params = {
            "num": 30,
            "cursor": cursor,
            "user_id": user_id,
            "image_scenes": "FD_PRV_WEBP,FD_WM_WEBP"
        }
        return self._get(uri, params)

    def get_note_detail(self, note_id: str, xsec_token: str = "") -> dict:
        uri = "/api/sns/web/v1/feed"
        data = {
            "source_note_id": note_id,
            "image_formats": ["jpg", "webp", "avif"],
            "extra": {"need_body_topic": 1},
            "xsec_source": "pc_search",
            "xsec_token": xsec_token
        }
        result = self._post(uri, data)
        if result and result.get("data", {}).get("items"):
            # 包装为原有格式 { "data": note_card }
            return {"data": result["data"]["items"][0].get("note_card", {})}
        return {}


