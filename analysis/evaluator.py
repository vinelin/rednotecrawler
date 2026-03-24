# ===== 达人评估算法模块 =====
# 对已采集的达人数据进行多维度打分，输出综合评分和合作推荐等级

import statistics  # 统计模块，用于计算中位数
from datetime import datetime, timedelta  # 日期时间工具
from loguru import logger                   # 日志记录器
from models.database import Database        # 数据库操作类


class Evaluator:
    """
    达人评估器。
    评估维度与权重：
    - 互动率 (30%): (赞+藏+评) / 粉丝数
    - 内容质量 (20%): 近 N 篇笔记互动中位数
    - 粉丝量级 (15%): 按粉丝数分档打分
    - 领域匹配度 (15%): 标签与亚文化关键词重合度
    - 更新频率 (10%): 近 30 天发布笔记数
    - 商业比例 (10%): 广告笔记占比（过高扣分）
    """

    # 亚文化领域相关关键词（用于领域匹配度计算）
    DOMAIN_KEYWORDS = [
        "亚文化", "jk", "jk制服", "lolita", "lo裙", "lo娘",
        "汉服", "cosplay", "cos", "二次元", "三坑",
        "穿搭", "ootd", "少女", "甜酷", "暗黑",
        "原宿", "Y2K", "辣妹", "地雷系", "量产型",
        "menhera", "古着", "vintage", "洛丽塔", "女仆",
    ]

    def __init__(self, db: Database):
        """
        初始化评估器。
        参数:
            db: 数据库实例
        """
        self.db = db  # 数据库

    def evaluate_all(self) -> list:
        """
        评估数据库中所有达人。
        返回:
            评估结果字典列表，按综合评分降序排列
        """
        # 获取所有已采集的达人
        users = self.db.get_all_users()
        logger.info(f"开始评估 {len(users)} 位达人...")

        # 存储评估结果
        results = []

        # 遍历每位达人进行评估
        for user in users:
            # 获取该达人的所有笔记
            notes = self.db.get_user_notes(user.user_id)
            # 执行评估
            eval_result = self._evaluate_single(user, notes)
            # 保存评估结果到数据库
            self.db.save_evaluation(eval_result)
            # 添加到结果列表
            results.append(eval_result)
            # 记录日志
            logger.debug(
                f"  {user.nickname}: 总分={eval_result['total_score']:.1f}, "
                f"等级={eval_result['grade']}"
            )

        # 按总分降序排列
        results.sort(key=lambda x: x["total_score"], reverse=True)
        logger.info(f"评估完成！S级: {sum(1 for r in results if r['grade']=='S')} | "
                    f"A级: {sum(1 for r in results if r['grade']=='A')} | "
                    f"B级: {sum(1 for r in results if r['grade']=='B')} | "
                    f"C级: {sum(1 for r in results if r['grade']=='C')} | "
                    f"D级: {sum(1 for r in results if r['grade']=='D')}")

        return results

    def _evaluate_single(self, user, notes: list) -> dict:
        """
        评估单个达人。
        参数:
            user: UserModel 达人数据库对象
            notes: NoteModel 笔记数据库对象列表
        返回:
            评估结果字典
        """
        # ----- 1. 互动率 (权重 30%) -----
        engagement_rate = self._calc_engagement_rate(user, notes)
        # 将互动率转换为 0-100 分
        # 互动率 > 10% 算 100 分，按比例线性映射
        engagement_score = min(100, engagement_rate * 10)

        # ----- 2. 内容质量分 (权重 20%) -----
        content_quality = self._calc_content_quality(notes)

        # ----- 3. 粉丝量级分 (权重 15%) -----
        fans_score = self._calc_fans_score(user.fans_count)

        # ----- 4. 领域匹配度 (权重 15%) -----
        domain_match = self._calc_domain_match(user, notes)

        # ----- 5. 更新频率分 (权重 10%) -----
        update_frequency = self._calc_update_frequency(notes)

        # ----- 6. 商业合作比例 (权重 10%) -----
        commercial_ratio = self._calc_commercial_ratio(notes)
        # 商业比例转评分：比例越低得分越高（超过 50% 大幅扣分）
        commercial_score = max(0, 100 - commercial_ratio * 2)

        # ----- 计算综合评分 -----
        total_score = (
            engagement_score * 0.30 +   # 互动率权重 30%
            content_quality * 0.20 +    # 内容质量权重 20%
            fans_score * 0.15 +         # 粉丝量级权重 15%
            domain_match * 0.15 +       # 领域匹配权重 15%
            update_frequency * 0.10 +   # 更新频率权重 10%
            commercial_score * 0.10     # 商业比例权重 10%
        )

        # ----- 确定合作推荐等级 -----
        grade = self._get_grade(total_score)

        # 构建评估结果字典
        eval_result = {
            "user_id": user.user_id,               # 用户 ID
            "nickname": user.nickname,              # 昵称
            "engagement_rate": round(engagement_rate, 2),      # 互动率 (%)
            "content_quality": round(content_quality, 1),      # 内容质量分
            "fans_score": round(fans_score, 1),                # 粉丝量级分
            "domain_match": round(domain_match, 1),            # 领域匹配度
            "update_frequency": round(update_frequency, 1),    # 更新频率分
            "commercial_ratio": round(commercial_ratio, 1),    # 商业比例 (%)
            "total_score": round(total_score, 1),              # 综合评分
            "grade": grade,                                     # 推荐等级
        }

        return eval_result

    def _calc_engagement_rate(self, user, notes: list) -> float:
        """
        计算互动率。
        公式: (平均点赞 + 平均收藏 + 平均评论) / 粉丝数 × 100%
        参数:
            user: 达人对象
            notes: 笔记列表
        返回:
            互动率百分比
        """
        # 粉丝数为 0 时无法计算互动率
        if user.fans_count == 0 or not notes:
            return 0.0

        # 计算所有笔记的总互动量
        total_interaction = sum(
            note.liked_count + note.collected_count + note.comment_count
            for note in notes
        )
        # 计算平均每篇互动量
        avg_interaction = total_interaction / len(notes)
        # 计算互动率（百分比）
        rate = (avg_interaction / user.fans_count) * 100
        return rate

    def _calc_content_quality(self, notes: list) -> float:
        """
        计算内容质量分。
        使用笔记互动量的中位数来衡量（中位数比均值更抗异常值干扰）。
        参数:
            notes: 笔记列表
        返回:
            内容质量分 (0-100)
        """
        # 没有笔记则返回 0
        if not notes:
            return 0.0

        # 计算每篇笔记的总互动量
        interactions = [
            note.liked_count + note.collected_count + note.comment_count
            for note in notes
        ]

        # 计算中位数
        median_val = statistics.median(interactions)

        # 将中位数映射到 0-100 分
        # 中位数 >= 1000 为满分 100，按比例线性映射
        score = min(100, (median_val / 1000) * 100)
        return score

    def _calc_fans_score(self, fans_count: int) -> float:
        """
        计算粉丝量级分。
        按粉丝数分档打分，适合亚文化领域的特点（小众但精准）。
        参数:
            fans_count: 粉丝数
        返回:
            粉丝量级分 (0-100)
        """
        # 定义粉丝数量档位和对应分数
        # 亚文化领域不需要超大V，1万-50万是最佳区间
        if fans_count >= 500000:       # 50万+ 大V
            return 90
        elif fans_count >= 100000:     # 10万-50万 头部达人
            return 100                 # 最佳合作区间
        elif fans_count >= 50000:      # 5万-10万 腰部达人
            return 95                  # 性价比最高
        elif fans_count >= 10000:      # 1万-5万 中部达人
            return 80
        elif fans_count >= 5000:       # 5千-1万 尾部达人
            return 60
        elif fans_count >= 1000:       # 1千-5千 微型达人
            return 40
        else:                          # 1千以下
            return 20

    def _calc_domain_match(self, user, notes: list) -> float:
        """
        计算领域匹配度。
        检查达人标签和笔记标签中包含多少亚文化关键词。
        参数:
            user: 达人对象
            notes: 笔记列表
        返回:
            领域匹配度 (0-100)
        """
        # 收集所有标签文本（用户标签 + 笔记标签）
        all_tags_text = user.tags.lower() if user.tags else ""
        # 加入个人简介
        all_tags_text += " " + (user.desc.lower() if user.desc else "")
        # 加入所有笔记标签
        for note in notes:
            if note.tags:
                all_tags_text += " " + note.tags.lower()
            # 加入笔记标题
            if note.title:
                all_tags_text += " " + note.title.lower()

        # 计算匹配的关键词数量
        matched_count = 0
        for keyword in self.DOMAIN_KEYWORDS:
            if keyword.lower() in all_tags_text:
                matched_count += 1

        # 将匹配数映射为 0-100 分
        # 匹配 5 个及以上关键词为满分
        score = min(100, (matched_count / 5) * 100)
        return score

    def _calc_update_frequency(self, notes: list) -> float:
        """
        计算更新频率分。
        统计近 30 天内发布的笔记数量。
        参数:
            notes: 笔记列表
        返回:
            更新频率分 (0-100)
        """
        # 没有笔记
        if not notes:
            return 0.0

        # 计算 30 天前的时间戳
        thirty_days_ago = datetime.now() - timedelta(days=30)

        # 统计近 30 天内的笔记数
        recent_count = 0
        for note in notes:
            try:
                # 尝试解析笔记发布时间
                if note.create_time:
                    # 处理时间戳格式（小红书可能返回毫秒级时间戳）
                    timestamp = float(note.create_time)
                    # 如果是毫秒级时间戳（>10位），转为秒级
                    if timestamp > 1e12:
                        timestamp = timestamp / 1000
                    note_time = datetime.fromtimestamp(timestamp)
                    # 如果在近 30 天内
                    if note_time >= thirty_days_ago:
                        recent_count += 1
            except (ValueError, TypeError, OSError):
                # 时间解析失败，跳过
                continue

        # 将笔记数映射为 0-100 分
        # 30天内发 8 篇及以上为满分（约每4天一篇）
        score = min(100, (recent_count / 8) * 100)
        return score

    def _calc_commercial_ratio(self, notes: list) -> float:
        """
        计算商业合作比例。
        参数:
            notes: 笔记列表
        返回:
            商业笔记占比百分比
        """
        # 没有笔记
        if not notes:
            return 0.0

        # 统计广告/合作笔记数量
        ad_count = sum(1 for note in notes if note.is_ad)
        # 计算占比
        ratio = (ad_count / len(notes)) * 100
        return ratio

    def _get_grade(self, total_score: float) -> str:
        """
        根据综合评分确定合作推荐等级。
        参数:
            total_score: 综合评分 (0-100)
        返回:
            推荐等级字符串: S/A/B/C/D
        """
        if total_score >= 85:
            return "S"  # 极力推荐合作
        elif total_score >= 70:
            return "A"  # 推荐合作
        elif total_score >= 55:
            return "B"  # 可以合作
        elif total_score >= 40:
            return "C"  # 谨慎合作
        else:
            return "D"  # 不推荐
