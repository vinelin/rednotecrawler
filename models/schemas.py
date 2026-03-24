# ===== Pydantic 数据模型定义 =====
# 定义达人、笔记、评估结果的数据结构，用于数据校验和序列化

from pydantic import BaseModel, Field  # Pydantic 基础类和字段定义
from typing import Optional, List       # 类型提示工具
from datetime import datetime           # 日期时间类型


class UserSchema(BaseModel):
    """
    达人（用户）数据模型。
    对应小红书用户主页的所有关键字段。
    """
    user_id: str = Field(..., description="用户唯一 ID")                    # 必填，用户 ID
    nickname: str = Field(default="", description="用户昵称")               # 昵称
    avatar: str = Field(default="", description="头像图片 URL")             # 头像链接
    desc: str = Field(default="", description="个人简介")                   # 个人简介
    gender: int = Field(default=0, description="性别: 0=未知, 1=男, 2=女")  # 性别标识
    ip_location: str = Field(default="", description="IP 属地")             # IP 属地
    fans_count: int = Field(default=0, description="粉丝数")               # 粉丝数
    following_count: int = Field(default=0, description="关注数")           # 关注数
    notes_count: int = Field(default=0, description="笔记总数")             # 笔记数
    liked_count: int = Field(default=0, description="获赞与收藏总数")       # 获赞收藏
    verified: bool = Field(default=False, description="是否已认证")         # 认证状态
    verified_type: str = Field(default="", description="认证类型")          # 认证类型
    tags: str = Field(default="", description="用户标签，逗号分隔")         # 标签列表
    level: str = Field(default="", description="用户等级")                  # 等级
    avatar_local: str = Field(default="", description="头像本地保存路径")   # 本地头像路径
    crawl_time: datetime = Field(default_factory=datetime.now, description="采集时间")  # 采集时间戳


class NoteSchema(BaseModel):
    """
    笔记数据模型。
    对应小红书单篇笔记的核心字段。
    """
    note_id: str = Field(..., description="笔记唯一 ID")                     # 必填，笔记 ID
    user_id: str = Field(..., description="所属用户 ID")                     # 必填，关联用户
    title: str = Field(default="", description="笔记标题")                   # 标题
    note_type: str = Field(default="normal", description="类型: normal=图文, video=视频")  # 类型
    liked_count: int = Field(default=0, description="点赞数")                # 点赞数
    collected_count: int = Field(default=0, description="收藏数")            # 收藏数
    comment_count: int = Field(default=0, description="评论数")              # 评论数
    share_count: int = Field(default=0, description="分享数")                # 分享数
    cover_image: str = Field(default="", description="封面图 URL")           # 封面图链接
    cover_local: str = Field(default="", description="封面图本地路径")       # 本地封面路径
    tags: str = Field(default="", description="话题标签，逗号分隔")          # 标签列表
    create_time: str = Field(default="", description="发布时间")             # 发布时间
    is_ad: bool = Field(default=False, description="是否为合作/广告笔记")    # 广告标识
    crawl_time: datetime = Field(default_factory=datetime.now, description="采集时间")  # 采集时间戳


class EvaluationSchema(BaseModel):
    """
    达人评估结果数据模型。
    包含各维度评分和最终综合评分。
    """
    user_id: str = Field(..., description="用户 ID")                                      # 关联用户
    nickname: str = Field(default="", description="用户昵称（冗余存储方便查看）")           # 昵称
    engagement_rate: float = Field(default=0.0, description="互动率 (%)")                  # 互动率
    content_quality: float = Field(default=0.0, description="内容质量分 (0-100)")          # 内容质量
    fans_score: float = Field(default=0.0, description="粉丝量级分 (0-100)")              # 粉丝量级
    domain_match: float = Field(default=0.0, description="领域匹配度 (0-100)")            # 领域匹配
    update_frequency: float = Field(default=0.0, description="更新频率分 (0-100)")        # 更新频率
    commercial_ratio: float = Field(default=0.0, description="商业合作比例 (%)")           # 商业比例
    total_score: float = Field(default=0.0, description="综合评分 (0-100)")                # 总分
    grade: str = Field(default="D", description="合作推荐等级: S/A/B/C/D")                 # 推荐等级
    evaluate_time: datetime = Field(default_factory=datetime.now, description="评估时间")  # 评估时间
