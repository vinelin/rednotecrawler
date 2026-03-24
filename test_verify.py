# ===== 简化验证脚本 =====
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("=" * 50)
print("  验证测试")
print("=" * 50)

# 1. 导入测试
print("\n1. 模块导入测试")
from core.rate_limiter import RateLimiter
print("  ✓ core.rate_limiter")
from models.schemas import UserSchema, NoteSchema, EvaluationSchema
print("  ✓ models.schemas")
from models.database import Database
print("  ✓ models.database")
from crawlers.search import SearchCrawler
print("  ✓ crawlers.search")
from crawlers.user_profile import UserProfileCrawler
print("  ✓ crawlers.user_profile")
from crawlers.note_detail import NoteDetailCrawler
print("  ✓ crawlers.note_detail")
from analysis.evaluator import Evaluator
print("  ✓ analysis.evaluator")
from export.exporter import Exporter
print("  ✓ export.exporter")

# 2. 限速器测试
print("\n2. 限速器测试")
rl = RateLimiter(0.1, 0.2, 1, 3)
print(f"  ✓ 统计: {rl.get_stats()}")

# 3. Pydantic 模型测试
print("\n3. Pydantic 模型测试")
user = UserSchema(user_id="test123", nickname="测试用户", fans_count=10000)
print(f"  ✓ UserSchema: {user.nickname}")
note = NoteSchema(note_id="note001", user_id="test123", title="测试笔记")
print(f"  ✓ NoteSchema: {note.title}")

# 4. 数据库测试
print("\n4. 数据库测试")
db = Database("data/db/test_simple.db")
db.save_user({"user_id": "t001", "nickname": "测试达人", "fans_count": 50000, "desc": "jk", "tags": "jk,lolita"})
db.save_note({"note_id": "n001", "user_id": "t001", "title": "jk穿搭", "liked_count": 500, "collected_count": 200, "comment_count": 50, "tags": "jk制服", "create_time": "", "is_ad": False})
users = db.get_all_users()
print(f"  ✓ 保存并读取: {users[0].nickname}")

# 5. 评估测试
print("\n5. 评估算法测试")
evaluator = Evaluator(db)
results = evaluator.evaluate_all()
r = results[0]
print(f"  ✓ 评估结果: {r['nickname']} = {r['total_score']}分 ({r['grade']}级)")

# 清理
db_path = os.path.join(os.path.dirname(__file__), "data", "db", "test_simple.db")
if os.path.exists(db_path):
    os.remove(db_path)
    print("  ✓ 临时数据库已清理")

print("\n" + "=" * 50)
print("  全部测试通过 ✓")
print("=" * 50)
