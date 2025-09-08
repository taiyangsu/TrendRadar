# coding=utf-8

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

import pytz

from .config import load_config
from .utils import get_beijing_time, format_date_folder


# 加载配置
CONFIG = load_config()


class PushRecordManager:
    """推送记录管理器"""

    def __init__(self):
        self.record_dir = Path("output") / ".push_records"
        self.ensure_record_dir()
        self.cleanup_old_records()

    def ensure_record_dir(self):
        """确保记录目录存在"""
        self.record_dir.mkdir(parents=True, exist_ok=True)

    def get_today_record_file(self) -> Path:
        """获取今天的记录文件路径"""
        today = get_beijing_time().strftime("%Y%m%d")
        return self.record_dir / f"push_record_{today}.json"

    def cleanup_old_records(self):
        """清理过期的推送记录"""
        retention_days = CONFIG["SILENT_PUSH"]["RECORD_RETENTION_DAYS"]
        current_time = get_beijing_time()

        for record_file in self.record_dir.glob("push_record_*.json"):
            try:
                date_str = record_file.stem.replace("push_record_", "")
                file_date = datetime.strptime(date_str, "%Y%m%d")
                file_date = pytz.timezone("Asia/Shanghai").localize(file_date)

                if (current_time - file_date).days > retention_days:
                    record_file.unlink()
                    print(f"清理过期推送记录: {record_file.name}")
            except Exception as e:
                print(f"清理记录文件失败 {record_file}: {e}")

    def has_pushed_today(self) -> bool:
        """检查今天是否已经推送过"""
        record_file = self.get_today_record_file()

        if not record_file.exists():
            return False

        try:
            with open(record_file, "r", encoding="utf-8") as f:
                record = json.load(f)
            return record.get("pushed", False)
        except Exception as e:
            print(f"读取推送记录失败: {e}")
            return False

    def record_push(self, report_type: str):
        """记录推送"""
        record_file = self.get_today_record_file()
        now = get_beijing_time()

        record = {
            "pushed": True,
            "push_time": now.strftime("%Y-%m-%d %H:%M:%S"),
            "report_type": report_type,
        }

        try:
            with open(record_file, "w", encoding="utf-8") as f:
                json.dump(record, f, ensure_ascii=False, indent=2)
            print(f"推送记录已保存: {report_type} at {now.strftime('%H:%M:%S')}")
        except Exception as e:
            print(f"保存推送记录失败: {e}")

    def is_in_time_range(self, start_time: str, end_time: str) -> bool:
        """检查当前时间是否在指定时间范围内"""
        now = get_beijing_time()
        current_time = now.strftime("%H:%M")
        return start_time <= current_time <= end_time