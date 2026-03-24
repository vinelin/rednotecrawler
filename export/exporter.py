# ===== 数据导出模块 =====
# 将达人数据、笔记数据、评估结果导出为 Excel 文件

import os                              # 操作系统模块
import pandas as pd                    # 数据处理库
from datetime import datetime          # 日期时间
from loguru import logger              # 日志记录器
from models.database import Database   # 数据库操作类


class Exporter:
    """
    数据导出器。
    功能：
    1. 将达人信息导出为 Excel（含达人列表、笔记明细、评分排行三个 Sheet）
    2. 支持 CSV 格式导出
    """

    def __init__(self, db: Database, export_dir: str = "data/exports"):
        """
        初始化导出器。
        参数:
            db: 数据库实例
            export_dir: 导出文件保存目录
        """
        self.db = db  # 数据库
        # 获取项目根目录
        project_root = os.path.dirname(os.path.dirname(__file__))
        # 构建导出目录绝对路径
        self.export_dir = os.path.join(project_root, export_dir)
        # 确保导出目录存在
        os.makedirs(self.export_dir, exist_ok=True)

    def export_excel(self) -> str:
        """
        导出为 Excel 文件（.xlsx），包含三个 Sheet。
        返回:
            导出文件的绝对路径
        """
        # 生成文件名（包含时间戳）
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")  # 格式: 20240101_120000
        filename = f"达人评估报告_{timestamp}.xlsx"
        filepath = os.path.join(self.export_dir, filename)

        logger.info(f"正在导出 Excel 报告: {filename}")

        # 使用 pandas ExcelWriter 创建多 Sheet 的 Excel 文件
        with pd.ExcelWriter(filepath, engine="openpyxl") as writer:
            # ----- Sheet 1: 评分排行 -----
            self._write_evaluation_sheet(writer)
            # ----- Sheet 2: 达人列表 -----
            self._write_users_sheet(writer)
            # ----- Sheet 3: 笔记明细 -----
            self._write_notes_sheet(writer)

        logger.info(f"Excel 报告导出成功: {filepath}")
        return filepath

    def _write_evaluation_sheet(self, writer):
        """
        写入评分排行 Sheet。
        参数:
            writer: pandas ExcelWriter 实例
        """
        # 从数据库获取所有评估结果
        evaluations = self.db.get_all_evaluations()

        # 如果没有评估数据
        if not evaluations:
            # 创建空的 DataFrame 写入
            pd.DataFrame({"提示": ["暂无评估数据"]}).to_excel(
                writer, sheet_name="评分排行", index=False
            )
            return

        # 构建数据列表
        rows = []
        for rank, eval_item in enumerate(evaluations, 1):
            rows.append({
                "排名": rank,                                           # 排名
                "推荐等级": eval_item.grade,                             # S/A/B/C/D
                "昵称": eval_item.nickname,                              # 达人昵称
                "综合评分": eval_item.total_score,                       # 总分
                "互动率(%)": eval_item.engagement_rate,                  # 互动率
                "内容质量": eval_item.content_quality,                   # 内容质量分
                "粉丝量级": eval_item.fans_score,                       # 粉丝分
                "领域匹配": eval_item.domain_match,                     # 领域匹配度
                "更新频率": eval_item.update_frequency,                 # 更新频率分
                "商业比例(%)": eval_item.commercial_ratio,               # 广告占比
                "用户ID": eval_item.user_id,                            # 用户 ID
            })

        # 转为 DataFrame 并写入 Excel
        df = pd.DataFrame(rows)
        df.to_excel(writer, sheet_name="评分排行", index=False)
        logger.debug(f"评分排行 Sheet: {len(rows)} 条记录")

    def _write_users_sheet(self, writer):
        """
        写入达人列表 Sheet。
        参数:
            writer: pandas ExcelWriter 实例
        """
        # 获取所有达人信息
        users = self.db.get_all_users()

        if not users:
            pd.DataFrame({"提示": ["暂无达人数据"]}).to_excel(
                writer, sheet_name="达人列表", index=False
            )
            return

        # 构建数据列表
        rows = []
        for user in users:
            rows.append({
                "昵称": user.nickname,                    # 昵称
                "用户ID": user.user_id,                  # ID
                "粉丝数": user.fans_count,                # 粉丝数
                "关注数": user.following_count,            # 关注数
                "笔记数": user.notes_count,                # 笔记数
                "获赞收藏": user.liked_count,              # 获赞收藏数
                "个人简介": user.desc,                     # 简介
                "IP属地": user.ip_location,                # 属地
                "认证": "是" if user.verified else "否",   # 是否认证
                "标签": user.tags,                         # 标签
                "等级": user.level,                        # 等级
            })

        df = pd.DataFrame(rows)
        df.to_excel(writer, sheet_name="达人列表", index=False)
        logger.debug(f"达人列表 Sheet: {len(rows)} 条记录")

    def _write_notes_sheet(self, writer):
        """
        写入笔记明细 Sheet。
        参数:
            writer: pandas ExcelWriter 实例
        """
        # 获取所有达人
        users = self.db.get_all_users()

        if not users:
            pd.DataFrame({"提示": ["暂无笔记数据"]}).to_excel(
                writer, sheet_name="笔记明细", index=False
            )
            return

        # 构建数据列表
        rows = []
        for user in users:
            # 获取该达人的所有笔记
            notes = self.db.get_user_notes(user.user_id)
            for note in notes:
                rows.append({
                    "达人昵称": user.nickname,                              # 所属达人
                    "笔记标题": note.title,                                 # 标题
                    "类型": note.note_type,                                 # 图文/视频
                    "点赞": note.liked_count,                               # 点赞数
                    "收藏": note.collected_count,                           # 收藏数
                    "评论": note.comment_count,                             # 评论数
                    "分享": note.share_count,                               # 分享数
                    "标签": note.tags,                                      # 标签
                    "是否广告": "是" if note.is_ad else "否",                # 广告标识
                    "发布时间": note.create_time,                           # 发布时间
                    "笔记ID": note.note_id,                                # 笔记 ID
                    "用户ID": note.user_id,                                # 用户 ID
                })

        df = pd.DataFrame(rows)
        df.to_excel(writer, sheet_name="笔记明细", index=False)
        logger.debug(f"笔记明细 Sheet: {len(rows)} 条记录")

    def export_csv(self) -> str:
        """
        导出评分排行为 CSV 文件。
        返回:
            导出文件的绝对路径
        """
        # 生成文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"达人评估_{timestamp}.csv"
        filepath = os.path.join(self.export_dir, filename)

        # 获取评估结果
        evaluations = self.db.get_all_evaluations()

        if not evaluations:
            logger.warning("没有评估数据可导出")
            return ""

        # 构建数据
        rows = []
        for eval_item in evaluations:
            rows.append({
                "昵称": eval_item.nickname,
                "综合评分": eval_item.total_score,
                "推荐等级": eval_item.grade,
                "互动率(%)": eval_item.engagement_rate,
                "内容质量": eval_item.content_quality,
                "粉丝量级": eval_item.fans_score,
                "领域匹配": eval_item.domain_match,
                "更新频率": eval_item.update_frequency,
                "商业比例(%)": eval_item.commercial_ratio,
                "用户ID": eval_item.user_id,
            })

        # 转为 DataFrame 并导出 CSV
        df = pd.DataFrame(rows)
        df.to_csv(filepath, index=False, encoding="utf-8-sig")  # utf-8-sig 解决 Excel 打开乱码
        logger.info(f"CSV 导出成功: {filepath}")
        return filepath
