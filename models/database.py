# ===== SQLite 数据库模型与初始化 =====
# 使用 SQLAlchemy ORM 定义数据库表结构，管理数据持久化

import os  # 操作系统模块，用于路径操作
from sqlalchemy import create_engine, Column, String, Integer, Float, Boolean, DateTime, Text  # SQLAlchemy 核心组件
from sqlalchemy.orm import declarative_base, sessionmaker, Session  # ORM 基类和会话管理
from datetime import datetime  # 日期时间类型
from loguru import logger      # 日志记录器

# 创建 ORM 基类（所有模型类都继承自它）
Base = declarative_base()


class UserModel(Base):
    """
    达人信息数据库表。
    存储从小红书采集的用户主页数据。
    """
    __tablename__ = "users"  # 表名

    user_id = Column(String(64), primary_key=True, comment="用户唯一 ID")        # 主键
    nickname = Column(String(128), default="", comment="用户昵称")                # 昵称
    avatar = Column(Text, default="", comment="头像图片 URL")                     # 头像链接
    desc = Column(Text, default="", comment="个人简介")                           # 简介
    gender = Column(Integer, default=0, comment="性别: 0=未知, 1=男, 2=女")       # 性别
    ip_location = Column(String(64), default="", comment="IP 属地")               # 属地
    fans_count = Column(Integer, default=0, comment="粉丝数")                     # 粉丝数
    following_count = Column(Integer, default=0, comment="关注数")                # 关注数
    notes_count = Column(Integer, default=0, comment="笔记总数")                  # 笔记数
    liked_count = Column(Integer, default=0, comment="获赞与收藏总数")            # 获赞收藏
    verified = Column(Boolean, default=False, comment="是否已认证")               # 认证状态
    verified_type = Column(String(64), default="", comment="认证类型")            # 认证类型
    tags = Column(Text, default="", comment="用户标签，逗号分隔")                 # 标签
    level = Column(String(32), default="", comment="用户等级")                    # 等级
    avatar_local = Column(String(256), default="", comment="头像本地保存路径")    # 本地路径
    crawl_time = Column(DateTime, default=datetime.now, comment="采集时间")       # 采集时间


class NoteModel(Base):
    """
    笔记信息数据库表。
    存储达人发布的笔记详情数据。
    """
    __tablename__ = "notes"  # 表名

    note_id = Column(String(64), primary_key=True, comment="笔记唯一 ID")         # 主键
    user_id = Column(String(64), index=True, comment="所属用户 ID")               # 外键索引
    title = Column(Text, default="", comment="笔记标题")                          # 标题
    note_type = Column(String(16), default="normal", comment="类型: normal/video")  # 类型
    liked_count = Column(Integer, default=0, comment="点赞数")                    # 点赞数
    collected_count = Column(Integer, default=0, comment="收藏数")                # 收藏数
    comment_count = Column(Integer, default=0, comment="评论数")                  # 评论数
    share_count = Column(Integer, default=0, comment="分享数")                    # 分享数
    cover_image = Column(Text, default="", comment="封面图 URL")                  # 封面链接
    cover_local = Column(String(256), default="", comment="封面图本地路径")       # 本地路径
    tags = Column(Text, default="", comment="话题标签，逗号分隔")                 # 标签
    create_time = Column(String(64), default="", comment="发布时间")              # 发布时间
    is_ad = Column(Boolean, default=False, comment="是否为合作/广告笔记")         # 广告标识
    crawl_time = Column(DateTime, default=datetime.now, comment="采集时间")       # 采集时间


class EvaluationModel(Base):
    """
    达人评估结果数据库表。
    存储评估算法输出的各维度评分。
    """
    __tablename__ = "evaluations"  # 表名

    user_id = Column(String(64), primary_key=True, comment="用户 ID")              # 主键
    nickname = Column(String(128), default="", comment="用户昵称")                  # 昵称
    engagement_rate = Column(Float, default=0.0, comment="互动率 (%)")              # 互动率
    content_quality = Column(Float, default=0.0, comment="内容质量分 (0-100)")      # 内容质量
    fans_score = Column(Float, default=0.0, comment="粉丝量级分 (0-100)")          # 粉丝量级
    domain_match = Column(Float, default=0.0, comment="领域匹配度 (0-100)")        # 领域匹配
    update_frequency = Column(Float, default=0.0, comment="更新频率分 (0-100)")    # 更新频率
    commercial_ratio = Column(Float, default=0.0, comment="商业合作比例 (%)")       # 商业比例
    total_score = Column(Float, default=0.0, comment="综合评分 (0-100)")            # 总分
    grade = Column(String(2), default="D", comment="合作推荐等级: S/A/B/C/D")       # 推荐等级
    evaluate_time = Column(DateTime, default=datetime.now, comment="评估时间")      # 评估时间


class Database:
    """
    数据库管理类。
    负责初始化数据库连接、创建表、提供增删改查接口。
    """

    def __init__(self, db_path: str = "data/db/xiaohongshu.db"):
        """
        初始化数据库。
        参数:
            db_path: SQLite 数据库文件路径（相对于项目根目录）
        """
        # 获取项目根目录的绝对路径
        project_root = os.path.dirname(os.path.dirname(__file__))
        # 构建数据库文件的绝对路径
        self.db_path = os.path.join(project_root, db_path)
        # 确保数据库目录存在
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        # 创建 SQLAlchemy 引擎（连接 SQLite 数据库）
        self.engine = create_engine(
            f"sqlite:///{self.db_path}",  # SQLite 连接字符串
            echo=False                     # 不输出 SQL 语句到控制台
        )
        # 创建所有表（如果不存在）
        Base.metadata.create_all(self.engine)
        # 创建会话工厂
        self.SessionLocal = sessionmaker(bind=self.engine)
        # 记录初始化日志
        logger.info(f"数据库已初始化: {self.db_path}")

    def get_session(self) -> Session:
        """
        获取一个新的数据库会话。
        返回:
            SQLAlchemy Session 实例
        """
        return self.SessionLocal()

    def save_user(self, user_data: dict):
        """
        保存或更新达人信息到数据库。
        如果 user_id 已存在则更新，否则插入新记录。
        参数:
            user_data: 达人信息字典
        """
        # 创建数据库会话
        session = self.get_session()
        try:
            # 根据 user_id 查询是否已存在
            existing = session.query(UserModel).filter_by(user_id=user_data["user_id"]).first()
            if existing:
                # 已存在：更新所有字段
                for key, value in user_data.items():
                    setattr(existing, key, value)  # 动态设置属性值
                logger.debug(f"更新达人: {user_data.get('nickname', user_data['user_id'])}")
            else:
                # 不存在：创建新记录
                user = UserModel(**user_data)  # 用字典参数创建模型实例
                session.add(user)              # 添加到会话
                logger.debug(f"新增达人: {user_data.get('nickname', user_data['user_id'])}")
            # 提交事务
            session.commit()
        except Exception as e:
            # 发生异常时回滚事务
            session.rollback()
            logger.error(f"保存达人数据失败: {e}")
        finally:
            # 无论成功失败都关闭会话
            session.close()

    def save_note(self, note_data: dict):
        """
        保存或更新笔记信息到数据库。
        参数:
            note_data: 笔记信息字典
        """
        # 创建数据库会话
        session = self.get_session()
        try:
            # 根据 note_id 查询是否已存在
            existing = session.query(NoteModel).filter_by(note_id=note_data["note_id"]).first()
            if existing:
                # 已存在：更新所有字段
                for key, value in note_data.items():
                    setattr(existing, key, value)
            else:
                # 不存在：插入新记录
                note = NoteModel(**note_data)
                session.add(note)
            # 提交事务
            session.commit()
        except Exception as e:
            # 回滚事务
            session.rollback()
            logger.error(f"保存笔记数据失败: {e}")
        finally:
            # 关闭会话
            session.close()

    def save_evaluation(self, eval_data: dict):
        """
        保存或更新评估结果到数据库。
        参数:
            eval_data: 评估结果字典
        """
        # 创建数据库会话
        session = self.get_session()
        try:
            # 根据 user_id 查询是否已存在
            existing = session.query(EvaluationModel).filter_by(user_id=eval_data["user_id"]).first()
            if existing:
                # 已存在：更新
                for key, value in eval_data.items():
                    setattr(existing, key, value)
            else:
                # 不存在：插入
                evaluation = EvaluationModel(**eval_data)
                session.add(evaluation)
            # 提交事务
            session.commit()
        except Exception as e:
            # 回滚事务
            session.rollback()
            logger.error(f"保存评估数据失败: {e}")
        finally:
            # 关闭会话
            session.close()

    def get_all_users(self) -> list:
        """
        获取所有达人信息。
        返回:
            UserModel 对象列表
        """
        session = self.get_session()
        try:
            # 查询所有用户记录
            users = session.query(UserModel).all()
            return users
        finally:
            session.close()

    def get_user_notes(self, user_id: str) -> list:
        """
        获取指定达人的所有笔记。
        参数:
            user_id: 达人用户 ID
        返回:
            NoteModel 对象列表
        """
        session = self.get_session()
        try:
            # 按 user_id 过滤查询笔记
            notes = session.query(NoteModel).filter_by(user_id=user_id).all()
            return notes
        finally:
            session.close()

    def get_all_evaluations(self) -> list:
        """
        获取所有评估结果。
        返回:
            EvaluationModel 对象列表
        """
        session = self.get_session()
        try:
            # 查询所有评估记录，按总分降序排列
            evaluations = session.query(EvaluationModel).order_by(
                EvaluationModel.total_score.desc()  # 按综合评分从高到低排序
            ).all()
            return evaluations
        finally:
            session.close()

    def get_user_count(self) -> int:
        """
        获取已采集的达人总数。
        返回:
            达人数量
        """
        session = self.get_session()
        try:
            return session.query(UserModel).count()
        finally:
            session.close()

    def get_note_count(self) -> int:
        """
        获取已采集的笔记总数。
        返回:
            笔记数量
        """
        session = self.get_session()
        try:
            return session.query(NoteModel).count()
        finally:
            session.close()
