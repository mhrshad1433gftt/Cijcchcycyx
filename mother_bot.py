# پیشفرض (استاندارد پایتون)
import asyncio
import json
import logging
import os
import re
import shutil
import signal
import socket
import subprocess
import threading
import time
import uuid
import zipfile
import traceback
import math
import mimetypes
import tempfile
from collections import defaultdict, deque
from datetime import datetime, timedelta
from pathlib import Path

# خارجی (پکیج‌های نصب‌شده)
import psutil
import jdatetime
import pytz
import requests
import schedule
import telebot
from telebot import types
from PIL import Image
from PyPDF2 import PdfReader, PdfWriter
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET
import re
import mimetypes
from pathlib import Path
import tempfile
from datetime import datetime
import pytz

# تنظیم لاگ‌گذاری برای دیباگ و ردیابی خطاها
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    force=True  # این خط خیلی مهمه!
)

logger = logging.getLogger(__name__)

# تنظیمات اولیه بات با توکن
TOKEN = '7619157398:AAGgVDGx8dEKIS-xhrdery3W_TiVQX9za94'
ADMIN_ID = 1113652228
OWNER_ID = 1113652228
BOT_VERSION = "2.11.106.27"

# ایجاد نمونه بات
bot = telebot.TeleBot(TOKEN)

# کلاس ذخیره‌سازی داده‌ها برای مدیریت تمام اطلاعات
class DataStore:
    def __init__(self, base_folder="central_data", token=None):
        self.base_folder = base_folder
        os.makedirs(self.base_folder, exist_ok=True)
        self.user_data_path = os.path.join(self.base_folder, "user_data.json")
        self.user_data = {}
        if token is not None:
            with open(os.path.join(self.base_folder, "bot_token.txt"), "w", encoding="utf-8") as f:
                f.write(token)
        self.signatures = {
            "Default": {
                "template": "{Bold}\n\n{BlockQuote}\n\n{Simple}\n\n{Italic}\n\n{Code}\n\n{Strike}\n\n{Underline}\n\n{Spoiler}\n\n{Link}",
                "variables": ["Bold", "BlockQuote", "Simple", "Italic", "Code", "Strike", "Underline", "Spoiler", "Link"]
            }
        }
        self.broadcast_users = []
        self.variables = {}
        self.default_values = {}
        self.user_states = {}
        self.channel_monitor_enabled = False
        self.channel_events = []  # [{event_type, channel, user_id, ...}]
        self.settings = {
            "default_welcome": "🌟 خوش آمدید {name} عزیز! 🌟\n\nبه ربات مدیریت پست و امضا خوش آمدید."
        }
        self.channels = []
        self.channel_admins = {}
        self.protected_channels = []  # چنل‌های محافظت شده برای ضد خیانت
        self.security_logs = []  # لاگ‌های امنیتی
        self.notification_settings = {}  # تنظیمات نوتیفیکیشن
        self.uploader_channels = []
        self.scheduled_posts = []
        self.scheduled_broadcasts = []
        self.file_details = []
        self.admins = [OWNER_ID]
        self.admin_permissions = {str(OWNER_ID): {
            "create_post": True,
            "admin_management": True,
            "uploader_management": True,
            "broadcast_management": True,
            "bot_creator": True,
            "user_account": True,
            "forced_management": True, 
            "trust": True, 
            "manage_channel" : True,
            "manage_timers" : True,
            "options_management": True
        }}
        self.timer_settings = {
            "timers_enabled": True,
            "inline_buttons_enabled": True,
            "coinpy_daily_limit": 3,
            "coinpy_timeout_min": 7,
            "owner_discrimination": False,
            "delete_upload_file_timeout": 60   # مقدار پیش‌فرض ۶۰ ثانیه
        }
        self.last_message_id = {}
        self.last_user_message_id = {}
        self.uploader_file_map = {}
        self.uploader_file_map_path = os.path.join(self.base_folder, 'uploader_files.json')
        self.stats_path = os.path.join(self.base_folder, 'stats.json')

        # --- اجباری‌ها
        self.forced_channels = []
        self.forced_join_message = "برای استفاده از ربات باید در چنل‌های زیر عضو باشید:"
        self.forced_seen_channels = []
        self.forced_seen_message = "برای استفاده از ربات باید {count} پست آخر چنل را سین کنید و سپس روی دکمه «زدم» بزنید."
        self.forced_seen_count = 5
        self.forced_reaction_channels = []
        self.forced_reaction_message = "برای استفاده از ربات باید در چنل‌های زیر ری‌اکشن بزنید:"
        self.forced_reaction_count = 2

        # --- NEW: execution options for auto file changes ---
        self.exec_options_path = os.path.join(self.base_folder, "auto_exec_options.json")
        self.auto_exec_options = {
            "rename": False,
            "filter": False
        }

        self.create_default_files()
        self.load_data()

    def create_default_files(self):
        logger = logging.getLogger("DataStore")
        default_files = {
            'signatures.json': self.signatures,
            'scheduled_broadcasts.json': [],
            'variables.json': {
                "Bold": {"format": "Bold"},
                "BlockQuote": {"format": "BlockQuote"},
                "Simple": {"format": "Simple"},
                "Italic": {"format": "Italic"},
                "Code": {"format": "Code"},
                "Strike": {"format": "Strike"},
                "Underline": {"format": "Underline"},
                "Spoiler": {"format": "Spoiler"},
                "Link": {"format": "Link"}
            },
            'x_channels.json': [],
            'youtube_channels.json': [],
            'channel_monitor_enabled.json': False,
            'channel_events.json': [],
            'default_values.json': {},
            'user_data.json': {},
            'settings.json': self.settings,
            'channels.json': [],
            'channel_admins.json': {},
            'protected_channels.json': [],  # اضافه شده
            'security_logs.json': [],  # اضافه شده
            'uploader_channels.json': [],
            'admins.json': [OWNER_ID],
            'admin_permissions.json': self.admin_permissions,
            'timer_settings.json': self.timer_settings,
            'uploader_files.json': {},
            'stats.json': {
                "uploader_files_total": 0,
                "uploader_files_total_size_mb": 0.0,
                "last_updated": "",
            },
            'forced_channels.json': [],
            'forced_seen_channels.json': [],
            'forced_reaction_channels.json': [],
            'uploader_auto_rename.json': {},
            'exec_options.json': {
                "rename": False,
                "filter": False
            },
            'scheduled_posts.json': [],
            'broadcast_users.json': [],
            'scheduled_broadcasts.json': [],
        }
        # ایجاد و مقداردهی فایل‌های جیسون
        for file_name, default_content in default_files.items():
            file_path = os.path.join(self.base_folder, file_name)
            if not os.path.exists(file_path):
                try:
                    with open(file_path, 'w', encoding='utf-8') as f:
                        json.dump(default_content, f, ensure_ascii=False, indent=4)
                    logger.info(f"[DataStore] Created {file_name} with default content.")
                except Exception as e:
                    logger.error(f"[DataStore] Failed to create {file_name}: {e}")
            else:
                logger.info(f"[DataStore] {file_name} already exists, skipped.")

        # ایجاد فایل‌های متنی مورد نیاز
        text_files = [
            ('forced_join_message.txt', "برای استفاده از ربات باید در چنل‌های زیر عضو باشید:"),
            ('forced_seen_message.txt', "برای استفاده از ربات باید {count} پست آخر چنل را سین کنید و سپس روی دکمه «زدم» بزنید."),
            ('forced_seen_count.txt', "5"),
            ('forced_reaction_count.txt', "2"),
        ]
        for file_name, default_text in text_files:
            file_path = os.path.join(self.base_folder, file_name)
            if not os.path.exists(file_path):
                try:
                    with open(file_path, "w", encoding="utf-8") as f:
                        f.write(default_text)
                    logger.info(f"[DataStore] Created {file_name} with default text.")
                except Exception as e:
                    logger.error(f"[DataStore] Failed to create {file_name}: {e}")
            else:
                logger.info(f"[DataStore] {file_name} already exists, skipped.")
                
    def load_data(self):
        logger = logging.getLogger("DataStore")
        def _load(file, attr, default):
            path = os.path.join(self.base_folder, file)
            try:
                if os.path.exists(path):
                    if file.endswith('.txt'):
                        with open(path, 'r', encoding='utf-8') as f:
                            setattr(self, attr, f.read().strip())
                    else:
                        with open(path, 'r', encoding='utf-8') as f:
                            setattr(self, attr, json.load(f))
                    logger.info(f"[DataStore] {file} → {attr} [OK]")
                else:
                    setattr(self, attr, default)
                    logger.warning(f"[DataStore] {file} → {attr} [NOT FOUND, default]")
            except Exception as e:
                setattr(self, attr, default)
                logger.error(f"[DataStore] {file} → {attr} [ERROR: {e}]")
    
        # جیسون‌های اصلی
        _load('signatures.json', 'signatures', {})
        _load('variables.json', 'variables', {})
        _load('default_values.json', 'default_values', {})
        _load('user_data.json', 'user_data', {})
        _load('scheduled_broadcasts.json', 'scheduled_broadcasts', [])
        _load('settings.json', 'settings', {})
        _load('channels.json', 'channels', [])
        _load('channel_admins.json', 'channel_admins', {})
        _load('protected_channels.json', 'protected_channels', [])  # اضافه شده
        _load('security_logs.json', 'security_logs', [])  # اضافه شده
        _load('channel_monitor_enabled.json', 'channel_monitor_enabled', False)
        _load('channel_events.json', 'channel_events', [])
        _load('uploader_channels.json', 'uploader_channels', [])
        _load('uploader_files.json', 'uploader_file_map', {})
        _load('admins.json', 'admins', [])
        _load('admin_permissions.json', 'admin_permissions', {})
        _load('timer_settings.json', 'timer_settings', {})
        _load('forced_channels.json', 'forced_channels', [])
        _load('forced_seen_channels.json', 'forced_seen_channels', [])
        _load('forced_reaction_channels.json', 'forced_reaction_channels', [])
        _load('uploader_auto_rename.json', 'uploader_auto_rename', {})
        _load('exec_options.json', 'auto_exec_options', {})
        _load('scheduled_posts.json', 'scheduled_posts', [])
        _load('broadcast_users.json', 'broadcast_users', [])
    
        # اطمینان از وجود کلید جدید در timer_settings (در صورت نبود)
        if not hasattr(self, "timer_settings") or not isinstance(self.timer_settings, dict):
            self.timer_settings = {}
        if "delete_upload_file_timeout" not in self.timer_settings:
            self.timer_settings["delete_upload_file_timeout"] = 60  # مقدار پیش‌فرض 60 ثانیه
    
        # فایل‌های متنی و خاص
        txt_files = [
            ('forced_join_message.txt', 'forced_join_message', "برای استفاده از ربات باید در چنل‌های زیر عضو باشید:"),
            ('forced_seen_message.txt', 'forced_seen_message', "برای استفاده از ربات باید {count} پست آخر چنل را سین کنید و سپس روی دکمه «زدم» بزنید."),
            ('forced_seen_count.txt', 'forced_seen_count', 5),
            ('forced_reaction_count.txt', 'forced_reaction_count', 2),
        ]
        for fname, attr, default in txt_files:
            try:
                path = os.path.join(self.base_folder, fname)
                if os.path.exists(path):
                    with open(path, 'r', encoding='utf-8') as f:
                        val = f.read()
                        if fname.endswith('_count.txt'):
                            val = int(val)
                        setattr(self, attr, val)
                    logger.info(f"[DataStore] {fname} [OK]")
                else:
                    setattr(self, attr, default)
                    logger.warning(f"[DataStore] {fname} [NOT FOUND, default]")
            except Exception as e:
                setattr(self, attr, default)
                logger.warning(f"[DataStore] {fname} [FAIL, default] {e}")
    
        # stats.json
        stats_path = os.path.join(self.base_folder, 'stats.json')
        if os.path.exists(stats_path):
            try:
                with open(stats_path, 'r', encoding='utf-8') as f:
                    stats = json.load(f)
                    self.uploader_files_total = stats.get('uploader_files_total', 0)
                    self.uploader_files_total_size_mb = stats.get('uploader_files_total_size_mb', 0.0)
            except Exception as e:
                self.uploader_files_total = 0
                self.uploader_files_total_size_mb = 0.0
        else:
            self.uploader_files_total = 0
            self.uploader_files_total_size_mb = 0.0
    
        # auto_exec_options.json
        exec_options_path = os.path.join(self.base_folder, "auto_exec_options.json")
        if os.path.exists(exec_options_path):
            try:
                with open(exec_options_path, "r", encoding="utf-8") as f:
                    self.auto_exec_options = json.load(f)
                logger.info("[DataStore] auto_exec_options.json [OK]")
            except Exception as e:
                self.auto_exec_options = {"rename": False, "filter": False}
                logger.warning(f"[DataStore] auto_exec_options.json [FAIL, default] {e}")
        else:
            self.auto_exec_options = {"rename": False, "filter": False}
            logger.warning("[DataStore] auto_exec_options.json [NOT FOUND, default]")
    
        logger.info("✅ [DataStore] load_data کاملاً اجرا شد و همه داده‌ها بارگذاری شدند.")
        
    def save_data(self):
        logger = logging.getLogger("DataStore")
        def _save(file, value):
            path = os.path.join(self.base_folder, file)
            try:
                if file.endswith('.txt'):
                    with open(path, 'w', encoding='utf-8') as f:
                        f.write(str(value))
                else:
                    with open(path, 'w', encoding='utf-8') as f:
                        json.dump(value, f, ensure_ascii=False, indent=4)
            except OSError as e:
                if e.errno == 122:  # Disk quota exceeded
                    logger.error(f"[DiskQuota] فضای دیسک پر شده و فایل {file} ذخیره نشد.")
                    # اطلاع به OWNER_ID اگر bot موجود بود:
                    try:
                        if 'bot' in globals():
                            bot.send_message(OWNER_ID, f"❌ [DiskQuota] فضای دیسک پر است و ذخیره فایل `{file}` ممکن نیست.", parse_mode="HTML")
                    except Exception:
                        pass
                else:
                    logger.error(f"[DataStore] خطای ذخیره‌سازی {file}: {e}")
    
        # لیست کامل جیسون/تکست‌ها
        _save('signatures.json', self.signatures)
        _save('variables.json', getattr(self, 'variables', {}))
        _save('default_values.json', self.default_values)
        _save('user_data.json', self.user_data)
        _save('scheduled_broadcasts.json', self.scheduled_broadcasts)
        _save('settings.json', self.settings)
        _save('channels.json', self.channels)
        _save('channel_monitor_enabled.json', self.channel_monitor_enabled)
        _save('channel_events.json', self.channel_events)
        _save('channel_admins.json', getattr(self, 'channel_admins', {}))
        _save('protected_channels.json', getattr(self, 'protected_channels', []))  # اضافه شده
        _save('security_logs.json', getattr(self, 'security_logs', []))  # اضافه شده
        _save('uploader_channels.json', self.uploader_channels)
        _save('uploader_files.json', self.uploader_file_map)
        _save('admins.json', self.admins)
        _save('admin_permissions.json', self.admin_permissions)
        _save('timer_settings.json', self.timer_settings)
        _save('forced_channels.json', self.forced_channels)
        _save('forced_seen_channels.json', self.forced_seen_channels)
        _save('forced_reaction_channels.json', self.forced_reaction_channels)
        _save('forced_seen_message.txt', self.forced_seen_message)
        _save('forced_join_message.txt', self.forced_join_message)
        _save('forced_seen_count.txt', self.forced_seen_count)
        _save('forced_reaction_count.txt', self.forced_reaction_count)
        _save('uploader_auto_rename.json', getattr(self, 'uploader_auto_rename', {}))
        _save('exec_options.json', getattr(self, 'auto_exec_options', {}))
        _save('scheduled_posts.json', getattr(self, 'scheduled_posts', []))
        _save('broadcast_users.json', getattr(self, 'broadcast_users', []))
        _save('forced_channels.json', getattr(self, 'forced_channels', []))
        _save('forced_seen_channels.json', getattr(self, 'forced_seen_channels', []))
        _save('forced_reaction_channels.json', getattr(self, 'forced_reaction_channels', []))
        _save('scheduled_broadcasts.json', getattr(self, 'scheduled_broadcasts', []))
    
        # آمار اپلودر
        stats = {
            "uploader_files_total": getattr(self, 'uploader_files_total', 0),
            "uploader_files_total_size_mb": getattr(self, 'uploader_files_total_size_mb', 0.0),
            "last_updated": "",
        }
        _save('stats.json', stats)
        self.save_exec_options()
        # ... طبق قبل برای همه فایل‌ها
        logger.info("[DataStore] All files saved in save_data.")
    def remember(self):
        """
        همه جیسون‌ها و تکست‌های دیتاستور را با ساختار فعلی کلاس سینک می‌کند:
        - کلیدهای جدید را اضافه می‌کند (با مقدار پیش‌فرض یا تهی)
        - کلیدهای حذف‌شده را پاک می‌کند
        - فایل‌های متنی هم اگر مقدار جدید دارند، آپدیت می‌شوند
        """
        # لیست کامل فایل‌های داده‌ای که باید سینک شوند
        files_structure = {
            'signatures.json': self.signatures,
            'variables.json': getattr(self, 'variables', {}),
            'default_values.json': self.default_values,
            'user_data.json': self.user_data,
            'scheduled_broadcasts.json': self.scheduled_broadcasts,
            'settings.json': self.settings,
            'channels.json': self.channels,
            'protected_channels.json': getattr(self, 'protected_channels', []),  # اضافه شده
            'security_logs.json': getattr(self, 'security_logs', []),  # اضافه شده
            'uploader_channels.json': self.uploader_channels,
            'uploader_files.json': self.uploader_file_map,
            'admins.json': self.admins,
            'admin_permissions.json': self.admin_permissions,
            'timer_settings.json': self.timer_settings,
            'forced_channels.json': self.forced_channels,
            'forced_seen_channels.json': self.forced_seen_channels,
            'forced_reaction_channels.json': self.forced_reaction_channels,
            'uploader_auto_rename.json': getattr(self, 'uploader_auto_rename', {}),
            'exec_options.json': getattr(self, 'auto_exec_options', {}),
            'stats.json': {
                "uploader_files_total": getattr(self, 'uploader_files_total', 0),
                "uploader_files_total_size_mb": getattr(self, 'uploader_files_total_size_mb', 0.0),
                "last_updated": "",
            },
            'scheduled_posts.json': getattr(self, 'scheduled_posts', []),
            'broadcast_users.json': getattr(self, 'broadcast_users', []),
            'forced_join_message.txt': getattr(self, 'forced_join_message', ""),
            'forced_seen_message.txt': getattr(self, 'forced_seen_message', ""),
            'forced_seen_count.txt': str(getattr(self, 'forced_seen_count', 5)),
            'forced_reaction_count.txt': str(getattr(self, 'forced_reaction_count', 2)),
            # اضافه کن اگر دیتای جدیدی به پروژه اضافه کردی!
        }

        for file, current_data in files_structure.items():
            path = os.path.join(self.base_folder, file)
            if file.endswith('.json'):
                try:
                    if os.path.exists(path):
                        with open(path, 'r', encoding='utf-8') as f:
                            disk_data = json.load(f)
                    else:
                        disk_data = {} if isinstance(current_data, dict) else []
                except Exception:
                    disk_data = {} if isinstance(current_data, dict) else []

                # فقط دیکشنری‌ها و لیست‌ها را سینک کن
                if isinstance(current_data, dict) and isinstance(disk_data, dict):
                    # اضافه: کلید جدید
                    for k in current_data.keys():
                        if k not in disk_data:
                            disk_data[k] = current_data[k]
                    # حذف: کلید حذف‌شده
                    for k in list(disk_data.keys()):
                        if k not in current_data:
                            del disk_data[k]
                    # مقداردهی مجدد به حافظه
                    files_structure[file] = disk_data
                elif isinstance(current_data, list) and isinstance(disk_data, list):
                    # اگر لیست باید migration خاصی داشته باشد، اینجا انجام بده
                    # فعلاً فقط یکنواخت‌سازی
                    files_structure[file] = disk_data
                # ذخیره مجدد
                with open(path, 'w', encoding='utf-8') as f:
                    json.dump(disk_data, f, ensure_ascii=False, indent=4)
                logger.info(f"[DataStore] Synced {file} in remember.")
            elif file.endswith('.txt'):
                try:
                    with open(path, 'w', encoding='utf-8') as f:
                        f.write(str(current_data))
                    logger.info(f"[DataStore] Synced {file} (txt) in remember.")
                except Exception as e:
                    logger.error(f"[DataStore] Failed to sync {file} (txt) in remember: {e}")

        logger.info("[DataStore] remember completed for all files.")
        self.load_data()
        self.save_data()
    # --- NEW: save just exec options and pack type ---
    def save_exec_options(self):
        try:
            with open(self.exec_options_path, "w", encoding="utf-8") as f:
                json.dump(self.auto_exec_options, f, ensure_ascii=False, indent=4)
        except OSError as e:
            if e.errno == 122:
                logger.error("[DiskQuota] فضای دیسک پر شده و exec_options ذخیره نشد.")
                try:
                    if 'bot' in globals():
                        bot.send_message(OWNER_ID, "❌ [DiskQuota] فضای دیسک پر است و ذخیره exec_options ممکن نیست.", parse_mode="HTML")
                except Exception:
                    pass
            else:
                logger.error(f"[DataStore] خطا در ذخیره exec_options: {e}")

    def get_user_state(self, user_id):
        user_id = str(user_id)
        if user_id not in self.user_states:
            self.user_states[user_id] = {
                "state": None,
                "data": {}
            }
        return self.user_states[user_id]

    def update_user_state(self, user_id, state=None, data=None):
        user_id = str(user_id)
        if user_id not in self.user_states:
            self.user_states[user_id] = {
                "state": None,
                "data": {}
            }
        if state is not None:
            self.user_states[user_id]["state"] = state
        if data is not None:
            self.user_states[user_id]["data"].update(data)

    def reset_user_state(self, user_id):
        user_id = str(user_id)
        self.user_states[user_id] = {
            "state": None,
            "data": {}
        }

    def add_security_log(self, log_entry):
        """اضافه کردن لاگ امنیتی"""
        if not hasattr(self, 'security_logs'):
            self.security_logs = []
        
        self.security_logs.append(log_entry)
        
        # نگهداری فقط 1000 لاگ آخر
        if len(self.security_logs) > 1000:
            self.security_logs = self.security_logs[-1000:]
        
        self.save_data()

    def get_security_settings(self):
        """دریافت تنظیمات امنیتی"""
        if not hasattr(self, 'security_settings'):
            self.security_settings = {
                'enabled': True,
                'response_time': 5,
                'sensitivity_level': 'متوسط',
                'instant_notify': True,
                'auto_demote': True,
                'action_delay': 3,
                'sound_alert': True,
                'alert_member_removal': True,
                'alert_admin_removal': True,
                'alert_settings_change': True,
                'alert_promotion': True
            }
        return self.security_settings

    def set_security_settings(self, settings):
        """تنظیم تنظیمات امنیتی"""
        self.security_settings = settings
        self.save_data()

    def get_admin_trust_level(self, admin_id):
        """محاسبه سطح اعتماد ادمین"""
        logs = getattr(self, 'security_logs', [])
        admin_logs = [log for log in logs if log.get('admin_id') == int(admin_id)]
        
        if not admin_logs:
            return "جدید"
        
        # محاسبه بر اساس تعداد فعالیت‌های مشکوک
        suspicious_count = len([log for log in admin_logs if log.get('danger_level', 0) >= 2])
        
        if suspicious_count == 0:
            return "بالا"
        elif suspicious_count <= 2:
            return "متوسط"
        else:
            return "پایین"
 
data_store = DataStore(base_folder="central_data", token=TOKEN)

def is_owner(user_id):
    return user_id == OWNER_ID

def is_admin(user_id):
    return user_id in data_store.admins

def get_bot_token_from_folder(base_folder):
    token_file = os.path.join(base_folder, "bot_token.txt")
    with open(token_file, "r", encoding="utf-8") as f:
        return f.read().strip()

# منوی مدیریت ادمین‌ها
def get_admin_management_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    add_admin_btn = types.KeyboardButton("➕ افزودن ادمین")
    remove_admin_btn = types.KeyboardButton("➖ حذف ادمین")
    list_admins_btn = types.KeyboardButton("👀 لیست ادمین‌ها")
    permissions_btn = types.KeyboardButton("🔧 تنظیم دسترسی ادمین‌ها")
    block_user_btn = types.KeyboardButton("🚫 بلاک کاربران")
    unblock_user_btn = types.KeyboardButton("✅ رفع بلاک کاربران")
    block_list_btn = types.KeyboardButton("📋 لیست کاربران بلاک")
    back_btn = types.KeyboardButton("🔙 بازگشت به منوی اصلی")
    markup.add(add_admin_btn, remove_admin_btn)
    markup.add(list_admins_btn, permissions_btn)
    markup.add(block_user_btn, unblock_user_btn)
    markup.add(block_list_btn)
    markup.add(back_btn)
    return markup
    
def get_main_menu(user_id):
    def add_in_pairs(markup, btns):
        for i in range(0, len(btns), 2):
            if i+1 < len(btns):
                markup.add(btns[i], btns[i+1])
            else:
                markup.add(btns[i])
    
    if is_owner(user_id) or (is_admin(user_id) and data_store.admin_permissions.get(str(user_id), {}).get("options_management", False)):
        markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
        btns = [
            types.KeyboardButton("🆕 ایجاد پست"),
            types.KeyboardButton("📤 اپلودر"),
            types.KeyboardButton("📣 ارسال همگانی"),
            types.KeyboardButton("🤖 ربات ساز"),
            types.KeyboardButton("👥 مدیریت کاربران"),
            types.KeyboardButton("⚡️ امکانات اجباری"),
            types.KeyboardButton("🛡 مدیریت چنل"),  # ← دکمه جدید
            types.KeyboardButton("🛒 کرکفای"),
            types.KeyboardButton("🏛 تنظیمات ربات"),
            types.KeyboardButton("⏰ مدیریت تایمرها"),
            types.KeyboardButton("👤 حساب کاربری"),
            types.KeyboardButton("🗄 پشتیبان گیری"),
        ]
        add_in_pairs(markup, btns)
        markup.add(types.KeyboardButton(f"🤖 بات دستیار نسخه {BOT_VERSION}"))
        return markup
    elif user_id in data_store.admins:
        permissions = data_store.admin_permissions.get(str(user_id), {})
        markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
        btns = []
        if permissions.get("create_post"):
            btns.append(types.KeyboardButton("🆕 ایجاد پست"))
        if permissions.get("uploader_management"):
            btns.append(types.KeyboardButton("📤 اپلودر"))
        if permissions.get("admin_management"):
            btns.append(types.KeyboardButton("👥 مدیریت کاربران"))
        if permissions.get("broadcast_management"):
            btns.append(types.KeyboardButton("📣 ارسال همگانی"))
        if permissions.get("bot_creator"):
            btns.append(types.KeyboardButton("🤖 ربات ساز"))
        if permissions.get("manage_channel"):
            btns.append(types.KeyboardButton("🛡 مدیریت چنل"))
        if permissions.get("forced_management"):
            btns.append(types.KeyboardButton("⚡️ امکانات اجباری"))
        if permissions.get("manage_timers"):
            btns.append(types.KeyboardButton("⏰ مدیریت تایمرها"))
        if permissions.get("options_management"):
            btns.append(types.KeyboardButton("🏛 تنظیمات ربات"))
        if permissions.get("trust"):
            btns.append(types.KeyboardButton("🗄 پشتیبان گیری"))
        btns.append(types.KeyboardButton("🛒 کرکفای"))
        btns.append(types.KeyboardButton("👤 حساب کاربری"))
        add_in_pairs(markup, btns)
        markup.add(types.KeyboardButton(f"🤖 بات دستیار نسخه {BOT_VERSION}"))
        return markup
    else:
        markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
        btns = [
            types.KeyboardButton("👤 حساب کاربری"),
            types.KeyboardButton("🛒 کرکفای"),
        ]
        add_in_pairs(markup, btns)
        markup.add(types.KeyboardButton(f"🤖 بات دستیار نسخه {BOT_VERSION}"))
        return markup
    
# منوی بازگشت برای راحتی کاربر
def get_back_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    back_btn = types.KeyboardButton("🔙 بازگشت به منوی اصلی")
    markup.add(back_btn)
    return markup

# منوی انتخاب نحوه نمایش کلیدهای شیشه‌ای
def get_button_layout_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    inline_btn = types.KeyboardButton("📏 به کنار")
    stacked_btn = types.KeyboardButton("📐 به پایین")
    markup.add(inline_btn, stacked_btn)
    markup.add(types.KeyboardButton("🔙 بازگشت به منوی اصلی"))
    return markup

#==========================================================
#===========================مدیریت کاربران======================
#==========================================================

@bot.message_handler(func=lambda m: data_store.get_user_state(m.from_user.id)["state"] == "admin_management")
def handle_admin_management_menu(message):
    user_id = message.from_user.id
    text = message.text

    # هندلینگ دکمه بازگشت به منوی اصلی
    if text == "🔙 بازگشت به منوی اصلی":
        data_store.reset_user_state(user_id)
        bot.send_message(user_id, "🏠 بازگشت به منوی اصلی:", reply_markup=get_main_menu(user_id))
        return

    # دکمه‌های مدیریت ادمین‌ها را به تابع اصلی هندلر ارجاع بده
    if text in ["➕ افزودن ادمین", "➖ حذف ادمین", "👀 لیست ادمین‌ها", "🔧 تنظیم دسترسی ادمین‌ها"]:
        handle_admin_management(user_id, text)
        return

    if text == "🚫 بلاک کاربران":
        data_store.update_user_state(user_id, "block_user_ask_id")
        msg = bot.send_message(user_id, "آیدی عددی کاربری که می‌خواهید بلاک شود را وارد کنید:", reply_markup=get_back_menu())
        data_store.last_message_id[user_id] = msg.message_id
        return

    if text == "✅ رفع بلاک کاربران":
        data_store.update_user_state(user_id, "unblock_user_ask_id")
        msg = bot.send_message(user_id, "آیدی عددی کاربری که می‌خواهید رفع بلاک شود را وارد کنید:", reply_markup=get_back_menu())
        data_store.last_message_id[user_id] = msg.message_id
        return

    if text == "📋 لیست کاربران بلاک":
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(types.InlineKeyboardButton("لیست بلاک شده توسط اونر", callback_data="blocklist_owner"))
        markup.add(types.InlineKeyboardButton("لیست بلاک شده توسط ربات", callback_data="blocklist_bot"))
        bot.send_message(user_id, "لیست مورد نظر را انتخاب کنید:", reply_markup=markup)
        return

@bot.message_handler(func=lambda m: data_store.get_user_state(m.from_user.id)["state"] == "block_user_ask_id")
def handle_block_user(message):
    user_id = message.from_user.id
    target_id = message.text.strip()
    if not target_id.isdigit():
        bot.send_message(user_id, "آیدی عددی صحیح وارد کنید.", reply_markup=get_back_menu())
        return
    target_id = str(target_id)
    # تغییر: اگر کاربر قبلاً در دیتابیس نیست اضافه کن
    if target_id not in data_store.user_data:
        data_store.user_data[target_id] = {
            "first_name": "",
            "last_name": "",
            "username": "",
            "join_date": "",
            "is_active": False,
            "stage": "",
            "status": "",
            "maram": False,
            "is_blocked_by_owner": True
        }
    else:
        data_store.user_data[target_id]["is_blocked_by_owner"] = True
    data_store.save_data()
    bot.send_message(user_id, f"کاربر {target_id} بلاک شد.", reply_markup=get_admin_management_menu())
    data_store.update_user_state(user_id, "admin_management")

@bot.message_handler(func=lambda m: data_store.get_user_state(m.from_user.id)["state"] == "unblock_user_ask_id")
def handle_unblock_user(message):
    user_id = message.from_user.id
    target_id = message.text.strip()
    if not target_id.isdigit():
        bot.send_message(user_id, "آیدی عددی صحیح وارد کنید.", reply_markup=get_back_menu())
        return
    target_id = str(target_id)
    user_info = data_store.user_data.get(target_id)
    if not user_info:
        bot.send_message(user_id, "کاربر یافت نشد.", reply_markup=get_back_menu())
        return
    # فقط اگر بلاک باشد رفع بلاک شود
    if user_info.get("is_blocked_by_owner", False) or user_info.get("is_blocked", False):
        user_info["is_blocked_by_owner"] = False
        user_info["is_blocked"] = False
        data_store.save_data()
        bot.send_message(user_id, f"✅ کاربر با آیدی عددی {target_id} رفع بلاک شد.", reply_markup=get_admin_management_menu())
        try:
            bot.send_message(int(target_id), "✅ شما از بلاکی درآمدید و اکنون آزاد هستید. می‌توانید دوباره از ربات استفاده کنید.")
        except Exception: pass
    else:
        bot.send_message(user_id, "❗️ این کاربر بلاک نیست.", reply_markup=get_admin_management_menu())

def get_blocked_users_list(block_type, page=0, users_per_page=8):
    all_users = list(data_store.user_data.items())
    if block_type == "owner":
        blocked = [(uid, udata) for uid, udata in all_users if udata.get("is_blocked_by_owner")]
        title = "لیست کاربران بلاک شده توسط اونر"
    else:
        blocked = [(uid, udata) for uid, udata in all_users if udata.get("is_blocked", False)]
        title = "لیست کاربران بلاک شده توسط ربات"
    total = len(blocked)
    if total == 0:
        return f"<b>{title}</b>\n\nلیست بلاک خالی است!", None
    start = page * users_per_page
    end = start + users_per_page
    page_blocked = blocked[start:end]
    text = f"<b>{title}</b>\n"
    for uid, udata in page_blocked:
        username = udata.get("username", "ندارد")
        text += f"\nآیدی عددی: <code>{uid}</code> | یوزرنیم: @{username}"
    text += f"\n\nصفحه {page+1} از {((total-1)//users_per_page)+1}"
    markup = types.InlineKeyboardMarkup(row_width=2)
    if page > 0:
        markup.add(types.InlineKeyboardButton("قبلی", callback_data=f"{block_type}_blocklist_prev_{page-1}"))
    if end < total:
        markup.add(types.InlineKeyboardButton("بعدی", callback_data=f"{block_type}_blocklist_next_{page+1}"))
    for uid, _ in page_blocked:
        markup.add(types.InlineKeyboardButton("رفع بلاک", callback_data=f"unblock_{block_type}_{uid}"))
        markup.add(types.InlineKeyboardButton("ارسال پیام", callback_data=f"sendmsg_{uid}"))
    return text, markup

@bot.callback_query_handler(func=lambda call: call.data.startswith("blocklist_"))
def handle_blocklist_callback(call):
    user_id = call.from_user.id
    block_type = "owner" if "owner" in call.data else "bot"
    text, markup = get_blocked_users_list(block_type, page=0)
    if markup:
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="HTML")
    else:
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, parse_mode="HTML")

@bot.callback_query_handler(func=lambda call: call.data.startswith(("owner_blocklist_next_", "owner_blocklist_prev_", "bot_blocklist_next_", "bot_blocklist_prev_")))
def handle_blocklist_page_callback(call):
    user_id = call.from_user.id
    m = re.match(r"(owner|bot)_blocklist_(?:next|prev)_(\d+)", call.data)
    if m:
        block_type, page = m.group(1), int(m.group(2))
        text, markup = get_blocked_users_list(block_type, page)
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="HTML")

@bot.callback_query_handler(func=lambda call: call.data.startswith("unblock_owner_"))
def handle_unblock_owner_callback(call):
    uid = call.data.replace("unblock_owner_", "")
    if uid in data_store.user_data:
        data_store.user_data[uid]["is_blocked_by_owner"] = False
        data_store.save_data()
        bot.answer_callback_query(call.id, text="رفع بلاک شد")
    else:
        bot.answer_callback_query(call.id, text="کاربر یافت نشد", show_alert=True)

@bot.callback_query_handler(func=lambda call: call.data.startswith("unblock_bot_"))
def handle_unblock_bot_callback(call):
    uid = call.data.replace("unblock_bot_", "")
    if uid in data_store.user_data:
        data_store.user_data[uid]["is_blocked"] = False
        data_store.save_data()
        bot.answer_callback_query(call.id, text="رفع بلاک شد")
    else:
        bot.answer_callback_query(call.id, text="کاربر یافت نشد", show_alert=True)

@bot.callback_query_handler(func=lambda call: call.data.startswith("sendmsg_"))
def handle_sendmsg_callback(call):
    uid = call.data.replace("sendmsg_", "")
    data_store.update_user_state(call.from_user.id, "send_message_to_blocked", {"blocked_id": uid})
    bot.send_message(call.from_user.id, f"متن پیام برای کاربر بلاک شده <code>{uid}</code> را وارد کنید:", parse_mode="HTML")

def get_admin_permissions_menu(admin_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    permissions = data_store.admin_permissions.get(str(admin_id), {
        "create_post": False,
        "admin_management": False,
        "uploader_management": False,
        "broadcast_management": False,
        "bot_creator": False,
        "user_account": False,
        "forced_management": False,
        "trust": False,
        "manage_channel" : False,
        "manage_timers" : False,
        "options_management": False
    })
    markup.add(
        types.KeyboardButton(f"{'✅' if permissions.get('create_post', False) else '❌'} ایجاد پست"),
        types.KeyboardButton(f"{'✅' if permissions.get('options_management', False) else '❌'} تنظیمات ربات")
    )
    markup.add(
        types.KeyboardButton(f"{'✅' if permissions.get('admin_management', False) else '❌'} مدیریت ادمین‌ها"),
        types.KeyboardButton(f"{'✅' if permissions.get('uploader_management', False) else '❌'} اپلودر")
    )
    markup.add(
        types.KeyboardButton(f"{'✅' if permissions.get('broadcast_management', False) else '❌'} ارسال همگانی"),
        types.KeyboardButton(f"{'✅' if permissions.get('bot_creator', False) else '❌'} ربات ساز")
    )
    markup.add(
        types.KeyboardButton(f"{'✅' if permissions.get('manage_channel', False) else '❌'} مدیریت چنل"),
        types.KeyboardButton(f"{'✅' if permissions.get('user_account', False) else '❌'} حساب کاربری")
    )
    markup.add(
        types.KeyboardButton(f"{'✅' if permissions.get('forced_management', False) else '❌'} امکانات اجباری"),
        types.KeyboardButton(f"{'✅' if permissions.get('trust', False) else '❌'} پشتیبان گیری")
    )
    markup.add(
        types.KeyboardButton(f"{'✅' if permissions.get('manage_timers', False) else '❌'} مدیریت تایمرها"),
    )
    markup.add(types.KeyboardButton("🔙 بازگشت به مدیریت کاربران"))
    return markup

# مدیریت ادمین‌ها
def handle_admin_management(user_id, text):
    user_state = data_store.get_user_state(user_id)
    state = user_state["state"]
    
    logger.info(f"پردازش پیام در handle_admin_management، متن: '{text}'، حالت: {state}")
    
    if text == "➕ افزودن ادمین":
        logger.info(f"تغییر حالت به add_admin برای کاربر {user_id}")
        data_store.update_user_state(user_id, "add_admin")
        msg = bot.send_message(user_id, f"🖊️ آیدی عددی کاربر را برای افزودن به ادمین‌ها وارد کنید:", reply_markup=get_back_menu())
        data_store.last_message_id[user_id] = msg.message_id
            
    elif text == "➖ حذف ادمین":
        logger.info(f"تغییر حالت به remove_admin برای کاربر {user_id}")
        if len(data_store.admins) <= 1:  # جلوگیری از حذف تنها ادمین (اونر)
            msg = bot.send_message(user_id, f"⚠️ حداقل یک ادمین (اونر) باید باقی بماند.", reply_markup=get_admin_management_menu())
            data_store.last_message_id[user_id] = msg.message_id
            return
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        for admin_id in data_store.admins:
            if admin_id != OWNER_ID:  # اونر قابل حذف نیست
                markup.add(types.KeyboardButton(str(admin_id)))
        markup.add(types.KeyboardButton("🔙 بازگشت به منوی اصلی"))
        data_store.update_user_state(user_id, "remove_admin")
        msg = bot.send_message(user_id, f"🗑️ آیدی ادمینی که می‌خواهید حذف کنید را انتخاب کنید:", reply_markup=markup)
        data_store.last_message_id[user_id] = msg.message_id
    
    elif text == "👀 لیست ادمین‌ها":
        logger.info(f"نمایش لیست ادمین‌ها برای کاربر {user_id}")
        admins_text = f"👤 لیست ادمین‌ها:\n\n"
        if not data_store.admins:
            admins_text += "هیچ ادمینی وجود ندارد.\n"
        else:
            for admin_id in data_store.admins:
                admins_text += f"🔹 آیدی: {admin_id}\n"
        msg = bot.send_message(user_id, admins_text, reply_markup=get_admin_management_menu())
        data_store.last_message_id[user_id] = msg.message_id
        data_store.update_user_state(user_id, "admin_management")

    elif text == "🔧 تنظیم دسترسی ادمین‌ها":
            if not data_store.admins:
                try:
                    bot.edit_message_text(
                        chat_id=user_id,
                        message_id=data_store.last_message_id.get(user_id, 0),
                        text=f"⚠️ هیچ ادمینی وجود ندارد.",
                        reply_markup=get_admin_management_menu()
                    )
                except Exception as e:
                    logger.error(f"خطا در ویرایش پیام: {e}")
                    msg = bot.send_message(user_id, f"⚠️ هیچ ادمینی وجود ندارد.", reply_markup=get_admin_management_menu())
                    data_store.last_message_id[user_id] = msg.message_id
                return
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
            for admin_id in data_store.admins:
                markup.add(types.KeyboardButton(str(admin_id)))
            markup.add(types.KeyboardButton("🔙 بازگشت به مدیریت کاربران"))
            data_store.update_user_state(user_id, "select_admin_for_permissions")
            msg = bot.send_message(user_id, f"🔧 آیدی ادمینی که می‌خواهید دسترسی‌هایش را تنظیم کنید را انتخاب کنید:", reply_markup=markup)
            data_store.last_message_id[user_id] = msg.message_id
        
    elif state == "select_admin_for_permissions":
        try:
            admin_id = int(text.strip())
            if admin_id == OWNER_ID:
                msg = bot.send_message(user_id, f"⚠️ دسترسی‌های اونر قابل تغییر نیست.", reply_markup=get_admin_management_menu())
                data_store.last_message_id[user_id] = msg.message_id
                data_store.update_user_state(user_id, "admin_management")
                return
            if admin_id in data_store.admins:
                data_store.update_user_state(user_id, "manage_admin_permissions", {"selected_admin_id": admin_id})
                msg = bot.send_message(user_id, f"🔧 تنظیم دسترسی‌های ادمین {admin_id}:", reply_markup=get_admin_permissions_menu(admin_id))
                data_store.last_message_id[user_id] = msg.message_id
            else:
                msg = bot.send_message(user_id, f"⚠️ این آیدی در لیست ادمین‌ها نیست.", reply_markup=get_admin_management_menu())
                data_store.last_message_id[user_id] = msg.message_id
                data_store.update_user_state(user_id, "admin_management")
        except ValueError:
            msg = bot.send_message(user_id, f"⚠️ لطفاً یک آیدی عددی معتبر وارد کنید.", reply_markup=get_admin_management_menu())
            data_store.last_message_id[user_id] = msg.message_id
    
    elif state == "manage_admin_permissions":
        admin_id = user_state["data"]["selected_admin_id"]
        permissions = data_store.admin_permissions.get(str(admin_id), {
            "create_post": False,
            "admin_management": False,
            "uploader_management": False,
            "broadcast_management": False,
            "bot_creator": False,
            "user_account": False,
            "forced_management": False,
            "trust": False,
            "manage_channel" : False,
            "manage_timers" : False,
            "options_management": False
        })
        permission_map = {
            "✅ ایجاد پست": ("create_post", True),
            "❌ ایجاد پست": ("create_post", False),
            "✅ مدیریت ادمین‌ها": ("admin_management", True),
            "❌ مدیریت ادمین‌ها": ("admin_management", False),
            "✅ اپلودر": ("uploader_management", True),
            "❌ اپلودر": ("uploader_management", False),
            "✅ ارسال همگانی": ("broadcast_management", True),
            "❌ ارسال همگانی": ("broadcast_management", False),
            "✅ ربات ساز": ("bot_creator", True),
            "❌ ربات ساز": ("bot_creator", False),
            "✅ حساب کاربری": ("user_account", True),
            "❌ حساب کاربری": ("user_account", False),
            "✅ امکانات اجباری": ("forced_management", True),
            "❌ امکانات اجباری": ("forced_management", False),
            "✅ پشتیبان گیری": ("trust", True),
            "❌ پشتیبان گیری": ("trust", False),
            "✅ مدیریت چنل": ("manage_channel", True),
            "❌ مدیریت چنل": ("manage_channel", False),
            "✅ مدیریت تایمرها": ("manage_timers", True),
            "❌ مدیریت تایمرها": ("manage_timers", False),
            "✅ تنظیمات ربات": ("options_management", True),
            "❌ تنظیمات ربات": ("options_management", False),
        }

        if text == "🔙 بازگشت به مدیریت کاربران":
            data_store.update_user_state(user_id, "admin_management")
            msg = bot.send_message(user_id, f"👤 مدیریت ادمین‌ها:", reply_markup=get_admin_management_menu())
            data_store.last_message_id[user_id] = msg.message_id
            return
        elif text in permission_map:
            perm_key, new_value = permission_map[text]
            permissions[perm_key] = not permissions.get(perm_key, False)
            data_store.admin_permissions[str(admin_id)] = permissions
            data_store.save_data()
            action_text = "فعال شد" if permissions[perm_key] else "غیرفعال شد"
            msg = bot.send_message(user_id, f"✅ دسترسی '{perm_key}' {action_text}.\n🔧 تنظیم دسترسی‌های ادمین {admin_id}:", reply_markup=get_admin_permissions_menu(admin_id))
            data_store.last_message_id[user_id] = msg.message_id
        else:
            msg = bot.send_message(user_id, f"⚠️ گزینه نامعتبر. لطفاً یکی از گزینه‌های منو را انتخاب کنید.", reply_markup=get_admin_permissions_menu(admin_id))
            data_store.last_message_id[user_id] = msg.message_id

    elif state == "add_admin":
        logger.info(f"تلاش برای افزودن ادمین با آیدی: '{text}'")
        try:
            admin_id = int(text.strip())
            logger.info(f"آیدی تبدیل‌شده: {admin_id}")
            if admin_id in data_store.admins:
                logger.warning(f"آیدی {admin_id} قبلاً در لیست ادمین‌ها وجود دارد.")
                msg = bot.send_message(user_id, f"⚠️ این کاربر قبلاً ادمین است.", reply_markup=get_admin_management_menu())
                data_store.last_message_id[user_id] = msg.message_id
                data_store.update_user_state(user_id, "admin_management")
                return
            logger.info(f"لیست ادمین‌ها قبل از افزودن: {data_store.admins}")
            data_store.admins.append(admin_id)
            # مقداردهی اولیه دسترسی‌های ادمین جدید
            data_store.admin_permissions[str(admin_id)] = {
                "create_post": False,
                "admin_management": False,
                "uploader_management": False,
                "broadcast_management": False,
                "bot_creator": False,
                "user_account": False,
                "forced_management": False,
                "trust": False,
                "manage_channel" : False,
                "manage_timers" : False,

                "options_management": False
            }
            logger.info(f"لیست ادمین‌ها بعد از افزودن: {data_store.admins}")
            data_store.save_data()
            logger.info(f"آیدی {admin_id} با موفقیت به ادمین‌ها اضافه و ذخیره شد.")
            msg = bot.send_message(user_id, f"✅ کاربر با آیدی {admin_id} به ادمین‌ها اضافه شد.\n👤 مدیریت ادمین‌ها:", reply_markup=get_admin_management_menu())
            data_store.last_message_id[user_id] = msg.message_id
            data_store.update_user_state(user_id, "admin_management")
        except ValueError as ve:
            logger.error(f"آیدی نامعتبر وارد شده: '{text}', خطا: {ve}")
            try:
                bot.edit_message_text(
                    chat_id=user_id,
                    message_id=data_store.last_message_id.get(user_id, 0),
                    text=f"⚠️ لطفاً یک آیدی عددی معتبر وارد کنید.",
                    reply_markup=get_back_menu()
                )
            except Exception as e:
                logger.error(f"خطا در ویرایش پیام: {e}")
                msg = bot.send_message(user_id, f"⚠️ لطفاً یک آیدی عددی معتبر وارد کنید.", reply_markup=get_back_menu())
                data_store.last_message_id[user_id] = msg.message_id
    
    elif state == "remove_admin":
        logger.info(f"تلاش برای حذف ادمین با آیدی: '{text}'")
        try:
            admin_id = int(text.strip())
            logger.info(f"آیدی تبدیل‌شده: {admin_id}")
            if admin_id == OWNER_ID:
                logger.warning(f"تلاش برای حذف اونر با آیدی {admin_id}")
                msg = bot.send_message(user_id, f"⚠️ اونر قابل حذف نیست.", reply_markup=get_admin_management_menu())
                data_store.last_message_id[user_id] = msg.message_id
                data_store.update_user_state(user_id, "admin_management")
                return
            if admin_id in data_store.admins:
                logger.info(f"لیست ادمین‌ها قبل از حذف: {data_store.admins}")
                data_store.admins.remove(admin_id)
                logger.info(f"لیست ادمین‌ها بعد از حذف: {data_store.admins}")
                try:
                    data_store.save_data()
                    logger.info(f"آیدی {admin_id} با موفقیت از ادمین‌ها حذف شد.")
                    msg = bot.send_message(user_id, f"✅ ادمین با آیدی {admin_id} حذف شد.\n👤 مدیریت ادمین‌ها:", reply_markup=get_admin_management_menu())
                    data_store.last_message_id[user_id] = msg.message_id
                except Exception as e:
                    logger.error(f"خطا در ذخیره‌سازی پس از حذف آیدی {admin_id}: {e}")
                    data_store.admins.append(admin_id)  # rollback در صورت خطا
                    msg = bot.send_message(user_id, f"⚠️ خطا در ذخیره‌سازی پس از حذف ادمین. لطفاً دوباره امتحان کنید.", reply_markup=get_admin_management_menu())
                    data_store.last_message_id[user_id] = msg.message_id
            else:
                logger.warning(f"آیدی {admin_id} در لیست ادمین‌ها نیست.")
                msg = bot.send_message(user_id, f"⚠️ این آیدی در لیست ادمین‌ها نیست.", reply_markup=get_admin_management_menu())
                data_store.last_message_id[user_id] = msg.message_id
            data_store.update_user_state(user_id, "admin_management")
        except ValueError as ve:
            logger.error(f"آیدی نامعتبر برای حذف: '{text}', خطا: {ve}")
            msg = bot.send_message(user_id, f"⚠️ لطفاً یک آیدی عددی معتبر وارد کنید.", reply_markup=get_admin_management_menu())
            data_store.last_message_id[user_id] = msg.message_id
        except Exception as e:
            logger.error(f"خطای غیرمنتظره در حذف ادمین: {e}")
            msg = bot.send_message(user_id, f"⚠️ خطای غیرمنتظره رخ داد. لطفاً دوباره امتحان کنید.", reply_markup=get_admin_management_menu())
            data_store.last_message_id[user_id] = msg.message_id
            
# منوی مدیریت امضاها
def get_signature_management_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    view_btn = types.KeyboardButton("👀 مشاهده امضاها")
    add_btn = types.KeyboardButton("➕ افزودن امضای جدید")
    delete_btn = types.KeyboardButton("🗑️ حذف امضا")
    back_btn = types.KeyboardButton("🔙 بازگشت به تنظیمات ربات")
    markup.add(view_btn, add_btn)
    markup.add(delete_btn, back_btn)
    return markup

MAIN_MENU_BUTTONS = [
    # منوی اصلی و امکانات پایه
    "❌ بستن کرکفای",
    "🛒 کرکفای",
    "🆕 ایجاد پست",
    "📤 اپلودر",
    "📣 ارسال همگانی",
    "🤖 ربات ساز",
    "👤 حساب کاربری",
    "👥 مدیریت کاربران",
    "⚡️ امکانات اجباری",
    "🏛 تنظیمات ربات",
    f"🤖 بات دستیار نسخه {BOT_VERSION}",

    # اپلودر
    "⬆️ اپلود فایل",
    "⬆️ اپلود دیلیت فایل",
    "✅ پایان اپلود",
    "🔙 بازگشت به اپلودر",
    "🛠️ ویرایش فایل",
    "🔤 تغییر اسم فایل",
    "🖼 تغییر تامنیل فایل",

    # پشتیبان گیری
    "🗄 پشتیبان گیری",
    "📥 تزریق پشتیبان",
    "📦 ایجاد پشتیبان",

    # مدیریت ادمین‌ها و دسترسی‌ها
    "➕ افزودن ادمین",
    "➖ حذف ادمین",
    "👀 لیست ادمین‌ها",
    "🔧 تنظیم دسترسی ادمین‌ها",
    "🚫 بلاک کاربران",
    "✅ رفع بلاک کاربران",
    "📋 لیست کاربران بلاک",
    "🔙 بازگشت به منوی اصلی",
    "🔙 بازگشت به مدیریت کاربران",

    # ربات ساز
    "➕ افزودن ربات",
    "📋 لیست ربات‌ها",
    "🗑️ حذف ربات",
    "♻️ ری ران ربات‌ها",
    "🔙 بازگشت به منوی اصلی",

    # مدیریت چنل
    "🛡 مدیریت چنل",
    "🕵️ ضد خیانت!",
    "➕ ادمین کردن در چنل",
    "➖ حذف ادمین در چنل",
    "✏️ ویرایش ادمین در چنل",
    "🔙 بازگشت به مدیریت چنل",

    # امکانات اجباری و مدیریت چنل/سین/ری‌اکشن
    "🔥 چنل اجباری",
    "👑 سین اجباری",
    "💥 ری اکشن اجباری",
    "➕ افزودن چنل سین",
    "➖ حذف چنل سین",
    "✏️ ثبت پیام سین اجباری",
    "🔢 مقدار زمان سین",
    "📋 لیست چنل‌های سین",
    "➕ افزودن چنل اجباری",
    "➖ حذف چنل اجباری",
    "✏️ ثبت پیام جوین اجباری",
    "لیست چنل‌های اجباری",
    "کردم ✅",
    "عضو شدم ✅",
    "➕ افزودن چنل ری اکشن",
    "➖ حذف چنل ری اکشن",
    "🔢 مقدار زمان ری اکشن",
    "📋 لیست چنل‌های ری اکشن",
    "ری اکشن زدم ✅",

    # مقادیر پیش‌فرض
    "📝 مدیریت مقادیر پیش‌فرض",
    "👀 مشاهده مقادیر پیش‌فرض",
    "➕ تنظیم مقدار پیش‌فرض",
    "➖ حذف مقدار پیش‌فرض",

    # منوی امضا
    "✍️ تنظیم امضا",
    "👀 مشاهده امضاها",
    "➕ افزودن امضای جدید",
    "🗑️ حذف امضا",
    "🔙 بازگشت به تنظیمات ربات",

    # مدیریت متغیرها
    "⚙️ مدیریت متغیرها",
    "👀 مشاهده متغیرها",
    "➕ افزودن متغیر",
    "➖ حذف متغیر",

    # منوی اپلودر
    "✨ تغییرات اتوماتیک",
    "🆕 کلمه جدید",
    "🧹 فیلتر کلمه",
    "📃 لیست کلمات جدید",
    "📃 لیست کلمات فیلتر",
    "⚙️ تنظیمات اجرایی",

    # سایر دسترسی‌ها
    "✅ مدیریت چنل", "❌ مدیریت چنل",
    "✅ مدیریت تایمرها", "❌ مدیریت تایمرها",
    "✅ ایجاد پست", "❌ ایجاد پست",
    "✅ اپلودر", "❌ اپلودر",
    "✅ ارسال همگانی", "❌ ارسال همگانی",
    "✅ ربات ساز", "❌ ربات ساز",
    "✅ حساب کاربری", "❌ حساب کاربری",
    "✅ امکانات اجباری", "❌ امکانات اجباری",
    "✅ پشتیبان گیری", "❌ پشتیبان گیری",

    # ارسال پست و رسانه
    "⏭️ رد کردن مرحله رسانه",
    "🆕 پست جدید",
    "⏭️ پایان ارسال رسانه",
    "📏 به کنار",
    "📐 به پایین",
    "⏰ زمان‌بندی پست",
    "🚀 ارسال فوری",
    "✅ ادامه دادن",
    "✅ بله",
    "❌ خیر",

    # انواع فرمت متنی
    "Bold",
    "Italic",
    "Code",
    "Strike",
    "Underline",
    "Spoiler",
    "BlockQuote",
    "Simple",
    "Link",

    # تایمر و کلید شیشه‌ای
    "✅ تایمرها: فعال", "❌ تایمرها: غیرفعال",
    "✅ کلیدهای شیشه‌ای: فعال", "❌ کلیدهای شیشه‌ای: غیرفعال",

    # دکمه‌های اضافی منوها و مراحل
    "✅ انجام دادم",
    "🔙 انصراف",
    "✏️ ویرایش فایل",
    "🔗 ویرایش لینک",
    "✅ استفاده شود",
    "❌ وارد کنم",
    "📢 ثبت چنل پست",
    "📢 ثبت چنل اپلودری",
    "⏰ مدیریت تایمرها",
    "🏠 تنظیمات پیش‌فرض",
    "---- 💠 تنظیمات ساخت پست 💠 ----",
    "---- 🔥 تنظیمات اپلودر و ارسال همگانی 🔥 ----",
    "---- 🧭تنظیمات کرکفای 🧭 ----",
    "🎩 جاسوس چنل: ✅",
    "🎩 جاسوس چنل: ❌",
    "✅ تبعیض برای اونر: فعال",
    "❌ تبعیض برای اونر: غیرفعال",
    "⏱ تایم اپلود دیلیت فایل",
    "🔥 تعداد کرکفای فایل",
    "⏳ مقدار زمان خستگی (فعلی: 7 دقیقه)",  # مقدار فعلی را هنگام ساخت منو تنظیم کن
    "🏠 بازگشت به منوی اصلی",
    "🔙 بازگشت",
]

# هندلر عکس برای دریافت تصاویر
@bot.message_handler(func=lambda m: data_store.get_user_state(m.from_user.id)["state"] == "post_with_signature_media", content_types=['photo', 'video'])
def handle_post_with_signature_media(message):
    user_id = message.from_user.id
    user_state = data_store.get_user_state(user_id)
    data_store.last_user_message_id[user_id] = message.message_id

    uploader_channel = data_store.uploader_channels[0] if data_store.uploader_channels else None
    if not uploader_channel:
        bot.send_message(user_id, "❗️ چنل اپلودری ثبت نشده است.", reply_markup=get_back_menu())
        return

    if message.content_type == 'photo':
        file_id = message.photo[-1].file_id
        sent_message = bot.send_photo(uploader_channel, file_id)
        media_type = 'photo'
    elif message.content_type == 'video':
        file_id = message.video.file_id
        sent_message = bot.send_video(uploader_channel, file_id)
        media_type = 'video'
    else:
        return

    if "media_ids" not in user_state["data"]:
        user_state["data"]["media_ids"] = []
    # ذخیره اطلاعات کامل برای استفاده مجدد
    user_state["data"]["media_ids"].append({
        "type": media_type,
        "file_id": file_id,
        "uploader_msg_id": sent_message.message_id,
        "uploader_channel": uploader_channel
    })
    data_store.update_user_state(user_id, "post_with_signature_media", user_state["data"])

    # بلافاصله مدیا را به کاربر هم نمایش بده (پیش‌نمایش)
    try:
        if media_type == "photo":
            bot.send_photo(user_id, file_id, caption="پیش‌نمایش عکس دریافت شده (فایل ذخیره شد).")
        elif media_type == "video":
            bot.send_video(user_id, file_id, caption="پیش‌نمایش ویدیو دریافت شده (فایل ذخیره شد).")
    except Exception as e:
        logger.error(f"خطا در ارسال پیش‌نمایش مدیا به کاربر: {e}")

    try:
        msg = bot.send_message(
            user_id,
            f"✅ فایل به چنل اپلودر ارسال شد و پیش‌نمایش داده شد.\n⏭️ برای ادامه، رسانه دیگری ارسال کنید یا گزینه مناسب را انتخاب کنید.",
            reply_markup=types.ReplyKeyboardMarkup(resize_keyboard=True).add(
                types.KeyboardButton("⏭️ پایان ارسال رسانه"),
                types.KeyboardButton("🔙 بازگشت به منوی اصلی")
            )
        )
        data_store.last_message_id[user_id] = msg.message_id
    except Exception as e:
        logger.error(f"خطا در ارسال پیام: {e}")

#=====================هلندر های امکانات اجباری====================
def get_forced_features_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(types.KeyboardButton("🔥 چنل اجباری"))
    markup.add(types.KeyboardButton("👑 سین اجباری"))
    markup.add(types.KeyboardButton("💥 ری اکشن اجباری"))
    markup.add(types.KeyboardButton("🔙 بازگشت به منوی اصلی"))
    return markup

def get_forced_reaction_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(types.KeyboardButton("➕ افزودن چنل ری اکشن"), types.KeyboardButton("➖ حذف چنل ری اکشن"))
    markup.add(types.KeyboardButton("🔢 مقدار زمان ری اکشن"))
    markup.add(types.KeyboardButton("📋 لیست چنل‌های ری اکشن"))
    markup.add(types.KeyboardButton("🔙 بازگشت به منوی اصلی"))
    return markup
   
@bot.message_handler(func=lambda m: data_store.get_user_state(m.from_user.id)["state"] == "forced_features_menu")
def handle_forced_features_menu(message):
    user_id = message.from_user.id
    text = message.text
    if text == "🔥 چنل اجباری":
        data_store.update_user_state(user_id, "forced_channel_menu")
        bot.send_message(user_id, "مدیریت چنل‌های اجباری:", reply_markup=get_forced_channel_menu())
        return
    if text == "👑 سین اجباری":
        data_store.update_user_state(user_id, "forced_seen_menu")
        bot.send_message(user_id, "مدیریت سین اجباری:", reply_markup=get_forced_seen_menu())
        return
    if text == "💥 ری اکشن اجباری":
        data_store.update_user_state(user_id, "forced_reaction_menu")
        bot.send_message(user_id, "مدیریت ری اکشن اجباری:", reply_markup=get_forced_reaction_menu())
        return
    if text == "🔙 بازگشت به منوی اصلی":
        data_store.reset_user_state(user_id)
        bot.send_message(user_id, "🏠 بازگشت به منوی اصلی:", reply_markup=get_main_menu(user_id))
        return
       
@bot.message_handler(func=lambda m: data_store.get_user_state(m.from_user.id)["state"] == "forced_reaction_menu")
def handle_forced_reaction_menu(message):
    user_id = message.from_user.id
    text = message.text
    if text == "📋 لیست چنل‌های ری اکشن":
        chans = data_store.forced_reaction_channels
        if chans:
            ch_list = "\n".join([f"<blockquote>{ch}</blockquote>" for ch in chans])
            bot.send_message(user_id, f"📋 لیست چنل‌های ری اکشن ثبت‌شده:\n{ch_list}", reply_markup=get_forced_reaction_menu(), parse_mode="HTML")
        else:
            bot.send_message(user_id, "هیچ چنل ری اکشن ثبت نشده.", reply_markup=get_forced_reaction_menu())
        return
    if text == "➕ افزودن چنل ری اکشن":
        data_store.update_user_state(user_id, "add_forced_reaction_channel")
        bot.send_message(user_id, "آیدی چنل ری اکشن را وارد کنید (مثال: @channelname):", reply_markup=get_back_menu())
        return
    if text == "➖ حذف چنل ری اکشن":
        if not data_store.forced_reaction_channels:
            bot.send_message(user_id, "هیچ چنلی برای حذف وجود ندارد.", reply_markup=get_forced_reaction_menu())
        else:
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
            for ch in data_store.forced_reaction_channels:
                markup.add(types.KeyboardButton(ch))
            markup.add(types.KeyboardButton("🔙 بازگشت به منوی اصلی"))
            data_store.update_user_state(user_id, "remove_forced_reaction_channel")
            bot.send_message(user_id, "یک چنل برای حذف انتخاب کن:", reply_markup=markup)
        return
    if text == "🔢 مقدار زمان ری اکشن":
        data_store.update_user_state(user_id, "set_forced_reaction_count")
        bot.send_message(user_id, f"مدت زمان مجاز برای ری اکشن (ثانیه): (فعلی: {data_store.forced_reaction_count})", reply_markup=get_back_menu())
        return
    if text == "🔙 بازگشت به منوی اصلی":
        data_store.update_user_state(user_id, "forced_features_menu")
        bot.send_message(user_id, "⚡️ امکانات اجباری:", reply_markup=get_forced_features_menu())
        return
       
      
@bot.message_handler(func=lambda m: data_store.get_user_state(m.from_user.id)["state"] == "add_forced_reaction_channel")
def handle_add_forced_reaction_channel(message):
    user_id = message.from_user.id
    channel_name = message.text.strip()
    if channel_name == "🔙 بازگشت به منوی اصلی":
        data_store.update_user_state(user_id, "forced_reaction_menu")
        bot.send_message(user_id, "مدیریت ری اکشن اجباری:", reply_markup=get_forced_reaction_menu())
        return
    if not channel_name.startswith('@'):
        bot.send_message(user_id, "آیدی چنل باید با @ شروع شود.", reply_markup=get_back_menu())
        return
    try:
        chat = bot.get_chat(channel_name)
        bot_member = bot.get_chat_member(channel_name, bot.get_me().id)
        if bot_member.status not in ['administrator', 'creator']:
            bot.send_message(user_id, "ربات باید ادمین باشد.", reply_markup=get_back_menu())
            return
        if channel_name in data_store.forced_reaction_channels:
            bot.send_message(user_id, "این چنل قبلاً ثبت شده است.", reply_markup=get_back_menu())
            return
        data_store.forced_reaction_channels.append(channel_name)
        data_store.save_data()
        data_store.update_user_state(user_id, "forced_reaction_menu")
        bot.send_message(user_id, f"✅ چنل ری اکشن {channel_name} ثبت شد.", reply_markup=get_forced_reaction_menu())
    except Exception as e:
        bot.send_message(user_id, f"خطا در ثبت چن: {e}", reply_markup=get_back_menu())

@bot.message_handler(func=lambda m: data_store.get_user_state(m.from_user.id)["state"] == "remove_forced_reaction_channel")
def handle_remove_forced_reaction_channel(message):
    user_id = message.from_user.id
    channel_name = message.text.strip()
    if channel_name == "🔙 بازگشت به منوی اصلی":
        data_store.update_user_state(user_id, "forced_reaction_menu")
        bot.send_message(user_id, "مدیریت ری اکشن اجباری:", reply_markup=get_forced_reaction_menu())
        return
    if channel_name in data_store.forced_reaction_channels:
        data_store.forced_reaction_channels.remove(channel_name)
        data_store.save_data()
        bot.send_message(user_id, f"✅ چنل {channel_name} حذف شد.", reply_markup=get_forced_reaction_menu())
    else:
        bot.send_message(user_id, "چنل انتخاب‌شده معتبر نیست.", reply_markup=get_back_menu())
    data_store.update_user_state(user_id, "forced_reaction_menu")
   
  
@bot.message_handler(func=lambda m: data_store.get_user_state(m.from_user.id)["state"] == "set_forced_reaction_count")
def handle_set_forced_reaction_count(message):
    user_id = message.from_user.id
    val = message.text.strip()
    if val == "🔙 بازگشت به منوی اصلی":
        data_store.update_user_state(user_id, "forced_reaction_menu")
        bot.send_message(user_id, "مدیریت ری اکشن اجباری:", reply_markup=get_forced_reaction_menu())
        return
    if not val.isdigit() or int(val) < 1:
        bot.send_message(user_id, "لطفاً فقط یک عدد صحیح مثبت وارد کنید.", reply_markup=get_back_menu())
        return
    data_store.forced_reaction_count = int(val)
    with open(os.path.join(data_store.base_folder, 'forced_reaction_count.txt'), 'w', encoding='utf-8') as f:
        f.write(str(data_store.forced_reaction_count))
    data_store.save_data()
    bot.send_message(user_id, f"مدت زمان ری اکشن به {val} ثانیه تغییر یافت.", reply_markup=get_forced_reaction_menu())
    data_store.update_user_state(user_id, "forced_reaction_menu")

def set_reaction_time(user_id):
    now = datetime.now(pytz.timezone('Asia/Tehran')).isoformat()
    if str(user_id) in data_store.user_data:
        data_store.user_data[str(user_id)]["last_forced_reaction"] = now
    else:
        data_store.user_data[str(user_id)] = {
            "first_name": "",
            "last_name": "",
            "username": "",
            "join_date": now,
            "is_active": True,
            "stage": "start",
            "status": "online",
            "maram": False,
            "last_forced_reaction": now
        }
    data_store.save_data()

def get_forced_reaction_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("ری اکشن زدم ✅"))
    return markup

@bot.message_handler(func=lambda m: data_store.get_user_state(m.from_user.id)["state"] == "wait_for_forced_reaction" and m.text == "ری اکشن زدم ✅")
def handle_forced_reaction_check(message):
    user_id = message.from_user.id
    set_reaction_time(user_id)
    data_store.reset_user_state(user_id)
    bot.send_message(user_id, "✅ ری اکشن شما تایید شد. خوش آمدید.", reply_markup=get_main_menu(user_id))

def check_forced_seen(user_id):
    chs = getattr(data_store, "forced_seen_channels", [])
    if not chs:
        return True, []
    user_info = data_store.user_data.get(str(user_id), {})
    last_seen = user_info.get("last_seen_forced_seen")
    now = datetime.now()
    if last_seen:
        try:
            dt = datetime.fromisoformat(last_seen)
            if (now - dt).total_seconds() < 3600:
                return True, []
        except Exception:
            pass
    return False, chs

def get_forced_channel_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(types.KeyboardButton("➕ افزودن چنل اجباری"), types.KeyboardButton("➖ حذف چنل اجباری"))
    markup.add(types.KeyboardButton("✏️ ثبت پیام جوین اجباری"))
    markup.add(types.KeyboardButton("لیست چنل‌های اجباری"))
    markup.add(types.KeyboardButton("🔙 بازگشت به منوی اصلی"))
    return markup

@bot.message_handler(func=lambda m: data_store.get_user_state(m.from_user.id)["state"] == "forced_channel_menu")
def handle_forced_channel_menu(message):
    user_id = message.from_user.id
    text = message.text
    if text == "➕ افزودن چنل اجباری":
        data_store.update_user_state(user_id, "add_forced_channel")
        bot.send_message(user_id, "آیدی چنل اجباری را وارد کنید (مثال: @channelname):", reply_markup=get_back_menu())
        return
    if text == "➖ حذف چنل اجباری":
        if not data_store.forced_channels:
            bot.send_message(user_id, "هیچ چنلی برای حذف وجود ندارد.", reply_markup=get_forced_channel_menu())
        else:
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
            for ch in data_store.forced_channels:
                markup.add(types.KeyboardButton(ch))
            markup.add(types.KeyboardButton("🔙 بازگشت به منوی اصلی"))
            data_store.update_user_state(user_id, "remove_forced_channel")
            bot.send_message(user_id, "یک چنل برای حذف انتخاب کن:", reply_markup=markup)
        return
    if text == "✏️ ثبت پیام جوین اجباری":
        data_store.update_user_state(user_id, "set_forced_join_msg")
        bot.send_message(user_id, "پیام جوین اجباری جدید را وارد کنید:", reply_markup=get_back_menu())
        return
    if text == "لیست چنل‌های اجباری":
        chans = data_store.forced_channels
        if chans:
            ch_list = "\n".join(chans)
            bot.send_message(user_id, f"📋 لیست چنل‌های اجباری ثبت‌شده:\n{ch_list}", reply_markup=get_forced_channel_menu())
        else:
            bot.send_message(user_id, "هیچ چنل اجباری ثبت نشده.", reply_markup=get_forced_channel_menu())
        return
    if text == "🔙 بازگشت به منوی اصلی":
        data_store.update_user_state(user_id, "forced_features_menu")
        bot.send_message(user_id, "⚡️ امکانات اجباری:", reply_markup=get_forced_features_menu())
        return

# جدید: هندلر واقعی برای ثبت چنل اجباری
@bot.message_handler(func=lambda m: data_store.get_user_state(m.from_user.id)["state"] == "add_forced_channel")
def handle_add_forced_channel(message):
    user_id = message.from_user.id
    channel_name = message.text.strip()
    if channel_name == "🔙 بازگشت به منوی اصلی":
        data_store.update_user_state(user_id, "forced_channel_menu")
        bot.send_message(user_id, "مدیریت چنل‌های اجباری:", reply_markup=get_forced_channel_menu())
        return
    if not channel_name.startswith('@'):
        bot.send_message(user_id, "آیدی چنل باید با @ شروع شود.", reply_markup=get_back_menu())
        return
    if channel_name in data_store.forced_channels:
        bot.send_message(user_id, "این چنل قبلاً ثبت شده است.", reply_markup=get_back_menu())
        return
    try:
        chat = bot.get_chat(channel_name)
        bot_member = bot.get_chat_member(channel_name, bot.get_me().id)
        if bot_member.status not in ['administrator', 'creator']:
            bot.send_message(user_id, "ربات باید ادمین باشد.", reply_markup=get_back_menu())
            return
        data_store.forced_channels.append(channel_name)
        data_store.save_data()
        data_store.update_user_state(user_id, "forced_channel_menu")
        bot.send_message(user_id, f"✅ چنل {channel_name} ثبت شد.", reply_markup=get_forced_channel_menu())
    except Exception as e:
        bot.send_message(user_id, f"خطا در ثبت چنل: {e}", reply_markup=get_back_menu())

def get_forced_seen_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(types.KeyboardButton("➕ افزودن چنل سین"), types.KeyboardButton("➖ حذف چنل سین"))
    markup.add(types.KeyboardButton("✏️ ثبت پیام سین اجباری"))
    markup.add(types.KeyboardButton("🔢 مقدار زمان سین"))
    markup.add(types.KeyboardButton("📋 لیست چنل‌های سین"))
    markup.add(types.KeyboardButton("🔙 بازگشت به منوی اصلی"))
    return markup

# جدید: هندلر واقعی برای ثبت چنل سین اجباری
@bot.message_handler(func=lambda m: data_store.get_user_state(m.from_user.id)["state"] == "add_forced_seen_channel")
def handle_add_forced_seen_channel(message):
    user_id = message.from_user.id
    channel_name = message.text.strip()
    if channel_name == "🔙 بازگشت به منوی اصلی":
        data_store.update_user_state(user_id, "forced_seen_menu")
        bot.send_message(user_id, "مدیریت سین اجباری:", reply_markup=get_forced_seen_menu())
        return
    if not channel_name.startswith('@'):
        bot.send_message(user_id, "آیدی چنل باید با @ شروع شود.", reply_markup=get_back_menu())
        return
    if channel_name in data_store.forced_seen_channels:
        bot.send_message(user_id, "این چنل قبلاً ثبت شده است.", reply_markup=get_back_menu())
        return
    # فقط ادمین/اونر مجاز است
    if not (is_owner(user_id) or is_admin(user_id)):
        bot.send_message(user_id, "دسترسی ندارید.", reply_markup=get_main_menu(user_id))
        return
    data_store.forced_seen_channels.append(channel_name)
    data_store.save_data()
    data_store.update_user_state(user_id, "forced_seen_menu")
    bot.send_message(user_id, f"✅ چنل سین {channel_name} ثبت شد.", reply_markup=get_forced_seen_menu())

# جدید: هندلر حذف چنل سین
@bot.message_handler(func=lambda m: data_store.get_user_state(m.from_user.id)["state"] == "remove_forced_seen_channel")
def handle_remove_forced_seen_channel(message):
    user_id = message.from_user.id
    channel_name = message.text.strip()
    if channel_name == "🔙 بازگشت به منوی اصلی":
        data_store.update_user_state(user_id, "forced_seen_menu")
        bot.send_message(user_id, "مدیریت سین اجباری:", reply_markup=get_forced_seen_menu())
        return
    # فقط ادمین/اونر مجاز است
    if not (is_owner(user_id) or is_admin(user_id)):
        bot.send_message(user_id, "دسترسی ندارید.", reply_markup=get_main_menu(user_id))
        return
    if channel_name in data_store.forced_seen_channels:
        data_store.forced_seen_channels.remove(channel_name)
        data_store.save_data()
        bot.send_message(user_id, f"✅ چنل سین {channel_name} حذف شد.", reply_markup=get_forced_seen_menu())
    else:
        bot.send_message(user_id, "چنل انتخاب‌شده معتبر نیست.", reply_markup=get_back_menu())
    data_store.update_user_state(user_id, "forced_seen_menu")

# جدید: هندلر حذف چنل اجباری
@bot.message_handler(func=lambda m: data_store.get_user_state(m.from_user.id)["state"] == "remove_forced_channel")
def handle_remove_forced_channel(message):
    user_id = message.from_user.id
    channel_name = message.text.strip()
    if channel_name == "🔙 بازگشت به منوی اصلی":
        data_store.update_user_state(user_id, "forced_channel_menu")
        bot.send_message(user_id, "مدیریت چنل‌های اجباری:", reply_markup=get_forced_channel_menu())
        return
    if channel_name in data_store.forced_channels:
        data_store.forced_channels.remove(channel_name)
        data_store.save_data()
        bot.send_message(user_id, f"✅ چنل {channel_name} حذف شد.", reply_markup=get_forced_channel_menu())
    else:
        bot.send_message(user_id, "چنل انتخاب‌شده معتبر نیست.", reply_markup=get_back_menu())
    data_store.update_user_state(user_id, "forced_channel_menu")

@bot.message_handler(func=lambda m: data_store.get_user_state(m.from_user.id)["state"] == "forced_seen_menu")
def handle_forced_seen_menu(message):
    user_id = message.from_user.id
    text = message.text
    if text == "📋 لیست چنل‌های سین":
        chans = data_store.forced_seen_channels
        if chans:
            ch_list = "\n".join(chans)
            bot.send_message(user_id, f"📋 لیست چنل‌های سین ثبت‌شده:\n{ch_list}", reply_markup=get_forced_seen_menu())
        else:
            bot.send_message(user_id, "هیچ چنل سین ثبت نشده.", reply_markup=get_forced_seen_menu())
        return
    if text == "➕ افزودن چنل سین":
        data_store.update_user_state(user_id, "add_forced_seen_channel")
        bot.send_message(user_id, "آیدی چنل سین را وارد کن (مثال: @channelname):", reply_markup=get_back_menu())
        return
    if text == "➖ حذف چنل سین":
        chans = data_store.forced_seen_channels
        if not chans:
            bot.send_message(user_id, "هیچ چنلی برای حذف وجود ندارد.", reply_markup=get_forced_seen_menu())
        else:
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
            for ch in chans:
                markup.add(types.KeyboardButton(ch))
            markup.add(types.KeyboardButton("🔙 بازگشت به منوی اصلی"))
            data_store.update_user_state(user_id, "remove_forced_seen_channel")
            bot.send_message(user_id, "یک چنل برای حذف انتخاب کن:", reply_markup=markup)
        return
    if text == "✏️ ثبت پیام سین اجباری":
        data_store.update_user_state(user_id, "set_forced_seen_msg")
        bot.send_message(user_id, "پیام سین اجباری جدید را وارد کن:", reply_markup=get_back_menu())
        return
    if text == "🔢 مقدار زمان سین":
        data_store.update_user_state(user_id, "set_forced_seen_count")
        bot.send_message(user_id, f"مدت زمان مجاز برای سین کردن (دقیقه): (فعلی: {data_store.forced_seen_count})", reply_markup=get_back_menu())
        return
    if text == "🔙 بازگشت به منوی اصلی":
        data_store.update_user_state(user_id, "forced_features_menu")
        bot.send_message(user_id, "⚡️ امکانات اجباری:", reply_markup=get_forced_features_menu())
        return

@bot.message_handler(func=lambda m: data_store.get_user_state(m.from_user.id)["state"] == "set_forced_seen_count")
def handle_set_forced_seen_count(message):
    user_id = message.from_user.id
    val = message.text.strip()
    if val == "🔙 بازگشت به منوی اصلی":
        data_store.update_user_state(user_id, "forced_seen_menu")
        bot.send_message(user_id, "مدیریت سین اجباری:", reply_markup=get_forced_seen_menu())
        return
    if not val.isdigit() or int(val) < 1:
        bot.send_message(user_id, "لطفاً فقط یک عدد صحیح مثبت وارد کنید.", reply_markup=get_back_menu())
        return
    data_store.forced_seen_count = int(val)
    data_store.save_data()
    bot.send_message(user_id, f"مدت زمان سین به {val} دقیقه تغییر یافت.", reply_markup=get_forced_seen_menu())
    data_store.update_user_state(user_id, "forced_seen_menu")
    
def get_forced_seen_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("کردم ✅"))
    return markup

def get_forced_join_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("عضو شدم ✅"))
    return markup
def check_forced_actions(user_id):
    """بررسی انجام سین و ری‌اکشن اجباری با منطق تایمی"""
    
    # اگر کاربر ادمین یا اونر باشد
    if is_owner(user_id) or is_admin(user_id):
        return True, [], []

    # گرفتن اطلاعات کاربر
    user_info = data_store.user_data.get(str(user_id), {})
    tehran_tz = pytz.timezone('Asia/Tehran')
    now = datetime.now(tehran_tz)
    
    # بررسی زمان سین
    seen_valid = False
    last_seen = user_info.get("last_forced_seen")
    if last_seen:
        try:
            last_seen_dt = datetime.fromisoformat(last_seen)
            if last_seen_dt.tzinfo is None:
                last_seen_dt = tehran_tz.localize(last_seen_dt)
            else:
                last_seen_dt = last_seen_dt.astimezone(tehran_tz)
            
            time_diff = (now - last_seen_dt).total_seconds()
            seen_time_limit = data_store.forced_seen_count * 60  # دقیقه → ثانیه
            seen_valid = time_diff < seen_time_limit
        except Exception as e:
            logger.error(f"خطا در بررسی زمان سین: {e}")
    
    # بررسی زمان ری‌اکشن
    reaction_valid = False
    last_reaction = user_info.get("last_forced_reaction")
    if last_reaction:
        try:
            last_reaction_dt = datetime.fromisoformat(last_reaction)
            if last_reaction_dt.tzinfo is None:
                last_reaction_dt = tehran_tz.localize(last_reaction_dt)
            else:
                last_reaction_dt = last_reaction_dt.astimezone(tehran_tz)
            
            time_diff = (now - last_reaction_dt).total_seconds()
            reaction_time_limit = data_store.forced_reaction_count  # ثانیه
            reaction_valid = time_diff < reaction_time_limit
        except Exception as e:
            logger.error(f"خطا در بررسی زمان ری‌اکشن: {e}")

    # دریافت لیست چنل‌ها
    seen_chs = set(getattr(data_store, "forced_seen_channels", []))
    reaction_chs = set(getattr(data_store, "forced_reaction_channels", []))
    
    not_seen = []
    not_reacted = []
    
    # اگر زمان سین معتبر نیست
    if not seen_valid:
        not_seen.extend(seen_chs)
    
    # اگر زمان ری‌اکشن معتبر نیست
    if not reaction_valid:
        not_reacted.extend(reaction_chs)

    # بررسی عضویت در چنل‌ها
    for ch in seen_chs.union(reaction_chs):
        try:
            member = bot.get_chat_member(ch, user_id)
            if member.status not in ['member', 'administrator', 'creator']:
                if ch in seen_chs and ch not in not_seen:
                    not_seen.append(ch)
                if ch in reaction_chs and ch not in not_reacted:
                    not_reacted.append(ch)
        except Exception as e:
            logger.error(f"خطا در بررسی عضویت چنل {ch}: {e}")
            if ch in seen_chs and ch not in not_seen:
                not_seen.append(ch)
            if ch in reaction_chs and ch not in not_reacted:
                not_reacted.append(ch)

    all_ok = (len(not_seen) == 0 and len(not_reacted) == 0)
    return all_ok, not_seen, not_reacted

def set_seen_time(user_id):
    now = datetime.now(pytz.timezone('Asia/Tehran')).isoformat()
    if str(user_id) in data_store.user_data:
        data_store.user_data[str(user_id)]["last_forced_seen"] = now
    else:
        data_store.user_data[str(user_id)] = {
            "first_name": "",
            "last_name": "",
            "username": "",
            "join_date": now,
            "is_active": True,
            "stage": "start",
            "status": "online",
            "maram": False,
            "last_forced_seen": now
        }
    data_store.save_data()
    
def چه_join(user_id):
    if not data_store.forced_channels:
        return True, []
    
    not_joined = []
    for ch in data_store.forced_channels:
        try:
            member = bot.get_chat_member(ch, user_id)
            if member.status not in ['member', 'administrator', 'creator']:
                not_joined.append(ch)
        except Exception:
            not_joined.append(ch)
    
    # اگر هنوز عضو نشده باشد، تایید نمی‌کند
    if not_joined:
        return False, not_joined
    return True, []
    
def set_join_time(user_id):
    now = datetime.now(pytz.timezone('Asia/Tehran')).isoformat()
    if str(user_id) in data_store.user_data:
        data_store.user_data[str(user_id)]["last_forced_join"] = now
    else:
        data_store.user_data[str(user_id)] = {
            "first_name": "",
            "last_name": "",
            "username": "",
            "join_date": now,
            "is_active": True,
            "stage": "start",
            "status": "online",
            "maram": False,
            "last_forced_join": now
        }
    data_store.save_data()

@bot.message_handler(func=lambda m: data_store.get_user_state(m.from_user.id)["state"] == "wait_for_forced_seen" and m.text == "کردم ✅")
def handle_forced_seen_check(message):
    user_id = message.from_user.id
    set_seen_time(user_id)
    data_store.reset_user_state(user_id)
    bot.send_message(user_id, "✅ سین شما تایید شد. خوش آمدید.", reply_markup=get_main_menu(user_id))

forced_join_clicks = defaultdict(int)

@bot.message_handler(func=lambda m: data_store.get_user_state(m.from_user.id)["state"] == "wait_for_forced_join" and m.text == "عضو شدم ✅")
def handle_forced_join_check(message):
    user_id = message.from_user.id
    joined, not_joined = check_forced_join(user_id)
    if not joined:
        forced_join_clicks[user_id] += 1
        if forced_join_clicks[user_id] >= 4:
            # بلاک دائمی دیتابیس:
            if str(user_id) not in data_store.user_data:
                data_store.user_data[str(user_id)] = {}
            data_store.user_data[str(user_id)]["is_blocked_by_owner"] = True
            data_store.save_data()
            blocked_users.add(user_id)
            try:
                bot.send_message(
                    user_id,
                    "⛔️ شما به دلیل تلاش برای دور زدن سیستم امکانات اجباری بلاک شدید و **این تخلف** برای اونر ربات ارسال شد.",
                    parse_mode="HTML"
                )
                bot.send_message(
                    OWNER_ID,
                    f"❗️ کاربر بلاک شد\nآیدی: <code>{user_id}</code>\nیوزرنیم: @{message.from_user.username}\nعلت: **تخلف امکانات اجباری**",
                    parse_mode="HTML"
                )
            except: pass
            return
        chs = "\n".join([f"<blockquote>{ch}</blockquote>" for ch in not_joined])
        bot.send_message(
            user_id,
            f"🚫 توجه!\n"
            f"{data_store.forced_join_message}\n\n"
            f"کانال‌هایی که باید عضو شوید:\n{chs}\n"
            "تا زمانی که عضو نشدید، ربات برای شما فعال نمی‌شود!\n"
            "اگر ظرف ۵ دقیقه یا چند بار تلاش کنید بدون عضویت دور بزنید، بلاک خواهید شد و مالک ربات گزارش تخلف شما را دریافت خواهد کرد.\n"
            "پس از عضویت، روی دکمه «عضو شدم ✅» کلیک کنید.",
            parse_mode="HTML",
            disable_web_page_preview=True,
            reply_markup=get_forced_join_keyboard()
        )
        data_store.update_user_state(user_id, "wait_for_forced_join")
        return
    forced_join_clicks[user_id] = 0
    set_join_time(user_id)
    data_store.reset_user_state(user_id)
    bot.send_message(user_id, "✅ عضویت شما تایید شد. خوش آمدید.", reply_markup=get_main_menu(user_id))

def check_forced_join(user_id):
    """
    بررسی عضویت کاربر در چنل‌های اجباری
    ورودی: آیدی کاربر
    خروجی:
    - وضعیت کلی عضویت (True/False)
    - لیست چنل‌هایی که کاربر عضو آنها نیست
    """
    if is_owner(user_id) or is_admin(user_id):
        return True, []

    not_joined = []
    for ch in data_store.forced_channels:
        try:
            member = bot.get_chat_member(ch, user_id)
            if member.status not in ['member', 'administrator', 'creator']:
                not_joined.append(ch)
        except Exception as e:
            logger.error(f"خطا در بررسی عضویت در چنل {ch}: {str(e)}")
            not_joined.append(ch)

    return (len(not_joined) == 0), not_joined 
    
def require_join(handler_func):
    def wrapper(message, *args, **kwargs):
        user_id = message.from_user.id
        if not (is_owner(user_id) or is_admin(user_id)):
            joined, not_joined = check_forced_join(user_id)
            if not joined:
                msg_text = "🚫 توجه!\n"
                msg_text += f"{data_store.forced_join_message}\n\n"
                if not_joined:
                    msg_text += "📌 چنل‌های اجباری:\n" + "\n".join([f"<blockquote>{ch}</blockquote>" for ch in not_joined])
                msg_text += "\nتا زمانی که عضو نشدید، ربات برای شما فعال نمی‌شود!\nپس از عضویت، روی دکمه «عضو شدم ✅» کلیک کنید."
                bot.send_message(
                    user_id,
                    msg_text,
                    parse_mode="HTML",
                    reply_markup=get_forced_join_keyboard()
                )
                data_store.update_user_state(user_id, "wait_for_forced_join")
                return
        return handler_func(message, *args, **kwargs)
    return wrapper

def require_seen_reaction(handler_func):
    def wrapper(message, *args, **kwargs):
        user_id = message.from_user.id
        if not (is_owner(user_id) or is_admin(user_id)):
            now = datetime.now(pytz.timezone('Asia/Tehran'))
            user_info = data_store.user_data.get(str(user_id), {})
            last_seen = user_info.get("last_forced_seen")
            last_react = user_info.get("last_forced_reaction")
            need_check = False
            for key in ["last_forced_seen", "last_forced_reaction"]:
                last = user_info.get(key)
                if not last:
                    need_check = True
                else:
                    try:
                        dt = datetime.fromisoformat(last)
                        if (now - dt).total_seconds() > 7200:
                            need_check = True
                    except Exception:
                        need_check = True
            if need_check:
                seen_chs = getattr(data_store, "forced_seen_channels", [])
                reaction_chs = getattr(data_store, "forced_reaction_channels", [])
                msg_text = "🚫 برای ادامه باید دوباره سین و ری‌اکشن اجباری انجام دهید!\n\n" + "\n".join([f"<blockquote>{ch}</blockquote>" for ch in reaction_chs]) + "\n" + "\n".join([f"<blockquote>{ch}</blockquote>" for ch in seen_chs]) + "\n"
                if seen_chs:
                    msg_text += "📌 چنل‌های سین:\n" + "\n".join([f"<blockquote>{ch}</blockquote>" for ch in seen_chs]) + "\n"
                if reaction_chs:
                    msg_text += "📌 چنل‌های ری‌اکشن:\n" + "\n".join([f"<blockquote>{ch}</blockquote>" for ch in reaction_chs]) + "\n"
                msg_text += "\nلطفاً موارد بالا را انجام دهید و سپس دکمه تایید را بزنید."
                bot.send_message(
                    user_id,
                    msg_text,
                    parse_mode="HTML",
                    reply_markup=types.ReplyKeyboardMarkup(resize_keyboard=True).add(types.KeyboardButton("✅ انجام دادم"))
                )
                data_store.update_user_state(user_id, "wait_for_forced_actions")
                return
        return handler_func(message, *args, **kwargs)
    return wrapper

@bot.message_handler(func=lambda m: data_store.get_user_state(m.from_user.id)["state"] == "wait_for_forced_actions" and m.text == "✅ انجام دادم")
def handle_forced_actions_response(message):
    user_id = message.from_user.id
    now = datetime.now(pytz.timezone('Asia/Tehran')).isoformat()
    
    # بررسی وجود کاربر و ایجاد رکورد در صورت نیاز
    if str(user_id) not in data_store.user_data:
        data_store.user_data[str(user_id)] = {
            "first_name": message.from_user.first_name or "",
            "last_name": message.from_user.last_name or "",
            "username": message.from_user.username or "",
            "join_date": now,
            "is_active": True,
            "stage": "start",
            "status": "online",
            "maram": False
        }
    
    data_store.user_data[str(user_id)]["last_forced_seen"] = now
    data_store.user_data[str(user_id)]["last_forced_reaction"] = now
    data_store.save_data()
    data_store.reset_user_state(user_id)
    bot.send_message(user_id, "✅ تایید شد! حالا می‌توانید از ربات استفاده کنید.", reply_markup=get_main_menu(user_id))

# ==================== استارت ======================

       
# فرمت کردن پست با قابلیت‌های متنی تلگرام
def format_post_content(post_content, variables):
    formatted_content = post_content
    for var, value in variables.items():
        var_format = data_store.variables.get(var, {}).get("format", "Simple")
        if var_format == "Link":
            # value could be a tuple (text, url) or a string (url only)
            if isinstance(value, tuple):
                text_part, url_part = value
                if text_part and url_part:
                    formatted_content = formatted_content.replace(f"{{{var}}}", f'<a href="{url_part.strip()}">{text_part.strip()}</a>')
                else:
                    formatted_content = formatted_content.replace(f"{{{var}}}", "")
            elif isinstance(value, str):
                formatted_content = formatted_content.replace(f"{{{var}}}", f'<a href="{value.strip()}">{value.strip()}</a>')
            else:
                formatted_content = formatted_content.replace(f"{{{var}}}", "")
        elif var_format == "Bold":
            formatted_content = formatted_content.replace(f"{{{var}}}", f"<b>{value}</b>")
        elif var_format == "BlockQuote":
            formatted_content = formatted_content.replace(f"{{{var}}}", f"<blockquote>{value}</blockquote>")
        elif var_format == "Italic":
            formatted_content = formatted_content.replace(f"{{{var}}}", f"<i>{value}</i>")
        elif var_format == "Code":
            formatted_content = formatted_content.replace(f"{{{var}}}", f"<code>{value}</code>")
        elif var_format == "Strike":
            formatted_content = formatted_content.replace(f"{{{var}}}", f"<s>{value}</s>")
        elif var_format == "Underline":
            formatted_content = formatted_content.replace(f"{{{var}}}", f"<u>{value}</u>")
        elif var_format == "Spoiler":
            formatted_content = formatted_content.replace(f"{{{var}}}", f"<tg-spoiler>{value}</tg-spoiler>")
        else:
            formatted_content = formatted_content.replace(f"{{{var}}}", value)
    return formatted_content

def send_post_preview(user_id, post_content, media_ids=None, inline_buttons=None, row_width=4):
    logger.info(f"[STEP 1] شروع تابع send_post_preview برای کاربر: {user_id}")
    logger.info(f"[STEP 2] مقدار اولیه post_content: {repr(post_content)}")
    logger.info(f"[STEP 3] media_ids دریافتی: {repr(media_ids)}")
    logger.info(f"[STEP 4] inline_buttons دریافتی: {repr(inline_buttons)}")
    logger.info(f"[STEP 5] مقدار row_width: {row_width}")

    # ساخت کیبورد ساده
    markup_preview = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    continue_btn = types.KeyboardButton("🚀 ارسال فوری")
    schedule_btn = types.KeyboardButton("⏰ زمان‌بندی پست")
    new_post_btn = types.KeyboardButton("🆕 پست جدید")
    main_menu_btn = types.KeyboardButton("🔙 بازگشت به منوی اصلی")
    markup_preview.add(continue_btn)
    markup_preview.add(schedule_btn)
    markup_preview.add(new_post_btn)
    markup_preview.add(main_menu_btn)
    logger.info("[STEP 6] کیبورد ساده ساخته شد و کلیدها اضافه شدند.")

    # ساخت کیبورد شیشه‌ای
    inline_keyboard = None
    if data_store.timer_settings.get("inline_buttons_enabled", True) and inline_buttons:
        logger.info("[STEP 7] ساخت کیبورد شیشه‌ای فعال است و دکمه‌ها وجود دارد.")
        inline_keyboard = types.InlineKeyboardMarkup(row_width=row_width)
        for button in inline_buttons:
            logger.info(f"[STEP 7.1] اضافه کردن دکمه شیشه‌ای: {button}")
            inline_keyboard.add(types.InlineKeyboardButton(button["text"], url=button["url"]))
        logger.info(f"[STEP 7.2] کیبورد شیشه‌ای با دکمه‌های داده شده ساخته شد.")
    else:
        logger.info("[STEP 7.3] کیبورد شیشه‌ای غیرفعال است یا دکمه‌ای داده نشده.")

    # دریافت وضعیت کاربر
    user_state = data_store.get_user_state(user_id)
    logger.info(f"[STEP 8] وضعیت کاربر دریافت شد: {repr(user_state)}")

    # اگر کلید شیشه‌ای فعال باشد، فقط رسانه را از چنل اپلودر بخوان
    preview_medias = []
    found_media = False

    if data_store.timer_settings.get("inline_buttons_enabled", True) and inline_buttons:
        logger.info("[STEP 9-A] کلید شیشه‌ای فعال است، رسانه فقط از چنل اپلودر خوانده می‌شود.")
        media_source = None
        # اولویت با media_ids (اگر داده شده) و بعد user_state["data"]["media_ids"]
        if media_ids:
            media_source = media_ids
        elif user_state["data"].get("media_ids"):
            media_source = user_state["data"]["media_ids"]
        if media_source:
            for media in media_source:
                logger.info(f"[STEP 9-A.1] بررسی media فقط چنل اپلودر: {repr(media)}")
                if "uploader_channel" in media and "uploader_msg_id" in media:
                    preview_medias.append({
                        "type": media["type"],
                        "uploader_channel": media["uploader_channel"],
                        "uploader_msg_id": media["uploader_msg_id"]
                    })
                    logger.info(f"[STEP 9-A.2] رسانه فقط از اپلودر اضافه شد: {repr(preview_medias[-1])}")
                    found_media = True
        if not found_media:
            logger.info("[STEP 9-A.3] هیچ رسانه‌ای در چنل اپلودر یافت نشد.")
    else:
        # حالت معمولی (بدون کلید شیشه‌ای)
        if media_ids:
            logger.info("[STEP 9] media_ids دریافت شده است. بررسی و آماده‌سازی رسانه‌ها.")
            for media in media_ids:
                logger.info(f"[STEP 9.1] بررسی media: {repr(media)}")
                if "uploader_channel" in media and "uploader_msg_id" in media:
                    preview_medias.append({
                        "type": media["type"],
                        "uploader_channel": media["uploader_channel"],
                        "uploader_msg_id": media["uploader_msg_id"]
                    })
                    logger.info(f"[STEP 9.2] رسانه از کانال اپلودر اضافه شد: {repr(preview_medias[-1])}")
                    found_media = True
                elif "file_id" in media:
                    preview_medias.append({
                        "type": media["type"],
                        "file_id": media["file_id"]
                    })
                    logger.info(f"[STEP 9.3] رسانه از file_id اضافه شد: {repr(preview_medias[-1])}")
                    found_media = True

        if not found_media and user_state["data"].get("media_ids"):
            logger.info("[STEP 9.4] بررسی رسانه‌های ذخیره‌شده در user_state['data']['media_ids'].")
            for media in user_state["data"]["media_ids"]:
                logger.info(f"[STEP 9.5] بررسی media: {repr(media)}")
                if "uploader_channel" in media and "uploader_msg_id" in media:
                    preview_medias.append({
                        "type": media["type"],
                        "uploader_channel": media["uploader_channel"],
                        "uploader_msg_id": media["uploader_msg_id"]
                    })
                    logger.info(f"[STEP 9.6] رسانه اپلودر اضافه شد: {repr(preview_medias[-1])}")
                    found_media = True
                elif "file_id" in media:
                    preview_medias.append({
                        "type": media["type"],
                        "file_id": media["file_id"]
                    })
                    logger.info(f"[STEP 9.7] رسانه file_id اضافه شد: {repr(preview_medias[-1])}")
                    found_media = True

        if not found_media and user_state["data"].get("media_paths"):
            logger.info("[STEP 10] هیچ رسانه‌ای در media_ids نبود، بررسی media_paths از وضعیت کاربر.")
            for media in user_state["data"].get("media_paths", []):
                logger.info(f"[STEP 10.1] بررسی media: {repr(media)}")
                if "uploader_channel" in media and "uploader_msg_id" in media:
                    preview_medias.append({
                        "type": media["type"],
                        "uploader_channel": media["uploader_channel"],
                        "uploader_msg_id": media["uploader_msg_id"]
                    })
                    logger.info(f"[STEP 10.2] رسانه اپلودر اضافه شد: {repr(preview_medias[-1])}")
                    found_media = True
                elif "file_id" in media:
                    preview_medias.append({
                        "type": media["type"],
                        "file_id": media["file_id"]
                    })
                    logger.info(f"[STEP 10.3] رسانه file_id اضافه شد: {repr(preview_medias[-1])}")
                    found_media = True

        if not found_media:
            logger.info("[STEP 11] هیچ رسانه‌ای برای پیش‌نمایش یافت نشد.")

    # ارسال رسانه‌ها یا پیام متنی
    if preview_medias:
        logger.info(f"[STEP 12] لیست رسانه‌ها جهت ارسال: {repr(preview_medias)}")
        for i, media in enumerate(preview_medias):
            try:
                logger.info(f"[STEP 12.{i}] ارسال رسانه: {repr(media)}")
                if "uploader_channel" in media and "uploader_msg_id" in media:
                    logger.info(f"[STEP 12.{i}.1] ارسال رسانه با copy_message از کانال اپلودر.")
                    msg = bot.copy_message(
                        user_id, media["uploader_channel"], media["uploader_msg_id"], 
                        caption=post_content if i == 0 else None,
                        reply_markup=inline_keyboard if i == 0 else None,
                        parse_mode="HTML"
                    )
                elif "file_id" in media:
                    if media["type"] == "photo":
                        logger.info(f"[STEP 12.{i}.2] ارسال عکس با send_photo.")
                        msg = bot.send_photo(
                            user_id, media["file_id"], 
                            caption=post_content if i == 0 else None,
                            reply_markup=inline_keyboard if i == 0 else None, 
                            parse_mode="HTML"
                        )
                    elif media["type"] == "video":
                        logger.info(f"[STEP 12.{i}.3] ارسال ویدیو با send_video.")
                        msg = bot.send_video(
                            user_id, media["file_id"], 
                            caption=post_content if i == 0 else None,
                            reply_markup=inline_keyboard if i == 0 else None,
                            parse_mode="HTML"
                        )
                    else:
                        logger.info(f"[STEP 12.{i}.4] ارسال فایل با send_document.")
                        msg = bot.send_document(
                            user_id, media["file_id"],
                            caption=post_content if i == 0 else None,
                            reply_markup=inline_keyboard if i == 0 else None,
                            parse_mode="HTML"
                        )
                data_store.last_message_id[user_id] = msg.message_id
                logger.info(f"[STEP 12.{i}.5] آیدی پیام آخرین رسانه ذخیره شد: {msg.message_id}")
                sent_any_media = True
            except Exception as e:
                logger.error(f"[STEP 12.{i}.6] خطا در ارسال رسانه تلگرام برای پیش‌نمایش: {e}")
    else:
        try:
            logger.info("[STEP 13] هیچ رسانه‌ای وجود ندارد. ارسال پیام متنی به جای آن.")
            msg = bot.send_message(
                user_id, post_content,
                reply_markup=inline_keyboard,
                parse_mode="HTML"
            )
            data_store.last_message_id[user_id] = msg.message_id
            logger.info(f"[STEP 13.1] پیام متنی ارسال شد و آیدی ذخیره شد: {msg.message_id}")
        except Exception as e:
            logger.error(f"[STEP 13.2] خطا در ارسال پیام متنی: {e}")

    # ارسال منوی انتخاب پایین پیام
    try:
        logger.info("[STEP 14] ارسال پیام منوی نهایی با کیبورد ساده.")
        bot.send_message(user_id, "📬 گزینه‌های پست:", reply_markup=markup_preview)
        logger.info("[STEP 14.1] ارسال منوی نهایی موفق بود.")
    except Exception as e:
        logger.error(f"[STEP 14.2] خطا در ارسال منوی نهایی: {e}")

    logger.info(f"[STEP 15] پایان تابع send_post_preview برای کاربر: {user_id}")
    
def send_scheduled_post(job_id):
    logger.info(f"[TIMER START] شروع اجرای تایمر با job_id: {job_id}")

    if not data_store.timer_settings.get("timers_enabled", True):
        logger.info(f"[TIMER DISABLED] تایمر {job_id} اجرا نشد چون تایمرها غیرفعال هستند.")
        return

    for post in data_store.scheduled_posts:
        if post["job_id"] == job_id:
            logger.info(f"[TIMER FOUND] پست پیدا شد: {post}")
            channel = post["channel"]
            post_content = post["post_content"]
            media_paths = post.get("media_paths", [])
            media_ids = post.get("media_ids", [])
            # اگر media_paths و media_ids جفتشون تهی بود، هیچ مدیایی وجود ندارد
            all_medias = []
            if media_paths:
                all_medias.extend(media_paths)
            if media_ids:
                all_medias.extend(media_ids)
            logger.info(f"[TIMER MEDIA] مجموع مدیاها: {all_medias}")

            inline_buttons = post.get("inline_buttons")
            row_width = post.get("row_width", 4)

            inline_keyboard = None
            if data_store.timer_settings.get("inline_buttons_enabled", True) and inline_buttons:
                inline_keyboard = types.InlineKeyboardMarkup(row_width=row_width)
                for button in inline_buttons:
                    inline_keyboard.add(types.InlineKeyboardButton(button["text"], url=button["url"]))

            try:
                if all_medias:
                    logger.info(f"[POST SEND][TIMER] ارسال پست با مدیا به چنل {channel} :: تعداد رسانه: {len(all_medias)}")
                    for i, media in enumerate(all_medias):
                        try:
                            logger.info(f"[POST SEND][TIMER] مدیا #{i}: {media}")
                            # تلاش برای ارسال هر نوع مدیا
                            if "uploader_channel" in media and "uploader_msg_id" in media:
                                bot.copy_message(
                                    channel,
                                    media["uploader_channel"],
                                    media["uploader_msg_id"],
                                    caption=post_content if i == 0 else None,
                                    reply_markup=inline_keyboard if i == 0 else None,
                                    parse_mode="HTML"
                                )
                            elif "file_id" in media:
                                if media.get("type") == "photo":
                                    bot.send_photo(
                                        channel, media["file_id"],
                                        caption=post_content if i == 0 else None,
                                        reply_markup=inline_keyboard if i == 0 else None,
                                        parse_mode="HTML"
                                    )
                                elif media.get("type") == "video":
                                    bot.send_video(
                                        channel, media["file_id"],
                                        caption=post_content if i == 0 else None,
                                        reply_markup=inline_keyboard if i == 0 else None,
                                        parse_mode="HTML"
                                    )
                                else:
                                    bot.send_document(
                                        channel, media["file_id"],
                                        caption=post_content if i == 0 else None,
                                        reply_markup=inline_keyboard if i == 0 else None,
                                        parse_mode="HTML"
                                    )
                            else:
                                logger.warning(f"[POST SEND][TIMER] مدیا #{i} ساختار ناشناخته داشت: {media}")
                        except Exception as e:
                            logger.error(f"[POST SEND][TIMER] خطا در ارسال مدیا #{i}: {e}")
                else:
                    logger.info(f"[POST SEND][TIMER] ارسال پست بدون مدیا به {channel}")
                    bot.send_message(channel, post_content, reply_markup=inline_keyboard, parse_mode="HTML")

                # حذف پست از scheduled_posts فقط اگر ارسال مدیا موفق بود
                data_store.scheduled_posts.remove(post)
                data_store.save_data()
                schedule.clear(job_id)
                logger.info(f"[TIMER SUCCESS] پست زمان‌بندی شده با موفقیت ارسال شد و از لیست حذف شد")
            except Exception as e:
                logger.error(f"[TIMER ERROR] خطا در ارسال پست زمان‌بندی‌شده {job_id}: {e}")
            break
    else:
        logger.warning(f"[TIMER NOT FOUND] پست با job_id {job_id} یافت نشد!")
            

@bot.message_handler(commands=['start'])
@require_join
@require_seen_reaction
def handle_start(message):
    user_id = message.from_user.id

    # اگر می‌خواهیم reset_user_state فراخوانی شود، ابتدا حالت فعلی مهم را نگهداریم و بعد بازیابی کنیم
    preserved = {}
    try:
        current = data_store.user_data.get(str(user_id), {})
        # نگهداری فیلدهای پایدار که نباید از بین بروند
        preserved['is_active'] = current.get('is_active', True)
        preserved['stage'] = current.get('stage', 'start')
        preserved['status'] = current.get('status', 'online')
        # سپس ریست ایمن
        data_store.reset_user_state(user_id)
        # بازیابی فیلدهای ضروری
        u = data_store.user_data.get(str(user_id), {})
        u['is_active'] = preserved['is_active']
        u['stage'] = preserved['stage'] or 'start'
        u['status'] = preserved['status']
        data_store.user_data[str(user_id)] = u
        data_store.save_data()
    except Exception:
        # در صورت خطا از پاکسازی جزئی استفاده کن
        try:
            if getattr(data_store, "coinpy_user", None) == user_id:
                data_store.coinpy_user = None
            if hasattr(data_store, "coinpy_active_msg_id"):
                data_store.coinpy_active_msg_id.pop(user_id, None)
            if hasattr(data_store, "coinpy_chatbuffer"):
                data_store.coinpy_chatbuffer.pop(user_id, None)
        except Exception:
            pass

    # Handler updated: رویه‌ی کامل ارسال فایل و حذف زمان‌بندی‌شده طبق تنظیمات دیتاستور
    if message.text.startswith("/start file_"):
        priv_token = message.text.split()[1]
        priv_link = f"https://t.me/{bot.get_me().username}?start={priv_token}"
        file_info = data_store.uploader_file_map.get(priv_link)
        if not file_info:
            bot.send_message(user_id, "❌ فایل پیدا نشد یا حذف شده است.")
            return
    
        # اگر فایل لیست سفید است: بررسی دسترسی کاربر
        if file_info.get("is_whitelist"):
            allowed = False
            if is_owner(user_id) or is_admin(user_id):
                allowed = True
            if data_store.user_data.get(str(user_id), {}).get("is_whitelisted", False):
                allowed = True
            wh = file_info.get("whitelisted_users", []) or []
            if str(user_id) in list(map(str, wh)) or int(user_id) in [int(x) for x in wh if str(x).isdigit()]:
                allowed = True
            if not allowed:
                bot.send_message(user_id, "🔒 این فایل پرمیوم است.\nبرای دسترسی به این فایل باید با مراجعه به پی وی اونر ربات مورد نظر پرمیوم تهیه کنید!.", reply_markup=get_main_menu(user_id))
                return
    
        ch_link = file_info.get("channel_link")
        if not ch_link:
            bot.send_message(user_id, "❌ لینک فایل نامعتبر است.")
            return
    
        # ایمن‌تر پارس کردن username و message id از لینک کانال
        try:
            parts = ch_link.rstrip("/").split("/")
            channel_username = parts[-2].lstrip("@")
            msg_id = int(parts[-1])
        except Exception:
            bot.send_message(user_id, "❌ ساختار لینک فایل نامعتبر است.")
            return
    
        try:
            if file_info.get("upload_type") == "delete":
                # کپی پیام به کاربر
                copied_msg = bot.copy_message(user_id, f"@{channel_username}", msg_id)
    
                # ایمن‌سازی و ذخیره‌ی آیدی پیام برای استفاده در fallback
                try:
                    if copied_msg and getattr(copied_msg, "message_id", None):
                        data_store.last_message_id[int(user_id)] = copied_msg.message_id
                        logger.info(f"[FILE_DELIVERY] saved message_id {copied_msg.message_id} for user {user_id}")
                except Exception as e:
                    logger.warning(f"[FILE_DELIVERY] failed to save message_id: {e}")

                # سیستم حذف بهبود یافته با چند روش fallback
                def _delete_file_from_user_improved(copied, target_user_id, file_obj):
                    """سیستم حذف بهبود یافته با پشتیبانی از چندین روش حذف"""
                    try:
                        timeout = int(data_store.timer_settings.get("delete_upload_file_timeout", 60) or 60)
                    except Exception:
                        timeout = 60
                
                    logger.info(f"[DELETE_SCHEDULE] scheduling delete in {timeout}s for user={target_user_id} uuid={file_obj.get('uuid')}")
                    
                    # ثبت لاگ زمان‌بندی
                    try:
                        data_store.add_security_log({
                            "action": "file_delete_scheduled",
                            "user_id": int(target_user_id),
                            "file_uuid": file_obj.get("uuid"),
                            "channel_link": file_obj.get("channel_link"),
                            "start_link": file_obj.get("start_link"),
                            "timeout": timeout,
                            "timestamp": datetime.now().isoformat(),
                            "danger_level": 0,
                            "response": f"scheduled to delete after {timeout}s"
                        })
                    except Exception:
                        pass
                
                    def _delete_worker():
                        try:
                            time.sleep(timeout)
                            logger.info(f"[DELETE_WORKER] starting delete process for user={target_user_id}")
                            
                            # روش 1: استفاده از copied message object
                            deleted_success = False
                            deletion_method = "unknown"
                            
                            if copied and hasattr(copied, 'message_id'):
                                try:
                                    bot.delete_message(target_user_id, copied.message_id)
                                    deleted_success = True
                                    deletion_method = "copied_object"
                                    logger.info(f"[DELETE_SUCCESS] method 1 - deleted via copied object: msg_id={copied.message_id}")
                                except Exception as e1:
                                    logger.warning(f"[DELETE_ATTEMPT1] failed via copied object: {e1}")
                            
                            # روش 2: استفاده از cached message_id
                            if not deleted_success:
                                try:
                                    cached_msg_id = data_store.last_message_id.get(int(target_user_id))
                                    if cached_msg_id:
                                        bot.delete_message(target_user_id, cached_msg_id)
                                        deleted_success = True
                                        deletion_method = "cached_id"
                                        logger.info(f"[DELETE_SUCCESS] method 2 - deleted via cache: msg_id={cached_msg_id}")
                                except Exception as e2:
                                    logger.warning(f"[DELETE_ATTEMPT2] failed via cached id: {e2}")
                            
                            # روش 3: تلاش حذف چند پیام اخیر (fallback)
                            if not deleted_success:
                                try:
                                    # گرفتن message_id پیام فعلی و تلاش حذف چند پیام قبلی
                                    current_msg = bot.send_message(target_user_id, ".")
                                    current_id = current_msg.message_id
                                    bot.delete_message(target_user_id, current_id)  # حذف پیام نقطه
                                    
                                    # تلاش حذف 10 پیام قبلی
                                    for i in range(1, 11):
                                        try:
                                            bot.delete_message(target_user_id, current_id - i)
                                            logger.info(f"[DELETE_FALLBACK] deleted message {current_id - i}")
                                            deleted_success = True
                                            deletion_method = f"fallback_sweep_msg_{current_id - i}"
                                        except Exception:
                                            continue
                                    
                                    if deleted_success:
                                        logger.info(f"[DELETE_SUCCESS] method 3 - fallback sweep successful")
                                        
                                except Exception as e3:
                                    logger.warning(f"[DELETE_ATTEMPT3] fallback method failed: {e3}")
                            
                            # روش 4: استفاده از پیام جدید برای تشخیص ID
                            if not deleted_success:
                                try:
                                    # ارسال پیام موقت برای محاسبه message_id احتمالی فایل
                                    temp_msg = bot.send_message(target_user_id, "🔍 در حال جستجوی فایل...")
                                    temp_id = temp_msg.message_id
                                    
                                    # محاسبه احتمالی message_id فایل (معمولاً کمتر از temp_id)
                                    for offset in range(1, 20):
                                        try:
                                            potential_file_id = temp_id - offset
                                            bot.delete_message(target_user_id, potential_file_id)
                                            deleted_success = True
                                            deletion_method = f"calculated_offset_{offset}"
                                            logger.info(f"[DELETE_SUCCESS] method 4 - found file at offset {offset}: msg_id={potential_file_id}")
                                            break
                                        except Exception:
                                            continue
                                    
                                    # حذف پیام موقت
                                    bot.delete_message(target_user_id, temp_id)
                                    
                                except Exception as e4:
                                    logger.warning(f"[DELETE_ATTEMPT4] calculation method failed: {e4}")
                
                            # ثبت نتیجه نهایی
                            if deleted_success:
                                logger.info(f"[DELETE_FINAL] successfully deleted file for user={target_user_id} via {deletion_method}")
                                try:
                                    data_store.add_security_log({
                                        "action": "file_deleted_success",
                                        "user_id": int(target_user_id),
                                        "file_uuid": file_obj.get("uuid"),
                                        "start_link": file_obj.get("start_link"),
                                        "channel_link": file_obj.get("channel_link"),
                                        "deletion_method": deletion_method,
                                        "timeout": timeout,
                                        "timestamp": datetime.now().isoformat(),
                                        "danger_level": 0,
                                        "response": f"successfully deleted after {timeout}s using {deletion_method}"
                                    })
                                except Exception:
                                    pass
                                
                                # پیام اطلاع‌رسانی حذف موفق
                                try:
                                    bot.send_message(
                                        target_user_id,
                                        "✅ فایل با موفقیت حذف شد.\n💡 برای دریافت مجدد، دوباره روی لینک کلیک کنید.",
                                        reply_markup=get_main_menu(target_user_id)
                                    )
                                except Exception:
                                    pass
                                    
                            else:
                                logger.error(f"[DELETE_FINAL] all deletion methods failed for user={target_user_id}")
                                try:
                                    data_store.add_security_log({
                                        "action": "file_delete_failed_all_methods",
                                        "user_id": int(target_user_id),
                                        "file_uuid": file_obj.get("uuid"),
                                        "start_link": file_obj.get("start_link"),
                                        "channel_link": file_obj.get("channel_link"),
                                        "timeout": timeout,
                                        "timestamp": datetime.now().isoformat(),
                                        "danger_level": 3,
                                        "response": f"all 4 deletion methods failed after {timeout}s"
                                    })
                                except Exception:
                                    pass
                
                                # ارسال دکمه دریافت مجدد
                                try:
                                    start_link = file_obj.get("start_link")
                                    if start_link:
                                        ik = types.InlineKeyboardMarkup()
                                        ik.add(types.InlineKeyboardButton("📥 دریافت مجدد فایل", url=start_link))
                                        bot.send_message(
                                            target_user_id,
                                            "⚠️ خطا در حذف خودکار فایل.\n💡 برای دریافت مجدد از دکمه زیر استفاده کنید:",
                                            reply_markup=ik
                                        )
                                except Exception:
                                    pass
                
                        except Exception as e:
                            logger.exception(f"[DELETE_WORKER] unexpected error while deleting file for user={target_user_id}: {e}")
                            try:
                                data_store.add_security_log({
                                    "action": "file_delete_worker_error",
                                    "user_id": int(target_user_id),
                                    "file_uuid": file_obj.get("uuid"),
                                    "error": str(e),
                                    "timestamp": datetime.now().isoformat(),
                                    "danger_level": 2,
                                    "response": f"delete worker crashed: {e}"
                                })
                            except Exception:
                                pass
                
                    # راه‌اندازی thread حذف
                    threading.Thread(target=_delete_worker, daemon=True).start()
    
                # اجرای سیستم حذف بهبود یافته
                _delete_file_from_user_improved(copied_msg, user_id, file_info)
                
                # ارسال پیام تایید دریافت
                try:
                    bot.send_message(
                        user_id, 
                        f"📁 فایل ارسال شد!\n⏰ این فایل پس از {data_store.timer_settings.get('delete_upload_file_timeout', 60)} ثانیه حذف خواهد شد.",
                        reply_markup=get_main_menu(user_id)
                    )
                except Exception:
                    pass
                    
                return
            else:
                # فایل دائمی: فقط کپی کن و بازگردان
                bot.copy_message(user_id, f"@{channel_username}", msg_id)
                try:
                    bot.send_message(
                        user_id,
                        "📁 فایل دائمی ارسال شد!\n💾 این فایل حذف نخواهد شد.",
                        reply_markup=get_main_menu(user_id)
                    )
                except Exception:
                    pass
                return
        except Exception as ex:
            logger.error(f"[FILE_DELIVERY] error sending file to user {user_id}: {ex}")
            bot.send_message(user_id, f"❌ خطا در ارسال فایل: {ex}")
        return

    # ثبت یا بروزرسانی اطلاعات کاربر
    now = datetime.now().isoformat()
    user_info = data_store.user_data.get(str(user_id))
    if not user_info:
        data_store.user_data[str(user_id)] = {
            "first_name": message.from_user.first_name or "",
            "last_name": message.from_user.last_name or "",
            "username": message.from_user.username or "",
            "join_date": now,
            "is_active": True,
            "stage": "start",
            "status": "online",
            "maram": False
        }
        data_store.save_data()
    else:
        if not user_info.get("is_active", False):
            data_store.user_data[str(user_id)]["is_active"] = True
            data_store.user_data[str(user_id)]["status"] = "online"
            data_store.user_data[str(user_id)]["stage"] = "start"
            data_store.save_data()

    if user_id not in data_store.broadcast_users:
        data_store.broadcast_users.append(user_id)
        data_store.save_data()

    user_name = message.from_user.first_name or ""
    markup = get_main_menu(user_id)
    if is_owner(user_id) or is_admin(user_id):
        welcome_text = data_store.settings.get("default_welcome", "🌟 خوش آمدید {name} عزیز! 🌟").format(name=user_name)
        data_store.last_user_message_id[user_id] = message.message_id
        msg = bot.send_message(user_id, f"{welcome_text}", reply_markup=markup)
        data_store.last_message_id[user_id] = msg.message_id
    else:
        bot.send_message(
            user_id,
            f"سلام {user_name} عزیز!\nشما کاربر معمولی هستید و به امکانات مدیریت دسترسی ندارید.\nبرای امکانات بیشتر با مدیر بات تماس بگیرید.",
            reply_markup=markup
        )

# ===========================مدیریت چنل و ضد خیانت======================
# دسترسی‌های مختلف ادمین چنل
CHANNEL_ADMIN_PERMISSIONS = [
    ("can_change_info", "ادیت چنل"),
    ("can_post_messages", "ارسال پیام"),
    ("can_edit_messages", "ادیت پیام دیگران"),
    ("can_delete_messages", "حذف پیام دیگران"),
    ("can_post_stories", "ارسال استوری"),
    ("can_edit_stories", "ویرایش استوری دیگران"),
    ("can_delete_stories", "حذف استوری دیگران"),
    ("can_invite_users", "دعوت کاربران از طریق لینک"),
    ("can_manage_video_chats", "مدیریت ویدیو چت"),
    ("can_promote_members", "افزودن ادمین جدید"),
]

# سطوح خطر برای اعمال مختلف
DANGER_LEVELS = {
    "member_removed": 4,        # حذف عضو - فقط برای خلع ادمینی
    "admin_removed": 4,         # حذف ادمین
    "channel_updated": 2,       # تغییر تنظیمات چنل
    "messages_deleted": 1,      # حذف پیام‌ها (بالک)
    "member_banned": 3,         # بن کردن عضو
    "admin_promoted": 2,        # ادمین کردن کسی
    "channel_photo_deleted": 4, # حذف عکس چنل
    "channel_title_changed": 3, # تغییر اسم چنل
    "new_post": 1,              # ارسال پست جدید
    "post_edited": 1,           # ویرایش پست
}

def get_channel_management_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(types.KeyboardButton("🛡️ ضد خیانت"))
    markup.add(types.KeyboardButton("🔙 بازگشت به منوی اصلی"))
    return markup

def get_anti_betrayal_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(types.KeyboardButton("➕ افزودن ادمین محفوظ"), types.KeyboardButton("➖ حذف ادمین محفوظ"))
    markup.add(types.KeyboardButton("✏️ تنظیم دسترسی‌ها"), types.KeyboardButton("🔍 بررسی ادمین‌ها"))
    markup.add(types.KeyboardButton("➕ افزودن چنل ضد خیانت"), types.KeyboardButton("➖ حذف چنل ضد خیانت"))
    markup.add(types.KeyboardButton("📋 لیست چنل ضد خیانت"))
    markup.add(types.KeyboardButton("🚨 تنظیم هشدارها"), types.KeyboardButton("📈 آمار امنیتی"))
    markup.add(types.KeyboardButton("🔙 بازگشت به مدیریت چنل"))
    return markup

def get_back_menu():
    """منوی بازگشت ساده"""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
    markup.add(types.KeyboardButton("🔙 لغو"))
    return markup

def show_channels_list_for_admin_add(user_id):
    # فقط چنل‌های محافظت شده را نمایش بده
    if not data_store.protected_channels:
        bot.send_message(user_id, "❌ هیچ چنل ضد خیانت ثبت نشده است.", reply_markup=get_anti_betrayal_menu())
        return

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
    for channel in data_store.protected_channels:
        markup.add(types.KeyboardButton(f"📢 {channel}"))
    markup.add(types.KeyboardButton("🔙 لغو"))
    data_store.update_user_state(user_id, "select_channel_for_admin_add")
    bot.send_message(user_id, "📢 **انتخاب چنل ضد خیانت**\n\nچنل مورد نظر برای افزودن ادمین محفوظ را انتخاب کنید:", 
                    reply_markup=markup, parse_mode="HTML")

def show_admin_list_for_permission_edit(user_id, channel):
    """نمایش لیست ادمین‌های چنل برای ویرایش دسترسی"""
    try:
        # دریافت ادمین‌های واقعی چنل از تلگرام
        chat_admins = bot.get_chat_administrators(channel)
        
        if not chat_admins:
            bot.send_message(user_id, f"❌ نتوانستم ادمین‌های چنل {channel} را دریافت کنم.", 
                            reply_markup=get_anti_betrayal_menu())
            return
        
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
        
        for admin in chat_admins:
            # رد کردن خود ربات
            if admin.user.id == bot.get_me().id:
                continue
                
            name = admin.user.first_name or "نام نامشخص"
            admin_id = admin.user.id
            
            # نوع ادمین
            admin_type = "👑" if admin.status == "creator" else "👤"
            
            markup.add(types.KeyboardButton(f"{admin_type} {name} ({admin_id})"))
        
        if markup.keyboard:  # اگر ادمینی پیدا شد
            markup.add(types.KeyboardButton("🔙 لغو"))
            data_store.update_user_state(user_id, "select_admin_for_permission_edit", {"channel": channel})
            bot.send_message(user_id, f"👤 **انتخاب ادمین**\n\nادمین مورد نظر در چنل {channel} را برای ویرایش دسترسی انتخاب کنید:", 
                            reply_markup=markup, parse_mode="HTML")
        else:
            bot.send_message(user_id, f"❌ هیچ ادمین قابل ویرایشی در چنل {channel} یافت نشد.", 
                            reply_markup=get_anti_betrayal_menu())
        
    except Exception as e:
        logger.error(f"خطا در دریافت لیست ادمین‌های چنل {channel}: {e}")
        bot.send_message(user_id, "❌ خطا در دریافت اطلاعات. لطفاً بررسی کنید که ربات ادمین چنل باشد.", 
                        reply_markup=get_anti_betrayal_menu())

@bot.message_handler(func=lambda m: m.text == "📊 مدیریت چنل")
def handle_channel_management_entry(message):
    user_id = message.from_user.id
    if user_id not in data_store.admins:
        bot.send_message(user_id, "❌ شما دسترسی به این بخش ندارید.")
        return
    
    permissions = data_store.admin_permissions.get(str(user_id), {})
    if not permissions.get("manage_channel", False):
        bot.send_message(user_id, "❌ شما دسترسی مدیریت چنل ندارید.")
        return
    
    data_store.update_user_state(user_id, "channel_management_menu")
    
    # نمایش آمار کلی
    total_channels = len(data_store.channels)
    total_protected = len(data_store.protected_channels)
    total_admins = sum(len(admins) for admins in data_store.channel_admins.values())
    security_status = "🟢 فعال" if data_store.get_security_settings().get("enabled", True) else "🔴 غیرفعال"
    
    msg = f"""🛡️ **پنل مدیریت چنل**

📊 **آمار کلی:**
🏢 کل چنل‌ها: {total_channels}
🛡️ چنل‌های محافظت شده: {total_protected}
👥 کل ادمین‌های تحت نظر: {total_admins}
🔐 وضعیت امنیتی: {security_status}

لطفاً یکی از گزینه‌های زیر را انتخاب کنید:"""
    
    bot.send_message(user_id, msg, reply_markup=get_channel_management_menu(), parse_mode="HTML")

@bot.message_handler(func=lambda m: data_store.get_user_state(m.from_user.id)["state"] == "channel_management_menu")
def handle_channel_management_menu(message):
    user_id = message.from_user.id
    text = message.text
    
    if text == "🛡️ ضد خیانت":
        data_store.update_user_state(user_id, "anti_betrayal_menu")
        bot.send_message(user_id, "🛡️ **ضد خیانت فعال شد**\n\nیکی از گزینه‌های زیر را انتخاب کنید:", 
                        reply_markup=get_anti_betrayal_menu(), parse_mode="HTML")
    
    elif text == "🔙 بازگشت به منوی اصلی":
        data_store.reset_user_state(user_id)
        bot.send_message(user_id, "🏠 بازگشت به منوی اصلی:", reply_markup=get_main_menu(user_id))

@bot.message_handler(func=lambda m: data_store.get_user_state(m.from_user.id)["state"] == "anti_betrayal_menu")
def handle_anti_betrayal_menu(message):
    user_id = message.from_user.id
    text = message.text

    if text == "➕ افزودن ادمین محفوظ":
        show_channels_list_for_admin_add(user_id)

    elif text == "➖ حذف ادمین محفوظ":
        show_protected_admins_for_removal(user_id)

    elif text == "✏️ تنظیم دسترسی‌ها":
        show_channels_for_permission_edit(user_id)

    elif text == "🔍 بررسی ادمین‌ها":
        start_admin_check(user_id)

    elif text == "🚨 تنظیم هشدارها":
        data_store.update_user_state(user_id, "alert_settings")
        show_alert_settings(user_id)

    elif text == "📈 آمار امنیتی":
        show_security_stats(user_id)

    elif text == "➕ افزودن چنل ضد خیانت":
        data_store.update_user_state(user_id, "add_protected_channel")
        bot.send_message(user_id, "آیدی چنل ضد خیانت را وارد کنید (مثال: @channelname):", reply_markup=get_back_menu())

    elif text == "➖ حذف چنل ضد خیانت":
        if not data_store.protected_channels:
            bot.send_message(user_id, "هیچ چنل ضد خیانت ثبت نشده.", reply_markup=get_anti_betrayal_menu())
        else:
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
            for ch in data_store.protected_channels:
                markup.add(types.KeyboardButton(ch))
            markup.add(types.KeyboardButton("🔙 بازگشت به منوی ضد خیانت"))
            data_store.update_user_state(user_id, "remove_protected_channel")
            bot.send_message(user_id, "یک چنل برای حذف انتخاب کن:", reply_markup=markup)

    elif text == "📋 لیست چنل ضد خیانت":
        chans = data_store.protected_channels
        if chans:
            ch_list = "\n".join(chans)
            bot.send_message(user_id, f"📋 لیست چنل‌های ضد خیانت ثبت‌شده:\n{ch_list}", reply_markup=get_anti_betrayal_menu())
        else:
            bot.send_message(user_id, "هیچ چنل ضد خیانت ثبت نشده.", reply_markup=get_anti_betrayal_menu())

    elif text == "🔙 بازگشت به مدیریت چنل":
        data_store.update_user_state(user_id, "channel_management_menu")
        bot.send_message(user_id, "🛡️ پنل مدیریت چنل:", reply_markup=get_channel_management_menu())
       
@bot.message_handler(func=lambda m: data_store.get_user_state(m.from_user.id)["state"] == "add_protected_channel")
def handle_add_protected_channel(message):
    user_id = message.from_user.id
    channel_name = message.text.strip()
    
    if channel_name == "🔙 لغو":
        data_store.update_user_state(user_id, "anti_betrayal_menu")
        bot.send_message(user_id, "منوی ضد خیانت:", reply_markup=get_anti_betrayal_menu())
        return
    
    if not channel_name.startswith('@'):
        msg = bot.send_message(user_id, f"⚠️ آیدی چنل باید با @ شروع شود (مثال: @channelname).", reply_markup=get_back_menu())
        data_store.last_message_id[user_id] = msg.message_id
        return
    
    try:
        chat = bot.get_chat(channel_name)
        bot_member = bot.get_chat_member(channel_name, bot.get_me().id)
        
        if bot_member.status not in ['administrator', 'creator']:
            permissions_text = "ربات باید حتماً ادمین چنل باشد!"
            msg = bot.send_message(user_id, f"❌ {permissions_text}\nحتماً ربات را به عنوان ادمین به چنل اضافه کنید.", reply_markup=get_back_menu())
            data_store.last_message_id[user_id] = msg.message_id
            return
        
        # بررسی دسترسی‌های مورد نیاز ربات
        required_permissions = {
            "can_change_info": getattr(bot_member, 'can_change_info', False),
            "can_post_messages": getattr(bot_member, 'can_post_messages', False),
            "can_edit_messages": getattr(bot_member, 'can_edit_messages', False),
            "can_delete_messages": getattr(bot_member, 'can_delete_messages', False),
            "can_invite_users": getattr(bot_member, 'can_invite_users', False),
            "can_manage_video_chats": getattr(bot_member, 'can_manage_video_chats', False),
            "can_promote_members": getattr(bot_member, 'can_promote_members', False)
        }
        
        missing_permissions = [name for name, granted in required_permissions.items() if not granted]
        
        if missing_permissions:
            permissions_text = "\n".join([
                f"{'✅' if required_permissions[perm] else '❌'} {perm}" for perm in required_permissions
            ])
            msg = bot.send_message(
                user_id,
                f"❌ همه مجوزهای زیر باید فعال باشد:\n{permissions_text}\nلطفاً همه دسترسیها را بدهید و دوباره امتحان کنید.",
                reply_markup=get_back_menu()
            )
            data_store.last_message_id[user_id] = msg.message_id
            return
        
        if channel_name in data_store.protected_channels:
            msg = bot.send_message(user_id, f"⚠️ این چنل قبلاً در لیست محافظت شده ثبت شده است.", reply_markup=get_back_menu())
            data_store.last_message_id[user_id] = msg.message_id
            return
        
        data_store.protected_channels.append(channel_name)
        data_store.save_data()
        
        data_store.update_user_state(user_id, "anti_betrayal_menu")
        msg = bot.send_message(user_id, f"✅ چنل ضد خیانت {channel_name} ثبت شد و همه دسترسیها چک شد.", reply_markup=get_anti_betrayal_menu())
        data_store.last_message_id[user_id] = msg.message_id
        
    except Exception as e:
        logger.error(f"خطا در بررسی دسترسی چنل {channel_name}: {e}")
        error_message = "❌ خطا در بررسی چنل. لطفاً بررسی کنید که:\n• ربات عضو چنل باشد\n• ربات ادمین چنل باشد\n• تمام دسترسی‌های لازم داده شده باشد"
        msg = bot.send_message(user_id, error_message, reply_markup=get_back_menu())
        data_store.last_message_id[user_id] = msg.message_id
        return

@bot.message_handler(func=lambda m: data_store.get_user_state(m.from_user.id)["state"] == "remove_protected_channel")
def handle_remove_protected_channel(message):
    user_id = message.from_user.id
    channel_name = message.text.strip()
    
    if channel_name == "🔙 بازگشت به منوی ضد خیانت":
        data_store.update_user_state(user_id, "anti_betrayal_menu")
        bot.send_message(user_id, "منوی ضد خیانت:", reply_markup=get_anti_betrayal_menu())
        return
    
    if channel_name in data_store.protected_channels:
        data_store.protected_channels.remove(channel_name)
        # حذف ادمین‌های این چنل نیز
        if channel_name in data_store.channel_admins:
            del data_store.channel_admins[channel_name]
        data_store.save_data()
        data_store.update_user_state(user_id, "anti_betrayal_menu")
        msg = bot.send_message(user_id, f"✅ چنل ضد خیانت {channel_name} از لیست محافظت شده حذف شد.", reply_markup=get_anti_betrayal_menu())
        data_store.last_message_id[user_id] = msg.message_id
    else:
        msg = bot.send_message(user_id, f"⚠️ چنل {channel_name} در لیست محافظت شده وجود ندارد.", reply_markup=get_back_menu())
        data_store.last_message_id[user_id] = msg.message_id
        data_store.update_user_state(user_id, "anti_betrayal_menu")
        
@bot.message_handler(func=lambda m: data_store.get_user_state(m.from_user.id)["state"] == "select_channel_for_admin_add")
def handle_channel_selection_for_admin_add(message):
    user_id = message.from_user.id
    text = message.text.strip()
    
    if text == "🔙 لغو":
        data_store.update_user_state(user_id, "anti_betrayal_menu")
        bot.send_message(user_id, "عملیات لغو شد.", reply_markup=get_anti_betrayal_menu())
        return
    
    # استخراج نام چنل
    channel = text.replace("📢 ", "")
    
    if channel not in data_store.protected_channels:
        bot.send_message(user_id, "❌ چنل نامعتبر است.", reply_markup=get_back_menu())
        return
    
    data_store.update_user_state(user_id, "add_protected_admin_step1", {"selected_channel": channel})
    bot.send_message(user_id, f"""➕ **افزودن ادمین محفوظ**
    
🏢 **چنل انتخاب شده:** {channel}

لطفاً آیدی عددی کاربری که می‌خواهید به عنوان ادمین محفوظ اضافه کنید را وارد کنید:

مثال: 123456789

⚠️ این کاربر باید قبلاً در چنل مورد نظر ادمین باشد.""", 
                    reply_markup=get_back_menu(), parse_mode="HTML")

import re
import time
from datetime import datetime
from telebot.apihelper import ApiTelegramException

@bot.message_handler(func=lambda m: data_store.get_user_state(m.from_user.id)["state"] == "add_protected_admin_step1")
def handle_add_protected_admin_step1(message):
    user_id = message.from_user.id
    text = (message.text or "").strip()
    state_data = data_store.get_user_state(user_id).get("data", {})

    # بازگشت
    if text == "🔙 لغو":
        data_store.update_user_state(user_id, "anti_betrayal_menu")
        bot.send_message(user_id, "عملیات لغو شد.", reply_markup=get_anti_betrayal_menu())
        return

    # اعتبارسنجی آیدی عددی
    if not text.isdigit():
        bot.send_message(user_id, "❌ لطفاً آیدی عددی معتبر وارد کنید.", reply_markup=get_back_menu())
        return

    target_id = int(text)
    channel = state_data.get("selected_channel")
    if not channel:
        bot.send_message(user_id, "❌ خطا در دریافت اطلاعات چنل.", reply_markup=get_anti_betrayal_menu())
        return

    # گرفتن اطلاعات کاربر
    try:
        user_info = bot.get_chat(target_id)
        name = getattr(user_info, "first_name", None) or getattr(user_info, "title", None) or "نام نامشخص"
        username = getattr(user_info, "username", None) or ""
        if username and re.match(r'^[a-zA-Z0-9_]{5,}$', username):
            username_disp = f"@{username}"
        else:
            username_disp = f"آیدی عددی: <code>{target_id}</code>"
    except Exception:
        bot.send_message(user_id, "❌ کاربری با این آیدی یافت نشد.", reply_markup=get_back_menu())
        return

    # بررسی ادمین‌ها و تلاش برای ارتقاء در صورت نیاز
    try:
        chat_admins = bot.get_chat_administrators(channel)
        admin_ids = [admin.user.id for admin in chat_admins]
    except Exception as e:
        bot.send_message(user_id, f"❌ خطا در بررسی وضعیت چنل: {str(e)}", reply_markup=get_back_menu())
        return

    promoted_by_bot = False
    if target_id not in admin_ids:
        # تلاش اولیه برای پروموت با پرمیشن‌های حداقلی که لازم داریم
        try:
            try:
                bot.promote_chat_member(
                    channel,
                    target_id,
                    can_change_info=False,
                    can_post_messages=True,
                    can_edit_messages=False,
                    can_delete_messages=False,
                    can_post_stories=False,
                    can_edit_stories=False,
                    can_delete_stories=False,
                    can_invite_users=True,
                    can_manage_video_chats=False,
                    can_promote_members=False
                )
                promoted_by_bot = True
            except ApiTelegramException as e:
                err = str(e)
                # برخی خطاها ممکن است در پاسخ برگردند اما عمل انجام شده باشد — وضعیت را دوباره چک کن
                time.sleep(1)
                try:
                    chat_admins = bot.get_chat_administrators(channel)
                    admin_ids = [admin.user.id for admin in chat_admins]
                except Exception:
                    admin_ids = []

                if target_id in admin_ids:
                    promoted_by_bot = True
                else:
                    # اگر خطای محدودیت کاربران/ادمین‌ها است، تلاش جایگزین یا علامت‌گذاری درخواست
                    if "USERS_TOO_MUCH" in err.upper() or "USERS_TOO_MANY" in err.upper() or "TOO_MANY" in err.upper():
                        # تلاش جایگزین با حداقل پارامترها (برخی APIها فقط بعضی پارمترها را نیاز دارند)
                        try:
                            bot.promote_chat_member(channel, target_id, can_post_messages=True)
                            time.sleep(1)
                            chat_admins = bot.get_chat_administrators(channel)
                            admin_ids = [admin.user.id for admin in chat_admins]
                            if target_id in admin_ids:
                                promoted_by_bot = True
                            else:
                                # علامت‌گذاری درخواست برای بررسی دستی
                                data_store.channel_admins.setdefault(channel, {"protected": {}, "free": {}})
                                data_store.channel_admins[channel].setdefault("protected", {})[str(target_id)] = {
                                    "pending_promotion": True,
                                    "requested_by": user_id,
                                    "requested_at": datetime.now().isoformat()
                                }
                                data_store.save_data()
                                try:
                                    bot.send_message(OWNER_ID, f"⚠️ درخواست ادمین خودکار برای کاربر <code>{target_id}</code> در {channel} انجام نشد به علت محدودیت سرویس. لطفاً بررسی و در صورت امکان به صورت دستی ادمین کنید.", parse_mode="HTML")
                                except Exception:
                                    pass
                                bot.send_message(user_id, f"⚠️ محدودیت سرویس مانع ادمین خودکار شد. درخواست ادمین برای {username_disp} ذخیره شد و اوُنر اطلاع داده شد.", reply_markup=get_back_menu(), parse_mode="HTML")
                                return
                        except Exception as ex2:
                            bot.send_message(user_id, f"❌ تلاش جایگزین برای ادمین کردن با شکست مواجه شد: {str(ex2)}", reply_markup=get_back_menu())
                            return
                    else:
                        bot.send_message(user_id, f"❌ خطا در ادمین کردن: {err}", reply_markup=get_back_menu())
                        return

            # تأیید نهایی پس از تلاش(ها)
            time.sleep(1)
            try:
                chat_admins = bot.get_chat_administrators(channel)
                admin_ids = [admin.user.id for admin in chat_admins]
            except Exception:
                admin_ids = []

            if not promoted_by_bot and target_id not in admin_ids:
                bot.send_message(user_id, f"❌ کاربر {name} - {username_disp} ادمین نیست و ربات نتوانست او را ادمین کند.", reply_markup=get_back_menu(), parse_mode="HTML")
                return

        except Exception as ex:
            bot.send_message(user_id, f"❌ خطای غیرمنتظره در فرایند ادمین کردن: {str(ex)}", reply_markup=get_back_menu())
            return

    # استخراج دسترسی‌های فعلی کاربر (اگر ادمین است)
    current_permissions = {
        "can_be_edited": False,
        "can_change_info": False,
        "can_post_messages": False,
        "can_edit_messages": False,
        "can_delete_messages": False,
        "can_post_stories": False,
        "can_edit_stories": False,
        "can_delete_stories": False,
        "can_invite_users": False,
        "can_manage_video_chats": False,
        "can_promote_members": False,
    }
    for admin in chat_admins:
        if admin.user.id == target_id:
            # از getattr استفاده می‌کنیم چون بعضی فیلدها ممکن است وجود نداشته باشند بسته به نسخه API
            current_permissions = {
                "can_be_edited": getattr(admin, "can_be_edited", False),
                "can_change_info": getattr(admin, "can_change_info", False),
                "can_post_messages": getattr(admin, "can_post_messages", False),
                "can_edit_messages": getattr(admin, "can_edit_messages", False),
                "can_delete_messages": getattr(admin, "can_delete_messages", False),
                "can_post_stories": getattr(admin, "can_post_stories", False),
                "can_edit_stories": getattr(admin, "can_edit_stories", False),
                "can_delete_stories": getattr(admin, "can_delete_stories", False),
                "can_invite_users": getattr(admin, "can_invite_users", False),
                "can_manage_video_chats": getattr(admin, "can_manage_video_chats", False),
                "can_promote_members": getattr(admin, "can_promote_members", False),
            }
            break

    # ذخیره‌سازی در data_store به صورت محافظت شده
    data_store.channel_admins.setdefault(channel, {"protected": {}, "free": {}})
    admin_permissions = current_permissions.copy()
    admin_permissions['by_bot'] = promoted_by_bot  # اگر ربات او را ادمین کرده باشد True

    data_store.channel_admins[channel].setdefault("protected", {})[str(target_id)] = admin_permissions

    # اضافه کردن چنل به لیست محافظت شده در صورت نیاز
    if channel not in data_store.protected_channels:
        data_store.protected_channels.append(channel)

    data_store.save_data()

    # ثبت لاگ امنیتی
    data_store.add_security_log({
        "action": "افزودن ادمین محافظت شده",
        "admin_id": target_id,
        "admin_name": name,
        "channel": channel,
        "timestamp": datetime.now().isoformat(),
        "danger_level": 0,
        "response": "ادمین به لیست محافظت اضافه شد",
        "by_bot": promoted_by_bot
    })

    data_store.update_user_state(user_id, "anti_betrayal_menu")

    # تعداد دسترسی‌های فعال (غیر از فلگ by_bot)
    permissions_count = sum(1 for k, v in admin_permissions.items() if k != "by_bot" and v)

    # پاسخ نهایی به کاربر
    bot.send_message(user_id,
                     "✅ ادمین محافظت شده اضافه شد\n\n"
                     f"👤 کاربر: {name} ({target_id})\n"
                     f"🏢 چنل: {channel}\n"
                     f"🔑 دسترسی‌های فعال: {permissions_count} مورد\n"
                     f"🛡️ وضعیت: تحت نظارت\n"
                     f"⏰ زمان ثبت: {datetime.now().strftime('%Y/%m/%d - %H:%M')}\n\n"
                     "از این پس تمام فعالیت‌های این ادمین نظارت خواهد شد.",
                     reply_markup=get_anti_betrayal_menu(), parse_mode="HTML")

def show_protected_admins_for_removal(user_id):
    """نمایش لیست ادمین‌های محافظت شده برای حذف"""
    if not data_store.channel_admins:
        bot.send_message(user_id, "❌ هیچ ادمین محفوظی وجود ندارد.", reply_markup=get_anti_betrayal_menu())
        return
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
    
    for channel, admins_container in data_store.channel_admins.items():
        protected = admins_container.get("protected", {})
        for admin_id, perms in protected.items():
            try:
                user_info = bot.get_chat(int(admin_id))
                name = user_info.first_name or "نام نامشخص"
                display_text = f"🗑️ {name} - {channel} ({admin_id})"
                markup.add(types.KeyboardButton(display_text))
            except:
                display_text = f"🗑️ کاربر نامشخص - {channel} ({admin_id})"
                markup.add(types.KeyboardButton(display_text))
    
    markup.add(types.KeyboardButton("🔙 لغو"))
    
    data_store.update_user_state(user_id, "remove_protected_admin")
    bot.send_message(user_id, "➖ **حذف ادمین محفوظ**\n\nیکی از ادمین‌های زیر را برای حذف انتخاب کنید:", 
                    reply_markup=markup, parse_mode="HTML")

@bot.message_handler(func=lambda m: data_store.get_user_state(m.from_user.id)["state"] == "remove_protected_admin")
def handle_remove_protected_admin(message):
    user_id = message.from_user.id
    text = (message.text or "").strip()
    
    if text == "🔙 لغو":
        data_store.update_user_state(user_id, "anti_betrayal_menu")
        bot.send_message(user_id, "عملیات لغو شد.", reply_markup=get_anti_betrayal_menu())
        return
    
    try:
        # استخراج اطلاعات از متن با ایمنی بیشتر
        # فرمت مورد انتظار: "🗑️ Name - channel (123456789)"
        m = re.match(r"^(?:🗑️\s*)?(?P<name>.+?)\s*-\s*(?P<channel>@?[^\(]+)\s*\(\s*(?P<id>\d+)\s*\)\s*$", text)
        if not m:
            bot.send_message(user_id, "❌ فرمت نامعتبر. فرمت درست: '🗑️ نام - @channel (123456789)'.", reply_markup=get_back_menu())
            return
        
        admin_name = m.group("name").strip()
        channel = m.group("channel").strip()
        admin_id = m.group("id").strip()
        
        if channel in data_store.channel_admins and admin_id in data_store.channel_admins[channel].get("protected", {}):
            del data_store.channel_admins[channel]["protected"][admin_id]
            
            # اگر چنل دیگر ادمینی نداشت، از لیست محافظت حذف کن
            if not data_store.channel_admins[channel].get("protected"):
                if not data_store.channel_admins[channel].get("free"):
                    del data_store.channel_admins[channel]
                else:
                    data_store.channel_admins[channel].pop("protected", None)
            
            data_store.save_data()
            
            data_store.add_security_log({
                "action": "حذف ادمین محافظت شده",
                "admin_id": int(admin_id),
                "admin_name": admin_name,
                "channel": channel,
                "timestamp": datetime.now().isoformat(),
                "danger_level": 0,
                "response": "ادمین از لیست محافظت حذف شد"
            })
            
            data_store.update_user_state(user_id, "anti_betrayal_menu")
            bot.send_message(user_id, f"✅ ادمین {admin_name} از چنل {channel} حذف شد.", reply_markup=get_anti_betrayal_menu())
        else:
            bot.send_message(user_id, "❌ ادمین مورد نظر یافت نشد یا قبلاً حذف شده است.", reply_markup=get_back_menu())
            
    except Exception as e:
        logger.exception(f"Error removing protected admin: {e}")
        bot.send_message(user_id, "❌ خطا در حذف ادمین. جزئیات در لاگ ثبت شد.", reply_markup=get_back_menu())
        
def show_channels_for_permission_edit(user_id):
    """نمایش چنل‌ها برای تنظیم دسترسی‌ها"""
    if not data_store.protected_channels:
        bot.send_message(user_id, "❌ هیچ چنل محافظت شده‌ای وجود ندارد.\n\nابتدا چنل‌ها را اضافه کنید.", 
                        reply_markup=get_anti_betrayal_menu())
        return
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
    for channel in data_store.protected_channels:
        # شمارش ادمین‌های واقعی در چنل
        try:
            chat_admins = bot.get_chat_administrators(channel)
            admin_count = len([admin for admin in chat_admins if admin.user.id != bot.get_me().id])
        except:
            admin_count = 0
        
        markup.add(types.KeyboardButton(f"📝 {channel} ({admin_count} ادمین)"))
    
    markup.add(types.KeyboardButton("🔙 لغو"))
    
    data_store.update_user_state(user_id, "select_channel_for_permissions")
    bot.send_message(user_id, "✏️ **تنظیم دسترسی‌ها**\n\nچنل مورد نظر را انتخاب کنید:", 
                    reply_markup=markup, parse_mode="HTML")

@bot.message_handler(func=lambda m: data_store.get_user_state(m.from_user.id)["state"] == "select_channel_for_permissions")
def handle_channel_selection_for_permissions(message):
    user_id = message.from_user.id
    text = message.text.strip()
    
    if text == "🔙 لغو":
        data_store.update_user_state(user_id, "anti_betrayal_menu")
        bot.send_message(user_id, "عملیات لغو شد.", reply_markup=get_anti_betrayal_menu())
        return
    
    # استخراج نام چنل
    channel = text.split(' (')[0].replace("📝 ", "")
    
    if channel not in data_store.protected_channels:
        bot.send_message(user_id, "❌ چنل نامعتبر است.", reply_markup=get_back_menu())
        return
    
    show_admin_list_for_permission_edit(user_id, channel)

# handlers/permissions.py
import re
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# توجه: فرض شده bot, types, data_store, OWNER_ID و توابع کمکی مثل get_anti_betrayal_menu و get_back_menu در جای دیگری تعریف شده‌اند.

def _extract_admin_id_from_text(text):
    """سعی کن یک آیدی عددی از متن استخراج کنی (پشتیبانی از فرمت 'Name (12345)' یا فقط '12345')."""
    if not text:
        return None
    # اول به دنبال پرانتز باشیم
    m = re.search(r'\((\d{5,})\)', text)
    if m:
        return m.group(1)
    # بعد، هر اولین توالی طولانی از ارقام
    m = re.search(r'(\d{5,})', text)
    if m:
        return m.group(1)
    return None

@bot.message_handler(func=lambda m: data_store.get_user_state(m.from_user.id)["state"] == "select_admin_for_permission_edit")
def handle_admin_selection_for_permission_edit(message):
    user_id = message.from_user.id
    text = (message.text or "").strip()
    logger.info(f"[PERM_SELECT] User {user_id} selected admin text: {text}")

    state = data_store.get_user_state(user_id)
    state_data = state.get("data", {})
    channel = state_data.get("channel")
    if not channel:
        logger.error(f"[PERM_SELECT] No channel in user state for user {user_id}: {state}")
        bot.send_message(user_id, "❌ خطا: اطلاعات چنل یافت نشد. لطفا دوباره تلاش کنید.", reply_markup=get_anti_betrayal_menu())
        return

    if text == "🔙 لغو":
        data_store.update_user_state(user_id, "anti_betrayal_menu")
        bot.send_message(user_id, "عملیات لغو شد.", reply_markup=get_anti_betrayal_menu())
        logger.info(f"[PERM_SELECT] User {user_id} canceled admin selection for channel {channel}")
        return

    admin_id = _extract_admin_id_from_text(text)
    if not admin_id:
        logger.warning(f"[PERM_SELECT] Invalid admin id format from user {user_id}: '{text}'")
        bot.send_message(user_id, "❌ فرمت نامعتبر است. لطفاً آیدی را مطابق مثال وارد کنید: نام (123456789)", reply_markup=get_back_menu())
        return

    try:
        logger.info(f"[PERM_SELECT] Fetching chat admins for channel {channel} to find admin {admin_id}")
        chat_admins = bot.get_chat_administrators(channel)
    except Exception as ex:
        logger.exception(f"[PERM_SELECT] Failed to get chat administrators for {channel}: {ex}")
        bot.send_message(user_id, "❌ خطا در دریافت لیست ادمین‌ها از تلگرام. ممکن است چنل در دسترس نباشد یا بات مجوز لازم را ندارد.", reply_markup=get_back_menu())
        return

    target_admin = None
    for admin in chat_admins:
        try:
            if str(admin.user.id) == str(admin_id):
                target_admin = admin
                break
        except Exception:
            continue

    if not target_admin:
        logger.warning(f"[PERM_SELECT] Admin {admin_id} not found in channel {channel} for user {user_id}")
        bot.send_message(user_id, "❌ این کاربر در چنل ادمین نیست.", reply_markup=get_back_menu())
        return

    logger.info(f"[PERM_SELECT] Found admin {admin_id} in channel {channel} for user {user_id}")
    show_permission_edit_menu(user_id, channel, admin_id, target_admin)


def show_permission_edit_menu(user_id, channel, admin_id, admin_obj):
    """نمایش منوی ویرایش دسترسی‌های ادمین - نسخه اصلاح شده با لاگ کامل"""
    logger.info(f"[SHOW_PERM_MENU] user={user_id}, channel={channel}, admin_id={admin_id}")
    try:
        admin_name = getattr(admin_obj.user, "first_name", None) or "نام نامشخص"
    except Exception:
        admin_name = "کاربر نامشخص"

    if str(admin_id) == str(OWNER_ID):
        logger.warning(f"[SHOW_PERM_MENU] Attempt to edit owner perms by user {user_id} for owner {admin_id}")
        bot.send_message(user_id, "❌ دسترسی اونر قابل تغییر نیست.", reply_markup=get_anti_betrayal_menu())
        return

    # آماده سازی ساختار در data_store در صورت نبودن
    channel_entry = data_store.channel_admins.setdefault(channel, {})
    protected = channel_entry.setdefault("protected", {})

    if str(admin_id) not in protected:
        # سعی کن پرمیشن فعلی را از تلگرام بگیری
        logger.info(f"[SHOW_PERM_MENU] No protected perms cached for {admin_id}@{channel} - fetching from telegram")
        try:
            chat_admins = bot.get_chat_administrators(channel)
        except Exception as ex:
            logger.exception(f"[SHOW_PERM_MENU] Failed to get chat admins for {channel}: {ex}")
            bot.send_message(user_id, "❌ خطا در دریافت اطلاعات چنل. لطفاً دسترسی بات و نام چنل را بررسی کنید.", reply_markup=get_back_menu())
            return

        admin_perms = {}
        for admin in chat_admins:
            try:
                if str(admin.user.id) == str(admin_id):
                    admin_perms = {
                        "can_change_info": getattr(admin, 'can_change_info', False),
                        "can_post_messages": getattr(admin, 'can_post_messages', False),
                        "can_edit_messages": getattr(admin, 'can_edit_messages', False),
                        "can_delete_messages": getattr(admin, 'can_delete_messages', False),
                        "can_post_stories": getattr(admin, 'can_post_stories', False),
                        "can_edit_stories": getattr(admin, 'can_edit_stories', False),
                        "can_delete_stories": getattr(admin, 'can_delete_stories', False),
                        "can_invite_users": getattr(admin, 'can_invite_users', False),
                        "can_manage_video_chats": getattr(admin, 'can_manage_video_chats', False),
                        "can_promote_members": getattr(admin, 'can_promote_members', False),
                    }
                    break
            except Exception:
                continue
        protected[str(admin_id)] = admin_perms
        try:
            data_store.save_data()
            logger.info(f"[SHOW_PERM_MENU] Saved initial perms for {admin_id}@{channel} into data_store")
        except Exception as ex:
            logger.exception(f"[SHOW_PERM_MENU] Failed to save data_store after caching admin perms: {ex}")

    current_perms = protected.get(str(admin_id), {})
    if not isinstance(current_perms, dict):
        logger.error(f"[SHOW_PERM_MENU] current_perms not dict for {admin_id}@{channel}: {current_perms}")
        bot.send_message(user_id, "❌ خطا در خواندن دسترسی‌ها.", reply_markup=get_back_menu())
        return

    # ساخت دکمه‌ها
    markup = types.InlineKeyboardMarkup(row_width=2)
    permissions_map = {
        "can_change_info": "ادیت چنل",
        "can_post_messages": "ارسال پیام",
        "can_edit_messages": "ادیت پیام",
        "can_delete_messages": "حذف پیام",
        "can_post_stories": "ارسال استوری",
        "can_edit_stories": "ادیت استوری",
        "can_delete_stories": "حذف استوری",
        "can_invite_users": "دعوت کاربران",
        "can_manage_video_chats": "مدیریت ویدیو",
        "can_promote_members": "ادمین کردن"
    }

    for key, name in permissions_map.items():
        status = "✅" if current_perms.get(key, False) else "❌"
        callback = f"perm_{channel}_{admin_id}_{key}"
        # توجه: callback ممکن است طولانی باشد؛ اگر خیلی طولانی است می‌توان از شناسه داخلی استفاده کرد.
        markup.add(types.InlineKeyboardButton(f"{status} {name}", callback_data=callback))

    # دکمه‌های نهایی (ذخیره و بازگشت)
    markup.add(
        types.InlineKeyboardButton("💾 اعمال تغییرات", callback_data=f"save_{channel}_{admin_id}"),
        types.InlineKeyboardButton("🔙 بازگشت", callback_data="back")
    )

    msg = (f"✏️ **ویرایش دسترسی‌های ادمین**\n\n"
           f"👤 **ادمین:** {admin_name} ({admin_id})\n"
           f"🏢 **چنل:** {channel}\n\n"
           "**دسترسی‌های فعلی:**\n"
           "روی هر دسترسی کلیک کنید تا وضعیت آن تغییر کند:")

    # ذخیره state کاربر به شکل امن
    data_store.update_user_state(user_id, f"edit_perm_{channel}_{admin_id}", {
        "channel": channel,
        "admin_id": admin_id,
        "admin_name": admin_name,
        "temp_permissions": current_perms.copy()
    })
    logger.info(f"[SHOW_PERM_MENU] Updated user state for {user_id} => edit_perm_{channel}_{admin_id}")

    try:
        bot.send_message(user_id, msg, reply_markup=markup, parse_mode="HTML")
    except Exception as ex:
        logger.exception(f"[SHOW_PERM_MENU] Failed to send permission edit menu to {user_id}: {ex}")


@bot.callback_query_handler(func=lambda call: call.data.startswith("perm_"))
def handle_permission_toggle(call):
    user_id = call.from_user.id
    logger.info(f"[PERM_TOGGLE] Callback from user={user_id}, data={call.data}")
    try:
        payload = call.data[len("perm_"):]  # everything after prefix
        m = re.match(r'^(?P<channel>.+)_(?P<admin_id>\d+)_(?P<perm_key>.+)$', payload)
        if not m:
            logger.error(f"[PERM_TOGGLE] Invalid callback_data format: {call.data}")
            bot.answer_callback_query(call.id, "❌ فرمت داده نامعتبر")
            return

        channel = m.group('channel')
        admin_id = m.group('admin_id')
        perm_key = m.group('perm_key')

        logger.info(f"[PERM_TOGGLE] Parsed channel={channel}, admin_id={admin_id}, perm_key={perm_key}")

        state = data_store.get_user_state(user_id)
        expected_state = f"edit_perm_{channel}_{admin_id}"
        if state.get("state") != expected_state:
            logger.warning(f"[PERM_TOGGLE] State mismatch for user {user_id}: expected={expected_state}, got={state.get('state')}")
            bot.answer_callback_query(call.id, "❌ خطا در وضعیت (ممکن است منو منقضی شده باشد)")
            return

        perms = data_store.channel_admins.get(channel, {}).get("protected", {}).get(str(admin_id))
        if perms is None:
            logger.error(f"[PERM_TOGGLE] No perms entry for {admin_id}@{channel}")
            bot.answer_callback_query(call.id, "❌ خطا: داده دسترسی موجود نیست")
            return

        old = perms.get(perm_key, False)
        perms[perm_key] = not old
        logger.info(f"[PERM_TOGGLE] Toggled {perm_key} for {admin_id}@{channel}: {old} -> {perms[perm_key]}")

        try:
            data_store.save_data()
        except Exception as ex:
            logger.exception(f"[PERM_TOGGLE] Failed to save data_store after toggle: {ex}")
            bot.answer_callback_query(call.id, "❌ خطا در ذخیره تغییرات")
            return

        state.setdefault("data", {})["temp_permissions"] = perms.copy()
        data_store.user_states[str(user_id)] = state

        try:
            permissions_map = [
                ("can_change_info", "ادیت چنل"),
                ("can_post_messages", "ارسال پیام"),
                ("can_edit_messages", "ادیت پیام"),
                ("can_delete_messages", "حذف پیام"),
                ("can_post_stories", "ارسال استوری"),
                ("can_edit_stories", "ادیت استوری"),
                ("can_delete_stories", "حذف استوری"),
                ("can_invite_users", "دعوت کاربران"),
                ("can_manage_video_chats", "مدیریت ویدیو"),
                ("can_promote_members", "ادمین کردن")
            ]
            markup = types.InlineKeyboardMarkup(row_width=2)
            for key, name in permissions_map:
                status = "✅" if perms.get(key, False) else "❌"
                markup.add(types.InlineKeyboardButton(f"{status} {name}", callback_data=f"perm_{channel}_{admin_id}_{key}"))

            markup.add(
                types.InlineKeyboardButton("💾 اعمال تغییرات", callback_data=f"save_{channel}_{admin_id}"),
                types.InlineKeyboardButton("🔙 بازگشت", callback_data="back")
            )

            bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=markup)
            bot.answer_callback_query(call.id, "✅ تغییر اعمال شد")
            logger.info(f"[PERM_TOGGLE] Updated inline markup for user {user_id}")
        except Exception as ex:
            logger.exception(f"[PERM_TOGGLE] Failed to edit message markup: {ex}")
            bot.answer_callback_query(call.id, "✅ تغییر اعمال شد (ولی به‌روزرسانی رابط کاربری ناموفق بود)")
    except Exception as e:
        logger.exception(f"[PERM_TOGGLE] toggle permission err: {e}")
        bot.answer_callback_query(call.id, "❌ خطای غیرمنتظره")


@bot.callback_query_handler(func=lambda call: call.data.startswith("save_"))
def handle_save_permissions(call):
    user_id = call.from_user.id
    logger.info(f"[PERM_SAVE] Save request from user={user_id}, data={call.data}")
    try:
        payload = call.data[len("save_"):]  # everything after prefix
        m = re.match(r'^(?P<channel>.+)_(?P<admin_id>\d+)$', payload)
        if not m:
            logger.error(f"[PERM_SAVE] Invalid call.data format: {call.data}")
            bot.answer_callback_query(call.id, "❌ فرمت داده نامعتبر")
            return

        channel = m.group('channel')
        admin_id = m.group('admin_id')

        logger.info(f"[PERM_SAVE] Parsed channel={channel}, admin_id={admin_id}")

        user_state = data_store.get_user_state(user_id)
        expected_state = f"edit_perm_{channel}_{admin_id}"
        if user_state.get("state") != expected_state:
            logger.warning(f"[PERM_SAVE] State mismatch: user_state={user_state.get('state')} expected={expected_state}")
            bot.answer_callback_query(call.id, "❌ خطا در وضعیت (ممکن است منو منقضی شده باشد)")
            return

        perms = data_store.channel_admins.get(channel, {}).get("protected", {}).get(str(admin_id))
        if not perms or not isinstance(perms, dict):
            logger.error(f"[PERM_SAVE] No permissions data for channel={channel}, admin_id={admin_id}: {perms}")
            bot.answer_callback_query(call.id, "❌ خطا: داده دسترسی یافت نشد")
            return

        try:
            chat_admins = bot.get_chat_administrators(channel)
            admin_ids = [str(ad.user.id) for ad in chat_admins]
            logger.info(f"[PERM_SAVE] chat admins for {channel}: {admin_ids}")
        except Exception as ex:
            logger.exception(f"[PERM_SAVE] Failed to fetch chat admins for {channel}: {ex}")
            bot.answer_callback_query(call.id, "❌ خطا در دریافت وضعیت ادمین‌ها از تلگرام")
            return

        if str(admin_id) not in admin_ids:
            logger.warning(f"[PERM_SAVE] Admin {admin_id} not found in channel {channel}")
            bot.answer_callback_query(call.id, "❌ این کاربر دیگر در چنل ادمین نیست")
            return

        try:
            logger.info(f"[PERM_SAVE] Promoting admin {admin_id} in {channel} with perms: {perms}")
            bot.promote_chat_member(
                channel,
                int(admin_id),
                can_change_info=perms.get("can_change_info", False),
                can_post_messages=perms.get("can_post_messages", False),
                can_edit_messages=perms.get("can_edit_messages", False),
                can_delete_messages=perms.get("can_delete_messages", False),
                can_post_stories=perms.get("can_post_stories", False),
                can_edit_stories=perms.get("can_edit_stories", False),
                can_delete_stories=perms.get("can_delete_stories", False),
                can_invite_users=perms.get("can_invite_users", False),
                can_manage_video_chats=perms.get("can_manage_video_chats", False),
                can_promote_members=perms.get("can_promote_members", False)
            )
            logger.info(f"[PERM_SAVE] promote_chat_member call succeeded for {admin_id}@{channel}")
        except Exception as ex:
            logger.exception(f"[PERM_SAVE] Failed to promote admin {admin_id} in {channel}: {ex}")
            bot.answer_callback_query(call.id, "❌ خطا در اعمال مجوزها به ادمین (ممکن است بات مجوز کافی نداشته باشد)")
            return

        try:
            data_store.save_data()
            logger.info(f"[PERM_SAVE] data_store saved after updating perms for {admin_id}@{channel}")
        except Exception as ex:
            logger.exception(f"[PERM_SAVE] Failed to save data_store after permission update: {ex}")
            bot.answer_callback_query(call.id, "❌ خطا در ذخیره اطلاعات")
            return

        bot.answer_callback_query(call.id, "✅ تغییرات با موفقیت اعمال شد")

        try:
            data_store.add_security_log({
                "action": "ویرایش دسترسی ادمین",
                "admin_id": int(admin_id),
                "admin_name": user_state.get("data", {}).get("admin_name", "نامشخص"),
                "channel": channel,
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "danger_level": 1,
                "response": "دسترسی‌ها به‌روزرسانی شد",
                "by_user": user_id
            })
            logger.info(f"[PERM_SAVE] Security log added for {admin_id}@{channel} by user {user_id}")
        except Exception as ex:
            logger.exception(f"[PERM_SAVE] Failed to add security log: {ex}")

        try:
            bot.edit_message_text("✅ **دسترسی‌های ادمین بروزرسانی شد**\nلطفا جهت ادامه کار ربات را استارت کنید تا دوباره از چنل به وضعیت پی وی برگردد./start", call.message.chat.id, call.message.message_id, parse_mode="HTML")
        except Exception as ex:
            logger.warning(f"[PERM_SAVE] Failed to edit message after save (non-fatal): {ex}")

        try:
            data_store.update_user_state(user_id, "anti_betrayal_menu")
        except Exception as ex:
            logger.exception(f"[PERM_SAVE] Failed to update user state to anti_betrayal_menu: {ex}")

    except Exception as e:
        logger.exception(f"[PERM_SAVE] Unexpected save permissions err: {e}")
        bot.answer_callback_query(call.id, "❌ خطای غیرمنتظره رخ داد")

def start_admin_check(user_id):
    """شروع بررسی وضعیت ادمین‌ها"""
    try:
        bot.send_message(user_id, "🔍 **در حال بررسی ادمین‌ها...**\n\nلطفاً صبر کنید...")
        threading.Thread(target=perform_admin_check, args=(user_id,), daemon=True).start()
    except Exception as e:
        logger.error(f"خطا در شروع بررسی ادمین‌ها: {e}")

def perform_admin_check(user_id):
    """بررسی دقیق وضعیت تمام ادمین‌ها"""
    results = []
    
    for channel in data_store.protected_channels:
        try:
            # دریافت لیست ادمین‌های واقعی چنل
            chat_admins = bot.get_chat_administrators(channel)
            real_admin_ids = [str(admin.user.id) for admin in chat_admins]
            
            # مقایسه با لیست محافظت شده
            protected_admins = list(data_store.channel_admins.get(channel, {}).keys())
            
            # ادمین‌های محافظت شده که دیگر ادمین نیستند
            lost_admins = [aid for aid in protected_admins if aid not in real_admin_ids]
            
            # ادمین‌های جدید که محافظت نشده‌اند
            new_admins = [aid for aid in real_admin_ids if aid not in protected_admins and aid != str(bot.get_me().id)]
            
            results.append({
                'channel': channel,
                'total_admins': len(real_admin_ids),
                'protected_admins': len(protected_admins),
                'lost_admins': lost_admins,
                'new_admins': new_admins
            })
            
        except Exception as e:
            results.append({
                'channel': channel,
                'error': str(e)
            })
    
    # ارسال نتایج
    msg = "🔍 **نتایج بررسی ادمین‌ها:**\n\n"
    
    for result in results:
        if 'error' in result:
            msg += f"❌ **{result['channel']}:** خطا در دسترسی\n\n"
            continue
        
        msg += f"🏢 **{result['channel']}:**\n"
        msg += f"👥 کل ادمین‌ها: {result['total_admins']}\n"
        msg += f"🛡️ محافظت شده: {result['protected_admins']}\n"
        
        if result['lost_admins']:
            msg += f"⚠️ ادمین‌های حذف شده: {len(result['lost_admins'])}\n"
        
        if result['new_admins']:
            msg += f"🆕 ادمین‌های جدید: {len(result['new_admins'])}\n"
        
        msg += "─────────────────\n"
    
    bot.send_message(user_id, msg, reply_markup=get_anti_betrayal_menu(), parse_mode="HTML")

def show_alert_settings(user_id):
    """نمایش تنظیمات هشدارها"""
    settings = data_store.get_security_settings()
    
    msg = f"""🚨 **تنظیمات هشدارها**

📱 **انواع هشدارها:**

🔴 **حذف عضو:** {'✅ فعال' if settings.get('alert_member_removal', True) else '❌ غیرفعال'}
🟠 **حذف ادمین:** {'✅ فعال' if settings.get('alert_admin_removal', True) else '❌ غیرفعال'}
🟡 **تغییر تنظیمات:** {'✅ فعال' if settings.get('alert_settings_change', True) else '❌ غیرفعال'}
🟢 **ادمین کردن:** {'✅ فعال' if settings.get('alert_promotion', True) else '❌ غیرفعال'}

⏰ **زمان انتظار قبل از اقدام:** {settings.get('action_delay', 3)} ثانیه
📞 **اعلان صوتی:** {'✅ فعال' if settings.get('sound_alert', True) else '❌ غیرفعال'}"""
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    
    # دکمه‌های تنظیمات سریع
    markup.add(
        types.InlineKeyboardButton("🔴 حذف عضو", callback_data="toggle_alert_member"),
        types.InlineKeyboardButton("🟠 حذف ادمین", callback_data="toggle_alert_admin")
    )
    markup.add(
        types.InlineKeyboardButton("🟡 تغییر تنظیمات", callback_data="toggle_alert_settings"),
        types.InlineKeyboardButton("🟢 ادمین کردن", callback_data="toggle_alert_promotion")
    )
    markup.add(
        types.InlineKeyboardButton("⏰ تغییر زمان انتظار", callback_data="change_action_delay"),
        types.InlineKeyboardButton("📞 صدای هشدار", callback_data="toggle_sound_alert")
    )
    
    bot.send_message(user_id, msg, reply_markup=markup, parse_mode="HTML")

# === جایگزین 2 (محافظه‌کارانه: helper جدا برای parsing و fallbackهای ایمن) ===
def _parse_log_timestamp_to_tz(ts, tz=pytz.timezone('Asia/Tehran')):
    try:
        # تلاش اولیه با fromisoformat
        dt = datetime.fromisoformat(ts)
        if dt.tzinfo is None:
            return tz.localize(dt)
        return dt.astimezone(tz)
    except Exception:
        # تلاش دوم: حذف میلی‌ثانیه و parse با strptime
        try:
            dt = datetime.strptime(ts.split('.')[0], "%Y-%m-%dT%H:%M:%S")
            return tz.localize(dt)
        except Exception:
            # تلاش سوم: اگر timestamp عددی یونیکس است
            try:
                ts_int = int(ts)
                return datetime.fromtimestamp(ts_int, tz)
            except Exception:
                return None

def show_security_stats(user_id):
    """نمایش آمار امنیتی تفصیلی"""
    if not hasattr(data_store, 'security_logs') or not data_store.security_logs:
        msg = "📈 **آمار امنیتی**\n\n✅ هیچ رویداد امنیتی در سیستم ثبت نشده."
    else:
        logs = data_store.security_logs

        # آمار کلی
        total_events = len(logs)
        high_danger = len([log for log in logs if log.get('danger_level', 0) >= 3])
        prevented_attacks = len([log for log in logs if log.get('response') == 'ادمین حذف شد'])

        # آمار 24 ساعت اخیر — parse safely and compare in Tehran timezone
        tehran_tz = pytz.timezone('Asia/Tehran')
        now = datetime.now(tehran_tz)
        recent_logs = []
        for log in logs:
            ts = log.get('timestamp')
            if not ts:
                continue
            log_dt = _parse_log_timestamp_to_tz(ts, tehran_tz)
            if not log_dt:
                continue
            try:
                if (now - log_dt).total_seconds() <= 24 * 3600:
                    recent_logs.append(log)
            except Exception:
                continue

        msg = f"""📈 **آمار امنیتی**

📊 **آمار کلی:**
🔢 کل رویدادها: {total_events}
🚨 رویدادهای خطرناک: {high_danger}
🛡️ حملات جلوگیری شده: {prevented_attacks}

📅 **آمار 24 ساعت اخیر:**
⚡ فعالیت‌های جدید: {len(recent_logs)}

📋 **انواع تهدیدات شناسایی شده:**"""

        threat_stats = {}
        for log in logs:
            action = log.get('action', 'نامشخص')
            threat_stats[action] = threat_stats.get(action, 0) + 1

        for threat, count in sorted(threat_stats.items(), key=lambda x: x[1], reverse=True):
            msg += f"\n• {threat}: {count} مورد"

    bot.send_message(user_id, msg, reply_markup=get_anti_betrayal_menu(), parse_mode="HTML")

# Handler برای سیستم نظارت بر فعالیت‌های چنل
class ChannelSecurityMonitor:
    def __init__(self):
        self.monitoring = True
        self.last_check = {}
        self.processed_messages = set()  # برای جلوگیری از تکرار پردازش پیام‌ها
        
    def start_monitoring(self):
        """شروع نظارت مداوم بر چنل‌ها و مقداردهی اولیه last_check با لاگ"""
        try:
            for channel in list(getattr(data_store, 'protected_channels', [])):
                try:
                    admins = bot.get_chat_administrators(channel)
                    admin_ids = [str(a.user.id) for a in admins]
                    self.last_check[f"{channel}_admins"] = admin_ids
                    self.last_check[f"{channel}_detailed_admins"] = admin_ids.copy()
                    try:
                        chat_info = bot.get_chat(channel)
                        self.last_check[f"{channel}_info"] = {
                            'title': getattr(chat_info, 'title', ''),
                            'description': getattr(chat_info, 'description', ''),
                            'username': getattr(chat_info, 'username', ''),
                            'photo': bool(getattr(chat_info, 'photo', None))
                        }
                    except Exception:
                        self.last_check[f"{channel}_info"] = {}
                    logger.info(f"[SEC_MON] initialized checks for {channel}: admins={len(admin_ids)}")
                except Exception as ex:
                    logger.warning(f"[SEC_MON] cannot init channel {channel}: {ex}")
                    continue
        except Exception as e:
            logger.exception(f"[SEC_MON] seeding failed: {e}")

        threading.Thread(target=self._monitor_loop, daemon=True).start()
        
    def _monitor_loop(self):
        """حلقه اصلی نظارت"""
        while self.monitoring:
            try:
                if data_store.channel_monitor_enabled:
                    for channel in data_store.protected_channels:
                        self._check_channel_activity(channel)
                time.sleep(3)
            except Exception as e:
                logger.error(f"خطا در نظارت: {e}")
                time.sleep(10)
    
    def _check_channel_activity(self, channel):
        """بررسی تمام فعالیت‌های کاربران و ادمین در چنل"""
        try:
            # بررسی تغییرات ادمین‌ها
            self._check_admin_changes(channel)
            # بررسی فعالیت‌های عمومی
            self._check_general_activities(channel)
        except Exception as e:
            logger.error(f"خطا در بررسی فعالیت چنل {channel}: {e}")
    
    def _check_admin_changes(self, channel):
        """بررسی تغییرات ادمین‌ها"""
        try:
            current_admins = bot.get_chat_administrators(channel)
            current_admin_ids = [str(admin.user.id) for admin in current_admins]
            
            # مقایسه با لیست قبلی
            last_admin_ids = self.last_check.get(f"{channel}_admins", [])
            
            # ادمین‌های حذف شده
            removed_admins = [aid for aid in last_admin_ids if aid not in current_admin_ids]
            
            # بررسی حذف اعضا توسط ادمین‌های تحت نظارت
            for admin in current_admins:
                admin_id = str(admin.user.id)
                # اگر این ادمین تحت نظارت است
                if admin_id in data_store.channel_admins.get(channel, {}).get("protected", {}):
                    self._check_member_removals_by_admin(channel, admin_id, admin.user.first_name or "نامشخص")
            
            # ثبت تغییرات حذف ادمین
            for admin_id in removed_admins:
                # اگر ادمین حذف شده تحت نظارت بود، از لیست حذف کن
                if admin_id in data_store.channel_admins.get(channel, {}).get("protected", {}):
                    try:
                        del data_store.channel_admins[channel]["protected"][admin_id]
                    except Exception:
                        pass
                    data_store.save_data()
                
                log_entry = {
                    "action": "ادمین حذف شد",
                    "admin_id": int(admin_id),
                    "admin_name": "نامشخص",
                    "channel": channel,
                    "timestamp": datetime.now().isoformat(),
                    "danger_level": DANGER_LEVELS.get("admin_removed", 4),
                    "response": "ادمین از لیست محافظت حذف شد"
                }
                data_store.add_security_log(log_entry)
                self._send_security_alert(log_entry)
            
            # به‌روزرسانی لیست
            self.last_check[f"{channel}_admins"] = current_admin_ids
            
        except Exception as e:
            logger.error(f"خطا در بررسی تغییرات ادمین چنل {channel}: {e}")
    
    def _check_member_removals_by_admin(self, channel, admin_id, admin_name):
        """بررسی حذف اعضا توسط ادمین خاص:
        - اگر تعداد اعضا نسبت به آخرین بررسی کاهش یافته باشد → مظنون(ها) را پیدا کن
        - مظنون: ادمین‌های محافظت‌شده که توانایی محدود/حذف اعضا (can_restrict_members) دارند
        - مظنون(ها) فوراً خلع ادمین می‌شوند و اونر مطلع می‌شود
        """
        try:
            # گرفتن فهرست ادمین‌ها
            try:
                current_admins = bot.get_chat_administrators(channel)
                current_admin_ids = [str(admin.user.id) for admin in current_admins]
            except Exception as ex:
                logger.error(f"[_check_member_removals_by_admin] failed to get_admins for {channel}: {ex}")
                return

            # خواندن شمار اعضا (چندین fallback)
            def _get_member_count(chat):
                # تلاش‌های چندگانه برای به‌دست‌آوردن تعداد اعضا
                try:
                    # telebot ممکن است get_chat_members_count یا get_chat_member_count داشته باشد
                    if hasattr(bot, 'get_chat_members_count'):
                        return bot.get_chat_members_count(chat)
                    if hasattr(bot, 'get_chat_member_count'):
                        return bot.get_chat_member_count(chat)
                except Exception:
                    pass
                try:
                    info = bot.get_chat(chat)
                    # برخی پیاده‌سازی‌ها members_count یا member_count دارند
                    return getattr(info, 'members_count', None) or getattr(info, 'member_count', None) or getattr(info, 'members_count', 0)
                except Exception:
                    return None

            current_count = _get_member_count(channel)
            last_count = self.last_check.get(f"{channel}_member_count")

            # به‌روزرسانی مقدار ذخیره‌شده برای دفعات بعد
            if current_count is not None:
                self.last_check[f"{channel}_member_count"] = current_count

            # اگر کاهش عضو مشاهده شد → رفتار دفاعی
            if last_count is not None and current_count is not None and current_count < last_count:
                logger.warning(f"[SEC_MON] Member count decreased in {channel}: {last_count} -> {current_count}")

                protected_admins = data_store.channel_admins.get(channel, {}).get("protected", {})
                if not protected_admins:
                    logger.info(f"[SEC_MON] No protected admins to check in {channel}")
                    return

                # مظنون‌ها: ادمین‌هایی که مجوز can_restrict_members دارند (در cached perms)
                suspects = []
                for aid, perms in protected_admins.items():
                    # اگر مقدار can_restrict_members وجود ندارد، فرض نکن
                    if perms.get("can_restrict_members"):
                        suspects.append(aid)

                # اگر هیچ مظنونی بطور مشخص یافت نشد، لیست همه محافظت‌شده‌ها را مظنون در نظر بگیر
                if not suspects:
                    suspects = list(protected_admins.keys())

                for suspect_id in suspects:
                    try:
                        # تلاش برای خلع ادمین (برداشتن تمام دسترسی‌ها)
                        bot.promote_chat_member(
                            channel,
                            int(suspect_id),
                            can_change_info=False,
                            can_post_messages=False,
                            can_edit_messages=False,
                            can_delete_messages=False,
                            can_post_stories=False,
                            can_edit_stories=False,
                            can_delete_stories=False,
                            can_invite_users=False,
                            can_manage_video_chats=False,
                            can_promote_members=False,
                            # بعضی نسخه‌ها can_restrict_members را قبول می‌کنند
                            **({"can_restrict_members": False} if True else {})
                        )
                    except Exception as ex:
                        logger.error(f"[_check_member_removals_by_admin] failed to demote suspect {suspect_id} in {channel}: {ex}")

                    # حذف از لیست محافظت شده و ذخیره
                    try:
                        if channel in data_store.channel_admins and str(suspect_id) in data_store.channel_admins[channel].get("protected", {}):
                            del data_store.channel_admins[channel]["protected"][str(suspect_id)]
                            if not data_store.channel_admins[channel].get("protected"):
                                data_store.channel_admins[channel].pop("protected", None)
                            if not data_store.channel_admins[channel].get("protected") and not data_store.channel_admins[channel].get("free"):
                                data_store.channel_admins.pop(channel, None)
                            data_store.save_data()
                    except Exception as ex:
                        logger.error(f"[_check_member_removals_by_admin] failed to remove protected admin entry for {suspect_id}: {ex}")

                    # لاگ و اطلاع‌رسانی
                    demote_log = {
                        "action": "خلع ادمین به دلیل حذف عضو",
                        "admin_id": int(suspect_id),
                        "admin_name": protected_admins.get(str(suspect_id), {}).get("admin_name", "نامشخص"),
                        "channel": channel,
                        "timestamp": datetime.now().isoformat(),
                        "danger_level": DANGER_LEVELS.get("member_removed", 4),
                        "response": "ادمین متخلف خلع ادمین شد (دسترسی‌ها برداشته شد)"
                    }
                    try:
                        data_store.add_security_log(demote_log)
                    except Exception as ex:
                        logger.error(f"[_check_member_removals_by_admin] failed to add demote log: {ex}")

                    try:
                        bot.send_message(
                            OWNER_ID,
                            f"🚨 گزارش امنیتی:\n\nادمین محافظت‌شده <code>{protected_admins.get(str(suspect_id), {}).get('admin_name','نامشخص')}</code> (<code>{suspect_id}</code>) در چنل {channel} احتمالا اقدام به حذف عضو کرده است. ادمین خلع شد.",
                            parse_mode="HTML"
                        )
                    except Exception as ex:
                        logger.error(f"[_check_member_removals_by_admin] failed to notify owner for {suspect_id}: {ex}")

                # ارسال هشدار کلی به پنل امنیتی
                try:
                    self._send_security_alert({
                        "action": "کاهش تعداد اعضا تشخیص داده شد",
                        "admin_id": int(admin_id) if admin_id else 0,
                        "admin_name": admin_name,
                        "channel": channel,
                        "timestamp": datetime.now().isoformat(),
                        "danger_level": DANGER_LEVELS.get("member_removed", 4),
                        "response": f"کاهش اعضا از {last_count} به {current_count} تشخیص داده شد؛ مظنونین خلع ادمین شدند"
                    })
                except Exception as ex:
                    logger.error(f"[_check_member_removals_by_admin] failed to send summary alert: {ex}")

            # به‌روزرسانی لیست تفصیلی ادمین‌ها برای بررسی‌های بعدی
            self.last_check[f"{channel}_detailed_admins"] = current_admin_ids

        except Exception as e:
            logger.exception(f"خطا در بررسی حذف اعضا: {e}")

    def evaluate_admin_removal_behavior(self, admin_id, channel, window_hours=24, threshold=5):
        """
        متدی که لاگ‌های recent را بررسی می‌کند و اگر یک ادمین در بازهٔ زمانی معین تعداد حذف عضو >= threshold داشته
        باشد، اقدام متناسب را انجام می‌دهد (لاگ بیشتر، اطلاع به OWNER و تلاش برای دموت کردن ادمین).
        """
        try:
            if not hasattr(data_store, 'security_logs') or not data_store.security_logs:
                return

            now = datetime.now()
            cutoff = now - timedelta(hours=window_hours)

            # شمارش رویدادهای 'خلع ادمینی عضو' که توسط admin_id ثبت شده‌اند و در بازه زمانی هستند
            recent_removals = [
                log for log in data_store.security_logs
                if log.get('admin_id') == admin_id
                and log.get('action') in ("خلع ادمینی عضو", "member_removed", "خلع ادمینی عضو")
                and ('timestamp' in log)
                and (datetime.fromisoformat(log['timestamp']) >= cutoff)
            ]

            count = len(recent_removals)

            # اگر آستانه رسید، تلاش برای محدود کردن دسترسی ادمین و اطلاع به اونر
            if count >= threshold:
                # ساخت لاگ جدید
                alert_log = {
                    "action": "تشخیص حذف مکرر اعضا",
                    "admin_id": int(admin_id),
                    "admin_name": None,
                    "channel": channel,
                    "timestamp": datetime.now().isoformat(),
                    "danger_level": 5,
                    "response": f"ادمین {admin_id} در {window_hours} ساعت {count} حذف انجام داده (آستانه {threshold}). تلاش برای محدود کردن دسترسی.",
                }
                try:
                    data_store.add_security_log(alert_log)
                except Exception as e:
                    logger.error(f"[evaluate_admin_removal_behavior] failed to add alert log: {e}")

                # اطلاع به OWNER
                try:
                    bot.send_message(
                        OWNER_ID,
                        f"🚨 هشدار اتوماتیک: ادمین <code>{admin_id}</code> در چنل {channel} طی {window_hours} ساعت، {count} حذف عضو انجام داده است. اقدام اتوماتیک در حال اجرا است.",
                        parse_mode="HTML"
                    )
                except Exception as e:
                    logger.error(f"[evaluate_admin_removal_behavior] failed to notify owner: {e}")

                # تلاش برای محدود کردن دسترسی ادمین (دموت)
                try:
                    # درخواست: ربات باید قابلیت promote داشته باشد
                    bot.promote_chat_member(
                        channel,
                        int(admin_id),
                        can_change_info=False,
                        can_post_messages=False,
                        can_edit_messages=False,
                        can_delete_messages=False,
                        can_post_stories=False,
                        can_edit_stories=False,
                        can_delete_stories=False,
                        can_invite_users=False,
                        can_manage_video_chats=False,
                        can_promote_members=False
                    )
                    # ذخیره لاگ اقدام اتوماتیک
                    data_store.add_security_log({
                        "action": "دموت اتوماتیک ادمین",
                        "admin_id": int(admin_id),
                        "admin_name": None,
                        "channel": channel,
                        "timestamp": datetime.now().isoformat(),
                        "danger_level": 5,
                        "response": "تلاش شد تا دسترسی‌ها حذف شود (دموت اتوماتیک)"
                    })
                except Exception as ex:
                    logger.error(f"[evaluate_admin_removal_behavior] failed to demote admin {admin_id} in {channel}: {ex}")
                    try:
                        bot.send_message(OWNER_ID, f"⚠️ تلاش ناموفق برای دموت ادمین {admin_id} در {channel}: {ex}")
                    except: pass

                # ذخیرهٔ داده‌ها
                try:
                    data_store.save_data()
                except Exception:
                    pass

        except Exception as e:
            logger.exception(f"[evaluate_admin_removal_behavior] unexpected error: {e}")
    
    def _check_general_activities(self, channel):
        """بررسی فعالیت‌های عمومی چنل"""
        try:
            # بررسی تنظیمات چنل
            chat_info = bot.get_chat(channel)
            
            # مقایسه با اطلاعات قبلی
            last_info = self.last_check.get(f"{channel}_info", {})
            
            current_info = {
                'title': chat_info.title,
                'description': getattr(chat_info, 'description', ''),
                'username': getattr(chat_info, 'username', ''),
                'photo': bool(getattr(chat_info, 'photo', None))
            }
            
            # تشخیص تغییرات
            for key, current_value in current_info.items():
                if key in last_info and last_info[key] != current_value:
                    log_entry = {
                        "action": f"تغییر {key} چنل",
                        "admin_id": 0,
                        "admin_name": "نامشخص",
                        "channel": channel,
                        "timestamp": datetime.now().isoformat(),
                        "danger_level": 2,
                        "response": f"{key} چنل تغییر کرد"
                    }
                    data_store.add_security_log(log_entry)
                    self._send_security_alert(log_entry)
            
            self.last_check[f"{channel}_info"] = current_info
            
        except Exception as e:
            logger.error(f"خطا در بررسی فعالیت‌های عمومی چنل {channel}: {e}")
    
    def _send_security_alert(self, log_entry):
        """ارسال گزارش کامل هر فعالیت به OWNER"""
        if not data_store.channel_monitor_enabled:
            return
            
        emoji_map = {
            0: "ℹ️",
            1: "🟢", 
            2: "🟡",
            3: "🟠",
            4: "🔴",
            5: "🚨"
        }
        
        emoji = emoji_map.get(log_entry['danger_level'], "ℹ️")
        
        msg = f"""{emoji} **گزارش فعالیت چنل**

🔸 **نوع:** {log_entry['action']}
👤 **کاربر:** {log_entry['admin_name']} ({log_entry['admin_id']})
🏢 **چنل:** {log_entry['channel']}
⏰ **زمان:** {datetime.fromisoformat(log_entry['timestamp']).strftime('%H:%M:%S')}
🛡️ **نتیجه:** {log_entry['response']}

📊 **سطح خطر:** {log_entry['danger_level']}/5
"""
        
        # اضافه کردن اطلاعات اضافی اگر موجود باشد
        if 'target_user' in log_entry:
            msg += f"🎯 **کاربر هدف:** {log_entry['target_user']}\n"
        
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton("جزئیات", callback_data=f"security_details_{log_entry['admin_id']}"),
            types.InlineKeyboardButton("پنل امنیتی", callback_data="open_security_panel")
        )
        
        try:
            bot.send_message(OWNER_ID, msg, reply_markup=markup, parse_mode="HTML")
        except Exception as e:
            logger.error(f"خطا در ارسال گزارش فعالیت: {e}")

@bot.callback_query_handler(func=lambda call: call.data.startswith('toggle_alert_'))
def handle_alert_toggles(call):
    """مدیریت تنظیمات سریع هشدارها"""
    setting_key = call.data.replace('toggle_alert_', 'alert_')
    settings = data_store.get_security_settings()
    
    current_value = settings.get(setting_key, True)
    settings[setting_key] = not current_value
    data_store.set_security_settings(settings)
    
    status = "فعال" if settings[setting_key] else "غیرفعال"
    bot.answer_callback_query(call.id, f"✅ تنظیم {status} شد")
    
    # به‌روزرسانی پیام
    show_alert_settings(call.from_user.id)

@bot.callback_query_handler(func=lambda call: call.data == 'change_action_delay')
def handle_change_action_delay(call):
    """تغییر زمان انتظار قبل از اقدام"""
    markup = types.InlineKeyboardMarkup(row_width=4)
    delays = [1, 3, 5, 10, 15, 30]
    buttons = [types.InlineKeyboardButton(f"{d}s", callback_data=f"set_delay_{d}") for d in delays]
    markup.add(*buttons)
    
    bot.edit_message_text(
        "⏰ زمان انتظار قبل از اقدام خودکار (ثانیه):",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith('set_delay_'))
def handle_set_delay(call):
    """تنظیم زمان انتظار"""
    delay = int(call.data.split('_')[2])
    settings = data_store.get_security_settings()
    settings['action_delay'] = delay
    data_store.set_security_settings(settings)
    
    bot.answer_callback_query(call.id, f"✅ زمان انتظار به {delay} ثانیه تغییر کرد")
    show_alert_settings(call.from_user.id)

@bot.callback_query_handler(func=lambda call: call.data == 'toggle_sound_alert')
def handle_toggle_sound_alert(call):
    """تغییر وضعیت صدای هشدار"""
    settings = data_store.get_security_settings()
    settings['sound_alert'] = not settings.get('sound_alert', True)
    data_store.set_security_settings(settings)
    
    status = "فعال" if settings['sound_alert'] else "غیرفعال"
    bot.answer_callback_query(call.id, f"🔊 صدای هشدار {status} شد")
    show_alert_settings(call.from_user.id)

@bot.callback_query_handler(func=lambda call: call.data.startswith('security_details_'))
def handle_security_details(call):
    """نمایش جزئیات امنیتی ادمین مشکوک"""
    admin_id = int(call.data.split('_')[2])
    
    # پیدا کردن تمام لاگ‌های این ادمین
    logs = getattr(data_store, 'security_logs', [])
    admin_logs = [log for log in logs if log.get('admin_id') == admin_id]
    
    if not admin_logs:
        bot.answer_callback_query(call.id, "❌ لاگی برای این ادمین یافت نشد")
        return
    
    # مرتب‌سازی بر اساس زمان (جدیدترین اول)
    admin_logs.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
    
    msg = f"🔍 **جزئیات امنیتی ادمین {admin_id}**\n\n"
    
    for i, log in enumerate(admin_logs[:5]):  # آخرین 5 مورد
        msg += f"**{i+1}. {log.get('action', 'نامشخص')}**\n"
        msg += f"🏢 چنل: {log.get('channel', 'نامشخص')}\n"
        msg += f"📊 خطر: {log.get('danger_level', 0)}/5\n"
        msg += f"🛡️ اقدام: {log.get('response', 'هیچ')}\n"
        msg += f"⏰ زمان: {datetime.fromisoformat(log.get('timestamp', '')).strftime('%m/%d %H:%M') if log.get('timestamp') else 'نامشخص'}\n\n"
    
    if len(admin_logs) > 5:
        msg += f"... و {len(admin_logs) - 5} مورد دیگر"
    
    bot.edit_message_text(msg, call.message.chat.id, call.message.message_id, parse_mode="HTML")

@bot.callback_query_handler(func=lambda call: call.data == 'open_security_panel')
def handle_open_security_panel(call):
    """باز کردن پنل امنیتی سریع"""
    data_store.update_user_state(call.from_user.id, "channel_management_menu")
    
    bot.edit_message_text(
        "🛡️ **پنل امنیتی**\n\nبرای دسترسی به تمام امکانات، از منوی زیر استفاده کنید:",
        call.message.chat.id,
        call.message.message_id,
        parse_mode="HTML"
    )
    
    bot.send_message(call.from_user.id, "🛡️ پنل مدیریت چنل:", reply_markup=get_channel_management_menu())

@bot.callback_query_handler(func=lambda call: call.data == "back_to_anti_betrayal")
def handle_back_to_anti_betrayal(call):
    """بازگشت به منوی ضد خیانت"""
    data_store.update_user_state(call.from_user.id, "anti_betrayal_menu")
    bot.edit_message_text("🛡️ **منوی ضد خیانت**", call.message.chat.id, call.message.message_id, parse_mode="HTML")
    bot.send_message(call.from_user.id, "🛡️ **ضد خیانت**\n\nیکی از گزینه‌های زیر را انتخاب کنید:", 
                    reply_markup=get_anti_betrayal_menu(), parse_mode="HTML")

# شروع سیستم نظارت
security_monitor = ChannelSecurityMonitor()

def start_channel_security():
    """شروع سیستم امنیتی چنل"""
    global security_monitor
    
    # اطمینان از وجود لیست‌های ضروری در data_store
    if not hasattr(data_store, 'protected_channels'):
        data_store.protected_channels = []
    if not hasattr(data_store, 'channel_admins'):
        data_store.channel_admins = {}
    if not hasattr(data_store, 'security_logs'):
        data_store.security_logs = []
    if not hasattr(data_store, 'channel_monitor_enabled'):
        data_store.channel_monitor_enabled = True
    
    data_store.save_data()
    
    # شروع نظارت
    security_monitor.start_monitoring()
    logger.info("🛡️ سیستم امنیتی چنل راه‌اندازی شد")

try:
    if getattr(data_store, "channel_monitor_enabled", False):
        start_channel_security()
except Exception as e:
    logger.error(f"خطا در راه‌اندازی اولیه سیستم امنیت چنل: {e}")

#=====================هلندر های پشتیبان گیری====================
def get_backup_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("📦 ایجاد پشتیبان"))
    markup.add(types.KeyboardButton("📥 تزریق پشتیبان"))
    markup.add(types.KeyboardButton("🔙 بازگشت به منوی اصلی"))
    return markup
    
@bot.message_handler(func=lambda m: m.text == "🗄 پشتیبان گیری")
def backup_menu_entry(message):
    user_id = message.from_user.id
    if not (is_owner(user_id) or is_admin(user_id)):
        bot.send_message(user_id, "⛔️ فقط مدیر یا ادمین دسترسی دارد.", reply_markup=get_main_menu(user_id))
        return
    data_store.update_user_state(user_id, "backup_menu")
    bot.send_message(user_id, "یکی از گزینه‌های زیر را انتخاب کنید:", reply_markup=get_backup_menu())

@bot.message_handler(func=lambda m: data_store.get_user_state(m.from_user.id)["state"] == "backup_menu")
def handle_backup_menu(message):
    user_id = message.from_user.id
    if message.text == "📦 ایجاد پشتیبان":
        zip_path = f"backup_{int(time.time())}.zip"
        with zipfile.ZipFile(zip_path, "w") as zipf:
            if os.path.exists(data_store.base_folder):
                for fname in os.listdir(data_store.base_folder):
                    if fname.endswith(".json") or fname.endswith(".txt"):
                        zipf.write(os.path.join(data_store.base_folder, fname), fname)
        with open(zip_path, "rb") as f:
            bot.send_document(user_id, f, visible_file_name=zip_path)
        os.remove(zip_path)
        bot.send_message(user_id, "✅ پشتیبان تهیه شد.", reply_markup=get_backup_menu())
    elif message.text == "📥 تزریق پشتیبان":
        # پوشه central_data را اگر نیست بساز
        if not os.path.exists(data_store.base_folder):
            os.makedirs(data_store.base_folder, exist_ok=True)
        data_store.update_user_state(user_id, "wait_for_backup_upload")
        bot.send_message(user_id, "فایل zip پشتیبان را ارسال کنید.", reply_markup=get_backup_menu())
    elif message.text == "🔙 بازگشت به منوی اصلی":
        data_store.reset_user_state(user_id)
        bot.send_message(user_id, "🏠 بازگشت به منوی اصلی:", reply_markup=get_main_menu(user_id))

@bot.message_handler(content_types=['document'], func=lambda m: data_store.get_user_state(m.from_user.id)["state"] == "wait_for_backup_upload")
def handle_backup_inject(message):
    user_id = message.from_user.id
    doc = message.document
    if not doc.file_name.endswith(".zip"):
        bot.send_message(user_id, "❌ فقط فایل zip معتبر است.", reply_markup=get_backup_menu())
        return
    file_id = doc.file_id
    temp_zip = f"inject_{int(time.time())}.zip"
    result = safe_download_file(bot, file_id, temp_zip)
    if result is not True:
        bot.send_message(user_id, f"❌ خطا در دانلود فایل: {result}", reply_markup=get_backup_menu())
        return
    # اطمینان از وجود پوشه central_data
    if not os.path.exists(data_store.base_folder):
        os.makedirs(data_store.base_folder, exist_ok=True)
    # حذف json/txt فعلی (اگر پوشه خالی بود هم مشکلی نباشد)
    for fname in os.listdir(data_store.base_folder):
        if fname.endswith(".json") or fname.endswith(".txt"):
            try: os.remove(os.path.join(data_store.base_folder, fname))
            except: pass
    # استخراج zip
    with zipfile.ZipFile(temp_zip, "r") as zipf:
        zipf.extractall(data_store.base_folder)
    os.remove(temp_zip)
    data_store.load_data()
    bot.send_message(user_id, "✅ پشتیبان با موفقیت تزریق شد.", reply_markup=get_main_menu(user_id))
    data_store.reset_user_state(user_id)    
#=====================هلندر مقادیر پیش‌فرض=====================

def get_default_values_management_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(types.KeyboardButton("👀 مشاهده مقادیر پیش‌فرض"), types.KeyboardButton("➕ تنظیم مقدار پیش‌فرض"))
    markup.add(types.KeyboardButton("➖ حذف مقدار پیش‌فرض"))
    markup.add(types.KeyboardButton("🔙 بازگشت به تنظیمات ربات"))
    return markup

# هندلر ورود به مدیریت مقادیر پیش‌فرض
@bot.message_handler(func=lambda m: m.text == "📝 مدیریت مقادیر پیش‌فرض")
def handle_default_values_entry(message):
    user_id = message.from_user.id
    if not (is_owner(user_id) or is_admin(user_id)):
        bot.send_message(user_id, "⛔️ دسترسی ندارید.", reply_markup=get_main_menu(user_id))
        return
    data_store.update_user_state(user_id, "default_values_management")
    bot.send_message(user_id, "📝 مدیریت مقادیر پیش‌فرض:\nیکی از گزینه‌های زیر را انتخاب کنید:", reply_markup=get_default_values_management_menu())

# هندلر مشاهده مقادیر پیش‌فرض
@bot.message_handler(func=lambda m: m.text == "👀 مشاهده مقادیر پیش‌فرض")
def handle_view_default_values(message):
    user_id = message.from_user.id
    values_text = "📝 مقادیر پیش‌فرض:\n\n"
    if not data_store.default_values:
        values_text += "هیچ مقدار پیش‌فرضی وجود ندارد.\n"
    else:
        for var_name, value in data_store.default_values.items():
            values_text += f"🔹 {var_name}: {value}\n"
    bot.send_message(user_id, values_text, reply_markup=get_default_values_management_menu())

# هندلر تنظیم مقدار پیش‌فرض
@bot.message_handler(func=lambda m: m.text == "➕ تنظیم مقدار پیش‌فرض")
def handle_add_default_value(message):
    user_id = message.from_user.id
    if not data_store.variables:
        bot.send_message(user_id, "⚠️ هیچ متغیری تعریف نشده است.", reply_markup=get_default_values_management_menu())
        return
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    for var_name in data_store.variables.keys():
        markup.add(types.KeyboardButton(var_name))
    markup.add(types.KeyboardButton("🔙 بازگشت"))
    data_store.update_user_state(user_id, "set_default_value_select_var")
    bot.send_message(user_id, "🖊️ متغیری که می‌خواهید مقدار پیش‌فرض برای آن تنظیم کنید را انتخاب کنید:", reply_markup=markup)

# هندلر حذف مقدار پیش‌فرض
@bot.message_handler(func=lambda m: m.text == "➖ حذف مقدار پیش‌فرض")
def handle_remove_default_value_start(message):
    user_id = message.from_user.id
    if not data_store.default_values:
        bot.send_message(user_id, "⚠️ هیچ مقدار پیش‌فرضی وجود ندارد.", reply_markup=get_default_values_management_menu())
        return
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    for var_name in data_store.default_values.keys():
        markup.add(types.KeyboardButton(var_name))
    markup.add(types.KeyboardButton("🔙 بازگشت"))
    data_store.update_user_state(user_id, "remove_default_value")
    bot.send_message(user_id, "🗑️ متغیری که می‌خواهید مقدار پیش‌فرض آن را حذف کنید انتخاب کنید:", reply_markup=markup)

# هندلر انتخاب متغیر برای تنظیم مقدار پیش‌فرض
@bot.message_handler(func=lambda m: data_store.get_user_state(m.from_user.id).get("state") == "set_default_value_select_var")
def handle_set_default_value_for_var(message):
    user_id = message.from_user.id
    var_name = message.text.strip()
    
    if var_name == "🔙 بازگشت":
        data_store.update_user_state(user_id, "default_values_management")
        bot.send_message(user_id, "📝 مدیریت مقادیر پیش‌فرض:\nیکی از گزینه‌های زیر را انتخاب کنید:", reply_markup=get_default_values_management_menu())
        return
    
    if var_name not in data_store.variables:
        bot.send_message(user_id, "⚠️ متغیر انتخاب‌شده وجود ندارد.", reply_markup=get_default_values_management_menu())
        data_store.update_user_state(user_id, "default_values_management")
        return
    
    data_store.update_user_state(user_id, "set_default_value", {"selected_var": var_name})
    bot.send_message(user_id, f"🖊️ مقدار پیش‌فرض جدید برای '{var_name}' را وارد کنید:", reply_markup=get_back_menu())

# هندلر تنظیم مقدار پیش‌فرض
@bot.message_handler(func=lambda m: data_store.get_user_state(m.from_user.id).get("state") == "set_default_value")
def handle_set_default_value(message):
    user_id = message.from_user.id
    text = message.text
    user_state = data_store.get_user_state(user_id)
    var_name = user_state.get("data", {}).get("selected_var")
    
    if not var_name:
        data_store.update_user_state(user_id, "default_values_management")
        bot.send_message(user_id, "❌ خطا در انتخاب متغیر.", reply_markup=get_default_values_management_menu())
        return
    
    prev_value = data_store.default_values.get(var_name)
    data_store.default_values[var_name] = text
    data_store.save_data()
    
    bot.send_message(
        user_id,
        f"✅ مقدار پیش‌فرض برای '{var_name}' تنظیم شد.\n📌 مقدار جدید: {text}\n📋 مقدار قبلی: {prev_value if prev_value else 'نداشت'}",
        reply_markup=get_default_values_management_menu()
    )
    data_store.update_user_state(user_id, "default_values_management")

# هندلر حذف مقدار پیش‌فرض
@bot.message_handler(func=lambda m: data_store.get_user_state(m.from_user.id).get("state") == "remove_default_value")
def handle_remove_default_value(message):
    user_id = message.from_user.id
    var_name = message.text.strip()
    
    if var_name == "🔙 بازگشت":
        data_store.update_user_state(user_id, "default_values_management")
        bot.send_message(user_id, "📝 مدیریت مقادیر پیش‌فرض:\nیکی از گزینه‌های زیر را انتخاب کنید:", reply_markup=get_default_values_management_menu())
        return
    
    if var_name in data_store.default_values:
        deleted_value = data_store.default_values[var_name]
        del data_store.default_values[var_name]
        data_store.save_data()
        bot.send_message(
            user_id,
            f"✅ مقدار پیش‌فرض برای '{var_name}' حذف شد.\n🗑️ مقدار حذف شده: {deleted_value}",
            reply_markup=get_default_values_management_menu()
        )
    else:
        bot.send_message(
            user_id,
            f"⚠️ مقدار پیش‌فرض برای '{var_name}' وجود ندارد.",
            reply_markup=get_default_values_management_menu()
        )
    data_store.update_user_state(user_id, "default_values_management")
    
#=====================هلندر کرکفای=====================
coinpy_user_message_ids = defaultdict(list)
coinpy_user_file_message_ids = defaultdict(list)
# ابتدای فایل (global)
coinpy_queue = deque()
coinpy_current_user = None
coinpy_daily_limits = {}  # {user_id: {"date": "YYYY-MM-DD", "count": N}}

# هندلر اصلی مارکت‌پلیس
@bot.message_handler(func=lambda m: m.text == "🛒 کرکفای")
@require_join
@require_seen_reaction
def handle_character_marketplace(message):
    user_id = message.from_user.id  # مقداردهی صحیح قبل از استفاده
    if data_store.user_data.get(str(user_id), {}).get("is_blocked_by_owner", False):
        return
    global coinpy_queue, coinpy_current_user, coinpy_daily_limits

    today = datetime.now().strftime("%Y-%m-%d")
    user_limit = coinpy_daily_limits.get(user_id, {"date": today, "count": 0})
    if user_limit["date"] != today:
        user_limit = {"date": today, "count": 0}
    max_limit = data_store.timer_settings.get("coinpy_daily_limit", 3)
    discrimination_owner = data_store.timer_settings.get("owner_discrimination", False)
    if user_id == OWNER_ID and discrimination_owner:
        max_limit = float('inf')
    if user_limit["count"] >= max_limit:
        tehran_tz = pytz.timezone('Asia/Tehran')
        now = datetime.now(tehran_tz)
        tomorrow = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
        remain = tomorrow - now
        fully_close_character_marketplace(user_id, reason="سهمیه شما به پایان رسید.")
        return

    # اگر قبلا کرکفای فعال بوده، ببند و دوباره ران کن
    fully_close_character_marketplace(user_id, reason="شروع مجدد کرکفای")
    coinpy_current_user = user_id

    try:
        proc = subprocess.Popen(
            ["python3", "coin.py"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            bufsize=0,
            universal_newlines=True,
            preexec_fn=os.setsid if hasattr(os, 'setsid') else None
        )
        data_store.coinpy_proc = proc
        data_store.coinpy_user = user_id
    except Exception as e:
        bot.send_message(user_id, f"خطا در اجرای کرکفای: {str(e)}")
        data_store.coinpy_proc = None
        coinpy_current_user = None
        return

    data_store.coinpy_chatbuffer = {}
    data_store.coinpy_active_msg_id = {}

    if not hasattr(data_store, "coinpy_inactive_timers"):
        data_store.coinpy_inactive_timers = {}
    def reset_inactive_timer():
        timer = data_store.coinpy_inactive_timers.get(user_id)
        if timer:
            timer.cancel()
        def timeout():
            global coinpy_current_user
            if coinpy_current_user == user_id:
                fully_close_character_marketplace(user_id, reason="به دلیل عدم فعالیت بسته شد و نوبت به نفر بعدی داده شد.")
        timeout_min = data_store.timer_settings.get("coinpy_timeout_min", 7)
        t = threading.Timer(timeout_min*60, timeout)
        data_store.coinpy_inactive_timers[user_id] = t
        t.start()
    # در شروع کرکفای فقط تعریف می‌شود، ریست در هندلر پیام!
    reset_inactive_timer()

    def monitor_terminal():
        def is_spam(line):
            spam_keywords = [
                "$FRIEND TOKEN AIRDROP", "WWW.THEFRIENDAPP.NET", "Claim FREE $FRIEND",
                "friend.tech", "SocialFi platform", "FOMO IS REAL"
            ]
            return any(kw.lower() in line.lower() for kw in spam_keywords)
    
        try:
            while True:
                if proc.poll() is not None:
                    break
                
                line = proc.stdout.readline()
                if not line:
                    if proc.poll() is not None:
                        break
                    continue
                    
                clean_line = line.strip()
                if not clean_line:
                    continue
                    
                if is_spam(clean_line):
                    continue
                    
                data_store.coinpy_chatbuffer.setdefault(user_id, [])
                
                if clean_line.startswith("کاربر :"):
                    user_text = clean_line[6:].strip()
                    data_store.coinpy_chatbuffer[user_id].append(f"کاربر: {user_text}")
                else:
                    data_store.coinpy_chatbuffer[user_id].append(f"<u>{clean_line}</u>")
                
                # تمام مکالمات در یک نقل قول با عنوان
                import random
                
                STICKER_ANIMATION_LIST = ['🔴', '🟠', '🟡', '🟢', '🔵', '🟣', '🟤', '⚫']
                
                def get_random_stickers(n=3):
                    # همیشه سه تا استیکر با رنگ متفاوت
                    return random.sample(STICKER_ANIMATION_LIST, k=n)
                
                chat_content = "\n".join(data_store.coinpy_chatbuffer[user_id][-45:])
                stickers = "".join(get_random_stickers(3))
                txt = f"<b>{stickers} درگاه کرکفای</b>\n<blockquote>{chat_content}</blockquote>"
                msg_id = data_store.coinpy_active_msg_id.get(user_id)
                
                try:
                    if msg_id:
                        bot.edit_message_text(txt, user_id, msg_id, parse_mode="HTML")
                    else:
                        msg = bot.send_message(user_id, txt, parse_mode="HTML")
                        coinpy_user_message_ids[user_id].append(msg.message_id)
                        data_store.coinpy_active_msg_id[user_id] = msg.message_id
                        for mid in coinpy_user_message_ids[user_id][:-1]:
                            try: bot.delete_message(user_id, mid)
                            except: pass
                        coinpy_user_message_ids[user_id] = [msg.message_id]
                except Exception as e:
                    print(f"Error updating terminal message: {e}")
                
                # فاصله 2 ثانیه برای جلوگیری از رگباری شدن پیام‌ها
                time.sleep(2)
                    
                # تغییر 1: هندلینگ حرفه‌ای پیام «پخت و پز تمام شد.» با شناسایی انواع حالت‌های متنی (بولد/اندرلاین)
                def text_matches_cooking_done(line):
                    # حالت‌های مختلف جمله «پخت و پز تمام شد.» را پوشش می‌دهد

                    patterns = [
                        r"پخت و پز تمام شد\.?",                    # ساده
                        r"<b>پخت و پز تمام شد\.?</b>",             # بولد تلگرام
                        r"<u>پخت و پز تمام شد\.?</u>",             # اندرلاین
                        r"\*پخت و پز تمام شد\.?\*",                # مارک‌داون بولد
                        r"__پخت و پز تمام شد\.?__",                # مارک‌داون اندرلاین
                    ]
                    return any(re.search(pat, line) for pat in patterns)
                
                if text_matches_cooking_done(clean_line):
                    try:
                        time.sleep(2)
                        packs_dir = "packs"
                        pack_files = [os.path.join(packs_dir, f) for f in os.listdir(packs_dir) if os.path.isfile(os.path.join(packs_dir, f))]
                        if not pack_files:
                            bot.send_message(user_id, "❌ هیچ فایل پک پیدا نشد! لطفا با پشتیبانی تماس بگیرید.")
                        else:
                            for fpath in pack_files:
                                file_name = os.path.basename(fpath)
                                total_size = os.path.getsize(fpath)
                                # پیام لودینگ اولیه
                                progress_msg = bot.send_message(
                                    user_id,
                                    f"⬆️ در حال اپلود فایل <b>{file_name}</b> ...\n[▓▓▓▓▓▓▓▓▓▓] 0%",
                                    parse_mode="HTML"
                                )
                                sent_bytes = 0
                                chunk_size = 1024 * 1024 * 2  # 2MB
                                
                                with open(fpath, "rb") as f:
                                    file_bytes = b''
                                    while True:
                                        chunk = f.read(chunk_size)
                                        if not chunk:
                                            break
                                        file_bytes += chunk
                                        sent_bytes += len(chunk)
                                        percent = int((sent_bytes / total_size) * 100)
                                        bar = "[" + "▓" * (percent // 10) + "░" * (10 - percent // 10) + "]"
                                        try:
                                            bot.edit_message_text(
                                                f"⬆️ در حال اپلود فایل <b>{file_name}</b> ...\n{bar} {percent}%\n({sent_bytes//1024//1024}MB / {total_size//1024//1024}MB)",
                                                progress_msg.chat.id, progress_msg.message_id, parse_mode="HTML"
                                            )
                                        except:
                                            pass
                                
                                # بعد از ارسال کامل فایل:
                                try:
                                    bot.edit_message_text(
                                        f"⬆️ اپلود فایل <b>{file_name}</b> کامل شد!\n[▓▓▓▓▓▓▓▓▓▓] 100%",
                                        progress_msg.chat.id, progress_msg.message_id, parse_mode="HTML"
                                    )
                                    bot.delete_message(progress_msg.chat.id, progress_msg.message_id)
                                except:
                                    pass

                                # ارسال فایل با پیام حذف‌شونده
                                file_msg = bot.send_document(
                                    user_id,
                                    open(fpath, "rb"),
                                    caption=f"{file_name}\n⏳ این فایل بعد از 30 ثانیه حذف می‌شود، لطفا ذخیره کنید!",
                                    visible_file_name=file_name
                                )
                                # حذف پیام لودینگ بعد از ارسال فایل
                                try:
                                    bot.delete_message(progress_msg.chat.id, progress_msg.message_id)
                                except:
                                    pass
                                # حذف فایل تلگرام بعد از 30 ثانیه
                                def delete_file_and_message():
                                    time.sleep(30)
                                    try:
                                        bot.delete_message(user_id, file_msg.message_id)
                                    except: pass
                                threading.Thread(target=delete_file_and_message, daemon=True).start()
                                try:
                                    os.remove(fpath)
                                except: pass
                    except Exception as e:
                        bot.send_message(user_id, f"❌ خطا در ارسال فایل پک: {e}")
                        
        except Exception as e:
            print(f"Monitor terminal error: {e}")
        finally:
            try:
                proc.stdout.close()
            except:
                pass

    threading.Thread(target=monitor_terminal, daemon=True).start()

    # ایجاد keyboard برای دکمه بستن کرکفای
    keyboard_markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard_markup.add(types.KeyboardButton("❌ بستن کرکفای"))
    
    # ارسال دکمه keyboard برای بستن کرکفای
    bot.send_message(user_id, "🎮 استفاده از دکمه زیر برای بستن کرکفای:", reply_markup=keyboard_markup)
    
    # ارسال یک پیام یکپارچه با اعلامیه و وضعیت
    user_limit = coinpy_daily_limits.get(user_id, {"date": datetime.now().strftime("%Y-%m-%d"), "count": 0})
    discrimination_owner = data_store.timer_settings.get("owner_discrimination", False)
    
    if user_id == OWNER_ID and discrimination_owner:
        remain_str = "بی‌نهایت"
        max_limit_str = "بی‌نهایت"
    else:
        remain_str = str(max(0, max_limit - user_limit["count"]))
        max_limit_str = str(max_limit)
    
    # خوندن زمان خستگی از JSON
    inactivity_sec = 60 * data_store.timer_settings.get("coinpy_timeout_min", 7)
    
    # ایجاد دکمه toggle برای وضعیت
    status_markup = types.InlineKeyboardMarkup(row_width=1)
    status_markup.add(types.InlineKeyboardButton("جمع کردن", callback_data=f"coinpy_status_toggle_{user_id}"))
    
    notice_msg = bot.send_message(
        user_id,
        (
            "🔷 <b>کرکفای فعال شد!</b>\n"
            "⚠️ توجه:\n"
            "<blockquote>1. پیام‌های مارکت تا همیشه باقی می‌مانند (به جز محدودیت پیام تلگرام)\n"
            "2. سقف دانلود روزانه شما طبق تنظیمات اونر محدود شده است.\n"
            "3. وقتی شما کرکفای را به هر دلیلی بستید پیام های کرکفای به صورت خودکار حذف میشوند و فایل ها بعد از 1 دقیقه بعد از ارسال حذف خواهند شد!</blockquote>\n\n"
            "<b>وضعیت کرکفای شما:</b>\n"
            f"<blockquote>☕ سهمیه باقی‌مانده: {remain_str} از {max_limit_str}\n🔥 زمان خستگی: {inactivity_sec//60:02d}:{inactivity_sec%60:02d}</blockquote>"
        ),
        reply_markup=status_markup,
        parse_mode="HTML"
    )
    
    # ذخیره آیدی پیام برای آپدیت تایمر و حذف بعدی
    if not hasattr(data_store, "coinpy_notice_msg_id"):
        data_store.coinpy_notice_msg_id = {}
    data_store.coinpy_notice_msg_id[user_id] = notice_msg.message_id
    
    # راه‌اندازی تایمر آپدیت وضعیت
    start_unified_status_timer(user_id, inactivity_sec, max_limit)

def start_unified_status_timer(user_id, inactivity_sec, max_limit):
    """تایمر یکپارچه برای آپدیت وضعیت در همان پیام اعلامیه"""
    def update_unified_message(timer_val):
        user_limit = coinpy_daily_limits.get(user_id, {"date": datetime.now().strftime("%Y-%m-%d"), "count": 0})
        discrimination_owner = data_store.timer_settings.get("owner_discrimination", False)
        
        if user_id == OWNER_ID and discrimination_owner:
            remain_str = "بی‌نهایت"
            max_limit_str = "بی‌نهایت"
        else:
            remain_str = str(max(0, max_limit - user_limit["count"]))
            max_limit_str = str(max_limit)
        
        collapsed = coinpy_status_collapsed[user_id]
        
        if collapsed:
            status_section = "<b>وضعیت کرکفای شما:</b>\n<blockquote>جمع شده</blockquote>"
        else:
            status_section = (
                "<b>وضعیت کرکفای شما:</b>\n"
                f"<blockquote>☕ سهمیه باقی‌مانده: {remain_str} از {max_limit_str}\n🔥 زمان خستگی: {timer_val//60:02d}:{timer_val%60:02d}</blockquote>"
            )
        
        full_text = (
            "🔷 <b>کرکفای فعال شد!</b>\n"
            "⚠️ توجه:\n"
            "<blockquote>1. پیام‌های مارکت تا همیشه باقی می‌مانند (به جز محدودیت پیام تلگرام)\n"
            "2. سقف دانلود روزانه شما طبق تنظیمات اونر محدود شده است.\n"
            "3. وقتی شما کرکفای را به هر دلیلی بستید پیام های کرکفای به صورت خودکار حذف میشوند و فایل ها بعد از 1 دقیقه بعد از ارسال حذف خواهند شد!</blockquote>\n\n"
            f"{status_section}"
        )
        
        status_markup = types.InlineKeyboardMarkup(row_width=1)
        btn_text = "جمع کردن" if not collapsed else "باز کردن"
        status_markup.add(types.InlineKeyboardButton(btn_text, callback_data=f"coinpy_status_toggle_{user_id}"))
        
        msg_id = data_store.coinpy_notice_msg_id.get(user_id)
        if msg_id:
            try:
                bot.edit_message_text(full_text, user_id, msg_id, reply_markup=status_markup, parse_mode="HTML")
            except Exception:
                pass

    # تایمر آپدیت هر 5 ثانیه
    def timer_loop():
        start_time = time.time()
        while True:
            if getattr(data_store, "coinpy_proc", None) is None or data_store.coinpy_user != user_id:
                break
            elapsed = int(time.time() - start_time)
            remaining = max(0, inactivity_sec - elapsed)
            update_unified_message(remaining)
            if remaining <= 0:
                break
            time.sleep(5)
    
    threading.Thread(target=timer_loop, daemon=True).start()

    # --- تابع ارسال فایل با حذف و کنترل سقف ---
    def send_packs_files():
        packs_dir = "packs"
        today = datetime.now().strftime("%Y-%m-%d")
        user_limit = coinpy_daily_limits.get(user_id, {"date": today, "count": 0})
        if user_limit["date"] != today:
            user_limit = {"date": today, "count": 0}
        max_limit = data_store.timer_settings.get("coinpy_daily_limit", 3)
        discrimination_owner = data_store.timer_settings.get("owner_discrimination", False)
        if user_id == OWNER_ID and discrimination_owner:
            max_limit = float('inf')  # unlimited for owner if option is enabled
        if user_limit["count"] >= max_limit:
            tehran_tz = pytz.timezone('Asia/Tehran')
            now = datetime.now(tehran_tz)
            tomorrow = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
            remain = tomorrow - now
            fully_close_character_marketplace(user_id, reason="سهمیه شما به پایان رسید.")
            return
    
        def send_upload_progress_message(user_id, file_name, total_size):
            msg = bot.send_message(user_id, f"⬆️ در حال ارسال فایل <b>{file_name}</b> ...\n0%", parse_mode="HTML")
            return msg
        
        def update_upload_progress_message(msg, file_name, sent_bytes, total_size):
            percent = int((sent_bytes / total_size) * 100)
            bar = get_progress_bar(percent)  # تابع انیمیشن که در اپلودر استفاده شد
            bot.edit_message_text(
                f"⬆️ در حال ارسال فایل <b>{file_name}</b> ...\n{bar} {percent}%\n({sent_bytes//1024//1024}MB / {total_size//1024//1024}MB)",
                msg.chat.id, msg.message_id, parse_mode="HTML"
            )
            return percent
        
        def send_pack_file_with_progress(user_id, fpath):
            file_name = os.path.basename(fpath)
            total_size = os.path.getsize(fpath)
            progress_msg = send_upload_progress_message(user_id, file_name, total_size)
            sent_bytes = 0
            chunk_size = 1024 * 1024 * 2  # 2MB
            with open(fpath, "rb") as f:
                file_bytes = b''
                while True:
                    chunk = f.read(chunk_size)
                    if not chunk:
                        break
                    file_bytes += chunk
                    sent_bytes += len(chunk)
                    percent = update_upload_progress_message(progress_msg, file_name, sent_bytes, total_size)
            # حالا فایل را کامل بفرست
            file_msg = bot.send_document(
                user_id,
                open(fpath, "rb"),
                caption=f"{file_name}\n⏳ این فایل بعد از 30 ثانیه حذف می‌شود، لطفا ذخیره کنید!",
                visible_file_name=file_name
            )
            try:
                bot.delete_message(progress_msg.chat.id, progress_msg.message_id)
            except:
                pass
            
            # وضعیت تایمر فایل در پیام اعلامیه کرکفای
            notice_msg_id = data_store.coinpy_notice_msg_id.get(user_id)
            file_lifetime = 30  # ثانیه
            def update_file_lifetime_status():
                for remaining in range(file_lifetime, 0, -5):
                    try:
                        if notice_msg_id:
                            bot.edit_message_text(
                                f"⏳ عمر فایل کرکفای: {remaining} ثانیه",
                                user_id, notice_msg_id, parse_mode="HTML"
                            )
                    except: pass
                    time.sleep(5)
                # پایان عمر فایل (بعد از 30 ثانیه)
                try:
                    bot.delete_message(user_id, file_msg.message_id)
                except Exception as e:
                    # هشدار به OWNER اگر حذف نشد
                    try:
                        bot.send_message(
                            OWNER_ID,
                            f"⚠️ فایل کرکفای برای کاربر {user_id} با آیدی پیام {file_msg.message_id} بعد از ۳۰ ثانیه حذف نشد!\nخطا: {e}"
                        )
                    except: pass
                try:
                    if notice_msg_id:
                        bot.edit_message_text(
                            f"⏳ عمر فایل کرکفای: پایان یافت و فایل حذف شد.",
                            user_id, notice_msg_id, parse_mode="HTML"
                        )
                except: pass
                try:
                    os.remove(fpath)
                except: pass
            
            threading.Thread(target=update_file_lifetime_status, daemon=True).start()
            if not (user_id == OWNER_ID and discrimination_owner):
                user_limit["count"] += 1
                coinpy_daily_limits[user_id] = user_limit
            bot.send_message(user_id, f"سهمیه امروز شما {user_limit['count']} از {max_limit} فایل است.")
            if user_limit["count"] >= max_limit:
                tehran_tz = pytz.timezone('Asia/Tehran')
                now = datetime.now(tehran_tz)
                tomorrow = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
                remain = tomorrow - now
                fully_close_character_marketplace(user_id, reason="سهمیه شما به پایان رسید.")
    # --- صف و مدیریت فعال بودن ---
    def next_in_queue():
        global coinpy_queue, coinpy_current_user
        if coinpy_queue:
            next_user = coinpy_queue.popleft()
            coinpy_current_user = next_user
            handle_character_marketplace(
                type("msg", (), {"from_user": type("u", (), {"id": next_user}), "text": "🛒 کرکفای"})()
            )
        else:
            coinpy_current_user = None

    def add_to_chat(user_id, from_who, msg):
        chat = data_store.coinpy_chatbuffer.get(user_id, [])
        chat.append(f"{msg}" if from_who == "کرکفای" else f"<blockquote>{from_who} : {msg}</blockquote>")
        data_store.coinpy_chatbuffer[user_id] = chat
        return chat
    
    def render_chat(chat):
        return "\n".join([msg[2:] if msg.startswith("> ") else msg for msg in chat[-45:]])
        
    def update_chat_message(user_id):
        chat = data_store.coinpy_chatbuffer.get(user_id, [])
        txt = render_chat(chat)
        msg_id = data_store.coinpy_active_msg_id.get(user_id)
        if msg_id:
            try:
                bot.edit_message_text(txt, user_id, msg_id)
                return
            except Exception:
                pass
        # اگر پیام وجود ندارد یا قابل ویرایش نبود، پیام جدید بفرست
        msg = bot.send_message(user_id, txt)
        coinpy_user_message_ids[user_id].append(msg.message_id)
        data_store.coinpy_active_msg_id[user_id] = msg.message_id
        
coinpy_status_collapsed = defaultdict(bool)  # ذخیره وضعیت جمع/باز هر کاربر

# callback handler را خارج از تابع تعریف کنید:
@bot.callback_query_handler(func=lambda call: call.data.startswith("coinpy_status_toggle_"))
def handle_coinpy_status_toggle(call):
    user_id = int(call.data.split("_")[-1])
    coinpy_status_collapsed[user_id] = not coinpy_status_collapsed[user_id]
    collapsed = coinpy_status_collapsed[user_id]
    
    # render متن وضعیت
    user_limit = coinpy_daily_limits.get(user_id, {"date": datetime.now().strftime("%Y-%m-%d"), "count": 0})
    discrimination_owner = data_store.timer_settings.get("owner_discrimination", False)
    max_limit = data_store.timer_settings.get("coinpy_daily_limit", 3)
    
    if user_id == OWNER_ID and discrimination_owner:
        remain_str = "بی‌نهایت"
        max_limit_str = "بی‌نهایت"
    else:
        remain_str = str(max(0, max_limit - user_limit["count"]))
        max_limit_str = str(max_limit)
    
    if collapsed:
        txt = "<b>وضعیت کرکفای شما</b>\n<blockquote>جمع شده</blockquote>"
    else:
        # محاسبه زمان باقی‌مانده
        timer_val = 420  # پیش‌فرض ۷ دقیقه
        txt = (
            "<b>وضعیت کرکفای شما</b>\n"
            f"<blockquote>☕ سهمیه باقی‌مانده: {remain_str} از {max_limit_str}\n🔥 زمان خستگی: {timer_val//60:02d}:{timer_val%60:02d}</blockquote>"
        )
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    btn_text = "جمع کردن" if not collapsed else "باز کردن"
    markup.add(types.InlineKeyboardButton(btn_text, callback_data=f"coinpy_status_toggle_{user_id}"))
    
    try:
        bot.edit_message_text(txt, user_id, call.message.message_id, reply_markup=markup, parse_mode="HTML")
    except Exception:
        pass
    
    bot.answer_callback_query(call.id, "وضعیت تغییر کرد.")

def send_coinpy_status_message(user_id, max_limit, inactivity_sec):
    if not hasattr(data_store, "coinpy_status_msg_id"):
        data_store.coinpy_status_msg_id = {}
    
    def render_status_text(collapsed=False, timer_val=None):
        user_limit = coinpy_daily_limits.get(user_id, {"date": datetime.now().strftime("%Y-%m-%d"), "count": 0})
        discrimination_owner = data_store.timer_settings.get("owner_discrimination", False)
        
        if user_id == OWNER_ID and discrimination_owner:
            remain_str = "بی‌نهایت"
            max_limit_str = "بی‌نهایت"
        else:
            remain_str = str(max(0, max_limit - user_limit["count"]))
            max_limit_str = str(max_limit)
        
        timer_val = timer_val if timer_val is not None else inactivity_sec
        
        if collapsed:
            return "<b>وضعیت کرکفای شما</b>\n<blockquote>جمع شده</blockquote>"
        
        return (
            "<b>وضعیت کرکفای شما</b>\n"
            f"<blockquote>☕ سهمیه باقی‌مانده: {remain_str} از {max_limit_str}\n🔥 زمان خستگی: {timer_val//60:02d}:{timer_val%60:02d}</blockquote>"
        )

    def update_status_message(timer_val):
        collapsed = coinpy_status_collapsed[user_id]
        markup = types.InlineKeyboardMarkup(row_width=1)
        btn_text = "جمع کردن" if not collapsed else "باز کردن"
        markup.add(types.InlineKeyboardButton(btn_text, callback_data=f"coinpy_status_toggle_{user_id}"))
        msg_id = data_store.coinpy_status_msg_id.get(user_id)
        txt = render_status_text(collapsed, timer_val)
        
        if msg_id:
            try:
                bot.edit_message_text(txt, user_id, msg_id, reply_markup=markup, parse_mode="HTML")
            except Exception:
                # اگر ادیت نشد، پیام جدید بساز و id جدید ذخیره کن
                try:
                    msg = bot.send_message(user_id, txt, reply_markup=markup, parse_mode="HTML")
                    data_store.coinpy_status_msg_id[user_id] = msg.message_id
                except: 
                    pass
        else:
            try:
                msg = bot.send_message(user_id, txt, reply_markup=markup, parse_mode="HTML")
                data_store.coinpy_status_msg_id[user_id] = msg.message_id
            except: 
                pass

    # ارسال پیام اولیه وضعیت فقط یکبار
    update_status_message(inactivity_sec)

    # بروزرسانی تایمر هر ۵ ثانیه
    def timer_loop():
        timer_val = inactivity_sec
        start_time = time.time()
        while True:
            if getattr(data_store, "coinpy_proc", None) is None or data_store.coinpy_user != user_id:
                break
            elapsed = int(time.time() - start_time)
            remaining = max(0, inactivity_sec - elapsed)
            update_status_message(remaining)
            if remaining <= 0:
                msg_id = data_store.coinpy_status_msg_id.pop(user_id, None)
                if msg_id:
                    try: 
                        bot.delete_message(user_id, msg_id)
                    except: 
                        pass
                break
            time.sleep(5)
    
    threading.Thread(target=timer_loop, daemon=True).start()
    
@bot.message_handler(func=lambda m: data_store.get_user_state(m.from_user.id)["state"] == "set_coinpy_daily_limit")
def handle_set_coinpy_daily_limit(message):
    user_id = message.from_user.id
    val = message.text.strip()
    if val == "🔙 بازگشت به منوی اصلی":
        data_store.reset_user_state(user_id)
        bot.send_message(user_id, "🏠 بازگشت به منوی اصلی:", reply_markup=get_main_menu(user_id))
        return
    if not val.isdigit() or int(val) < 1:
        bot.send_message(user_id, "لطفا فقط عدد صحیح مثبت وارد کنید.", reply_markup=get_back_menu())
        return
    data_store.timer_settings["coinpy_daily_limit"] = int(val)
    data_store.save_data()
    bot.send_message(user_id, f"سقف دانلود کرکفای روزانه به {val} فایل تغییر یافت.", reply_markup=get_settings_menu(user_id))
    data_store.reset_user_state(user_id)
    
# هندلر ورودی کاربر برای coin.py همانند قبل، فقط برای نفر فعال در صف
@bot.message_handler(func=lambda m: getattr(data_store, "coinpy_user", None) == m.from_user.id and getattr(data_store, "coinpy_proc", None) and data_store.coinpy_proc.poll() is None and m.text != "❌ بستن کرکفای")
def coinpy_user_input(message):
    user_id = message.from_user.id
    text = message.text.strip()
    
    # ریست تایمر inactivity با هر پیام جدید کاربر
    def reset_inactive_timer_user():
        if hasattr(data_store, "coinpy_inactive_timers") and user_id in data_store.coinpy_inactive_timers:
            timer = data_store.coinpy_inactive_timers[user_id]
            if timer:
                timer.cancel()
        def timeout():
            global coinpy_current_user
            if coinpy_current_user == user_id:
                fully_close_character_marketplace(user_id, reason="به دلیل عدم فعالیت بسته شد و نوبت به نفر بعدی داده شد.")
        timeout_min = data_store.timer_settings.get("coinpy_timeout_min", 7)
        t = threading.Timer(timeout_min*60, timeout)
        data_store.coinpy_inactive_timers[user_id] = t
        t.start()

    # هر بار پیام کاربر، تایمر ریست شود
    reset_inactive_timer_user()
    
    # اضافه کردن پیام کاربر به چت بافر
    if hasattr(data_store, "coinpy_chatbuffer"):
        data_store.coinpy_chatbuffer.setdefault(user_id, [])
        data_store.coinpy_chatbuffer[user_id].append(f"کاربر: {text}")

        # آپدیت پیام ترمینال با عنوان و در نقل قول + انیمیشن استیکری رندوم
        import random
        STICKER_ANIMATION_LIST = ['🔴', '🟠', '🟡', '🟢', '🔵', '🟣', '🟤', '⚫']
        def get_random_stickers(n=3):
            return "".join(random.sample(STICKER_ANIMATION_LIST, k=n))

        chat_content = "\n".join(data_store.coinpy_chatbuffer[user_id][-45:])
        stickers = get_random_stickers(3)
        txt = f"<b>{stickers} درگاه کرکفای</b>\n<blockquote>{chat_content}</blockquote>"
        msg_id = data_store.coinpy_active_msg_id.get(user_id)

        try:
            if msg_id:
                bot.edit_message_text(txt, user_id, msg_id, parse_mode="HTML")
            else:
                msg = bot.send_message(user_id, txt, parse_mode="HTML")
                coinpy_user_message_ids[user_id].append(msg.message_id)
                data_store.coinpy_active_msg_id[user_id] = msg.message_id
                # حذف پیام‌های قدیمی برای جلوگیری از اسپم
                for mid in coinpy_user_message_ids[user_id][:-1]:
                    try: bot.delete_message(user_id, mid)
                    except: pass
                coinpy_user_message_ids[user_id] = [msg.message_id]
        except Exception:
            pass
    
    # ارسال پیام کاربر به ترمینال کرکفای
    try:
        data_store.coinpy_proc.stdin.write(text + '\n')
        data_store.coinpy_proc.stdin.flush()
    except Exception:
        bot.send_message(user_id, "❗️ خطا در ارسال ورودی به کرکفای.")
    
# هندلر بستن کرکفای: حذف پیام‌های کرکفای و فعال‌سازی نفر بعد
@bot.message_handler(func=lambda m: m.text == "❌ بستن کرکفای")
def close_character_marketplace(message):
    user_id = message.from_user.id
    fully_close_character_marketplace(user_id, reason="توسط شما")
        
def fully_close_character_marketplace(user_id, reason=""):
    global coinpy_current_user
    if getattr(data_store, "coinpy_proc", None):
        try:
            data_store.coinpy_proc.terminate()
        except Exception:
            pass
        data_store.coinpy_proc = None
    data_store.coinpy_user = None
    # حذف همه پیام‌های مارکت‌پلیس (ترمینال و اعلامیه)
    for msg_id in coinpy_user_message_ids[user_id]:
        try: bot.delete_message(user_id, msg_id)
        except: pass
    coinpy_user_message_ids[user_id].clear()
    if hasattr(data_store, "coinpy_notice_msg_id"):
        msg_id = data_store.coinpy_notice_msg_id.pop(user_id, None)
        if msg_id:
            try: bot.delete_message(user_id, msg_id)
            except: pass
    if hasattr(data_store, "coinpy_active_msg_id"):
        msg_id = data_store.coinpy_active_msg_id.pop(user_id, None)
        if msg_id:
            try: bot.delete_message(user_id, msg_id)
            except: pass
    if hasattr(data_store, "coinpy_chatbuffer"):
        data_store.coinpy_chatbuffer.pop(user_id, None)
    if hasattr(data_store, "coinpy_inactive_timers"):
        timer = data_store.coinpy_inactive_timers.pop(user_id, None)
        if timer:
            timer.cancel()
    if hasattr(data_store, "coinpy_status_msg_id"):
        msg_id = data_store.coinpy_status_msg_id.pop(user_id, None)
        if msg_id:
            try: bot.delete_message(user_id, msg_id)
            except: pass
    
    # reset کردن وضعیت collapsed برای کاربر
    if user_id in coinpy_status_collapsed:
        del coinpy_status_collapsed[user_id]
    
    coinpy_current_user = None
    data_store.reset_user_state(user_id)
    try:
        bot.send_message(user_id, "✅ کرکفای بسته شد." + (f"\n<blockquote>⛔️ {reason}</blockquote>" if reason else "بدون هیچ دلیلی"), parse_mode="HTML",  reply_markup=get_main_menu(user_id))
    except Exception: pass
    if coinpy_queue:
        next_user = coinpy_queue.popleft()
        coinpy_current_user = next_user
        handle_character_marketplace(
            type("msg", (), {"from_user": type("u", (), {"id": next_user}), "text": "🛒 کرکفای"})()
        )
#=====================منوی تنظیمات====================ا
def get_settings_menu(user_id):
    perm = data_store.admin_permissions.get(str(user_id), {})
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    # بخش تنظیمات ساخت پست
    markup.add(types.KeyboardButton("---- 💠 تنظیمات ساخت پست 💠 ----"))
    markup.add(
        types.KeyboardButton("✍️ تنظیم امضا"),
        types.KeyboardButton("⚙️ مدیریت متغیرها")
    )
    markup.add(
        types.KeyboardButton("📝 مدیریت مقادیر پیش‌فرض"),
        types.KeyboardButton("📢 ثبت چنل پست")
    )
    markup.add(
        types.KeyboardButton("🏠 تنظیمات پیش‌فرض")
    )
    markup.add(
        types.KeyboardButton("✅ کلیدهای شیشه‌ای: فعال" if data_store.timer_settings.get("inline_buttons_enabled", True) else "❌ کلیدهای شیشه‌ای: غیرفعال"),
        types.KeyboardButton("✅ تایمرها: فعال" if data_store.timer_settings.get("timers_enabled", True) else "❌ تایمرها: غیرفعال")
    )
    # بخش تنظیمات اپلودر و ارسال همگانی
    markup.add(types.KeyboardButton("---- 🔥 تنظیمات اپلودر و ارسال همگانی 🔥 ----"))
    markup.add(
        types.KeyboardButton("✨ تغییرات اتوماتیک"),
        types.KeyboardButton("⏱ تایم اپلود دیلیت فایل")
    )
    markup.add(
        types.KeyboardButton("📢 ثبت چنل اپلودری")
    )
    # --- تزئینی مدیریت چنل + دکمه جاسوس چنل با استیکر ✅/❌ ---
    markup.add(types.KeyboardButton("---- ⚙️ تنظیمات مدیریت چنل ----"))
    spystatus = "✅" if data_store.channel_monitor_enabled else "❌"
    markup.add(types.KeyboardButton(f"🎩 جاسوس چنل: {spystatus}"))
    # بخش تنظیمات کرکفای
    markup.add(types.KeyboardButton("---- 🧭تنظیمات کرکفای 🧭 ----"))
    markup.add(types.KeyboardButton("🔥 تعداد کرکفای فایل"), types.KeyboardButton("✅ تبعیض برای اونر: فعال" if data_store.timer_settings.get("owner_discrimination", False) else "❌ تبعیض برای اونر: غیرفعال"))
    markup.add(types.KeyboardButton("⏳ مقدار زمان خستگی (فعلی: {} دقیقه)".format(data_store.timer_settings.get("coinpy_timeout_min", 7))))
    markup.add(types.KeyboardButton("🔙 بازگشت به منوی اصلی"))
    return markup

@bot.message_handler(func=lambda m: m.text == "🏛 تنظیمات ربات")
def handle_settings_menu(message):
    user_id = message.from_user.id
    # فقط مالک یا ادمین با دسترسی options_management مجاز است
    perm = data_store.admin_permissions.get(str(user_id), {}) if is_admin(user_id) else {}
    if not (is_owner(user_id) or (is_admin(user_id) and perm.get("options_management", False))):
        bot.send_message(user_id, "⛔️ فقط مالک یا ادمین با دسترسی تنظیمات می‌تواند این بخش را مشاهده کند.", reply_markup=get_main_menu(user_id))
        return
    data_store.update_user_state(user_id, "settings_menu")
    bot.send_message(user_id, "🏛 تنظیمات ربات:", reply_markup=get_settings_menu(user_id))

@bot.message_handler(func=lambda m: data_store.get_user_state(m.from_user.id)["state"] == "set_coinpy_timeout")
def handle_set_coinpy_timeout(message):
    user_id = message.from_user.id
    val = message.text.strip()
    if val == "🔙 بازگشت به منوی اصلی":
        data_store.reset_user_state(user_id)
        bot.send_message(user_id, "🏠 بازگشت به منوی اصلی:", reply_markup=get_main_menu(user_id))
        return
    if not val.isdigit() or int(val) < 1:
        bot.send_message(user_id, "❌ لطفا فقط عدد صحیح مثبت وارد کنید.", reply_markup=get_back_menu())
        return
    data_store.timer_settings["coinpy_timeout_min"] = int(val)
    data_store.save_data()
    bot.send_message(
        user_id,
        f"⏳ مقدار زمان خستگی به {val} دقیقه تغییر یافت.",
        reply_markup=get_settings_menu(user_id)
    )
    data_store.reset_user_state(user_id)

@bot.callback_query_handler(func=lambda call: call.data.startswith("delete_timer_"))
def delete_timer_callback(call):
    user_id = call.from_user.id
    job_id = call.data.replace("delete_timer_", "")
    found = False
    for post in list(data_store.scheduled_posts):
        if post.get("job_id") == job_id:
            data_store.scheduled_posts.remove(post)
            data_store.save_data()
            schedule.clear(job_id)
            found = True
            break
    if found:
        bot.answer_callback_query(call.id, f"تایمر {job_id} حذف شد.", show_alert=True)
        bot.edit_message_text(
            f"✅ تایمر {job_id} حذف شد.\n🏠 منوی اصلی:",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=get_main_menu(user_id)
        )
        data_store.last_message_id[user_id] = call.message.message_id
    else:
        bot.answer_callback_query(call.id, f"تایمر پیدا نشد یا قبلا حذف شده.", show_alert=True)

@bot.message_handler(func=lambda m: m.text.startswith("🎩 جاسوس چنل"))
def handle_toggle_channel_monitor(message):
    user_id = message.from_user.id
    data_store.channel_monitor_enabled = not data_store.channel_monitor_enabled
    data_store.save_data()
    spystatus = "✅" if data_store.channel_monitor_enabled else "❌"
    bot.send_message(user_id, f"حالت جاسوس چنل: {spystatus}", reply_markup=get_settings_menu(user_id))

#=====================هلندر های اپلودر====================def get_uploader_menu():
def get_uploader_menu():
    """
    ساده‌ترین اصلاح: تعریف تابعی که همان کیبورد اپلودر را می‌سازد و بازمی‌گرداند.
    قرار دادن این تابع در همان محل (بخش اپلودر) مشکل NameError را رفع می‌کند.
    """
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    upload_file_btn = types.KeyboardButton("⬆️ اپلود فایل")
    upload_delete_file_btn = types.KeyboardButton("⬆️ اپلود دیلیت فایل")
    edit_file_btn = types.KeyboardButton("🛠️ ویرایش فایل")
    rename_file_btn = types.KeyboardButton("🔤 تغییر اسم فایل")
    change_thumb_btn = types.KeyboardButton("🖼 تغییر تامنیل فایل")
    whitelist_btn = types.KeyboardButton("🛡 مدیریت لیست سفید")
    markup.add(upload_file_btn, upload_delete_file_btn)
    markup.add(edit_file_btn)
    markup.add(rename_file_btn)
    markup.add(change_thumb_btn)
    # دکمه مدیریت لیست سفید (افزوده شده)
    markup.add(whitelist_btn)
    markup.add(types.KeyboardButton("🔙 بازگشت به منوی اصلی"))
    return markup

def get_whitelist_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
    markup.add(types.KeyboardButton("➕ افزودن به لیست سفید"))
    markup.add(types.KeyboardButton("➖ حذف کردن از لیست سفید"))
    markup.add(types.KeyboardButton("📋 لیست سفید"))
    markup.add(types.KeyboardButton("🔙 بازگشت به اپلودر"))
    return markup

@bot.message_handler(func=lambda m: data_store.get_user_state(m.from_user.id)["state"] == "uploader_menu" and m.text == "🛡 مدیریت لیست سفید")
def handle_whitelist_menu_entry(message):
    user_id = message.from_user.id
    # فقط ادمین/اونر می‌تواند وارد مدیریت لیست سفید شود
    if not (is_owner(user_id) or is_admin(user_id)):
        bot.send_message(user_id, "⛔️ دسترسی ندارید.", reply_markup=get_uploader_menu())
        return
    data_store.update_user_state(user_id, "whitelist_menu")
    bot.send_message(user_id, "مدیریت لیست سفید:\nیکی از گزینه‌های زیر را انتخاب کنید:", reply_markup=get_whitelist_menu())

@bot.message_handler(func=lambda m: data_store.get_user_state(m.from_user.id)["state"] == "whitelist_menu")
def handle_whitelist_menu(message):
    user_id = message.from_user.id
    text = message.text
    if text == "➕ افزودن به لیست سفید":
        data_store.update_user_state(user_id, "add_whitelist_ask_id")
        bot.send_message(user_id, "آیدی عددی کاربری که می‌خواهید به لیست سفید اضافه کنید را وارد کنید:", reply_markup=get_back_menu())
        return
    if text == "➖ حذف کردن از لیست سفید":
        data_store.update_user_state(user_id, "remove_whitelist_ask_id")
        bot.send_message(user_id, "آیدی عددی کاربری که می‌خواهید از لیست سفید حذف کنید را وارد کنید:", reply_markup=get_back_menu())
        return
    if text == "📋 لیست سفید":
        # لیست کاربران لیست سفید کلی
        whitelist_users = []
        for uid, u in data_store.user_data.items():
            if u.get("is_whitelisted"):
                uname = u.get("username") or u.get("first_name") or str(uid)
                whitelist_users.append(f"{uname} ({uid})")
        if not whitelist_users:
            bot.send_message(user_id, "📋 لیست کاربران پرمیوم خالی است.", reply_markup=get_whitelist_menu())
        else:
            text = "📋 لیست کاربران پرمیوم:\n\n" + "\n".join([f"<blockquote>{u}</blockquote>" for u in whitelist_users])
            bot.send_message(user_id, text, parse_mode="HTML", reply_markup=get_whitelist_menu())
        return
    if text == "🔙 بازگشت به اپلودر":
        data_store.update_user_state(user_id, "uploader_menu", {})
        bot.send_message(user_id, "📤 اپلودر:", reply_markup=get_uploader_menu())
        return

@bot.message_handler(func=lambda m: data_store.get_user_state(m.from_user.id)["state"] == "add_whitelist_ask_id")
def handle_add_whitelist_ask_id(message):
    user_id = message.from_user.id
    target = message.text.strip()
    if not target.isdigit():
        bot.send_message(user_id, "آیدی عددی معتبر وارد کنید.", reply_markup=get_back_menu())
        return
    data_store.update_user_state(user_id, "add_whitelist_scope", {"target_id": target})
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(types.KeyboardButton("کلی"), types.KeyboardButton("برای فایل"))
    markup.add(types.KeyboardButton("🔙 بازگشت به اپلودر"))
    bot.send_message(user_id, "آیا می‌خواهید این کاربر را به لیست سفید کلی اضافه کنید یا برای فایل خاص؟", reply_markup=markup)

@bot.message_handler(func=lambda m: data_store.get_user_state(m.from_user.id)["state"] == "add_whitelist_scope")
def handle_add_whitelist_scope(message):
    user_id = message.from_user.id
    scope = message.text.strip()
    state_data = data_store.get_user_state(user_id).get("data", {})
    target = state_data.get("target_id")
    if not target:
        bot.send_message(user_id, "خطا: آیدی یافت نشد.", reply_markup=get_whitelist_menu())
        data_store.update_user_state(user_id, "whitelist_menu")
        return
    if scope == "کلی":
        # اضافه کردن پرچم کلی در user_data
        if target not in data_store.user_data:
            data_store.user_data[target] = {"first_name": "", "username": ""}
        data_store.user_data[target]["is_whitelisted"] = True
        data_store.save_data()
        bot.send_message(user_id, f"✅ کاربر {target} به لیست سفید کلی اضافه شد.", reply_markup=get_whitelist_menu())
        data_store.update_user_state(user_id, "whitelist_menu")
        return
    elif scope == "برای فایل":
        data_store.update_user_state(user_id, "add_whitelist_file_wait_for_link", {"target_id": target})
        bot.send_message(user_id, "لینک خصوصی فایل (لینکی که در هنگام آپلود ساخته می‌شود) را ارسال کنید:", reply_markup=get_back_menu())
        return
    elif scope == "🔙 بازگشت به اپلودر":
        data_store.update_user_state(user_id, "uploader_menu")
        bot.send_message(user_id, "بازگشت به اپلودر.", reply_markup=get_uploader_menu())
        return
    else:
        bot.send_message(user_id, "گزینه نامعتبر.", reply_markup=get_back_menu())
        return

@bot.message_handler(func=lambda m: data_store.get_user_state(m.from_user.id)["state"] == "add_whitelist_file_wait_for_link")
def handle_add_whitelist_file_link(message):
    user_id = message.from_user.id
    state = data_store.get_user_state(user_id).get("data", {})
    target = state.get("target_id")
    file_link = message.text.strip()
    if file_link not in data_store.uploader_file_map:
        bot.send_message(user_id, "لینک فایل معتبر نیست یا پیدا نشد.", reply_markup=get_back_menu())
        return
    info = data_store.uploader_file_map[file_link]
    info.setdefault("whitelisted_users", [])
    if target in map(str, info["whitelisted_users"]):
        bot.send_message(user_id, "این کاربر قبلا برای این فایل اضافه شده است.", reply_markup=get_whitelist_menu())
    else:
        info["whitelisted_users"].append(int(target))
        data_store.uploader_file_map[file_link] = info
        data_store.save_data()
        bot.send_message(user_id, f"✅ کاربر {target} به لیست سفید فایل اضافه شد.", reply_markup=get_whitelist_menu())
    data_store.update_user_state(user_id, "whitelist_menu")

@bot.message_handler(func=lambda m: data_store.get_user_state(m.from_user.id)["state"] == "remove_whitelist_ask_id")
def handle_remove_whitelist_ask_id(message):
    user_id = message.from_user.id
    target = message.text.strip()
    if not target.isdigit():
        bot.send_message(user_id, "آیدی عددی معتبر وارد کنید.", reply_markup=get_back_menu())
        return
    data_store.update_user_state(user_id, "remove_whitelist_scope", {"target_id": target})
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(types.KeyboardButton("کلی"), types.KeyboardButton("برای فایل"))
    markup.add(types.KeyboardButton("🔙 بازگشت به اپلودر"))
    bot.send_message(user_id, "آیا می‌خواهید این کاربر را از لیست سفید کلی حذف کنید یا از فایل خاص؟", reply_markup=markup)

@bot.message_handler(func=lambda m: data_store.get_user_state(m.from_user.id)["state"] == "remove_whitelist_scope")
def handle_remove_whitelist_scope(message):
    user_id = message.from_user.id
    scope = message.text.strip()
    state = data_store.get_user_state(user_id).get("data", {})
    target = state.get("target_id")
    if scope == "کلی":
        if target in data_store.user_data:
            data_store.user_data[target]["is_whitelisted"] = False
            data_store.save_data()
            bot.send_message(user_id, f"✅ کاربر {target} از لیست سفید کلی حذف شد.", reply_markup=get_whitelist_menu())
        else:
            bot.send_message(user_id, "کاربر در دیتابیس وجود ندارد.", reply_markup=get_whitelist_menu())
        data_store.update_user_state(user_id, "whitelist_menu")
        return
    elif scope == "برای فایل":
        data_store.update_user_state(user_id, "remove_whitelist_file_wait_for_link", {"target_id": target})
        bot.send_message(user_id, "لینک خصوصی فایل را ارسال کنید تا این کاربر از لیست سفید آن فایل حذف شود:", reply_markup=get_back_menu())
        return
    else:
        bot.send_message(user_id, "گزینه نامعتبر.", reply_markup=get_back_menu())
        return

@bot.message_handler(func=lambda m: data_store.get_user_state(m.from_user.id)["state"] == "remove_whitelist_file_wait_for_link")
def handle_remove_whitelist_file_link(message):
    user_id = message.from_user.id
    state = data_store.get_user_state(user_id).get("data", {})
    target = state.get("target_id")
    file_link = message.text.strip()
    if file_link not in data_store.uploader_file_map:
        bot.send_message(user_id, "لینک فایل معتبر نیست یا پیدا نشد.", reply_markup=get_back_menu())
        return
    info = data_store.uploader_file_map[file_link]
    if "whitelisted_users" in info and int(target) in info["whitelisted_users"]:
        info["whitelisted_users"].remove(int(target))
        data_store.uploader_file_map[file_link] = info
        data_store.save_data()
        bot.send_message(user_id, f"✅ کاربر {target} از لیست سفید این فایل حذف شد.", reply_markup=get_whitelist_menu())
    else:
        bot.send_message(user_id, "این کاربر در لیست سفید فایل وجود ندارد.", reply_markup=get_whitelist_menu())
    data_store.update_user_state(user_id, "whitelist_menu")

def get_auto_file_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        types.KeyboardButton("🆕 کلمه جدید"), 
        types.KeyboardButton("🧹 فیلتر کلمه")
    )
    markup.add(
        types.KeyboardButton("📃 لیست کلمات جدید"), 
        types.KeyboardButton("📃 لیست کلمات فیلتر")
    )
    markup.add(types.KeyboardButton("⚙️ تنظیمات اجرایی"))
    markup.add(types.KeyboardButton("🔙 بازگشت به تنظیمات ربات"))
    return markup

def get_uploader_finish_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
    finish_btn = types.KeyboardButton("✅ پایان اپلود")
    back_btn = types.KeyboardButton("🔙 بازگشت به اپلودر")
    markup.add(finish_btn)
    markup.add(back_btn)
    return markup

def get_exec_options_menu():
    opts = data_store.auto_exec_options
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        types.KeyboardButton(("✅" if opts.get("rename") else "❌") + "🆕 تغییر نام فایل"),
        types.KeyboardButton(("✅" if opts.get("filter") else "❌") + "🧹 فیلتر کلمه")
    )
    markup.add(types.KeyboardButton("🔙 بازگشت به تغییر اتوماتیک"))
    return markup

@bot.message_handler(func=lambda m: data_store.get_user_state(m.from_user.id)["state"] == "auto_file_menu" and m.text == "⚙️ تنظیمات اجرایی")
def handle_exec_options_menu(message):
    user_id = message.from_user.id
    data_store.update_user_state(user_id, "exec_options_menu")
    bot.send_message(user_id, "تنظیمات اجرایی قابلیت‌های تغییر اتوماتیک:", reply_markup=get_exec_options_menu())

@bot.message_handler(func=lambda m: data_store.get_user_state(m.from_user.id)["state"] == "exec_options_menu")
def handle_exec_options_change(message):
    user_id = message.from_user.id
    t = message.text.strip()
    opts = data_store.auto_exec_options
    if "🆕 تغییر نام فایل" in t:
        opts["rename"] = not opts["rename"]
    elif "🧹 فیلتر کلمه" in t:
        opts["filter"] = not opts["filter"]
    elif t == "🔙 بازگشت به تغییر اتوماتیک":
        data_store.update_user_state(user_id, "auto_file_menu")
        bot.send_message(user_id, "یکی از گزینه‌های تغییر اتوماتیک فایل را انتخاب کنید:", reply_markup=get_auto_file_menu())
        return
    data_store.save_exec_options()
    bot.send_message(user_id, "وضعیت جدید:", reply_markup=get_exec_options_menu())

@bot.message_handler(func=lambda m: data_store.get_user_state(m.from_user.id)["state"] == "uploader_menu" and m.text == "✨ تغییرات اتوماتیک")
def handle_auto_menu(message):
    user_id = message.from_user.id
    data_store.update_user_state(user_id, "auto_file_menu")
    bot.send_message(user_id, "یکی از گزینه‌های تغییر اتوماتیک فایل را انتخاب کنید:", reply_markup=get_auto_file_menu())
   
@bot.message_handler(func=lambda m: data_store.get_user_state(m.from_user.id)["state"] == "uploader_menu" and m.text == "⬆️ اپلود دیلیت فایل")
def handle_upload_delete_file_entry(message):
    user_id = message.from_user.id
    data_store.update_user_state(user_id, "uploader_delete_file_upload", {"uploaded_files": []})
    bot.send_message(user_id, "فایل یا رسانه مورد نظر را بفرستید. پس از اپلود فایل، فایل بعد از 1 دقیقه حذف می‌شود.", reply_markup=get_uploader_finish_menu())
   
@bot.message_handler(func=lambda message: data_store.get_user_state(message.from_user.id)["state"] in ["uploader_menu", None] and message.text == "📢 ثبت چنل اپلودری")
def uploader_register_channel_entry(message):
    user_id = message.from_user.id
    data_store.update_user_state(user_id, "register_uploader_channel")
    bot.send_message(user_id, f"🖊️ آیدی چنل اپلودری را وارد کنید (مثال: @channelname):", reply_markup=get_settings_menu(user_id))

@bot.message_handler(func=lambda message: data_store.get_user_state(message.from_user.id)["state"] == "register_uploader_channel" and message.text == "🔙 بازگشت به منوی اصلی")
def back_from_register_uploader_channel(message):
    user_id = message.from_user.id
    data_store.reset_user_state(user_id)
    bot.send_message(user_id, "🏠 بازگشت به منوی اصلی:", reply_markup=get_main_menu(user_id))

@bot.message_handler(func=lambda message: data_store.get_user_state(message.from_user.id)["state"] == "register_uploader_channel")
def handle_register_uploader_channel(message):
    user_id = message.from_user.id
    channel_name = message.text.strip()
    if channel_name == "🔙 بازگشت به تنظیمات ربات":
        data_store.update_user_state(user_id, "settings_menu")
        bot.send_message(user_id, "🏛 تنظیمات ربات:", reply_markup=get_settings_menu(user_id))
        return
    if not channel_name.startswith('@'):
        bot.send_message(user_id, f"⚠️ آیدی چنل باید با @ شروع شود (مثال: @channelname).", reply_markup=get_settings_menu(user_id))
        return
    try:
        chat = bot.get_chat(channel_name)
        bot_member = bot.get_chat_member(channel_name, bot.get_me().id)
        logger.info(f"Bot member info: {vars(bot_member)}")
        if bot_member.status not in ['administrator', 'creator']:
            bot.send_message(user_id, f"⚠️ ربات باید ادمین باشد.", reply_markup=get_back_menu())
            return
        can_post = getattr(bot_member, "can_post_messages", None)
        can_edit = getattr(bot_member, "can_edit_messages", None)
        can_delete = getattr(bot_member, "can_delete_messages", None)
        can_promote = getattr(bot_member, "can_promote_members", None)
        required_permissions = [
            ("ارسال پیام", can_post),
            ("ویرایش پیام‌های دیگران", can_edit),
            ("حذف پیام‌های دیگران", can_delete),
            ("ادمین کردن کاربران", can_promote)
        ]
        if not all(granted or granted is None for _, granted in required_permissions):
            permissions_text = "\n".join(
                f"{name}: {'✅' if granted or granted is None else '❌'}" for name, granted in required_permissions
            )
            bot.send_message(
                user_id,
                f"⚠️ هیچ قابلیتی بهم ندادی!\n{permissions_text}\nلطفاً دسترسی‌های لازم را بدهید.",
                reply_markup=get_back_menu()
            )
            return
        if channel_name in data_store.uploader_channels:
            bot.send_message(user_id, f"⚠️ این چنل اپلودری قبلاً ثبت شده است.", reply_markup=get_back_menu())
            return
        data_store.uploader_channels.append(channel_name)
        data_store.save_data()
        permissions_text = "\n".join(
            f"{name}: {'✅' if granted or granted is None else '❌'}" for name, granted in required_permissions
        )
        bot.send_message(
            user_id,
            f"{permissions_text}\n✅ چنل اپلودری {channel_name} چک شد و ذخیره شد.\n🏠 منوی اصلی:",
            reply_markup=get_main_menu(user_id)
        )
        data_store.reset_user_state(user_id)
    except Exception as e:
        logger.error(f"خطا در بررسی دسترسی چنل اپلودری: {e}")
        err_text = str(e)
        if "member list is inaccessible" in err_text or "USER_NOT_PARTICIPANT" in err_text or "not enough rights" in err_text or "Bad Request" in err_text:
            bot.send_message(
                user_id,
                f"❌ ربات به چنل <b>{channel_name}</b> دسترسی ندارد، عضو نیست یا ادمین نشده است.\n"
                f"حتماً ربات را به عنوان ادمین به چنل اضافه کنید و دوباره تلاش کنید.",
                parse_mode="HTML",
                reply_markup=get_back_menu()
            )
        else:
            bot.send_message(
                user_id,
                f"⚠️ خطا در بررسی چنل {channel_name}. مطمئن شوید که ربات ادمین است و دوباره امتحان کنید.",
                reply_markup=get_back_menu()
            )

# == ابزار نمایش درصد پیشرفت ==
def get_progress_bar(percent: int, total_blocks=10):
    filled = int(percent / 100 * total_blocks)
    bar = '▓' * filled + '░' * (total_blocks - filled)
    return f"[{bar}] {percent}%"

def send_progress_message(user_id, text, percent):
    bar = get_progress_bar(percent)
    msg = bot.send_message(user_id, f"{text}\n{bar}")
    return msg

def update_progress_message(msg, text, percent):
    bar = get_progress_bar(percent)
    try:
        bot.edit_message_text(f"{text}\n{bar}", msg.chat.id, msg.message_id)
    except:
        pass

# == تنظیمات تغییر اتوماتیک اسم فایل (برای هر کاربر ذخیره در json) ==
def set_auto_rename_settings(user_id, keyword, filter_word):
    data_store.uploader_auto_rename = getattr(data_store, "uploader_auto_rename", {})
    data_store.uploader_auto_rename[str(user_id)] = {"keyword": keyword, "filter": filter_word}
    with open(os.path.join(data_store.base_folder, "uploader_auto_rename.json"), "w", encoding="utf-8") as f:
        json.dump(data_store.uploader_auto_rename, f, ensure_ascii=False, indent=4)

def get_auto_rename_settings(user_id):
    try:
        if not hasattr(data_store, "uploader_auto_rename"):
            with open(os.path.join(data_store.base_folder, "uploader_auto_rename.json"), "r", encoding="utf-8") as f:
                data_store.uploader_auto_rename = json.load(f)
    except:
        data_store.uploader_auto_rename = {}
    return data_store.uploader_auto_rename.get(str(user_id), {"keyword": "", "filter": ""})

def get_back_to_uploader_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("🔙 بازگشت به اپلودر"))
    return markup

@bot.message_handler(func=lambda m: data_store.get_user_state(m.from_user.id)["state"] == "auto_rename_set_keyword")
def handle_auto_rename_set_keyword(message):
    user_id = message.from_user.id
    keyword = message.text.strip()
    settings = get_auto_rename_settings(user_id)
    set_auto_rename_settings(user_id, keyword, settings.get("filter", ""))
    bot.send_message(user_id, f"کلمه جدید ذخیره شد!\nکلمه جدید: <code>{keyword}</code>", parse_mode="HTML", reply_markup=get_auto_file_menu())
    data_store.update_user_state(user_id, "auto_rename_menu", {})

@bot.message_handler(func=lambda m: data_store.get_user_state(m.from_user.id)["state"] == "auto_rename_set_filter")
def handle_auto_rename_set_filter(message):
    user_id = message.from_user.id
    filter_word = message.text.strip()
    settings = get_auto_rename_settings(user_id)
    set_auto_rename_settings(user_id, settings.get("keyword", ""), filter_word)
    bot.send_message(user_id, f"کلمه فیلتر ذخیره شد!\nفیلتر: <code>{filter_word}</code>", parse_mode="HTML", reply_markup=get_auto_file_menu())
    data_store.update_user_state(user_id, "auto_file_menu", {})

def _extract_pending_info_from_message(message):
    """
    Extract a minimal serializable representation of the incoming Telegram message
    that handle_uploader_files needs to resume processing later.
    """
    info = {"content_type": message.content_type}
    if message.content_type == "document" and hasattr(message, "document"):
        info["document"] = {
            "file_id": message.document.file_id,
            "file_name": getattr(message.document, "file_name", None),
            "file_size": getattr(message.document, "file_size", None)
        }
    elif message.content_type == "photo" and hasattr(message, "photo"):
        # store list of file_ids (usually last is highest resolution)
        info["photo"] = [{"file_id": p.file_id} for p in message.photo]
    elif message.content_type == "video" and hasattr(message, "video"):
        info["video"] = {"file_id": message.video.file_id}
    elif message.content_type == "audio" and hasattr(message, "audio"):
        info["audio"] = {"file_id": message.audio.file_id}
    elif message.content_type == "voice" and hasattr(message, "voice"):
        info["voice"] = {"file_id": message.voice.file_id}
    elif message.content_type == "animation" and hasattr(message, "animation"):
        info["animation"] = {"file_id": message.animation.file_id}
    return info


def create_dummy_from_info(info, user_id):
    """
    Rebuild a minimal DummyMessage object from info produced by _extract_pending_info_from_message.
    This allows calling handle_uploader_files again as if the original message arrived.
    """
    class DummyMessage:
        pass

    m = DummyMessage()
    m.from_user = type("U", (), {"id": user_id})
    m.content_type = info.get("content_type", "document")

    if m.content_type == "document" and info.get("document"):
        doc = info["document"]
        m.document = type("D", (), {
            "file_id": doc.get("file_id"),
            "file_name": doc.get("file_name"),
            "file_size": doc.get("file_size", 0)
        })()
    if m.content_type == "photo" and info.get("photo"):
        m.photo = []
        for p in info["photo"]:
            m.photo.append(type("P", (), {"file_id": p.get("file_id")})())
    if m.content_type == "video" and info.get("video"):
        v = info["video"]
        m.video = type("V", (), {"file_id": v.get("file_id")})()
    if m.content_type == "audio" and info.get("audio"):
        a = info["audio"]
        m.audio = type("A", (), {"file_id": a.get("file_id")})()
    if m.content_type == "voice" and info.get("voice"):
        v = info["voice"]
        m.voice = type("VC", (), {"file_id": v.get("file_id")})()
    if m.content_type == "animation" and info.get("animation"):
        an = info["animation"]
        m.animation = type("AN", (), {"file_id": an.get("file_id")})()
    return m


@bot.message_handler(
    func=lambda message: data_store.get_user_state(message.from_user.id)["state"] in [
        "uploader_file_upload", "uploader_delete_file_upload"
    ],
    content_types=['document', 'photo', 'video', 'audio', 'voice', 'animation']
)
def handle_uploader_files(message):
    user_id = message.from_user.id

    opts = getattr(data_store, "auto_exec_options", {})
    user_state = data_store.get_user_state(user_id)
    delete_after = user_state["state"] == "uploader_delete_file_upload"
    file_type = message.content_type

    # If we haven't asked about whitelist for this upload, ask now and store the pending info.
    sdata = (user_state.get("data") or {})
    if not sdata.get("whitelist_confirmed"):
        pending_info = _extract_pending_info_from_message(message)
        # keep the original state so we can return to it after confirmation
        payload = {
            "pending_upload_info": pending_info,
            "original_state": user_state.get("state")
        }
        data_store.update_user_state(user_id, "confirm_whitelist_upload", payload)
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        markup.add(types.KeyboardButton("✅ بله"), types.KeyboardButton("❌ خیر"))
        markup.add(types.KeyboardButton("🔙 بازگشت به اپلودر"))
        bot.send_message(user_id, "آیا می‌خواهید این فایل لیست سفید شود؟\n(اگر لیست سفید شود، فقط اونر/ادمین‌ها یا کاربران اضافه‌شده به لیست سفید فایل قادر به دانلود خواهند بود.)", reply_markup=markup)
        return

    # now sdata contains whitelist decision
    sdata = (data_store.get_user_state(user_id).get("data") or {})

    # ایجاد پیام پیشرفت در ابتدای تابع
    progress_msg = send_progress_message(user_id, "شروع پردازش فایل...", 5)

    # Determine file_id and orig_name for all supported content_types
    file_id = None
    orig_name = None
    if file_type == "document":
        file_id = message.document.file_id
        orig_name = message.document.file_name or f"{int(time.time())}.dat"
    elif file_type == "photo":
        file_id = message.photo[-1].file_id
        orig_name = f"{int(time.time())}.jpg"
    elif file_type == "video":
        file_id = message.video.file_id
        orig_name = f"{int(time.time())}.mp4"
    elif file_type == "audio":
        file_id = message.audio.file_id
        orig_name = f"{int(time.time())}.mp3"
    elif file_type == "voice":
        file_id = message.voice.file_id
        orig_name = f"{int(time.time())}.ogg"
    elif file_type == "animation":
        file_id = message.animation.file_id
        orig_name = f"{int(time.time())}.gif"
    else:
        update_progress_message(progress_msg, "❌ نوع فایل پشتیبانی نمی‌شود.", 100)
        bot.send_message(user_id, "نوع فایل پشتیبانی نمی‌شود.", reply_markup=get_back_menu())
        return

    uploader_channel = data_store.uploader_channels[0] if data_store.uploader_channels else None
    if not uploader_channel:
        update_progress_message(progress_msg, "❌ چنل اپلودری ثبت نشده است.", 100)
        bot.send_message(user_id, "❗️ چنل اپلودری ثبت نشده است.", reply_markup=get_back_menu())
        return

    # helper to prepare file_obj common fields, including whitelist flags
    def _make_base_file_obj(uuid_str, ftype, ch_link, start_link, fname, original_name=None, auto_modified=False, upload_type="normal"):
        obj = {
            "uuid": uuid_str,
            "from_user": user_id,
            "file_type": ftype,
            "date": datetime.now(pytz.timezone('Asia/Tehran')).isoformat(),
            "channel_link": ch_link,
            "start_link": start_link,
            "file_name": fname,
            "upload_type": upload_type,
            "is_whitelist": bool(sdata.get("whitelist", False))
        }
        # always include whitelisted_users as a list for consistency (may be empty)
        if obj["is_whitelist"]:
            obj["whitelisted_users"] = []
        else:
            obj["whitelisted_users"] = []
        if original_name:
            obj["original_name"] = original_name
        if auto_modified:
            obj["auto_modified"] = True
        return obj

    # Only for document: check for rename/filter, otherwise direct send
    if file_type == "document" and not (opts.get("rename") or opts.get("filter")) and not delete_after:
        update_progress_message(progress_msg, "ارسال مستقیم فایل به چنل اپلودری بدون هیچ تغییری...", 10)
        sent_msg = bot.send_document(uploader_channel, file_id, visible_file_name=orig_name)
        update_progress_message(progress_msg, "ارسال به چنل اپلودری انجام شد.", 70)

        BOT_USERNAME = bot.get_me().username
        ch_link = f"https://t.me/{uploader_channel[1:]}/{sent_msg.message_id}"
        priv_link = None
        for k, v in data_store.uploader_file_map.items():
            if v.get("channel_link") == ch_link:
                priv_link = v.get("start_link")
                break
        if not priv_link:
            priv_uuid = str(uuid.uuid4())
            priv_link = f"https://t.me/{BOT_USERNAME}?start=file_{priv_uuid}"
            file_obj = _make_base_file_obj(priv_uuid, "document", ch_link, priv_link, orig_name, upload_type="delete" if delete_after else "normal")
            data_store.uploader_file_map[priv_link] = file_obj
            data_store.uploader_file_map[ch_link] = file_obj
        else:
            data_store.uploader_file_map[ch_link] = data_store.uploader_file_map[priv_link]
        data_store.save_data()
        update_progress_message(progress_msg, "همه چیز تکمیل شد!", 100)
        bot.send_message(user_id, f"✅ فایل آپلود شد!\nلینک خصوصی: {priv_link}", reply_markup=get_uploader_menu())
        data_store.update_user_state(user_id, "uploader_menu", {})
        return

    # If (rename/filter) is set for document or for all other file types or delete_after
    # Download, possibly rename/filter, then send (for documents); for others, just send
    if file_type == "document" and (opts.get("rename") or opts.get("filter")):
        update_progress_message(progress_msg, "شروع دانلود فایل برای تغییرات اتوماتیک...", 15)
        # پردازش تغییرات اتوماتیک برای همه فایل‌ها
        temp_path = f"temp_upload_{user_id}_{int(time.time())}_{orig_name}"
        result = safe_download_file(bot, file_id, temp_path)
        if result is not True:
            update_progress_message(progress_msg, f"❌ خطا در دانلود و تلاش برای دانلود مجدد تا دانلود کامل:\n{result}", 100)
            bot.send_message(user_id, f"❌ خطا در دانلود و تلاش برای دانلود مجدد تا دانلود کامل:\n{result}", reply_markup=get_back_menu())
            return
        update_progress_message(progress_msg, "دانلود فایل انجام شد.", 20)
        with open(temp_path, "rb") as f:
            file_bytes = f.read()

        settings = get_auto_rename_settings(user_id)
        kw = settings.get("keyword", "")
        filter_word = settings.get("filter", "")
        ext = os.path.splitext(orig_name)[-1]
        new_name = orig_name
        if opts.get("filter") and filter_word and filter_word in new_name:
            new_name = new_name.replace(filter_word, "")
        if opts.get("rename") and kw:
            base, ext = os.path.splitext(new_name)
            if ext:
                new_name = f"{base}{kw}{ext}"
            else:
                new_name = f"{base}{kw}"

        new_temp_path = f"temp_upload_{user_id}_{int(time.time())}_{new_name}"
        with open(new_temp_path, "wb") as f:
            f.write(file_bytes)

        update_progress_message(progress_msg, "ارسال فایل تغییر یافته به چنل اپلودری...", 50)
        sent_msg = bot.send_document(uploader_channel, open(new_temp_path, "rb"), visible_file_name=new_name)
        update_progress_message(progress_msg, "ارسال به چنل اپلودری و حذف فایل از هاست...", 70)
        try:
            if os.path.exists(new_temp_path):
                os.remove(new_temp_path)
            if os.path.exists(temp_path):
                os.remove(temp_path)
        except Exception:
            pass

        BOT_USERNAME = bot.get_me().username
        ch_link = f"https://t.me/{uploader_channel[1:]}/{sent_msg.message_id}"
        priv_link = None
        for k, v in data_store.uploader_file_map.items():
            if v.get("channel_link") == ch_link:
                priv_link = v.get("start_link")
                break
        if not priv_link:
            priv_uuid = str(uuid.uuid4())
            priv_link = f"https://t.me/{BOT_USERNAME}?start=file_{priv_uuid}"
            file_obj = _make_base_file_obj(priv_uuid, "document", ch_link, priv_link, new_name, original_name=orig_name, auto_modified=True, upload_type="delete" if delete_after else "normal")
            data_store.uploader_file_map[priv_link] = file_obj
            data_store.uploader_file_map[ch_link] = file_obj
        else:
            data_store.uploader_file_map[ch_link] = data_store.uploader_file_map[priv_link]
            data_store.uploader_file_map[ch_link].update({
                "file_name": new_name,
                "original_name": orig_name,
                "upload_type": "delete" if delete_after else "normal",
                "auto_modified": True,
                "is_whitelist": bool(sdata.get("whitelist", False))
            })
            # ensure whitelisted_users exists
            data_store.uploader_file_map[ch_link].setdefault("whitelisted_users", [])
        data_store.save_data()
        update_progress_message(progress_msg, "همه چیز تکمیل شد!", 100)
        upload_message = f"✅ فایل آپلود شد"
        if delete_after:
            upload_message += " و بعد از 1 دقیقه حذف می‌شود"
        upload_message += f"!\nلینک خصوصی: {priv_link}"
        bot.send_message(user_id, upload_message, reply_markup=get_uploader_menu())
        data_store.update_user_state(user_id, "uploader_menu", {})
        return

    # For all other types and for delete_after mode:
    update_progress_message(progress_msg, "ارسال فایل به چنل اپلودری...", 30)
    send_func = {
        "document": bot.send_document,
        "photo": bot.send_photo,
        "video": bot.send_video,
        "audio": bot.send_audio,
        "voice": bot.send_voice,
        "animation": bot.send_animation
    }[file_type]
    if file_type == "document":
        sent_msg = send_func(uploader_channel, file_id, visible_file_name=orig_name)
    else:
        sent_msg = send_func(uploader_channel, file_id)

    update_progress_message(progress_msg, "ثبت اطلاعات فایل...", 70)
    BOT_USERNAME = bot.get_me().username
    ch_link = f"https://t.me/{uploader_channel[1:]}/{sent_msg.message_id}"
    priv_uuid = str(uuid.uuid4())
    priv_link = f"https://t.me/{BOT_USERNAME}?start=file_{priv_uuid}"
    file_obj = _make_base_file_obj(priv_uuid, file_type, ch_link, priv_link, orig_name, upload_type="delete" if delete_after else "normal")
    data_store.uploader_file_map[priv_link] = file_obj
    data_store.uploader_file_map[ch_link] = file_obj
    data_store.save_data()
    update_progress_message(progress_msg, "همه چیز تکمیل شد!", 100)
    bot.send_message(user_id, f"✅ فایل آپلود شد!\nلینک خصوصی: {priv_link}", reply_markup=get_uploader_menu())
    data_store.update_user_state(user_id, "uploader_menu", {})


@bot.message_handler(func=lambda m: data_store.get_user_state(m.from_user.id)["state"] == "confirm_whitelist_upload")
def handle_confirm_whitelist_upload(message):
    user_id = message.from_user.id
    text = (message.text or "").strip()
    if text == "🔙 بازگشت به اپلودر":
        data_store.update_user_state(user_id, "uploader_menu", {})
        bot.send_message(user_id, "بازگشت به اپلودر.", reply_markup=get_uploader_menu())
        return

    if text not in ("✅ بله", "❌ خیر"):
        bot.send_message(user_id, "لطفا یکی از گزینه‌ها را انتخاب کنید.", reply_markup=get_back_menu())
        return

    confirmed = True if text == "✅ بله" else False
    state = data_store.get_user_state(user_id)
    sdata = state.get("data", {}) or {}
    sdata["whitelist"] = confirmed
    sdata["whitelist_confirmed"] = True

    # restore original state and attach sdata
    original = state.get("original_state", "uploader_file_upload")
    data_store.update_user_state(user_id, original, sdata)

    # Rebuild a DummyMessage from pending_upload_info and continue processing
    pending = sdata.get("pending_upload_info", {})
    msg_obj = create_dummy_from_info(pending, user_id)
    # Call the same handler to continue the upload flow
    handle_uploader_files(msg_obj)
# == هندلر اپلود فایل، پایان اپلود، بازگشت ==
@bot.message_handler(func=lambda message: data_store.get_user_state(message.from_user.id)["state"] == "uploader_menu" and message.text == "⬆️ اپلود فایل")
def start_uploader_file_upload(message):
    user_id = message.from_user.id
    data_store.update_user_state(user_id, "uploader_file_upload", {"uploaded_files": []})
    bot.send_message(user_id, "فایل(ها) را بفرستید. پس از اتمام، دکمه 'پایان اپلود' را بزنید.", reply_markup=get_uploader_finish_menu())

@bot.message_handler(func=lambda message: data_store.get_user_state(message.from_user.id)["state"] == "uploader_file_upload" and message.text == "✅ پایان اپلود")
def finish_uploader_file_upload(message):
    user_id = message.from_user.id
    user_state = data_store.get_user_state(user_id)
    uploaded_files = user_state["data"].get("uploaded_files", [])
    if not uploaded_files:
        bot.send_message(user_id, "❗️هیچ فایلی ارسال نشد. ابتدا فایل ارسال کنید.", reply_markup=get_uploader_finish_menu())
        return
    # ذخیره و اپلود فایل‌ها (کد دلخواه خودت اینجا)
    bot.send_message(user_id, f"✅ اپلود تمام شد! ({len(uploaded_files)} فایل دریافت شد.)", reply_markup=get_uploader_menu())
    
    data_store.update_user_state(user_id, "uploader_menu", {})

@bot.message_handler(func=lambda message: data_store.get_user_state(message.from_user.id)["state"] == "uploader_file_upload" and message.text == "🔙 بازگشت به اپلودر")
def back_to_uploader_menu(message):
    user_id = message.from_user.id
    data_store.update_user_state(user_id, "uploader_menu", {})
    bot.send_message(user_id, "📤 اپلودر:\nیکی از گزینه‌های زیر را انتخاب کنید.", reply_markup=get_uploader_menu())
    
def safe_download_file(bot, file_id, filename, chunk_size=1024*1024, original_name=None):
    try:
        file_info = bot.get_file(file_id)
        url = f"https://api.telegram.org/file/bot{bot.token}/{file_info.file_path}"
        r = requests.get(url, stream=True, timeout=10**6)
        if r.status_code == 200:
            with open(filename, "wb") as f:
                for chunk in r.iter_content(chunk_size=chunk_size):
                    if chunk:
                        f.write(chunk)
            if original_name and hasattr(data_store, 'uploader_auto_rename'):
                # ذخیره نام اصلی برای فایل‌های دیلیت
                user_settings = data_store.uploader_auto_rename.get(str(user_id), {})
                user_settings['original_name'] = original_name
                data_store.uploader_auto_rename[str(user_id)] = user_settings
                data_store.save_data()
            return True
        return f"خطا در دانلود: HTTP {r.status_code}"
    except Exception as e:
        return f"خطا در دانلود: {e}"

@bot.message_handler(content_types=['document'], func=lambda m: data_store.get_user_state(m.from_user.id)["state"] == "change_thumbnail_wait_for_file")
def handle_change_thumbnail_file(message):
    user_id = message.from_user.id
    doc = message.document
    file_id = doc.file_id
    file_name = doc.file_name.lower() if doc.file_name else ""
    file_size = doc.file_size if hasattr(doc, 'file_size') else 0

    # فقط PDF قابل قبول است
    if not file_name.endswith('.pdf'):
        bot.send_message(user_id, "❌ فقط فایل PDF قابل قبول است.", reply_markup=get_back_menu())
        return
    if file_size > 50 * 1024 * 1024:
        bot.send_message(user_id, "❌ حجم فایل خیلی زیاد است! لطفاً PDF کمتر از 50MB بفرست.", reply_markup=get_back_menu())
        return

    # ذخیره وضعیت برای مرحله بعد (عکس تامنیل)
    data_store.update_user_state(user_id, "change_thumbnail_wait_for_photo", {
        "pdf_file_id": file_id,
        "pdf_file_name": file_name,
        "pdf_file_size": file_size
    })
    bot.send_message(
        user_id,
        "📸 حالا عکس تامنیل رو بفرست (PNG یا JPG، حداکثر 320x320، حجم ≤ 200KB).\nبهتره به صورت document بفرستی تا کیفیت حفظ شه.",
        reply_markup=get_back_menu()
    )

@bot.message_handler(content_types=['document', 'photo'], func=lambda m: data_store.get_user_state(m.from_user.id)["state"] == "change_thumbnail_wait_for_photo")
def handle_change_thumbnail_photo(message):
    user_id = message.from_user.id
    state = data_store.get_user_state(user_id)["data"]
    pdf_file_id = state.get("pdf_file_id")
    pdf_file_name = state.get("pdf_file_name", "input.pdf")
    progress_msg = send_progress_message(user_id, "در حال دریافت فایل‌ها...", 5)

    # تشخیص عکس
    if message.content_type == "photo":
        thumb_file_id = message.photo[-1].file_id
        thumb_file_name = f"thumb_{user_id}_{int(time.time())}.jpg"
    elif message.content_type == "document":
        doc = message.document
        thumb_file_id = doc.file_id
        thumb_file_name = doc.file_name or f"thumb_{user_id}_{int(time.time())}.jpg"
        if not (thumb_file_name.lower().endswith(".jpg") or thumb_file_name.lower().endswith(".jpeg") or thumb_file_name.lower().endswith(".png")):
            update_progress_message(progress_msg, "❌ فقط عکس PNG یا JPG برای تامنیل قابل قبول است.", 100)
            bot.send_message(user_id, "❌ فقط عکس PNG/JPG برای تامنیل قابل قبول است.", reply_markup=get_uploader_menu())
            return
    else:
        update_progress_message(progress_msg, "❌ فقط عکس PNG/JPG قابل قبول است.", 100)
        bot.send_message(user_id, "❌ فقط عکس PNG/JPG قابل قبول است.", reply_markup=get_uploader_menu())
        return

    temp_pdf = f"temp_{user_id}_{int(time.time())}.pdf"
    temp_thumb = f"temp_{user_id}_{int(time.time())}.jpg"
    output_pdf = f"thumbed_{user_id}_{int(time.time())}.pdf"

    # دانلود PDF و عکس
    result_pdf = safe_download_file(bot, pdf_file_id, temp_pdf)
    if result_pdf is not True:
        update_progress_message(progress_msg, "❌ دانلود PDF ناموفق بود.", 100)
        bot.send_message(user_id, "❌ دانلود فایل PDF ناموفق بود.", reply_markup=get_uploader_menu())
        return
    update_progress_message(progress_msg, "دانلود PDF انجام شد.", 20)

    result_thumb = safe_download_file(bot, thumb_file_id, temp_thumb)
    if result_thumb is not True:
        update_progress_message(progress_msg, "❌ دانلود عکس تامنیل ناموفق بود.", 100)
        bot.send_message(user_id, "❌ دانلود عکس تامنیل ناموفق بود.", reply_markup=get_uploader_menu())
        try: os.remove(temp_pdf)
        except: pass
        return
    update_progress_message(progress_msg, "دانلود عکس انجام شد.", 40)

    # بررسی و بهینه‌سازی عکس تامنیل
    try:
        img = Image.open(temp_thumb)
        if img.mode != "RGB":
            img = img.convert("RGB")
        # ابعاد و حجم
        max_dim = 320
        max_size = 200*1024
        if img.size[0] > max_dim or img.size[1] > max_dim:
            img.thumbnail((max_dim, max_dim), Image.LANCZOS)
        img_bytes = io.BytesIO()
        img.save(img_bytes, format="JPEG", quality=85)
        img_bytes.seek(0)
        quality = 85
        while img_bytes.getbuffer().nbytes > max_size and quality > 20:
            img_bytes = io.BytesIO()
            img.save(img_bytes, format="JPEG", quality=quality)
            img_bytes.seek(0)
            quality -= 15
        if img_bytes.getbuffer().nbytes > max_size:
            raise ValueError("حجم عکس پس از بهینه‌سازی هنوز زیاد است.")
        with open(temp_thumb, "wb") as f:
            f.write(img_bytes.read())
        update_progress_message(progress_msg, "عکس تامنیل بهینه شد.", 60)
    except Exception as ex:
        update_progress_message(progress_msg, "❌ عکس ناسازگار یا خراب است.", 100)
        bot.send_message(
            user_id,
            "❌ عکس تامنیل ویژگی‌های لازم را ندارد یا خراب است.\nویژگی‌های مناسب:\n- فرمت JPG یا PNG\n- ابعاد ≤ 320x320\n- حجم ≤ 200KB",
            reply_markup=get_uploader_menu()
        )
        try: os.remove(temp_pdf)
        except: pass
        try: os.remove(temp_thumb)
        except: pass
        return

    # افزودن تامنیل به PDF و ارسال صحیح به تلگرام
    try:
        pdf_reader = PdfReader(temp_pdf)
        pdf_writer = PdfWriter()
        for page in pdf_reader.pages:
            pdf_writer.add_page(page)
        with open(output_pdf, "wb") as out_f:
            pdf_writer.write(out_f)
        update_progress_message(progress_msg, "PDF جدید آماده شد.", 90)
        # ارسال PDF با تامنیل به صورت thumbnail واقعی تلگرام
        with open(output_pdf, "rb") as file_f, open(temp_thumb, "rb") as thumb_f:
            bot.send_document(
                user_id,
                file_f,
                caption="📎 PDF با تامنیل جدید!",
                visible_file_name=os.path.basename(output_pdf),
                thumb=thumb_f,
                reply_markup=get_uploader_menu()
            )
        update_progress_message(progress_msg, "✅ PDF با تامنیل جدید ارسال شد.", 100)
    except Exception as ex:
        tb = traceback.format_exc()
        update_progress_message(progress_msg, "❌ خطا در ساخت یا ارسال PDF.", 100)
        bot.send_message(user_id, f"❌ خطا در ساخت PDF یا افزودن تامنیل.\n{ex}\n{tb}", reply_markup=get_uploader_menu())
    finally:
        # حذف همه فایل‌های موقت
        for f in [temp_pdf, temp_thumb, output_pdf]:
            try: os.remove(f)
            except: pass
    data_store.update_user_state(user_id, "uploader_menu", {})
    
# == ویرایش فایل ==
@bot.message_handler(func=lambda message: data_store.get_user_state(message.from_user.id)["state"] == "uploader_menu" and message.text == "🛠️ ویرایش فایل")
def handle_edit_file_entry(message):
    user_id = message.from_user.id
    data_store.update_user_state(user_id, "edit_file_menu")
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(types.KeyboardButton("✏️ ویرایش فایل"), types.KeyboardButton("🔗 ویرایش لینک"))
    markup.add(types.KeyboardButton("🔙 بازگشت به اپلودر"))
    bot.send_message(user_id, "یکی از گزینه‌ها را انتخاب کنید:", reply_markup=markup)

@bot.message_handler(content_types=['document', 'photo', 'video'], func=lambda message: data_store.get_user_state(message.from_user.id)["state"] == "edit_file_wait_for_new_file")
def handle_edit_file_upload_new(message):
    user_id = message.from_user.id
    user_state = data_store.get_user_state(user_id)
    file_link = user_state["data"].get("editing_file_link")
    progress_msg = send_progress_message(user_id, "در حال ویرایش فایل...", 10)
    old_info = data_store.uploader_file_map.get(file_link)
    # حذف پیام قبلی از چنل اپلودری
    if old_info and "channel_link" in old_info:
        ch_link = old_info["channel_link"]
        try:
            channel_username = ch_link.split("/")[3]
            msg_id = int(ch_link.split("/")[4])
            bot.delete_message(f"@{channel_username}", msg_id)
        except Exception:
            pass

    uploader_channel = data_store.uploader_channels[0] if data_store.uploader_channels else None
    if not uploader_channel:
        update_progress_message(progress_msg, "❗️چنل اپلودری ثبت نشده.", 100)
        bot.send_message(user_id, "❗️چنل اپلودری ثبت نشده.", reply_markup=get_uploader_menu())
        return

    settings = get_auto_rename_settings(user_id)
    kw = settings.get("keyword", "")
    filter_word = settings.get("filter", "")

    file_name, sent_message = None, None

    if message.content_type == "document":
        orig_name = message.document.file_name or f"{int(time.time())}.dat"
        new_name = orig_name
        if filter_word and filter_word in new_name:
            new_name = new_name.replace(filter_word, "")
        if kw:
            base, ext = os.path.splitext(new_name)
            if ext:
                new_name = f"{base}{kw}{ext}"
            else:
                new_name = f"{base}{kw}"
        file_id = message.document.file_id
        update_progress_message(progress_msg, "در حال ارسال فایل جدید...", 40)
        sent_message = bot.send_document(uploader_channel, file_id, visible_file_name=new_name)
        file_name = new_name
    elif message.content_type == "photo":
        file_id = message.photo[-1].file_id
        update_progress_message(progress_msg, "در حال ارسال عکس جدید...", 40)
        sent_message = bot.send_photo(uploader_channel, file_id)
        file_name = "photo.jpg"
    elif message.content_type == "video":
        file_id = message.video.file_id
        update_progress_message(progress_msg, "در حال ارسال ویدیو جدید...", 40)
        sent_message = send_func(uploader_channel, file_id)
        file_name = "video.mp4"
        # Only for delete after mode
        if delete_after:
            ch_link = f"https://t.me/{uploader_channel[1:]}/{sent_message.message_id}"
            priv_uuid = str(uuid.uuid4())
            priv_link = f"https://t.me/{BOT_USERNAME}?start=file_{priv_uuid}"
            file_obj = {
                "uuid": priv_uuid,
                "from_user": user_id,
                "file_type": file_type,
                "date": datetime.now(pytz.timezone('Asia/Tehran')).isoformat(),
                "channel_link": ch_link,
                "start_link": priv_link,
                "file_name": new_name if (opts.get("rename") or opts.get("filter")) else orig_name,
                "original_name": orig_name,
                "upload_type": "delete",
                "auto_modified": (opts.get("rename") or opts.get("filter"))
            }
            data_store.uploader_file_map[priv_link] = file_obj
            data_store.uploader_file_map[ch_link] = file_obj
            data_store.save_data()
            bot.send_message(user_id, f"✅ فایل آپلود شد و بعد از 1 دقیقه حذف می‌شود!\nلینک خصوصی: {priv_link}", reply_markup=get_uploader_menu())
            data_store.update_user_state(user_id, "uploader_menu", {})
            return
    else:
        update_progress_message(progress_msg, "نوع فایل پشتیبانی نمی‌شود.", 100)
        bot.send_message(user_id, "نوع فایل پشتیبانی نمی‌شود.", reply_markup=get_back_menu())
        return

    ch_link = f"https://t.me/{uploader_channel[1:]}/{sent_message.message_id}"
    if old_info:
        old_info.update({
            "file_type": message.content_type,
            "date": datetime.now(pytz.timezone('Asia/Tehran')).isoformat(),
            "channel_link": ch_link,
            "file_name": file_name
        })
        data_store.uploader_file_map[file_link] = old_info
        data_store.uploader_file_map[ch_link] = old_info
    else:
        BOT_USERNAME = bot.get_me().username
        priv_uuid = str(uuid.uuid4())
        priv_link = f"https://t.me/{BOT_USERNAME}?start=file_{priv_uuid}"
        info = {
            "uuid": priv_uuid,
            "from_user": user_id,
            "file_type": message.content_type,
            "date": datetime.now(pytz.timezone('Asia/Tehran')).isoformat(),
            "channel_link": ch_link,
            "start_link": priv_link,
            "file_name": file_name
        }
        data_store.uploader_file_map[priv_link] = info
        data_store.uploader_file_map[ch_link] = info
        file_link = priv_link

    data_store.save_data()
    update_progress_message(progress_msg, "فایل جدید ثبت شد!", 100)
    bot.send_message(user_id, f"فایل جدید ثبت شد!\nلینک خصوصی: {file_link}", reply_markup=get_uploader_menu())
    data_store.update_user_state(user_id, "uploader_menu", {})
    
@bot.message_handler(func=lambda m: data_store.get_user_state(m.from_user.id)["state"] == "uploader_menu" and m.text == "🖼 تغییر تامنیل فایل")
def handle_change_thumbnail_entry(message):
    user_id = message.from_user.id
    data_store.update_user_state(user_id, "change_thumbnail_wait_for_file")
    bot.send_message(user_id, "فایل پی دی اف مورد نظر را بفرست!", reply_markup=get_back_menu())
    
@bot.message_handler(func=lambda message: data_store.get_user_state(message.from_user.id)["state"] == "edit_file_menu")
def handle_edit_file_choice(message):
    user_id = message.from_user.id
    if message.text == "✏️ ویرایش فایل":
        data_store.update_user_state(user_id, "edit_file_wait_for_id")
        bot.send_message(user_id, "لینک فایل مورد نظر را بفرستید:", reply_markup=get_back_to_uploader_menu())
    elif message.text == "🔗 ویرایش لینک":
        data_store.update_user_state(user_id, "edit_link_wait_for_id")
        bot.send_message(user_id, "لینک فایل مورد نظر را بفرستید:", reply_markup=get_back_to_uploader_menu())

def handle_back_to_uploader_from_edit(message):
    user_id = message.from_user.id
    if message.text.strip() == "🔙 بازگشت به اپلودر":
        data_store.update_user_state(user_id, "uploader_menu")
        bot.send_message(user_id, "📤 اپلودر:\nیکی از گزینه‌های زیر را انتخاب کنید.", reply_markup=get_uploader_menu())
        return True
    return False

@bot.message_handler(func=lambda message: data_store.get_user_state(message.from_user.id)["state"] == "edit_file_wait_for_id")
def handle_edit_file_wait_for_id(message):
    if handle_back_to_uploader_from_edit(message): return
    user_id = message.from_user.id
    file_link = message.text.strip()
    if file_link not in data_store.uploader_file_map:
        bot.send_message(user_id, "لینک معتبر نیست یا پیدا نشد.", reply_markup=get_back_menu())
        return
    data_store.update_user_state(user_id, "edit_file_wait_for_new_file", {"editing_file_link": file_link})
    bot.send_message(user_id, "فایل جدید را بفرستید:", reply_markup=get_back_menu())

@bot.message_handler(func=lambda message: data_store.get_user_state(message.from_user.id)["state"] == "edit_link_wait_for_id")
def handle_edit_link_wait_for_id(message):
    if handle_back_to_uploader_from_edit(message): return
    user_id = message.from_user.id
    file_link = message.text.strip()
    progress_msg = send_progress_message(user_id, "در حال ساخت لینک جدید...", 20)
    if file_link not in data_store.uploader_file_map:
        update_progress_message(progress_msg, "لینک معتبر نیست یا پیدا نشد.", 100)
        bot.send_message(user_id, "لینک معتبر نیست یا پیدا نشد.", reply_markup=get_back_menu())
        return

    old_info = data_store.uploader_file_map[file_link]
    # فقط کلید start_link قبلی را حذف کن، channel_link را دست نزن
    del data_store.uploader_file_map[file_link]
    BOT_USERNAME = bot.get_me().username
    priv_uuid = str(uuid.uuid4())
    priv_link = f"https://t.me/{BOT_USERNAME}?start=file_{priv_uuid}"
    old_info["uuid"] = priv_uuid
    old_info["start_link"] = priv_link
    data_store.uploader_file_map[priv_link] = old_info
    # channel_link بدون تغییر باقی بماند و به همین old_info اشاره کند
    data_store.save_data()
    update_progress_message(progress_msg, "لینک خصوصی جدید ساخته شد!", 100)
    bot.send_message(user_id, f"لینک خصوصی جدید ساخته شد!\n{priv_link}", reply_markup=get_uploader_menu())
    data_store.update_user_state(user_id, "uploader_menu", {})

@bot.message_handler(func=lambda m: data_store.get_user_state(m.from_user.id)["state"] == "set_auto_rename_keyword")
def handle_set_auto_rename_keyword(message):
    user_id = message.from_user.id
    keyword = message.text.strip()
    if not keyword:
        bot.send_message(user_id, "❗️ کلمه نباید خالی باشد.", reply_markup=get_back_menu())
        return
    set_auto_rename_settings(user_id, keyword, "")
    bot.send_message(user_id, f"✨ کلمه جدید ذخیره شد و به نام همه فایل‌های آپلودی اضافه می‌شود.", reply_markup=get_uploader_menu())
    data_store.update_user_state(user_id, "uploader_menu", {})

@bot.message_handler(func=lambda m: m.text == "🔙 بازگشت به اپلودر")
def back_to_uploader(message):
    user_id = message.from_user.id
    data_store.update_user_state(user_id, "uploader_menu", {})
    bot.send_message(user_id, "📤 اپلودر:\nیکی از گزینه‌های زیر را انتخاب کنید.", reply_markup=get_uploader_menu())

@bot.message_handler(func=lambda m: data_store.get_user_state(m.from_user.id)["state"] == "auto_file_menu")
def handle_auto_file_menu(message):
    user_id = message.from_user.id
    text = message.text
    if text == "🆕 کلمه جدید":
        data_store.update_user_state(user_id, "auto_rename_set_keyword")
        bot.send_message(user_id, "کلمه‌ای که به اسم فایل اضافه شود را وارد کن:", reply_markup=get_back_menu())
    elif text == "🧹 فیلتر کلمه":
        data_store.update_user_state(user_id, "auto_rename_set_filter")
        bot.send_message(user_id, "کلمه‌ای که از اسم حذف شود (فیلتر):", reply_markup=get_back_menu())
    elif text == "📃 لیست کلمات جدید":
        settings = get_auto_rename_settings(user_id)
        kw = settings.get("keyword", "")
        bot.send_message(user_id, f"کلمه جدید فعلی:\n<code>{kw}</code>", parse_mode="HTML", reply_markup=get_auto_file_menu())
    elif text == "📃 لیست کلمات فیلتر":
        settings = get_auto_rename_settings(user_id)
        filter_word = settings.get("filter", "")
        bot.send_message(user_id, f"کلمه فیلتر فعلی:\n<code>{filter_word}</code>", parse_mode="HTML", reply_markup=get_auto_file_menu())
    elif text == "⚙️ تنظیمات اجرایی":
        data_store.update_user_state(user_id, "exec_options_menu")
        bot.send_message(user_id, "تنظیمات اجرایی قابلیت‌های تغییر اتوماتیک:", reply_markup=get_exec_options_menu())
    elif text == "🔙 بازگشت به تنظیمات ربات":
        data_store.update_user_state(user_id, "settings_menu")
        bot.send_message(user_id, "🏛 تنظیمات ربات:", reply_markup=get_settings_menu(user_id))
        
#======================هلندر های ارسال همگانی======================≠=
@bot.message_handler(func=lambda message: data_store.get_user_state(message.from_user.id)["state"] == "broadcast_choose_mode")
def handle_broadcast_choose_mode(message):
    user_id = message.from_user.id
    if message.text == "🗨️ ارسال با نقل قول":
        data_store.update_user_state(user_id, "broadcast_wait_for_message", {"broadcast_mode": "quote"})
        bot.send_message(user_id, "پیام خود را به همراه مدیا ارسال کنید (یا فوروارد کنید).", reply_markup=get_back_menu())
    elif message.text == "✉️ ارسال بدون نقل قول":
        data_store.update_user_state(user_id, "broadcast_wait_for_message", {"broadcast_mode": "noquote"})
        bot.send_message(user_id, "پیام خود را به همراه مدیا ارسال کنید (یا فوروارد کنید).", reply_markup=get_back_menu())
    elif message.text == "🔙 بازگشت به منوی اصلی":
        data_store.reset_user_state(user_id)
        bot.send_message(user_id, "🏠 بازگشت به منوی اصلی:", reply_markup=get_main_menu(user_id))
    else:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        markup.add(types.KeyboardButton("🗨️ ارسال با نقل قول"), types.KeyboardButton("✉️ ارسال بدون نقل قول"))
        markup.add(types.KeyboardButton("🔙 بازگشت به منوی اصلی"))
        bot.send_message(user_id, "یکی از گزینه‌های زیر را انتخاب کنید:", reply_markup=markup)
        
@bot.message_handler(func=lambda message: data_store.get_user_state(message.from_user.id)["state"] == "broadcast_wait_for_message", content_types=['text', 'photo', 'video', 'document', 'audio', 'voice', 'sticker', 'animation'])
def handle_broadcast_get_msg(message):
    user_id = message.from_user.id
    user_state = data_store.get_user_state(user_id)
    user_state["data"]["broadcast_message"] = message
    data_store.update_user_state(user_id, "broadcast_timer_or_instant", user_state["data"])
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("⏰ ارسال تایمردار"), types.KeyboardButton("🚀 ارسال فوری"))
    markup.add(types.KeyboardButton("🔙 بازگشت به منوی اصلی"))
    if message.content_type == "text":
        bot.send_message(user_id, "پیام دریافت شد. ارسال به صورت فوری باشد یا تایمردار؟", reply_markup=markup)
    else:
        bot.send_message(user_id, "پیام مدیای شما دریافت شد. ارسال به صورت فوری باشد یا تایمردار؟", reply_markup=markup)

def send_broadcast_instant(requester_id, msg, mode):
    users = list(data_store.broadcast_users)
    if requester_id not in users:
        users.append(requester_id)
    active_users = []
    maram_users = []
    total = len(users)
    sent = 0
    progress_msg = bot.send_message(requester_id, "شروع ارسال... 0%")
    for i, uid in enumerate(users):
        success = False
        try:
            if mode == "quote":
                bot.forward_message(uid, msg.chat.id, msg.message_id)
                success = True
            else:
                # حذف دکمه شیشه‌ای "قابلیت‌های جدید" از ارسال همگانی
                if msg.content_type == "text":
                    bot.send_message(uid, msg.text)  # فقط متن ساده بدون دکمه
                    success = True
                elif msg.content_type == "photo":
                    bot.send_photo(uid, msg.photo[-1].file_id, caption=msg.caption)
                    success = True
                elif msg.content_type == "video":
                    bot.send_video(uid, msg.video.file_id, caption=msg.caption)
                    success = True
                elif msg.content_type == "document":
                    bot.send_document(uid, msg.document.file_id, caption=msg.caption)
                    success = True
                elif msg.content_type == "audio":
                    bot.send_audio(uid, msg.audio.file_id, caption=msg.caption)
                    success = True
                elif msg.content_type == "voice":
                    bot.send_voice(uid, msg.voice.file_id)
                    success = True
                elif msg.content_type == "animation":
                    bot.send_animation(uid, msg.animation.file_id, caption=msg.caption)
                    success = True
                elif msg.content_type == "sticker":
                    bot.send_sticker(uid, msg.sticker.file_id)
                    success = True
                else:
                    bot.send_message(uid, "❗️ پیام متنی یا مدیا پشتیبانی نمی‌شود.")
            sent += 1
            if success:
                active_users.append(uid)
                data_store.user_data[str(uid)]["is_active"] = True
            else:
                data_store.user_data[str(uid)]["is_active"] = False
        except Exception:
            data_store.user_data[str(uid)]["is_active"] = False
        percent = math.ceil(sent * 100 / total)
        if sent == total or sent % max(1, total // 20) == 0:
            try:
                bot.edit_message_text(f"ارسال درحال انجام ... {percent}%", requester_id, progress_msg.message_id)
            except Exception:
                pass
        time.sleep(0.5)
    data_store.save_data()
    try:
        bot.edit_message_text("✅ ارسال به همه کاربران تکمیل شد!", requester_id, progress_msg.message_id)
    except Exception:
        pass
def send_scheduled_broadcast(job_id):
    broadcasts_file = os.path.join('jsons', 'scheduled_broadcasts.json')
    if not os.path.exists(broadcasts_file):
        return
    try:
        with open(broadcasts_file, 'r', encoding='utf-8') as f:
            broadcasts = json.load(f)
        for bc in broadcasts:
            if bc["job_id"] == job_id:
                users = list(data_store.broadcast_users)  # بدون set یا محدودیت!
                logging.info(f"لیست کاربران برای ارسال همگانی تایمردار: {users}")
                if bc["broadcast_mode"] == "quote":
                    for uid in users:
                        try:
                            logging.info(f"در حال ارسال تایمردار با نقل قول به کاربر: {uid}")
                            bot.forward_message(uid, bc["uploader_channel"], bc["uploader_message_id"])
                        except Exception as e:
                            logging.error(f"خطا در ارسال تایمردار برای کاربر {uid}: {e}")
                    try:
                        bot.delete_message(bc["uploader_channel"], bc["uploader_message_id"])
                    except Exception:
                        pass
                else:
                    for uid in users:
                        try:
                            logging.info(f"در حال ارسال تایمردار بدون نقل قول به کاربر: {uid}")
                            bot.copy_message(uid, bc["uploader_channel"], bc["uploader_message_id"])
                        except Exception as e:
                            logging.error(f"خطا در ارسال تایمردار برای کاربر {uid}: {e}")
                    try:
                        bot.delete_message(bc["uploader_channel"], bc["uploader_message_id"])
                    except Exception:
                        pass
                broadcasts = [b for b in broadcasts if b["job_id"] != job_id]
                with open(broadcasts_file, 'w', encoding='utf-8') as f:
                    json.dump(broadcasts, f, ensure_ascii=False, indent=4)
                break
    except Exception as e:
        logger.error(f"خطا در ارسال scheduled broadcast: {e}")

@bot.message_handler(func=lambda message: data_store.get_user_state(message.from_user.id)["state"] == "broadcast_wait_for_timer")
def handle_broadcast_wait_for_timer(message):
    user_id = message.from_user.id
    user_state = data_store.get_user_state(user_id)
    try:
        time_str = message.text.strip()
        tehran_tz = pytz.timezone('Asia/Tehran')
        scheduled_time = tehran_tz.localize(datetime.strptime(time_str, "%Y/%m/%d %H:%M"))
        now = datetime.now(tehran_tz)
        min_time = now + timedelta(minutes=5)
        example_time = (now + timedelta(minutes=5)).strftime("%Y/%m/%d %H:%M")
        if scheduled_time < min_time:
            bot.send_message(
                user_id,
                f"❗️ زمان باید متعلق به آینده باشد!\nباید در قالب yyyy/mm/dd hh:mm باشد.\nمثال:\n<code>{example_time}</code>",
                reply_markup=get_back_menu(),
                parse_mode="HTML"
            )
            return

        broadcast_mode = user_state["data"].get("broadcast_mode")
        broadcast_msg = user_state["data"].get("broadcast_message")
        if not data_store.uploader_channels:
            data_store.uploader_channels = []
        uploader_channel = None
        if data_store.uploader_channels:
            uploader_channel = data_store.uploader_channels[0]
        if not uploader_channel:
            bot.send_message(user_id, "❗️ چنل اپلودری ثبت نشده است.", reply_markup=get_back_menu())
            return

        # ارسال پیام به چنل اپلودر و گرفتن پیام ذخیره شده
        if broadcast_mode == "quote":
            sent_message = bot.forward_message(uploader_channel, broadcast_msg.chat.id, broadcast_msg.message_id)
        else:  # noquote
            if broadcast_msg.content_type == "text":
                sent_message = bot.send_message(uploader_channel, broadcast_msg.text)
            elif broadcast_msg.content_type == "photo":
                sent_message = bot.send_photo(uploader_channel, broadcast_msg.photo[-1].file_id, caption=broadcast_msg.caption)
            elif broadcast_msg.content_type == "video":
                sent_message = bot.send_video(uploader_channel, broadcast_msg.video.file_id, caption=broadcast_msg.caption)
            elif broadcast_msg.content_type == "document":
                sent_message = bot.send_document(uploader_channel, broadcast_msg.document.file_id, caption=broadcast_msg.caption)
            elif broadcast_msg.content_type == "audio":
                sent_message = bot.send_audio(uploader_channel, broadcast_msg.audio.file_id, caption=broadcast_msg.caption)
            elif broadcast_msg.content_type == "voice":
                sent_message = bot.send_voice(uploader_channel, broadcast_msg.voice.file_id)
            elif broadcast_msg.content_type == "animation":
                sent_message = bot.send_animation(uploader_channel, broadcast_msg.animation.file_id, caption=broadcast_msg.caption)
            elif broadcast_msg.content_type == "sticker":
                sent_message = bot.send_sticker(uploader_channel, broadcast_msg.sticker.file_id)
            else:
                sent_message = bot.send_message(uploader_channel, "❗️ پیام متنی یا مدیا پشتیبانی نمی‌شود.")

        # ذخیره شناسه و لینک پیام اپلودر
        post_uuid = str(uuid.uuid4())
        ch_link = f"https://t.me/{uploader_channel[1:]}/{sent_message.message_id}"
        data_store.scheduled_broadcasts.append({
            "job_id": post_uuid,
            "requester_id": user_id,
            "time": time_str,
            "broadcast_mode": broadcast_mode,
            "uploader_channel": uploader_channel,
            "uploader_message_id": sent_message.message_id,
            "uploader_link": ch_link,
            "content_type": broadcast_msg.content_type
        })
        data_store.save_data()
        schedule.every().day.at(scheduled_time.strftime("%H:%M")).do(send_scheduled_broadcast, job_id=post_uuid).tag(post_uuid)
        bot.send_message(user_id, f"✅ پیام شما برای ارسال همگانی در زمان {time_str} ذخیره شد.", reply_markup=get_main_menu(user_id))
        data_store.reset_user_state(user_id)
    except Exception as e:
        tehran_tz = pytz.timezone('Asia/Tehran')
        now = datetime.now(tehran_tz)
        example = (now + timedelta(minutes=5)).strftime("%Y/%m/%d %H:%M")
        bot.send_message(
            user_id,
            f"❗️ فرمت زمان اشتباه است!\n باید از زمان اینده باشد \n باید در قالب yyyy/mm/dd hh:mm باشد.\nمثال:\n<code>{example}</code>",
            reply_markup=get_back_menu(),
            parse_mode="HTML"
        )
        
@bot.message_handler(func=lambda m: data_store.get_user_state(m.from_user.id)["state"] == "uploader_menu" and m.text == "🔤 تغییر اسم فایل")
def handle_rename_file_entry(message):
    user_id = message.from_user.id
    data_store.update_user_state(user_id, "rename_file_wait_for_file")
    bot.send_message(
        user_id,
        "📤 لطفاً فایلی که می‌خواهید نام آن را تغییر دهید ارسال کنید:",
        reply_markup=get_back_menu()
    )

@bot.message_handler(content_types=['document'], func=lambda m: data_store.get_user_state(m.from_user.id)["state"] == "rename_file_wait_for_file")
def handle_rename_file_get_file(message):
    user_id = message.from_user.id
    file_id = message.document.file_id
    original_name = message.document.file_name or "file.bin"
    
    # ذخیره اطلاعات موقت
    data_store.update_user_state(user_id, "rename_file_wait_for_name", {
        "file_id": file_id,
        "original_name": original_name
    })
    
    bot.send_message(
        user_id,
        f"📝 نام فعلی فایل: <code>{original_name}</code>\n"
        "لطفاً نام جدید فایل را بدون پسوند وارد کنید:",
        parse_mode="HTML",
        reply_markup=get_back_menu()
    )

# کاراکترهای غیرمجاز در نام فایل
INVALID_FILENAME_CHARS = r'[<>:"/\\|?*\x00-\x1f]'
MAX_FILENAME_LENGTH = 200
MAX_FILE_SIZE_MB = 45  # محدودیت تلگرام ۵۰ مگ است، ۴۵ برای اطمینان

def validate_filename(filename):
    """اعتبارسنجی نام فایل"""
    if not filename or not filename.strip():
        return False, "نام فایل نمی‌تواند خالی باشد"
    
    filename = filename.strip()
    
    # بررسی طول نام فایل
    if len(filename) > MAX_FILENAME_LENGTH:
        return False, f"نام فایل نباید بیشتر از {MAX_FILENAME_LENGTH} کاراکتر باشد"
    
    # بررسی کاراکترهای غیرمجاز
    if re.search(INVALID_FILENAME_CHARS, filename):
        return False, "نام فایل حاوی کاراکترهای غیرمجاز است"
    
    # بررسی نام‌های رزرو شده (Windows)
    reserved_names = ['CON', 'PRN', 'AUX', 'NUL', 'COM1', 'COM2', 'COM3', 'COM4', 
                     'COM5', 'COM6', 'COM7', 'COM8', 'COM9', 'LPT1', 'LPT2', 'LPT3', 
                     'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9']
    
    name_without_ext = os.path.splitext(filename)[0].upper()
    if name_without_ext in reserved_names:
        return False, "این نام فایل رزرو شده است"
    
    return True, "نام فایل معتبر است"

def get_safe_temp_path(user_id, filename):
    """ایجاد مسیر امن برای فایل موقت"""
    # استفاده از tempfile برای مسیر امن‌تر
    temp_dir = tempfile.gettempdir()
    safe_filename = re.sub(INVALID_FILENAME_CHARS, '_', filename)
    timestamp = int(time.time())
    temp_filename = f"telegram_bot_{user_id}_{timestamp}_{safe_filename}"
    return os.path.join(temp_dir, temp_filename)

@bot.message_handler(func=lambda m: data_store.get_user_state(m.from_user.id)["state"] == "rename_file_wait_for_name")
def handle_rename_file_process(message):
    user_id = message.from_user.id
    new_name = message.text.strip() if message.text else ""
    
    # دریافت اطلاعات کاربر
    user_state = data_store.get_user_state(user_id)
    if not user_state or "data" not in user_state:
        bot.send_message(user_id, "❌ خطا در دریافت اطلاعات فایل. لطفاً مجدداً تلاش کنید.")
        data_store.update_user_state(user_id, "uploader_menu")
        return
    
    file_id = user_state["data"].get("file_id")
    original_name = user_state["data"].get("original_name", "file")
    
    if not file_id:
        bot.send_message(user_id, "❌ شناسه فایل یافت نشد. لطفاً مجدداً تلاش کنید.")
        data_store.update_user_state(user_id, "uploader_menu")
        return
    
    # اعتبارسنجی نام فایل
    is_valid, validation_message = validate_filename(new_name)
    if not is_valid:
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🔄 تلاش مجدد", callback_data="retry_rename"))
        markup.add(types.InlineKeyboardButton("↩️ بازگشت", callback_data="back_to_uploader"))
        
        bot.send_message(
            user_id, 
            f"❌ **نام فایل نامعتبر**\n\n"
            f"🔍 **مشکل:** {validation_message}\n\n"
            f"💡 **راهنما:**\n"
            f"• از کاراکترهای خاص استفاده نکنید\n"
            f"• حداکثر {MAX_FILENAME_LENGTH} کاراکتر\n"
            f"• فقط حروف، اعداد، نقطه و خط تیره", 
            reply_markup=markup,
            parse_mode='HTML'
        )
        return
    
    # پردازش پسوند فایل
    ext = os.path.splitext(original_name)[1].lower()
    
    # اگر کاربر پسوند را وارد نکرده، آن را اضافه کن
    if not new_name.lower().endswith(ext) and ext:
        final_name = f"{new_name}{ext}"
    else:
        final_name = new_name
    
    # ایجاد مسیر موقت امن
    temp_path = get_safe_temp_path(user_id, final_name)
    progress_msg = None
    
    try:
        # شروع پیام پیش‌رفت
        progress_msg = bot.send_message(
            user_id, 
            "⏳ **در حال پردازش فایل...**\n\n"
            "📥 **مرحله 1/3:** دریافت اطلاعات فایل\n"
            "░░░░░░░░░░ 0%",
            parse_mode='HTML'
        )
        
        # دریافت اطلاعات فایل
        try:
            file_info = bot.get_file(file_id)
        except Exception as e:
            raise Exception(f"خطا در دریافت اطلاعات فایل: {str(e)}")
        
        # بررسی اندازه فایل
        file_size_mb = file_info.file_size / (1024 * 1024) if file_info.file_size else 0
        if file_size_mb > MAX_FILE_SIZE_MB:
            raise Exception(f"حجم فایل ({file_size_mb:.1f} مگابایت) بیش از حد مجاز ({MAX_FILE_SIZE_MB} مگابایت) است")
        
        # به‌روزرسانی پیش‌رفت
        bot.edit_message_text(
            "⏳ **در حال پردازش فایل...**\n\n"
            "✅ **مرحله 1/3:** دریافت اطلاعات فایل\n"
            "📥 **مرحله 2/3:** دانلود فایل...\n"
            "███░░░░░░░ 30%",
            user_id, progress_msg.message_id, parse_mode='HTML'
        )
        
        # دانلود فایل
        url = f"https://api.telegram.org/file/bot{bot.token}/{file_info.file_path}"
        
        try:
            r = requests.get(url, stream=True, timeout=10**6)
            r.raise_for_status()
        except requests.exceptions.Timeout:
            raise Exception("زمان دانلود فایل به پایان رسید. لطفاً مجدداً تلاش کنید.")
        except requests.exceptions.RequestException as e:
            raise Exception(f"خطا در دانلود فایل: {str(e)}")
        
        # ذخیره فایل با نمایش پیش‌رفت
        downloaded_size = 0
        total_size = int(r.headers.get('content-length', 0))
        
        with open(temp_path, 'wb') as out_f:
            for chunk in r.iter_content(chunk_size=512*1024):  # 512KB chunks
                if chunk:
                    out_f.write(chunk)
                    downloaded_size += len(chunk)
                    
                    # به‌روزرسانی پیش‌رفت هر 2 مگابایت
                    if total_size > 0 and downloaded_size % (2*1024*1024) == 0:
                        progress = int((downloaded_size / total_size) * 40) + 30  # 30-70%
                        progress_bar = "█" * (progress // 10) + "░" * (10 - progress // 10)
                        
                        try:
                            bot.edit_message_text(
                                f"⏳ **در حال پردازش فایل...**\n\n"
                                f"✅ **مرحله 1/3:** دریافت اطلاعات فایل\n"
                                f"📥 **مرحله 2/3:** دانلود فایل ({downloaded_size/(1024*1024):.1f}MB)\n"
                                f"{progress_bar} {progress}%",
                                user_id, progress_msg.message_id, parse_mode='HTML'
                            )
                        except:
                            pass  # اگر edit نشد، ادامه بده
        
        # به‌روزرسانی نهایی پیش‌رفت
        bot.edit_message_text(
            "⏳ **در حال پردازش فایل...**\n\n"
            "✅ **مرحله 1/3:** دریافت اطلاعات فایل\n"
            "✅ **مرحله 2/3:** دانلود فایل\n"
            "📤 **مرحله 3/3:** ارسال فایل با نام جدید...\n"
            "███████░░░ 70%",
            user_id, progress_msg.message_id, parse_mode='HTML'
        )
        
        # بررسی اینکه فایل به درستی دانلود شده
        if not os.path.exists(temp_path) or os.path.getsize(temp_path) == 0:
            raise Exception("فایل به درستی دانلود نشد")
        
        # ارسال فایل با نام جدید
        with open(temp_path, 'rb') as file_to_send:
            # تشخیص نوع فایل
            mime_type, _ = mimetypes.guess_type(final_name)
            
            # کپشن مفصل
            caption = f"✅ **نام فایل تغییر یافت**\n\n" \
                     f"📝 **نام قبلی:** `{original_name}`\n" \
                     f"📝 **نام جدید:** `{final_name}`\n" \
                     f"📊 **حجم:** `{file_size_mb:.2f} MB`"
            
            if mime_type:
                caption += f"\n📄 **نوع:** `{mime_type}`"
            
            try:
                bot.send_document(
                    user_id,
                    file_to_send,
                    visible_file_name=final_name,
                    caption=caption,
                    reply_markup=get_uploader_menu(),
                    parse_mode='HTML'
                )
            except Exception as e:
                # اگر ارسال به عنوان document نشد، به عنوان file بفرست
                file_to_send.seek(0)
                bot.send_document(
                    user_id,
                    file_to_send,
                    visible_file_name=final_name,
                    caption=f"✅ نام فایل تغییر یافت به: {final_name}",
                    reply_markup=get_uploader_menu()
                )
        
        # حذف پیام پیش‌رفت
        if progress_msg:
            try:
                bot.delete_message(user_id, progress_msg.message_id)
            except:
                pass
        
        logger.info(f"✅ فایل {original_name} برای کاربر {user_id} به {final_name} تغییر نام یافت")
        
    except Exception as e:
        error_msg = str(e)
        logger.error(f"❌ خطا در تغییر نام فایل برای کاربر {user_id}: {error_msg}")
        
        # حذف پیام پیش‌رفت در صورت خطا
        if progress_msg:
            try:
                bot.delete_message(user_id, progress_msg.message_id)
            except:
                pass
        
        # ارسال پیام خطا با جزئیات
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(types.InlineKeyboardButton("🔄 تلاش مجدد", callback_data="retry_rename"))
        markup.add(types.InlineKeyboardButton("↩️ بازگشت", callback_data="back_to_uploader"))
        
        # مخفی کردن خطاهای حساس
        user_friendly_error = error_msg
        if "token" in error_msg.lower():
            user_friendly_error = "خطا در احراز هویت"
        elif "timeout" in error_msg.lower():
            user_friendly_error = "زمان پردازش به پایان رسید"
        elif "permission" in error_msg.lower():
            user_friendly_error = "عدم دسترسی به فایل"
        
        bot.send_message(
            user_id, 
            f"❌ **خطا در تغییر نام فایل**\n\n"
            f"🔍 **علت:** {user_friendly_error}\n\n"
            f"💡 **پیشنهادات:**\n"
            f"• اتصال اینترنت خود را بررسی کنید\n"
            f"• برای فایل‌های بزرگ کمی صبر کنید\n"
            f"• از نام‌های ساده‌تر استفاده کنید",
            reply_markup=markup,
            parse_mode='HTML'
        )
        
    finally:
        # حذف فایل موقت
        try:
            if os.path.exists(temp_path):
                os.remove(temp_path)
                logger.info(f"فایل موقت {temp_path} حذف شد")
        except Exception as cleanup_error:
            logger.warning(f"خطا در حذف فایل موقت: {cleanup_error}")
        
        # بازگشت به منوی اصلی
        data_store.update_user_state(user_id, "uploader_menu")

# اضافه کردن callback handlers برای دکمه‌های جدید
@bot.callback_query_handler(func=lambda call: call.data == "retry_rename")
def handle_retry_rename(call):
    user_id = call.from_user.id
    bot.answer_callback_query(call.id, "🔄 آماده دریافت نام جدید")
    
    bot.send_message(
        user_id,
        "📝 **نام جدید فایل را وارد کنید:**\n\n"
        "💡 **نکات مهم:**\n"
        "• فقط از حروف، اعداد و خط تیره استفاده کنید\n"
        "• نیازی به وارد کردن پسوند نیست\n"
        "• حداکثر ۲۰۰ کاراکتر\n\n"
        "✍️ **نام جدید:**",
        parse_mode='HTML'
    )
    
    data_store.update_user_state(user_id, "rename_file_wait_for_name")

@bot.callback_query_handler(func=lambda call: call.data == "back_to_uploader")
def handle_back_to_uploader(call):
    user_id = call.from_user.id
    bot.answer_callback_query(call.id, "↩️ بازگشت به منو")
    
    data_store.update_user_state(user_id, "uploader_menu")
    
    # ارسال منوی اصلی
    try:
        bot.send_message(
            user_id,
            "📁 **منوی اپلودر**\n\nبرای شروع، فایل خود را ارسال کنید:",
            reply_markup=get_uploader_menu(),
            parse_mode='HTML'
        )
    except:
        pass
        
@bot.message_handler(func=lambda message: data_store.get_user_state(message.from_user.id)["state"] == "rename_file_wait_for_link", content_types=['text', 'document', 'photo', 'video'])
def handle_rename_file_wait_for_link(message):
    user_id = message.from_user.id
    # اگر فایل است
    if message.content_type in ['document', 'photo', 'video']:
        file_type = message.content_type
        if file_type == "document":
            file_id = message.document.file_id
            old_name = message.document.file_name or "بدون‌نام"
        elif file_type == "photo":
            file_id = message.photo[-1].file_id
            old_name = "عکس"
        elif file_type == "video":
            file_id = message.video.file_id
            old_name = message.caption or "ویدیو"
        # ذخیره اطلاعات فایل به صورت موقت
        data_store.update_user_state(user_id, "rename_file_wait_for_new_name", {
            "file_id": file_id,
            "file_type": file_type,
            "old_file_name": old_name
        })
        bot.send_message(user_id, f"اسم فعلی فایل:\n<code>{old_name}</code>\nاسم جدید فایل را وارد کنید:", reply_markup=get_back_menu(), parse_mode="HTML")
    else:
        # اگر لینک است
        file_link = message.text.strip()
        info = data_store.uploader_file_map.get(file_link)
        if not info or "channel_link" not in info:
            bot.send_message(user_id, "لینک معتبر نیست یا پیدا نشد.", reply_markup=get_back_menu())
            return
        file_name = info.get("file_name", f"{info.get('uuid')}")
        data_store.update_user_state(user_id, "rename_file_wait_for_new_name", {
            "editing_file_link": file_link,
            "old_file_name": file_name,
            "file_type": info.get("file_type")
        })
        bot.send_message(user_id, f"اسم فعلی فایل:\n<code>{file_name}</code>\nاسم جدید فایل را وارد کنید:", reply_markup=get_back_menu(), parse_mode="HTML")
       
@bot.message_handler(func=lambda message: data_store.get_user_state(message.from_user.id)["state"] == "rename_file_wait_for_new_name")
def handle_rename_file_wait_for_new_name(message):
    user_id = message.from_user.id
    user_state = data_store.get_user_state(user_id)
    new_name = message.text.strip()
    file_type = user_state["data"].get("file_type")

    if user_state["data"].get("file_id"):
        file_id = user_state["data"]["file_id"]
        orig_name = user_state["data"]["old_file_name"]
        file_type = user_state["data"].get("file_type")
        base, ext = os.path.splitext(orig_name)
        # دریافت kw از تنظیمات اتوماتیک تغییر نام کاربر
        settings = get_auto_rename_settings(user_id)
        kw = settings.get("keyword", "")
        if kw:
            if ext:
                final_name = f"{base}{kw}{ext}"
            else:
                final_name = f"{base}{kw}"
        else:
            if not new_name.lower().endswith(ext.lower()):
                final_name = f"{new_name}{ext}" if ext else new_name
            else:
                final_name = new_name
        # فقط یک پیام لودینگ ایجاد می‌شود و شناسه پیام را ذخیره می‌کنیم تا در هر مرحله بروزرسانی شود
        progress_msg = send_progress_message(user_id, "در حال تغییر نام فایل...", 10)
        progress_msg_id = progress_msg.message_id

        temp_path = f"temp_rename_{user_id}_{int(time.time())}_{final_name}"
        # مرحله: دانلود فایل (نمایش لودینگ 20%)
        update_progress_message(progress_msg, "در حال دانلود فایل...", 20)
        result = safe_download_file(bot, file_id, temp_path)
        if result is True:
            # مرحله: دانلود انجام شد (نمایش لودینگ 50%)
            update_progress_message(progress_msg, "دانلود فایل انجام شد.", 50)
            # مرحله: اپلود فایل با نام جدید (نمایش لودینگ 80%)
            try:
                with open(temp_path, "rb") as file_f:
                    update_progress_message(progress_msg, "در حال اپلود فایل با نام جدید...", 80)
                    if file_type == "document":
                        bot.send_document(user_id, file_f, visible_file_name=final_name, caption=f"فایل با نام جدید: {final_name}", reply_markup=get_uploader_menu())
                    elif file_type == "photo":
                        bot.send_photo(user_id, file_f, caption=f"فایل با نام جدید: {final_name}", reply_markup=get_uploader_menu())
                    elif file_type == "video":
                        bot.send_video(user_id, file_f, caption=f"فایل با نام جدید: {final_name}", reply_markup=get_uploader_menu())
            finally:
                try:
                    os.remove(temp_path)
                except Exception:
                    pass
            # مرحله: پایان کار (نمایش لودینگ 100%)
            update_progress_message(progress_msg, "✅ اسم فایل تغییر کرد و فایل جدید ارسال شد.", 100)
        else:
            # مرحله: خطا در دانلود (نمایش لودینگ 100%)
            update_progress_message(progress_msg, f"❌ خطا در دانلود فایل:\n{result}", 100)
            bot.send_message(user_id, f"❌ خطا در دانلود فایل:\n{result}", reply_markup=get_back_menu())
            try:
                if os.path.exists(temp_path):
                    os.remove(temp_path)
            except Exception:
                pass
        data_store.update_user_state(user_id, "uploader_menu", {})

    elif user_state["data"].get("editing_file_link"):
        file_link = user_state["data"]["editing_file_link"]
        info = data_store.uploader_file_map.get(file_link)
        orig_name = info.get("file_name", "")
        base, ext = os.path.splitext(orig_name)
        final_name = f"{new_name}{ext}" if ext else new_name
        channel_username = info["channel_link"].split("/")[3]
        msg_id = int(info["channel_link"].split("/")[4])
        try:
            msg = bot.forward_message(chat_id=user_id, from_chat_id=f"@{channel_username}", message_id=msg_id)
            file_id = None
            if file_type == "document" and hasattr(msg, "document"):
                file_id = msg.document.file_id
            elif file_type == "photo" and hasattr(msg, "photo"):
                file_id = msg.photo[-1].file_id
            elif file_type == "video" and hasattr(msg, "video"):
                file_id = msg.video.file_id
            if file_id:
                if file_type == "document":
                    bot.send_document(user_id, file_id, visible_file_name=final_name, caption=f"فایل با نام جدید: {final_name}", reply_markup=get_uploader_menu())
                elif file_type == "photo":
                    bot.send_photo(user_id, file_id, caption=f"فایل با نام جدید: {final_name}", reply_markup=get_uploader_menu())
                elif file_type == "video":
                    bot.send_video(user_id, file_id, caption=f"فایل با نام جدید: {final_name}", reply_markup=get_uploader_menu())
                bot.send_message(user_id, "✅ اسم فایل تغییر کرد و فایل جدید ارسال شد.", reply_markup=get_uploader_menu())
            else:
                bot.send_message(user_id, "خطا در خواندن فایل.", reply_markup=get_back_menu())
        except Exception as e:
            bot.send_message(user_id, f"خطا: {e}", reply_markup=get_back_menu())

    data_store.update_user_state(user_id, "uploader_menu", {})
    
@bot.message_handler(func=lambda m: m.text == "🔙 بازگشت به منوی اصلی")
def back_to_main_menu(message):
    user_id = message.from_user.id
    data_store.reset_user_state(user_id)
    markup = get_main_menu(user_id)
    bot.send_message(user_id, "🏠 بازگشت به منوی اصلی:", reply_markup=markup)

@bot.message_handler(func=lambda m: data_store.get_user_state(m.from_user.id)["state"] == "set_delete_upload_file_timeout")
def handle_set_delete_upload_file_timeout(message):
    user_id = message.from_user.id
    val = message.text.strip()
    if val == "🔙 بازگشت به منوی اصلی":
        data_store.reset_user_state(user_id)
        bot.send_message(user_id, "🏠 بازگشت به منوی اصلی:", reply_markup=get_main_menu(user_id))
        return
    if not val.isdigit() or int(val) < 1:
        bot.send_message(user_id, "لطفاً فقط عدد صحیح مثبت (ثانیه) وارد کنید.", reply_markup=get_back_menu())
        return
    data_store.timer_settings["delete_upload_file_timeout"] = int(val)
    data_store.save_data()
    bot.send_message(user_id, f"⏱ مدت زمان حذف فایل اپلود دیلیت به {val} ثانیه تغییر یافت.", reply_markup=get_settings_menu(user_id))
    data_store.reset_user_state(user_id)

#==========================هلندر ربات ساز=======================
def get_bot_creator_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
    markup.add(types.KeyboardButton("➕ افزودن ربات"))
    markup.add(types.KeyboardButton("📋 لیست ربات‌ها"))
    markup.add(types.KeyboardButton("🗑️ حذف ربات"))
    markup.add(types.KeyboardButton("♻️ ری ران ربات‌ها"))  # <- اضافه شد
    markup.add(types.KeyboardButton("🔙 بازگشت به منوی اصلی"))
    return markup

@bot.message_handler(func=lambda m: m.text == "🤖 ربات ساز")
def handle_bot_creator_menu(message):
    user_id = message.from_user.id
    perm = data_store.admin_permissions.get(str(user_id), {}) if is_admin(user_id) else {}
    if not (is_owner(user_id) or (is_admin(user_id) and perm.get("bot_creator", False))):
        bot.send_message(user_id, "⛔️ فقط مالک یا ادمین با دسترسی ربات ساز می‌تواند این بخش را مشاهده کند.", reply_markup=get_main_menu(user_id))
        return
    data_store.update_user_state(user_id, "bot_creator_menu")
    bot.send_message(user_id, "منوی ربات ساز را انتخاب کنید:", reply_markup=get_bot_creator_menu())
    
@bot.message_handler(func=lambda m: data_store.get_user_state(m.from_user.id)["state"] == "bot_creator_menu")
def handle_bot_creator_menu_choice(message):
    user_id = message.from_user.id
    text = message.text
    if text == "➕ افزودن ربات":
        data_store.update_user_state(user_id, "wait_for_new_owner_id")
        bot.send_message(user_id, "آیدی عددی مالک ربات جدید را وارد کنید:", reply_markup=get_bot_creator_menu())
    elif text == "📋 لیست ربات‌ها":
        bots = []
        for folder in os.listdir("."):
            if folder.startswith("bot_") and os.path.isdir(folder):
                cfg_path = os.path.join(folder, "config.json")
                if os.path.exists(cfg_path):
                    try:
                        with open(cfg_path, "r", encoding="utf-8") as f:
                            cfg = json.load(f)
                        if str(cfg.get("OWNER_USER", "")) == str(user_id):
                            bots.append(cfg)
                    except:
                        continue
        if not bots:
            msg = "<b>لیست ربات‌های شما:</b>\n\n<blockquote>هیچ رباتی ندارید!</blockquote>"
        else:
            msg = "<b>لیست ربات‌های شما:</b>\n\n"
            for i, botinfo in enumerate(bots, 1):
                name = botinfo.get("BOT_CHILD_NAME", f"بدون‌نام{i}")
                token = botinfo.get("API_TOKEN", "ندارد")
                owner = botinfo.get("OWNER_USER", "نامشخص")
                msg += f"<blockquote>\nنام ربات: <code>{name}</code>\nکد API: <code>{token}</code>\nآیدی اونر: <code>{owner}</code>\n</blockquote>\n"
        bot.send_message(user_id, msg, reply_markup=get_bot_creator_menu(), parse_mode="HTML")
    elif text == "🗑️ حذف ربات":
        data_store.update_user_state(user_id, "delete_bot_name")
        bot.send_message(user_id, "نام رباتی که می‌خواهید حذف کنید را وارد کنید:", reply_markup=get_bot_creator_menu())
    elif text == "♻️ ری ران ربات‌ها":
        bot.send_message(user_id, "♻️ در حال ری‌ران همه ربات‌های بچه ...")
        update_and_run_all_children_bots()
        bot.send_message(user_id, "✅ همه ربات‌های بچه با موفقیت ری‌ران شدند.", reply_markup=get_bot_creator_menu())
        return
    elif text == "🔙 بازگشت به منوی اصلی":
        data_store.reset_user_state(user_id)
        bot.send_message(user_id, "🏠 بازگشت به منوی اصلی:", reply_markup=get_main_menu(user_id))

@bot.message_handler(func=lambda m: data_store.get_user_state(m.from_user.id)["state"] == "delete_bot_name")
def handle_delete_bot_name(message):
    user_id = message.from_user.id
    bot_name = message.text.strip()
    # پیدا کردن پوشه با این نام
    bot_folder = None
    for folder in os.listdir("."):
        if folder.startswith("bot_") and os.path.isdir(folder):
            cfg_path = os.path.join(folder, "config.json")
            if os.path.exists(cfg_path):
                try:
                    with open(cfg_path, "r", encoding="utf-8") as f:
                        cfg = json.load(f)
                    if cfg.get("BOT_CHILD_NAME", "") == bot_name and str(cfg.get("OWNER_USER", "")) == str(user_id):
                        bot_folder = folder
                        break
                except:
                    continue
    if not bot_folder:
        bot.send_message(user_id, "ربات با این نام پیدا نشد یا متعلق به شما نیست.", reply_markup=get_bot_creator_menu())
        return
    data_store.update_user_state(user_id, "confirm_delete_bot", {"bot_folder": bot_folder, "bot_name": bot_name})
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("✅ بله"))
    markup.add(types.KeyboardButton("❌ خیر"))
    bot.send_message(user_id, f"آیا مطمئن هستید که می‌خواهید ربات <code>{bot_name}</code> را حذف کنید؟\nدر صورتی که پشتیبان تهیه نکرده باشید، این کار غیر قابل بازگشت است!", reply_markup=markup, parse_mode="HTML")

@bot.message_handler(func=lambda m: data_store.get_user_state(m.from_user.id)["state"] == "confirm_delete_bot")
def handle_confirm_delete_bot(message):
    user_id = message.from_user.id
    text = message.text.strip()
    bot_folder = data_store.get_user_state(user_id)["data"].get("bot_folder")
    bot_name = data_store.get_user_state(user_id)["data"].get("bot_name")
    if text == "❌ خیر":
        data_store.update_user_state(user_id, "bot_creator_menu")
        bot.send_message(user_id, "حذف ربات لغو شد.", reply_markup=get_bot_creator_menu())
        return
    elif text == "✅ بله":
        try:
            shutil.rmtree(bot_folder)
        except Exception as e:
            bot.send_message(user_id, f"❌ خطا در حذف ربات:\n{e}", reply_markup=get_bot_creator_menu())
            data_store.update_user_state(user_id, "bot_creator_menu")
            return
        data_store.update_user_state(user_id, "bot_creator_menu")
        bot.send_message(user_id, f"✅ ربات <code>{bot_name}</code> حذف شد.", reply_markup=get_bot_creator_menu(), parse_mode="HTML")

@bot.message_handler(func=lambda m: data_store.get_user_state(m.from_user.id)["state"] == "wait_for_new_owner_id")
def handle_new_owner_id(message):
    user_id = message.from_user.id
    try:
        new_owner_id = int(message.text.strip())
        data_store.update_user_state(user_id, "wait_for_new_bot_token", {"new_owner_id": new_owner_id})
        bot.send_message(user_id, "کد API ربات جدید را وارد کنید:", reply_markup=get_main_menu(user_id))
    except:
        bot.send_message(user_id, "آیدی عددی معتبر وارد کنید:", reply_markup=get_main_menu(user_id))

@bot.message_handler(func=lambda m: data_store.get_user_state(m.from_user.id)["state"] == "wait_for_new_bot_token")
def handle_new_bot_token(message):
    user_id = message.from_user.id
    api_token = message.text.strip()
    new_owner_id = data_store.get_user_state(user_id)["data"].get("new_owner_id", user_id)
    data_store.update_user_state(user_id, "wait_for_bot_child_name", {"new_owner_id": new_owner_id, "api_token": api_token})
    bot.send_message(user_id, "یک نام (ایدی عددی یا یوزرنیم) برای ربات بچه انتخاب کنید:", reply_markup=get_main_menu(user_id))

@bot.message_handler(func=lambda m: data_store.get_user_state(m.from_user.id)["state"] == "wait_for_bot_child_name")
def handle_new_bot_child_name(message):
    user_id = message.from_user.id
    child_name = message.text.strip()
    st = data_store.get_user_state(user_id)
    api_token = st["data"]["api_token"]
    new_owner_id = st["data"]["new_owner_id"]
    bot_folder = f"bot_{user_id}_{int(time.time())}"
    os.makedirs(bot_folder, exist_ok=True)
    with open("baby_bot.py", "r", encoding="utf-8") as f:
        template_code = f.read()
    BOT_TEMPLATE = safe_format(
        template_code,
        API_TOKEN=api_token,
        OWNER_USER=new_owner_id,
        BOT_VERSION=BOT_VERSION,
        BOT_CHILD_NAME=child_name
    )
    bot_file_path = os.path.join(bot_folder, "bot.py")
    with open(bot_file_path, "w", encoding="utf-8") as f:
        f.write(BOT_TEMPLATE)
    config_path = os.path.join(bot_folder, "config.json")
    try:
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump({
                "API_TOKEN": api_token,
                "OWNER_USER": new_owner_id,
                "BOT_CHILD_NAME": child_name
            }, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"config.json written in: {config_path}")
        print(f"Exists? {os.path.exists(config_path)}")
    data_store.update_user_state(user_id, "ask_run_created_bot", {"bot_file_path": "bot.py", "bot_folder": bot_folder})
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("✅ بله"))
    bot.send_message(
        user_id,
        f"✅ ربات جدید ساخته شد و نام آن <code>{child_name}</code> است.\n\nآیا مایل هستید ربات ساخته‌شده فوراً ران شود؟",
        reply_markup=markup,
        parse_mode="HTML"
    )

@bot.message_handler(func=lambda m: data_store.get_user_state(m.from_user.id)["state"] == "ask_run_created_bot" and m.text == "✅ بله")
def handle_run_created_bot(message):
    user_id = message.from_user.id
    user_state = data_store.get_user_state(user_id)
    bot_file_path = user_state['data'].get('bot_file_path', 'bot.py')
    bot_folder = user_state['data'].get('bot_folder')
    
    # کپی همه فایل‌های کنار baby_bot.py به جز mother_bot.py و baby_bot.py و پوشه‌ها
    for file_name in os.listdir("."):
        if os.path.isfile(file_name) and file_name not in ("mother_bot.py", "baby_bot.py"):
            try:
                shutil.copy2(file_name, os.path.join(bot_folder, file_name))
            except Exception as e:
                logger.error(f"Error copying {file_name} to {bot_folder}: {e}")

    try:
        proc = subprocess.Popen(
            ["python3", "bot.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=bot_folder
        )
        
        time.sleep(2)
        retcode = proc.poll()
        if retcode is not None and retcode != 0:
            out, err = proc.communicate(timeout=5)
            error_msg = err.decode('utf-8') if err else "خطای نامشخص"
            bot.send_message(user_id, f"❌ اجرای ربات با خطا مواجه شد:\n<code>{error_msg}</code>", parse_mode="HTML")
        else:
            # استخراج یوزرنیم یا آیدی ربات ساخته شده
            try:
                child_bot = telebot.TeleBot(api_token)
                bot_info = child_bot.get_me()
                bot_username = bot_info.username
                bot_id = bot_info.id
                bot_identity = f"@{bot_username}" if bot_username else f"ID: <code>{bot_id}</code>"
            except Exception:
                bot_identity = "<code>نامشخص</code>"
            bot.send_message(user_id, 
                "✅ ربات ساخته‌شده با موفقیت اجرا شد.\n\n"
                f"<blockquote>{bot_identity}</blockquote>", 
                reply_markup=get_main_menu(user_id), 
                parse_mode="HTML"
            )
        data_store.reset_user_state(user_id)
    except Exception as ex:
        bot.send_message(user_id, f"❌ اجرای ربات جدید با خطا مواجه شد:\n<code>{str(ex)}</code>", parse_mode="HTML")
        data_store.reset_user_state(user_id)
#==========================================================
#===========================حساب کاربری======================
#==========================================================
# بارگذاری داده‌ها
def load_json(filename, default=None):
    try:
        with open(os.path.join("central_data", filename), "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default if default is not None else {}
@bot.message_handler(func=lambda m: m.text == "👤 حساب کاربری")
@require_join
@require_seen_reaction
def handle_user_account(message):
    user_id = message.from_user.id

    # اگر بلاک شده، هیچ پیامی نده
    if data_store.user_data.get(str(user_id), {}).get("is_blocked_by_owner", False):
        return

    user = data_store.user_data.get(str(user_id), {})
    first_name = user.get("first_name") or message.from_user.first_name or ""
    last_name = user.get("last_name") or message.from_user.last_name or ""
    username = user.get("username") or message.from_user.username or "ندارد"
    join_date = user.get("join_date", "")[:16] if user.get("join_date") else "نامشخص"
    status = user.get("status", "online")
    maram = user.get("maram", False)

    # آمار عمومی
    total_users = len(data_store.user_data)
    active_count = sum(1 for u in data_store.user_data.values() if u.get("is_active"))
    maram_count = sum(1 for u in data_store.user_data.values() if u.get("maram"))
    def days_ago(dtstr):
        try:
            dt = datetime.fromisoformat(dtstr)
            return (datetime.now() - dt).days
        except Exception:
            return 9999
    week_count = sum(1 for u in data_store.user_data.values() if u.get("join_date") and days_ago(u["join_date"]) < 7)
    month_count = sum(1 for u in data_store.user_data.values() if u.get("join_date") and days_ago(u["join_date"]) < 31)
    year_now = datetime.now().year
    year_count = sum(1 for u in data_store.user_data.values() if u.get("join_date") and datetime.fromisoformat(u["join_date"]).year == year_now)

    # پیام حساب کاربری
    profile_text = (
        "👤 <b>اطلاعات حساب کاربری</b>\n"
        "<blockquote>"
        f"نام: {first_name}\n"
        f"نام خانوادگی: {last_name}\n"
        f"یوزرنیم: @{username}\n"
        f"آیدی عددی: {user_id}\n"
        f"تاریخ عضویت: {join_date}\n"
        f"وضعیت: {status}\n"
        f"مرام: {'✅' if maram else '❌'}\n"
        "</blockquote>\n"
        "<b>آمار عضویت کل بات</b>\n"
        "<blockquote>"
        f"کل اعضا: {total_users}\n"
        f"اعضای فعال: {active_count}\n"
        f"اعضای با مرام: {maram_count}\n"
        f"اعضای هفته اخیر: {week_count}\n"
        f"اعضای ماه اخیر: {month_count}\n"
        f"اعضای امسال: {year_count}\n"
        "</blockquote>"
    )

    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(types.InlineKeyboardButton("👤 حساب کاربری", callback_data="show_profile"))
    markup.row(
        types.InlineKeyboardButton("📊 وضعیت چنل", callback_data="show_channels"),
        types.InlineKeyboardButton("👥 مدیریت کاربران", callback_data="show_users")
    )

    bot.send_message(user_id, profile_text, reply_markup=markup, parse_mode="HTML")
@bot.callback_query_handler(func=lambda call: call.data == "show_profile")
def handle_show_profile(call):
    user_id = call.from_user.id

    user_data = load_json("user_data.json", {})
    user = user_data.get(str(user_id))
    if not user:
        bot.answer_callback_query(call.id, "❌ کاربر یافت نشد", show_alert=True)
        return

    total_users = len(user_data)
    active_count = sum(1 for u in user_data.values() if u.get("is_active"))
    maram_count = sum(1 for u in user_data.values() if u.get("maram"))

    def days_ago(dtstr):
        tehran_tz = pytz.timezone('Asia/Tehran')
        try:
            dt = datetime.fromisoformat(dtstr)
            if dt.tzinfo is None:
                dt = tehran_tz.localize(dt)
            return (datetime.now(tehran_tz) - dt).days
        except Exception:
            return 9999

    week_count = sum(1 for u in user_data.values() if u.get("join_date") and days_ago(u["join_date"]) < 7)
    month_count = sum(1 for u in user_data.values() if u.get("join_date") and days_ago(u["join_date"]) < 31)
    year_now = datetime.now().year
    year_count = sum(1 for u in user_data.values() if u.get("join_date") and datetime.fromisoformat(u["join_date"]).year == year_now)

    first_name = user.get("first_name", "")
    last_name = user.get("last_name", "")
    username = user.get("username", "")
    username_disp = f"@{username}" if username else "ندارد"
    join_date = user.get("join_date", "")[:16] if user.get("join_date") else "نامشخص"
    status = user.get("status", "online")

    # همه اطلاعات در نقل قول
    profile_text = (
        "👤 <b>اطلاعات حساب کاربری</b>\n"
        "<blockquote>"
        f"نام: {first_name}\n"
        f"نام خانوادگی: {last_name}\n"
        f"یوزرنیم: {username_disp}\n"
        f"آیدی عددی: {user_id}\n"
        f"تاریخ عضویت: {join_date}\n"
        f"وضعیت: {status}\n"
        "</blockquote>\n"
        "<b>آمار عضویت کل بات</b>\n"
        "<blockquote>"
        f"کل اعضا: {total_users}\n"
        f"اعضای فعال: {active_count}\n"
        f"اعضای با مرام: {maram_count}\n"
        f"اعضای هفته اخیر: {week_count}\n"
        f"اعضای ماه اخیر: {month_count}\n"
        f"اعضای امسال: {year_count}\n"
        "</blockquote>"
    )

    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(types.InlineKeyboardButton("👤 حساب کاربری", callback_data="show_profile"))
    markup.row(
        types.InlineKeyboardButton("📊 وضعیت چنل", callback_data="show_channels"),
        types.InlineKeyboardButton("👥 مدیریت کاربران", callback_data="show_users")
    )

    bot.answer_callback_query(call.id, "✅ اطلاعات حساب کاربری")
    bot.edit_message_text(profile_text, call.message.chat.id, call.message.message_id,
                         reply_markup=markup, parse_mode='HTML')

# نمایش وضعیت چنل‌ها
@bot.callback_query_handler(func=lambda call: call.data == "show_channels")
def handle_show_channels(call):
    user_id = call.from_user.id

    uploader_channels = load_json("uploader_channels.json", [])
    channels = load_json("channels.json", [])

    # لیست دقیق همان مقادیر جیسون
    uploader_list = "\n".join([ch for ch in uploader_channels]) if uploader_channels else "هیچ کانالی ثبت نشده"
    channels_list = "\n".join([ch for ch in channels]) if channels else "هیچ کانالی ثبت نشده"

    channels_text = (
        "📊 <b>وضعیت کانال‌ها</b>\n"
        "<blockquote>"
        "🔺 کانال‌های اپلودری:\n"
        f"{uploader_list}\n\n"
        "📝 کانال‌های ساخت پست:\n"
        f"{channels_list}\n"
        "</blockquote>\n"
        "<b>آمار:</b>\n"
        "<blockquote>"
        f"تعداد کانال اپلودری: {len(uploader_channels)}\n"
        f"تعداد کانال پست: {len(channels)}\n"
        f"کل کانال‌ها: {len(uploader_channels) + len(channels)}\n"
        "</blockquote>\n"
        "<blockquote>💡 نکته: این بخش به زودی قابلیت‌های بیشتری خواهد داشت</blockquote>"
    )

    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(types.InlineKeyboardButton("👤 حساب کاربری", callback_data="show_profile"))
    markup.row(
        types.InlineKeyboardButton("📊 وضعیت چنل", callback_data="show_channels"),
        types.InlineKeyboardButton("👥 مدیریت کاربران", callback_data="show_users")
    )

    bot.answer_callback_query(call.id, "✅ وضعیت کانال‌ها")
    bot.edit_message_text(channels_text, call.message.chat.id, call.message.message_id,
                         reply_markup=markup, parse_mode='HTML')

# نمایش مدیریت کاربران
@bot.callback_query_handler(func=lambda call: call.data == "show_users")
def handle_show_users(call):
    user_id = call.from_user.id

    admins = load_json("admins.json", [])
    if user_id not in admins:
        bot.answer_callback_query(call.id, "❌ شما دسترسی ادمین ندارید", show_alert=True)
        return

    user_data = load_json("user_data.json", {})

    total_users = len(user_data)
    active_users = [u for u in user_data.values() if u.get("is_active")]
    blocked_users = [u for u in user_data.values() if u.get("is_blocked", False)]

    today = datetime.now().date()
    today_users, week_users, month_users = [], [], []
    for user in user_data.values():
        if user.get("join_date"):
            try:
                join_dt = datetime.fromisoformat(user["join_date"]).date()
                days_diff = (today - join_dt).days
                if days_diff == 0:
                    today_users.append(user)
                if days_diff < 7:
                    week_users.append(user)
                if days_diff < 30:
                    month_users.append(user)
            except:
                pass

    users_text = (
        "👥 <b>مدیریت کاربران</b>\n"
        "<blockquote>"
        f"کل کاربران: {total_users}\n"
        f"کاربران فعال: {len(active_users)}\n"
        f"کاربران مسدود: {len(blocked_users)}\n"
        "</blockquote>\n"
        "<b>آمار زمانی:</b>\n"
        "<blockquote>"
        f"عضو امروز: {len(today_users)}\n"
        f"عضو هفته اخیر: {len(week_users)}\n"
        f"عضو ماه اخیر: {len(month_users)}\n"
        "</blockquote>\n"
        "<blockquote>🔧 این بخش به زودی تکمیل می‌شود</blockquote>"
    )

    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(types.InlineKeyboardButton("👤 حساب کاربری", callback_data="show_profile"))
    markup.row(
        types.InlineKeyboardButton("📊 وضعیت چنل", callback_data="show_channels"),
        types.InlineKeyboardButton("👥 مدیریت کاربران", callback_data="show_users")
    )

    bot.answer_callback_query(call.id, "✅ پنل مدیریت کاربران")
    bot.edit_message_text(users_text, call.message.chat.id, call.message.message_id,
                         reply_markup=markup, parse_mode='HTML')
                         
def back_settings():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("🔙 بازگشت به تنظیمات ربات"))
    return markup
#==========================هلندر پیام ها=======================
# --- ضد اسپم کاربران ---
spam_times = defaultdict(lambda: deque(maxlen=30))
blocked_users = set()  # فقط کاربرانی که اسپم کرده‌اند اینجا ذخیره می‌شوند
blocked_notified = set()  # کاربرانی که پیام بلاک به آن‌ها ارسال شده

@bot.message_handler(func=lambda message: True)
def process_message(message):
    user_id = message.from_user.id
    text = message.text
    user_state = data_store.get_user_state(user_id)
    state = user_state["state"]

    # ضد اسپم
    now = int(time.time())
    if not (is_owner(user_id) or is_admin(user_id)):
        spam_times[user_id].append(now)
        recent_msgs = [t for t in spam_times[user_id] if now - t < 1]
        if len(recent_msgs) > 4:
            # ثبت بلاک دائمی در دیتابیس:
            if str(user_id) not in data_store.user_data:
                data_store.user_data[str(user_id)] = {}
            data_store.user_data[str(user_id)]["is_blocked_by_owner"] = True
            data_store.save_data()
            blocked_users.add(user_id)
            # پیام به کاربر و اونر (فقط یکبار)
            if user_id not in blocked_notified:
                try:
                    bot.send_message(
                        user_id,
                        "⛔️ شما به دلیل ارسال پیام‌های رگباری بلاک شدید و **این تخلف** برای اونر ربات ارسال شد.\nبرای رفع بلاک باید با مدیر تماس بگیرید.",
                        parse_mode="HTML"
                    )
                    bot.send_message(
                        OWNER_ID,
                        f"❗️ کاربر بلاک شد\nآیدی: <code>{user_id}</code>\nیوزرنیم: @{message.from_user.username}\nعلت: **اسپم یا تخلف چندباره**",
                        parse_mode="HTML"
                    )
                except: pass
                blocked_notified.add(user_id)
        # چک کنید اگر بلاک شده هیچ پیام دیگری پاسخ داده نشود:
        if data_store.user_data.get(str(user_id), {}).get("is_blocked_by_owner", False):
            return
    
    if text.startswith("/start"):
        return

    if text == "🔙 بازگشت به تنظیمات ربات":
        data_store.update_user_state(user_id, "settings_menu")
        bot.send_message(user_id, "🏛 تنظیمات ربات:", reply_markup=get_settings_menu(user_id))
        return

    # --- اضافه: هدایت پیام به هلندرهای stateهای مدیریت مقادیر پیش‌فرض ---
    # (اگر state فعلی کاربر مربوط به مدیریت مقادیر پیش‌فرض باشد، همینجا return کن تا به هلندر خودش برود)
    if state in [
        "default_values_management",
        "set_default_value_select_var",
        "set_default_value",
        "remove_default_value"
    ]:
        return  # اجازه بدهد هلندر‌های مربوط به این state اجرا شوند و همینجا متوقف شود

    # ذخیره اولیه
    if str(user_id) not in data_store.user_data:
        data_store.user_data[str(user_id)] = {
            "first_name": message.from_user.first_name or "",
            "last_name": message.from_user.last_name or "",
            "username": message.from_user.username or "",
            "join_date": datetime.now(pytz.timezone('Asia/Tehran')).isoformat()
        }
        data_store.save_data()
    user_state = data_store.get_user_state(user_id)
    state = user_state["state"]
    data_store.last_user_message_id[user_id] = message.message_id

    if text in MAIN_MENU_BUTTONS:
        if text == "👥 مدیریت کاربران":
            if not is_owner(user_id):
                bot.send_message(user_id, "⛔️ فقط اونر به این بخش دسترسی دارد.", reply_markup=get_main_menu(user_id))
                return
            data_store.update_user_state(user_id, "admin_management")
            bot.send_message(user_id, "👤 مدیریت ادمین‌ها:", reply_markup=get_admin_management_menu())
            return
        if process_main_menu_button(user_id, text):
            return

    if state in ["admin_management", "add_admin", "remove_admin", "select_admin_for_permissions", "manage_admin_permissions"]:
        handle_admin_management(user_id, text)
        return
        
    if state == "settings_menu":
        timers_enabled = data_store.timer_settings.get("timers_enabled", True)
        inline_buttons_enabled = data_store.timer_settings.get("inline_buttons_enabled", True)
        group_mode_enabled = data_store.timer_settings.get("group_mode_enabled", False)
        timers_btn_text = "✅ تایمرها: فعال" if timers_enabled else "❌ تایمرها: غیرفعال"
        inline_buttons_btn_text = "✅ کلیدهای شیشه‌ای: فعال" if inline_buttons_enabled else "❌ کلیدهای شیشه‌ای: غیرفعال"
        coinpy_btn_text = "🔥 تعداد کرکفای فایل"
        spy_btn_text = "جاسوس چنل: ✅" if data_store.channel_monitor_enabled else "جاسوس چنل: ❌"
        
        if text == timers_btn_text:
            data_store.timer_settings["timers_enabled"] = not timers_enabled
            data_store.save_data()
            status = "فعال" if data_store.timer_settings["timers_enabled"] else "غیرفعال"
            bot.send_message(user_id, f"⏰ وضعیت تایمرها به {status} تغییر کرد.", reply_markup=get_settings_menu(user_id))
            return
        elif text == "⏱ تایم اپلود دیلیت فایل":
            data_store.update_user_state(user_id, "set_delete_upload_file_timeout")
            current_val = data_store.timer_settings.get("delete_upload_file_timeout", 60)
            bot.send_message(
                user_id,
                f"⏱ مدت زمان تا حذف فایل اپلود دیلیت را (بر حسب ثانیه) وارد کنید:\n(فعلی: {current_val} ثانیه)",
                reply_markup=get_back_menu()
            )
            return
        elif text == inline_buttons_btn_text:
            data_store.timer_settings["inline_buttons_enabled"] = not inline_buttons_enabled
            data_store.save_data()
            status = "فعال" if data_store.timer_settings["inline_buttons_enabled"] else "غیرفعال"
            bot.send_message(user_id, f"🔗 وضعیت کلیدهای شیشه‌ای به {status} تغییر کرد.", reply_markup=get_settings_menu(user_id))
            return
        elif text == "✅ تبعیض برای اونر: فعال" or text == "❌ تبعیض برای اونر: غیرفعال":
            data_store.timer_settings["owner_discrimination"] = not data_store.timer_settings.get("owner_discrimination", False)
            data_store.save_data()
            bot.send_message(user_id, "وضعیت تبعیض اونر تغییر کرد.", reply_markup=get_settings_menu(user_id))
            return
        elif text.startswith("⏳ مقدار زمان خستگی"):
            data_store.update_user_state(user_id, "set_coinpy_timeout")
            bot.send_message(user_id, "مقدار جدید زمان خستگی (دقیقه) را وارد کنید:", reply_markup=get_back_menu())
            return
        elif text == coinpy_btn_text:
            data_store.update_user_state(user_id, "set_coinpy_daily_limit")
            bot.send_message(user_id, "مقدار جدید سقف دانلود روزانه کرکفای را وارد کنید (عدد صحیح):", reply_markup=get_back_menu())
            return
        elif text == "🏠 تنظیمات پیش‌فرض":
            data_store.update_user_state(user_id, "set_default_settings")
            bot.send_message(user_id, "متن خوش‌آمدگویی پیش‌فرض جدید را وارد کنید:", reply_markup=get_settings_menu(user_id))
            return
        elif text == "---- 💠 تنظیمات ساخت پست 💠 ----":
            bot.send_message(user_id, "این دکمه تزئینی است", reply_markup=get_settings_menu(user_id))
            return
        elif text == "✍️ تنظیم امضا":
            data_store.update_user_state(user_id, "signature_management")
            bot.send_message(user_id, "✍️ مدیریت امضاها:\nیکی از گزینه‌های زیر را انتخاب کنید.", reply_markup=get_signature_management_menu())
            return
        elif text == "⚙️ مدیریت متغیرها":
            data_store.update_user_state(user_id, "variable_management")
            bot.send_message(user_id, "⚙️ مدیریت متغیرها:\nیکی از گزینه‌های زیر را انتخاب کنید.", reply_markup=get_variable_management_menu())
            return
        elif text == "📝 مدیریت مقادیر پیش‌فرض":
            data_store.update_user_state(user_id, "default_values_management")
            bot.send_message(user_id, "📝 مدیریت مقادیر پیش‌فرض:\nیکی از گزینه‌های زیر را انتخاب کنید:", reply_markup=get_default_values_management_menu())
            return
        elif text == "📢 ثبت چنل پست":
            data_store.update_user_state(user_id, "register_channel")
            bot.send_message(user_id, "آیدی چنل را وارد کنید (مثال: @channelname):", reply_markup=back_settings())
            return
        elif text == "---- 🔥 تنظیمات اپلودر و ارسال همگانی 🔥 ----":
            bot.send_message(user_id, "این دکمه تزئینی است", reply_markup=get_settings_menu(user_id))
            return
        elif text == "📢 ثبت چنل اپلودری":
            data_store.update_user_state(user_id, "register_uploader_channel")
            bot.send_message(user_id, "آیدی چنل اپلودری را وارد کنید (مثال: @channelname):", reply_markup=back_settings())
            return
        elif text == "✨ تغییرات اتوماتیک":
            data_store.update_user_state(user_id, "auto_file_menu")
            bot.send_message(user_id, "یکی از گزینه‌های تغییر اتوماتیک فایل را انتخاب کنید:", reply_markup=get_auto_file_menu())
            return
        elif text == "---- 🧭تنظیمات کرکفای 🧭 ----":
            bot.send_message(user_id, "این دکمه تزئینی است", reply_markup=get_settings_menu(user_id))
            return
        # --- دکمه جاسوس چنل ---
        elif text == spy_btn_text:
            data_store.channel_monitor_enabled = not data_store.channel_monitor_enabled
            data_store.save_data()
            status = "✅" if data_store.channel_monitor_enabled else "❌"
            bot.send_message(user_id, f"جاسوس چنل الان: {status}", reply_markup=get_settings_menu(user_id))
            return
        elif text == "🔙 بازگشت به منوی اصلی":
            data_store.reset_user_state(user_id)
            bot.send_message(user_id, "🏠 بازگشت به منوی اصلی:", reply_markup=get_main_menu())
            return
        # اگر هیچ گزینه‌ای نبود
        else:
            bot.send_message(user_id, "❌ گزینه نامعتبر یا ناشناخته!", reply_markup=get_settings_menu(user_id))
            return
            
    if state is None:
        # If user is sending a main-menu button, allow further processing instead of always
        # returning and re-sending the menu. Only auto-show menu for other free-text messages.
        if text and text in MAIN_MENU_BUTTONS:
            # Let main-menu handling flow continue below (do not return here)
            pass
        else:
            if not (is_owner(user_id) or is_admin(user_id)):
                markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
                markup.add(types.KeyboardButton("👤 حساب کاربری"))
                markup.add(types.KeyboardButton(f"🤖 بات دستیار نسخه {BOT_VERSION}"))
                user_info = data_store.user_data.get(str(user_id), {})
                user_name = user_info.get("first_name", "") or ""
                welcome_text = f"سلام {user_name} عزیز!\nبه ربات خوش آمدید 😊\nبرای امکانات بیشتر لطفاً با ادمین ارتباط بگیرید یا اطلاعات حساب کاربری و نسخه را ببینید."
                msg = bot.send_message(user_id, welcome_text, reply_markup=markup)
                data_store.last_message_id[user_id] = msg.message_id
                return
            else:
                # For owners/admins, only auto-send the helper prompt when they didn't press a menu button.
                msg = bot.send_message(user_id, f"🔍 لطفاً یکی از گزینه‌های منو را انتخاب کنید.", reply_markup=get_main_menu(user_id))
                data_store.last_message_id[user_id] = msg.message_id
                return
    
    if state == "signature_management":
        handle_signature_management(user_id, text)
        return

    if state == "select_signature":
        if text in data_store.signatures:
            data_store.update_user_state(user_id, "post_with_signature_media", {"signature_name": text})
            markup = get_back_menu()
            markup.add(types.KeyboardButton("⏭️ رد کردن مرحله رسانه"))
            msg = bot.send_message(user_id, f"📸 عکس یا ویدیو ارسال کنید (یا دکمه زیر برای رد کردن):", reply_markup=markup)
            data_store.last_message_id[user_id] = msg.message_id
        return
        
    if state == "post_with_signature_media":
        if text == "⏭️ پایان ارسال رسانه" or text == "⏭️ رد کردن مرحله رسانه":
            media_paths = user_state["data"].get("media_paths", None)
            data_store.update_user_state(user_id, "post_with_signature_values", {"media_paths": media_paths, "current_var_index": 0})
            sig_name = user_state["data"]["signature_name"]
            signature = data_store.signatures[sig_name]
            variables = signature["variables"]
            
            # مقداردهی اولیه برای متغیرها با استفاده از مقادیر پیش‌فرض
            user_state["data"]["temp_post_content"] = signature["template"]
            variables_without_default = []
            for var in variables:
                if var in data_store.default_values:
                    user_state["data"][var] = data_store.default_values[var]
                else:
                    user_state["data"][var] = f"[{var} وارد نشده]"
                    variables_without_default.append(var)
            
            data_store.update_user_state(user_id, "post_with_signature_values", {
                "media_paths": media_paths,
                "current_var_index": 0,
                "variables_without_default": variables_without_default
            })
            
            if variables_without_default:
                # نمایش اولیه پست
                temp_content = user_state["data"]["temp_post_content"]
                for var in variables:
                    temp_content = temp_content.replace(f"{{{var}}}", user_state["data"][var])
                display_text = f"📝 در حال ساخت پست:\n\n{temp_content}\n\nـــــــــــــــــــــ\n🖊️ مقدار {variables_without_default[0]} را وارد کنید:"
                
                msg = bot.send_message(user_id, display_text, reply_markup=get_back_menu())
                data_store.last_message_id[user_id] = msg.message_id
            else:
                post_content = signature["template"]
                for var in variables:
                    post_content = post_content.replace(f"{{{var}}}", user_state["data"][var])
                data_store.update_user_state(user_id, "add_inline_buttons", {"post_content": post_content, "media_paths": media_paths})
                markup = get_back_menu()
                markup.add(types.KeyboardButton("✅ پایان افزودن کلیدها"))
                msg = bot.send_message(user_id, f"🔗 کلید شیشه‌ای اضافه کنید (نام کلید و لینک را به‌صورت 'نام|لینک' وارد کنید) یا 'پایان افزودن کلیدها' را بزنید:", reply_markup=markup)
                data_store.last_message_id[user_id] = msg.message_id
        return
    
    if state == "post_with_signature_values":
        sig_name = user_state["data"]["signature_name"]
        current_index = user_state["data"].get("current_var_index", 0)
        signature = data_store.signatures[sig_name]
        variables_without_default = user_state["data"].get("variables_without_default", signature["variables"])

        var_name = variables_without_default[current_index]

        if (
            var_name in data_store.default_values
            and not user_state["data"].get(f"{var_name}_asked_default", False)
        ):
            user_state["data"][f"{var_name}_asked_default"] = True
            data_store.update_user_state(user_id, state, user_state["data"])
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
            markup.add(types.KeyboardButton("✅ استفاده شود"), types.KeyboardButton("❌ وارد کنم"))
            markup.add(types.KeyboardButton("🔙 بازگشت به منوی اصلی"))
            msg = bot.send_message(
                user_id,
                f"برای متغیر <code>{var_name}</code> مقدار پیش‌فرض <b>{data_store.default_values[var_name]}</b> وجود دارد.\n"
                "آیا همین مقدار استفاده شود یا خودتان وارد کنید؟",
                reply_markup=markup,
                parse_mode="HTML"
            )
            data_store.last_message_id[user_id] = msg.message_id
            return
        
        if user_state["data"].get(f"{var_name}_asked_default", False):
            if text == "✅ استفاده شود":
                user_state["data"][var_name] = data_store.default_values[var_name]
                current_index += 1
                user_state["data"].pop(f"{var_name}_asked_default", None)
            elif text == "❌ وارد کنم":
                msg = bot.send_message(user_id, f"🖊️ مقدار متغیر '{var_name}' را وارد کنید:", reply_markup=get_back_menu())
                data_store.last_message_id[user_id] = msg.message_id
                user_state["data"][f"{var_name}_manual_mode"] = True
                data_store.update_user_state(user_id, state, user_state["data"])
                return
            elif user_state["data"].get(f"{var_name}_manual_mode", False):
                user_state["data"][var_name] = text
                current_index += 1
                user_state["data"].pop(f"{var_name}_manual_mode", None)
                user_state["data"].pop(f"{var_name}_asked_default", None)
            else:
                return
        elif user_state["data"].get('Link_url_mode', False):
            link_var_name = user_state["data"]['current_link_var']
            # اگر متغیر Link مقدار پیش‌فرض url دارد و هنوز نپرسیده‌ایم
            if (
                link_var_name in data_store.default_values
                and not user_state["data"].get(f"{link_var_name}_asked_link_default", False)
            ):
                user_state["data"][f"{link_var_name}_asked_link_default"] = True
                data_store.update_user_state(user_id, state, user_state["data"])
                markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
                markup.add(types.KeyboardButton("✅ استفاده شود"), types.KeyboardButton("❌ وارد کنم"))
                markup.add(types.KeyboardButton("🔙 بازگشت به منوی اصلی"))
                msg = bot.send_message(
                    user_id,
                    f"برای url لینک <code>{link_var_name}</code> مقدار پیش‌فرض <b>{data_store.default_values[link_var_name]}</b> وجود دارد.\n"
                    "آیا همین مقدار استفاده شود یا خودتان وارد کنید؟",
                    reply_markup=markup,
                    parse_mode="HTML"
                )
                data_store.last_message_id[user_id] = msg.message_id
                return
            # حالت انتخاب مقدار پیش‌فرض url یا دستی
            if user_state["data"].get(f"{link_var_name}_asked_link_default", False):
                if text == "✅ استفاده شود":
                    user_state["data"][f"{link_var_name}_url"] = data_store.default_values[link_var_name]
                    user_state["data"]['Link_url_mode'] = False
                    user_state["data"][link_var_name] = "done"
                    user_state["data"].pop(f"{link_var_name}_asked_link_default", None)
                    current_index += 1
                elif text == "❌ وارد کنم":
                    msg = bot.send_message(user_id, f"🖊️ مقدار url لینک '{link_var_name}' را وارد کنید:", reply_markup=get_back_menu())
                    data_store.last_message_id[user_id] = msg.message_id
                    user_state["data"][f"{link_var_name}_manual_url_mode"] = True
                    data_store.update_user_state(user_id, state, user_state["data"])
                    return
                elif user_state["data"].get(f"{link_var_name}_manual_url_mode", False):
                    user_state["data"][f"{link_var_name}_url"] = text
                    user_state["data"]['Link_url_mode'] = False
                    user_state["data"][link_var_name] = "done"
                    user_state["data"].pop(f"{link_var_name}_asked_link_default", None)
                    user_state["data"].pop(f"{link_var_name}_manual_url_mode", None)
                    current_index += 1
                else:
                    return
            else:
                user_state["data"][f"{link_var_name}_url"] = text
                user_state["data"]['Link_url_mode'] = False
                user_state["data"][link_var_name] = "done"
                current_index += 1

        else:
            var_format = data_store.variables.get(var_name, {}).get("format", "Simple")
            if var_format == "Link":
                # اول متن لینک را دریافت کن، سپس برای url اگر مقدار پیش فرض دارد بپرس
                user_state["data"][f"{var_name}_text"] = text
                user_state["data"]['Link_url_mode'] = True
                user_state["data"]['current_link_var'] = var_name
                msg = bot.send_message(user_id, f"📝 حالا آدرس لینک {var_name} را وارد کن:", reply_markup=get_back_menu())
                data_store.last_message_id[user_id] = msg.message_id
                return
            else:
                user_state["data"][var_name] = text
                current_index += 1
        
        if current_index < len(variables_without_default):
            data_store.update_user_state(user_id, None, {"current_var_index": current_index})
            temp_content = user_state["data"]["temp_post_content"]
            for var in signature["variables"]:
                temp_content = temp_content.replace(f"{{{var}}}", user_state["data"][var])
            display_text = f"📝 در حال ساخت پست:\n\n{temp_content}\n\nـــــــــــــــــــــ\n🖊️ مقدار {variables_without_default[current_index]} را وارد کنید:"
            msg = bot.send_message(user_id, display_text, reply_markup=get_back_menu())
            data_store.last_message_id[user_id] = msg.message_id
        else:
            variables_dict = {}
            for var in signature["variables"]:
                var_format = data_store.variables.get(var, {}).get("format", "Simple")
                if var_format == "Link":
                    text_part = user_state["data"].get(f"{var}_text", "")
                    url_part = user_state["data"].get(f"{var}_url", "")
                    variables_dict[var] = (text_part, url_part)
                else:
                    variables_dict[var] = user_state["data"][var]
            result = format_post_content(signature["template"], variables_dict)
            media_paths = user_state["data"].get("media_paths")
            data_store.update_user_state(user_id, "ask_for_inline_buttons", {"post_content": result, "media_paths": media_paths, "inline_buttons": []})
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
            markup.add(types.KeyboardButton("✅ بله"), types.KeyboardButton("❌ خیر"))
            markup.add(types.KeyboardButton("🔙 بازگشت به منوی اصلی"))
            msg = bot.send_message(user_id, f"🔗 آیا می‌خواهید کلید شیشه‌ای اضافه کنید؟", reply_markup=markup)
            data_store.last_message_id[user_id] = msg.message_id
        return
    
    if state == "ask_for_inline_buttons":
        if text == "✅ بله":
            data_store.update_user_state(user_id, "add_inline_button_name", {"inline_buttons": user_state["data"].get("inline_buttons", []), "row_width": 4})
            markup = get_back_menu()
            msg = bot.send_message(user_id, f"📝 نام کلید شیشه‌ای را وارد کنید:", reply_markup=markup)
            data_store.last_message_id[user_id] = msg.message_id
        elif text == "❌ خیر":
            post_content = user_state["data"].get("post_content", "")
            media_ids = user_state["data"].get("media_ids", None)
            media_paths = user_state["data"].get("media_paths", [])
            inline_buttons = user_state["data"].get("inline_buttons", [])
            data_store.update_user_state(user_id, "post_with_signature_ready", {
                "post_content": post_content,
                "media_ids": media_ids,
                "media_paths": media_paths,
                "inline_buttons": inline_buttons,
                "row_width": 4
            })
            media_ids = user_state["data"].get("media_ids", None)
            if not media_ids and user_state["data"].get("media_paths"):
                # اگر media_ids نداریم اما media_paths داریم، باید آنها را تبدیل کنیم
                media_ids = []
                for media in user_state["data"]["media_paths"]:
                    # فرض: media_paths شامل دیکشنری با type و path است
                    # باید file_id را استخراج کنیم (در صورت امکان)
                    if "file_id" in media:
                        media_ids.append({
                            "type": media["type"],
                            "file_id": media["file_id"]
                        })
            send_post_preview(user_id, post_content, media_ids, inline_buttons, row_width=4)
        return
    
    if state == "add_inline_button_name":
        button_text = text.strip()
        if button_text:
            data_store.update_user_state(user_id, "add_inline_button_url", {
                "inline_buttons": user_state["data"].get("inline_buttons", []),
                "row_width": user_state["data"].get("row_width", 4),
                "button_text": button_text
            })
            markup = get_back_menu()
            msg = bot.send_message(user_id, f"🔗 لینک کلید '{button_text}' را وارد کنید:", reply_markup=markup)
            data_store.last_message_id[user_id] = msg.message_id
        else:
            msg = bot.send_message(user_id, f"⚠️ نام کلید نمی‌تواند خالی باشد! لطفاً یک نام وارد کنید:", reply_markup=get_back_menu())
            data_store.last_message_id[user_id] = msg.message_id
        return
        
    if state == "add_inline_button_url":
        button_url = text.strip()
        if button_url:
            button_text = user_state["data"].get("button_text", "")
            inline_buttons = user_state["data"].get("inline_buttons", [])
            inline_buttons.append({"text": button_text, "url": button_url})
            
            data_store.update_user_state(user_id, "ask_continue_adding_buttons", {"inline_buttons": inline_buttons})
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
            markup.add(types.KeyboardButton("✅ ادامه دادن"), types.KeyboardButton("❌ خیر"))
            markup.add(types.KeyboardButton("🔙 بازگشت به منوی اصلی"))
            
            msg = bot.send_message(user_id, f"✅ کلید '{button_text}' اضافه شد. آیا می‌خواهید کلید دیگری اضافه کنید؟", reply_markup=markup)
            data_store.last_message_id[user_id] = msg.message_id
        else:
            msg = bot.send_message(user_id, f"⚠️ لینک نمی‌تواند خالی باشد! لطفاً یک لینک معتبر وارد کنید:", reply_markup=get_back_menu())
            data_store.last_message_id[user_id] = msg.message_id
        return
    
    if state == "ask_continue_adding_buttons":
        if text == "✅ ادامه دادن":
            data_store.update_user_state(user_id, "select_button_position")
            markup = get_button_layout_menu()
            msg = bot.send_message(user_id, f"📏 نحوه نمایش کلید شیشه‌ای بعدی را انتخاب کنید:", reply_markup=markup)
            data_store.last_message_id[user_id] = msg.message_id
        elif text == "❌ خیر":
            post_content = user_state["data"].get("post_content", "")
            media_paths = user_state["data"].get("media_paths", [])
            inline_buttons = user_state["data"].get("inline_buttons", [])
            data_store.update_user_state(user_id, "post_with_signature_ready", {
                "post_content": post_content,
                "media_paths": media_paths,
                "inline_buttons": inline_buttons,
                "row_width": 4
            })
            send_post_preview(user_id, post_content, media_paths, inline_buttons, row_width=4)
        return
    
    if state == "select_button_position":
        row_width = 4  # کنار هم (پیش‌فرض)
        if text == "📏 به کنار":
            row_width = 4
        elif text == "📐 به پایین":
            row_width = 1
    
        inline_buttons = user_state["data"].get("inline_buttons", [])
        data_store.update_user_state(user_id, "add_inline_button_name", {
            "inline_buttons": inline_buttons,
            "row_width": row_width
        })
        markup = get_back_menu()
        msg = bot.send_message(user_id, f"📝 نام کلید شیشه‌ای بعدی را وارد کنید:", reply_markup=markup)
        data_store.last_message_id[user_id] = msg.message_id
        return

    if state == "post_with_signature_ready":
        if text == "🚀 ارسال فوری":
            if not data_store.channels:
                msg = bot.send_message(user_id, f"⚠️ هیچ چنلی ثبت نشده است. ابتدا یک چنل ثبت کنید.", reply_markup=get_back_menu())
                data_store.last_message_id[user_id] = msg.message_id
                return
            
            # نمایش لیست چنل‌ها برای انتخاب
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
            for channel in data_store.channels:
                markup.add(types.KeyboardButton(channel))
            markup.add(types.KeyboardButton("🔙 بازگشت به منوی اصلی"))
            data_store.update_user_state(user_id, "select_channel_for_post", {
                "post_content": user_state["data"].get("post_content", ""),
                "media_paths": user_state["data"].get("media_paths", []),
                "inline_buttons": user_state["data"].get("inline_buttons", []),
                "row_width": user_state["data"].get("row_width", 4)
            })
            msg = bot.send_message(user_id, f"📢 چنل مقصد را انتخاب کنید:", reply_markup=markup)
            data_store.last_message_id[user_id] = msg.message_id
            return
    
    if state == "select_channel_for_post":
        if text in data_store.channels:
            post_content = user_state["data"].get("post_content", "")
            media_paths = user_state["data"].get("media_paths", [])
            # اگر media_paths تهی بود، media_ids را هم چک کن
            if not media_paths:
                media_paths = user_state["data"].get("media_ids", [])
            inline_buttons = user_state["data"].get("inline_buttons", [])
            row_width = user_state["data"].get("row_width", 4)
            channel = text
    
            inline_keyboard = None
            if data_store.timer_settings.get("inline_buttons_enabled", True) and inline_buttons:
                inline_keyboard = types.InlineKeyboardMarkup(row_width=row_width)
                for button in inline_buttons:
                    inline_keyboard.add(types.InlineKeyboardButton(button["text"], url=button["url"]))
    
            if media_paths:
                logger.info(f"[POST SEND] ارسال پست با مدیا به چنل {channel} :: تعداد رسانه: {len(media_paths)}")
                for i, media in enumerate(media_paths):
                    try:
                        logger.info(f"[POST SEND] مدیا #{i}: {media}")
                        if "uploader_channel" in media and "uploader_msg_id" in media:
                            logger.info(
                                f"[POST SEND] copy_message(channel={channel}, uploader_channel={media['uploader_channel']}, uploader_msg_id={media['uploader_msg_id']}, caption={(post_content if i==0 else None)})"
                            )
                            bot.copy_message(
                                channel,
                                media["uploader_channel"],
                                media["uploader_msg_id"],
                                caption=post_content if i == 0 else None,
                                reply_markup=inline_keyboard if i == 0 else None,
                                parse_mode="HTML"
                            )
                            logger.info(f"[POST SEND] copy_message موفق برای مدیا #{i}")
                        elif "file_id" in media:
                            # اگر فایل photo یا video باشد
                            if media["type"] == "photo":
                                bot.send_photo(
                                    channel, media["file_id"],
                                    caption=post_content if i == 0 else None,
                                    reply_markup=inline_keyboard if i == 0 else None,
                                    parse_mode="HTML"
                                )
                            elif media["type"] == "video":
                                bot.send_video(
                                    channel, media["file_id"],
                                    caption=post_content if i == 0 else None,
                                    reply_markup=inline_keyboard if i == 0 else None,
                                    parse_mode="HTML"
                                )
                            else:
                                bot.send_document(
                                    channel, media["file_id"],
                                    caption=post_content if i == 0 else None,
                                    reply_markup=inline_keyboard if i == 0 else None,
                                    parse_mode="HTML"
                                )
                            logger.info(f"[POST SEND] send_media موفق برای مدیا #{i}")
                        else:
                            logger.warning(f"[POST SEND] مدیا #{i} فاقد uploader_channel/uploader_msg_id یا file_id بود: {media}")
                            bot.send_message(channel, "⚠️ فقط مدیا از چنل اپلودر مجاز است.", reply_markup=get_main_menu(user_id))
                    except Exception as e:
                        logger.error(f"[POST SEND] خطا در ارسال مدیا #{i}: {e}")
            else:
                logger.info(f"[POST SEND] ارسال پست بدون مدیا به {channel}")
                bot.send_message(channel, post_content, reply_markup=inline_keyboard, parse_mode="HTML")
                
            msg = bot.send_message(user_id, f"✅ پست با موفقیت به {channel} ارسال شد.\n🏠 منوی اصلی:", reply_markup=get_main_menu(user_id))
            data_store.last_message_id[user_id] = msg.message_id
            data_store.reset_user_state(user_id)
            return

    if state == "post_with_signature_ready":
        if text == "🆕 پست جدید":
            data_store.reset_user_state(user_id)
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
            for sig_name in data_store.signatures.keys():
                markup.add(types.KeyboardButton(sig_name))
            markup.add(types.KeyboardButton("🔙 بازگشت به منوی اصلی"))
            data_store.update_user_state(user_id, "select_signature")
            msg = bot.send_message(user_id, f"🖊️ امضای مورد نظر را انتخاب کنید:", reply_markup=markup)
            data_store.last_message_id[user_id] = msg.message_id
    
        elif text == "⏰ زمان‌بندی پست":
            if not data_store.channels:
                msg = bot.send_message(
                    user_id,
                    f"⚠️ هیچ چنلی ثبت نشده است. ابتدا یک چنل ثبت کنید.",
                    reply_markup=get_back_menu()
                )
                data_store.last_message_id[user_id] = msg.message_id
            else:
                channels_list = "\n".join(data_store.channels)
                # زمان پیشنهادی را به شمسی بنویس
                one_minute_later = datetime.now() + timedelta(minutes=1)
                shamsi_time = jdatetime.datetime.fromgregorian(datetime=one_minute_later).strftime("%Y/%m/%d %H:%M")
                data_store.update_user_state(user_id, "schedule_post")
                msg = bot.send_message(
                    user_id,
                    f"📢 چنل‌های ثبت‌شده:\n{channels_list}\n\n"
                    f"⏰ زمان پیشنهادی: \n<blockquote><code>{shamsi_time}</code></blockquote>\n"
                    f"لطفاً چنل و زمان آینده را وارد کنید (مثال: <code>@channel {shamsi_time}</code>)\n"
                    f"⚠️ تاریخ را به صورت هجری شمسی وارد کنید.",
                    reply_markup=get_back_menu(),
                    parse_mode="HTML"
                )
                data_store.last_message_id[user_id] = msg.message_id
        return
    
    if state == "schedule_post":
        try:
            parts = text.split()
            tehran_tz = pytz.timezone('Asia/Tehran')
            if len(parts) < 3:
                one_minute_later = (datetime.now(tehran_tz) + timedelta(minutes=1)).strftime("%Y/%m/%d %H:%M")
                msg = bot.send_message(user_id, f"⚠️ لطفاً چنل و زمان آینده را وارد کنید (مثال: <code>@channel {one_minute_later}</code>)", reply_markup=get_back_menu(), parse_mode="HTML")
                data_store.last_message_id[user_id] = msg.message_id
                return
        
            channel = parts[0]
            time_str = " ".join(parts[1:])
            # تبدیل تاریخ شمسی به میلادی
            shamsi_dt = jdatetime.datetime.strptime(time_str, "%Y/%m/%d %H:%M")
            scheduled_time = shamsi_dt.togregorian()
            scheduled_time = tehran_tz.localize(scheduled_time)
        
            if scheduled_time <= datetime.now(tehran_tz):
                one_minute_later = (datetime.now(tehran_tz) + timedelta(minutes=1)).strftime("%Y/%m/%d %H:%M")
                msg = bot.send_message(user_id, f"⚠️ فقط زمان آینده قابل قبول است! زمان پیشنهادی: <code>{one_minute_later}</code>", reply_markup=get_back_menu(), parse_mode="HTML")
                data_store.last_message_id[user_id] = msg.message_id
                return
        
            if channel not in data_store.channels:
                one_minute_later = (datetime.now(tehran_tz) + timedelta(minutes=1)).strftime("%Y/%m/%d %H:%M")
                msg = bot.send_message(user_id, f"⚠️ این چنل ثبت نشده است. ابتدا چنل را ثبت کنید. زمان پیشنهادی: <code>{one_minute_later}</code>", reply_markup=get_back_menu(), parse_mode="HTML")
                data_store.last_message_id[user_id] = msg.message_id
                return
        
            post_content = user_state["data"].get("post_content", "")
            media_paths = user_state["data"].get("media_paths", [])
            media_ids = user_state["data"].get("media_ids", [])
            inline_buttons = user_state["data"].get("inline_buttons", [])
            row_width = user_state["data"].get("row_width", 4)
            
            job_id = str(uuid.uuid4())
            data_store.scheduled_posts.append({
                "job_id": job_id,
                "channel": channel,
                "time": time_str,
                "post_content": post_content,
                "media_paths": media_paths if media_paths else [],
                "media_ids": media_ids if media_ids else [],
                "inline_buttons": inline_buttons,
                "row_width": row_width
            })
            data_store.save_data()
        
            # تبدیل زمان به تاریخ شمسی (ایرانی/جلالی)
            shamsi_time = jdatetime.datetime.fromgregorian(datetime=scheduled_time).strftime("%Y/%m/%d %H:%M")
            channel_time_str = f"{channel} - {shamsi_time}"
        
            schedule_time_str = scheduled_time.astimezone(tehran_tz).strftime("%H:%M")
            schedule.every().day.at(schedule_time_str).do(send_scheduled_post, job_id=job_id).tag(job_id)
            markup = get_main_menu(user_id)
            msg = bot.send_message(
                user_id, 
                f"✅ پست برای ارسال به {channel_time_str} (تاریخ شمسی) زمان‌بندی شد.\n منوی اصلی:", 
                reply_markup=markup
            )
            data_store.last_message_id[user_id] = msg.message_id
            data_store.reset_user_state(user_id)
        except ValueError:
            tehran_tz = pytz.timezone('Asia/Tehran')
            one_minute_later = (datetime.now(tehran_tz) + timedelta(minutes=1)).strftime("%Y/%m/%d %H:%M")
            msg = bot.send_message(user_id, f"⚠️ فرمت زمان اشتباه است! از yyyy/mm/dd hh:mm استفاده کنید. زمان پیشنهادی: <code>{one_minute_later}</code>", reply_markup=get_back_menu(), parse_mode="HTML")
            data_store.last_message_id[user_id] = msg.message_id
        except Exception as e:
            logger.error(f"خطا در تنظیم تایمر: {e}")
            tehran_tz = pytz.timezone('Asia/Tehran')
            one_minute_later = (datetime.now(tehran_tz) + timedelta(minutes=1)).strftime("%Y/%m/%d %H:%M")
            msg = bot.send_message(user_id, f"⚠️ یه مشکلی پیش اومد. دوباره امتحان کنید. زمان پیشنهادی: <code>{one_minute_later}</code>", reply_markup=get_back_menu(), parse_mode="HTML")
            data_store.last_message_id[user_id] = msg.message_id
        return
    
    if state == "new_signature_name":
        if text in data_store.signatures:
            try:
                bot.edit_message_text(
                    chat_id=user_id,
                    message_id=data_store.last_message_id[user_id],
                    text=f"⚠️ این نام امضا قبلاً وجود دارد.\n✏️ نام دیگری وارد کنید:",
                    reply_markup=get_back_menu()
                )
            except Exception as e:
                logger.error(f"خطا در ویرایش پیام: {e}")
                msg = bot.send_message(user_id, f"⚠️ این نام امضا قبلاً وجود دارد.\n✏️ نام دیگری وارد کنید:", reply_markup=get_back_menu())
                data_store.last_message_id[user_id] = msg.message_id
        else:
            data_store.update_user_state(user_id, "new_signature_template", {"new_sig_name": text})
            example = "[5253877736207821121] {name}\n[5256160369591723706] {description}\n[5253864872780769235] {version}"
            msg = bot.send_message(user_id, f"🖊️ قالب امضا را وارد کنید.\nمثال:\n{example}", reply_markup=get_back_menu())
            data_store.last_message_id[user_id] = msg.message_id
        return
    
    if state == "new_signature_template":
        template = text
        sig_name = user_state["data"]["new_sig_name"]
        variables = re.findall(r'\{(\w+)\}', template)
        
        if not variables:
            try:
                bot.edit_message_text(
                    chat_id=user_id,
                    message_id=data_store.last_message_id[user_id],
                    text=f"⚠️ حداقل یک متغیر با فرمت {{variable_name}} وارد کنید.",
                    reply_markup=get_back_menu()
                )
            except Exception as e:
                logger.error(f"خطا در ویرایش پیام: {e}")
                msg = bot.send_message(user_id, f"⚠️ حداقل یک متغیر با فرمت {{variable_name}} وارد کنید.", reply_markup=get_back_menu())
                data_store.last_message_id[user_id] = msg.message_id
            return
        
        undefined_vars = [var for var in variables if var not in data_store.variables]
        if undefined_vars:
            msg = bot.send_message(
                user_id,
                f"⚠️ متغیرهای زیر تعریف نشده‌اند: {', '.join(undefined_vars)}\nلطفاً ابتدا این متغیرها را در بخش 'مدیریت متغیرها' تعریف کنید.",
                reply_markup=get_back_menu()
            )
            data_store.last_message_id[user_id] = msg.message_id
            return
        
        data_store.signatures[sig_name] = {
            "template": template,
            "variables": variables
        }
        data_store.save_data()
        
        markup = get_main_menu(user_id)
        msg = bot.send_message(user_id, f"✅ امضای جدید '{sig_name}' ایجاد شد.\n🏠 منوی اصلی:", reply_markup=markup)
        data_store.last_message_id[user_id] = msg.message_id
        
        data_store.reset_user_state(user_id)
        return
    
    if state == "delete_signature":
        if text in data_store.signatures:
            del data_store.signatures[text]
            data_store.save_data()
            markup = get_signature_management_menu()
            msg = bot.send_message(user_id, f"✅ امضای '{text}' حذف شد.\n✍️ مدیریت امضاها:", reply_markup=markup)
            data_store.last_message_id[user_id] = msg.message_id
            data_store.update_user_state(user_id, "signature_management")
        else:
            msg = bot.send_message(user_id, f"⚠️ امضای انتخاب‌شده وجود ندارد.", reply_markup=get_signature_management_menu())
            data_store.last_message_id[user_id] = msg.message_id
        return
    
    if state == "admin_management":
        msg = bot.send_message(user_id,f"⛔️ قابلیت مدیریت ادمین‌ها حذف شده است.",reply_markup=get_main_menu(user_id))
        data_store.last_message_id[user_id] = msg.message_id
        return
    
    if state in ["variable_management", "select_variable_format", "add_variable", "remove_variable"]:
        handle_variable_management(user_id, text)
        return
    
    if state == "set_default_settings":
        user_id = message.from_user.id
        text = message.text
        if text == "🔙 بازگشت به تنظیمات ربات":
            data_store.update_user_state(user_id, "settings_menu")
            bot.send_message(user_id, "🏛 تنظیمات ربات:", reply_markup=get_settings_menu(user_id))
            return
        try:
            if not text.strip():
                msg = bot.send_message(user_id, "⚠️ متن خوش‌آمدگویی نمی‌تواند خالی باشد.", reply_markup=get_back_menu())
                data_store.last_message_id[user_id] = msg.message_id
                return
            if "default_welcome" not in data_store.settings:
                data_store.settings["default_welcome"] = ""
            data_store.settings["default_welcome"] = text.strip()
            data_store.save_data()
            markup = get_main_menu(user_id)
            msg = bot.send_message(user_id, f"✅ متن خوش‌آمدگویی تنظیم شد:\n{text}\n🏠 منوی اصلی:", reply_markup=markup)
            data_store.last_message_id[user_id] = msg.message_id
            data_store.reset_user_state(user_id)
        except Exception as e:
            logger.error(f"خطا در تنظیم پیام خوش‌آمدگویی برای کاربر {user_id}: {str(e)}")
            msg = bot.send_message(user_id, "⚠️ خطایی رخ داد. لطفاً دوباره امتحان کنید.", reply_markup=get_back_menu())
            data_store.last_message_id[user_id] = msg.message_id
    
    if state == "register_channel":
        channel_name = text.strip()
        if channel_name == "🔙 بازگشت به تنظیمات ربات":
            data_store.update_user_state(user_id, "settings_menu")
            bot.send_message(user_id, "🏛 تنظیمات ربات:", reply_markup=get_settings_menu(user_id))
            return
        if not channel_name.startswith('@'):
            msg = bot.send_message(user_id, f"⚠️ آیدی چنل باید با @ شروع شود (مثال: @channelname).", reply_markup=get_settings_menu(user_id))
            data_store.last_message_id[user_id] = msg.message_id
            return
        try:
            chat = bot.get_chat(channel_name)
            bot_member = bot.get_chat_member(channel_name, bot.get_me().id)
            if bot_member.status not in ['administrator', 'creator']:
                permissions_text = "ربات باید حتماً ادمین چنل باشد!"
                msg = bot.send_message(user_id, f"❌ {permissions_text}\nحتماً ربات را به عنوان ادمین به چنل اضافه کنید.", reply_markup=get_back_menu())
                data_store.last_message_id[user_id] = msg.message_id
                return
            # استخراج دسترسی‌ها طبق تصویر و به صورت فارسی
            can_change_info = getattr(bot_member, 'can_change_info', False)
            can_post_messages = getattr(bot_member, 'can_post_messages', False)
            can_edit_messages = getattr(bot_member, 'can_edit_messages', False)
            can_delete_messages = getattr(bot_member, 'can_delete_messages', False)
            can_post_stories = getattr(bot_member, 'can_post_stories', False)
            can_edit_stories = getattr(bot_member, 'can_edit_stories', False)
            can_delete_stories = getattr(bot_member, 'can_delete_stories', False)
            can_invite_via_link = getattr(bot_member, 'can_invite_users', False)
            can_add_admins = getattr(bot_member, 'can_promote_members', False)
            
            required_permissions = [
                ("تغییر تنظیمات چنل", can_change_info),
                ("ارسال پیام", can_post_messages),
                ("ویرایش پیام دیگران", can_edit_messages),
                ("حذف پیام دیگران", can_delete_messages),
                ("ارسال استوری", can_post_stories),
                ("ویرایش استوری دیگران", can_edit_stories),
                ("حذف استوری دیگران", can_delete_stories),
                ("دعوت کاربران با لینک", can_invite_via_link),
                ("افزودن ادمین جدید", can_add_admins)
            ]
            if not all(granted for _, granted in required_permissions):
                permissions_text = "\n".join(
                    f"{name}: {'✅' if granted else '❌'}" for name, granted in required_permissions
                )
                msg = bot.send_message(
                    user_id,
                    f"❌ همه مجوزهای زیر باید فعال باشد:\n{permissions_text}\nلطفاً همه دسترسی‌ها را بدهید و دوباره امتحان کنید.",
                    reply_markup=get_back_menu()
                )
                data_store.last_message_id[user_id] = msg.message_id
                return
            if channel_name in data_store.channels:
                msg = bot.send_message(user_id, f"⚠️ این چنل قبلاً ثبت شده است.", reply_markup=get_back_menu())
                data_store.last_message_id[user_id] = msg.message_id
                return
            data_store.channels.append(channel_name)
            data_store.save_data()
            permissions_text = "\n".join(
                f"{name}: ✅" for name, _ in required_permissions
            )
            markup = get_main_menu(user_id)
            msg = bot.send_message(user_id, f"{permissions_text}\n✅ چنل {channel_name} ثبت شد و همه دسترسی‌ها چک شد.\n🏠 منوی اصلی:", reply_markup=markup)
            data_store.last_message_id[user_id] = msg.message_id
            data_store.reset_user_state(user_id)
            return
        except Exception as e:
            logger.error(f"خطا در بررسی دسترسی چنل {channel_name}: {e}")
            err_text = str(e)
            if "member list is inaccessible" in err_text or "USER_NOT_PARTICIPANT" in err_text or "not enough rights" in err_text or "Bad Request" in err_text:
                msg = bot.send_message(
                    user_id,
                    f"❌ ربات عضو چنل <b>{channel_name}</b> نیست یا ادمین نشده است و نمی‌تواند به چنل دسترسی داشته باشد.\n"
                    f"حتماً ربات را به عنوان ادمین به چنل اضافه کنید و دوباره تلاش کنید.",
                    parse_mode="HTML",
                    reply_markup=get_back_menu()
                )
                data_store.last_message_id[user_id] = msg.message_id
            else:
                msg = bot.send_message(user_id, f"⚠️ خطا در بررسی چنل {channel_name}. لطفاً مطمئن شوید که ربات به چنل دسترسی دارد و دوباره امتحان کنید.", reply_markup=get_back_menu())
                data_store.last_message_id[user_id] = msg.message_id
            return

    if state == "broadcast_timer_or_instant":
        if text == "⏰ ارسال تایمردار":
            data_store.update_user_state(user_id, "broadcast_wait_for_timer", user_state["data"])
            bot.send_message(user_id, "⏰ برای تایمر زمان را وارد کنید :\nاین زمان باید متعلق به آینده باشد.\nباید در قالب yyyy/mm/dd hh:mm باشد.\nبه عنوان مثال زمان حال در ۵ دقیقه بعد:\n<code>{example}</code>", reply_markup=get_back_menu())
            return
        if text == "🚀 ارسال فوری":
            broadcast_mode = user_state["data"].get("broadcast_mode")
            broadcast_msg = user_state["data"].get("broadcast_message")
            send_broadcast_instant(user_id, broadcast_msg, broadcast_mode)
            # پیام موفقیت بعد از ارسال واقعی (در send_broadcast_instant انجام می‌شود)
            data_store.reset_user_state(user_id)
            return
        bot.send_message(user_id, "لطفاً یکی از گزینه‌های ارسال را انتخاب کنید:", reply_markup=get_back_menu())
        return

def process_main_menu_button(user_id, text):
    user_state = data_store.get_user_state(user_id)
    state = user_state["state"]

    if text == "🔙 بازگشت به منوی اصلی":
        data_store.reset_user_state(user_id)
        bot.send_message(user_id, "🏠 بازگشت به منوی اصلی:", reply_markup=get_main_menu(user_id))
        return True

    if text == "🛡 مدیریت چنل":
        # فقط اونر یا ادمینی که manage_channel دارد مجاز است
        perm = data_store.admin_permissions.get(str(user_id), {}) if is_admin(user_id) else {}
        if not (is_owner(user_id) or (is_admin(user_id) and perm.get("manage_channel", False))):
            bot.send_message(user_id, "⛔️ فقط مالک یا ادمین با دسترسی مدیریت چنل می‌تواند این بخش را مشاهده کند.", reply_markup=get_main_menu(user_id))
            return True
        data_store.update_user_state(user_id, "channel_management_menu")
        bot.send_message(user_id, "مدیریت چنل:", reply_markup=get_channel_management_menu())
        return True

    if text == "⏰ مدیریت تایمرها":
        timers = data_store.scheduled_posts
        if not timers:
            bot.send_message(user_id, "⏰ هیچ تایمری ثبت نشده است.", reply_markup=get_main_menu(user_id))
            return True
        msg = "⏰ تایمرهای تنظیم‌شده:\n"
        markup = types.InlineKeyboardMarkup(row_width=1)
        for t in timers:
            job_id = t.get("job_id", "نامشخص")
            channel = t.get("channel", "نامشخص")
            time_str = t.get("time", "نامشخص")
            files = []
            for media in t.get("media_paths", []) + t.get("media_ids", []):
                info = ""
                if "file_id" in media:
                    info = f'file: {media["file_id"]}'
                if "type" in media:
                    info += f', نوع: {media["type"]}'
                if "file_id" in media and hasattr(bot, 'get_file'):
                    try:
                        fi = bot.get_file(media["file_id"])
                        size_mb = fi.file_size / (1024*1024)
                        info += f', حجم: MB {size_mb:.2f}'
                    except: pass
                files.append(info)
            files_text = "\n".join(files) if files else "-"
            msg += (
                f"\n🆔 <code>{job_id}</code>\n"
                f"چنل: <b>{channel}</b>\n"
                f"زمان: <b>{time_str}</b>\n"
                f"فایل:\n{files_text}\n"
                f"وضعیت: در انتظار\n"
            )
            markup.add(types.InlineKeyboardButton(f"حذف تایمر {job_id}", callback_data=f"delete_timer_{job_id}"))
        bot.send_message(user_id, msg, reply_markup=markup, parse_mode="HTML")
        return True

    if text == "🆕 ایجاد پست":
        if not (is_owner(user_id) or is_admin(user_id)):
            bot.send_message(user_id, "⛔️ دسترسی ندارید.", reply_markup=get_main_menu(user_id))
            return True
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        for sig_name in data_store.signatures.keys():
            markup.add(types.KeyboardButton(sig_name))
        markup.add(types.KeyboardButton("🔙 بازگشت به منوی اصلی"))
        data_store.update_user_state(user_id, "select_signature")
        bot.send_message(user_id, "🖊️ امضای مورد نظر را انتخاب کنید:", reply_markup=markup)
        return True

    if text == "📤 اپلودر":
        data_store.update_user_state(user_id, "uploader_menu", {})
        bot.send_message(user_id, "📤 اپلودر:\nیکی از گزینه‌های زیر را انتخاب کنید.", reply_markup=get_uploader_menu())
        return True

    if text == "📣 ارسال همگانی":
        if not (is_owner(user_id) or (is_admin(user_id) and data_store.admin_permissions.get(str(user_id), {}).get("broadcast_management", False))):
            bot.send_message(user_id, "⛔️ دسترسی به ارسال همگانی ندارید.", reply_markup=get_main_menu(user_id))
            return True
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        markup.add(types.KeyboardButton("🗨️ ارسال با نقل قول"), types.KeyboardButton("✉️ ارسال بدون نقل قول"))
        markup.add(types.KeyboardButton("🔙 بازگشت به منوی اصلی"))
        data_store.update_user_state(user_id, "broadcast_choose_mode", {})
        bot.send_message(user_id, "لطفاً روش ارسال همگانی را انتخاب کنید:", reply_markup=markup)
        return True

    if text == "🤖 ربات ساز":
        perm = data_store.admin_permissions.get(str(user_id), {}) if is_admin(user_id) else {}
        if not (is_owner(user_id) or (is_admin(user_id) and perm.get("bot_creator", False))):
            bot.send_message(user_id, "⛔️ فقط مالک یا ادمین با دسترسی ربات ساز می‌تواند این بخش را مشاهده کند.", reply_markup=get_main_menu(user_id))
            return True
        # اینجا فقط وارد منوی ربات ساز شو (نه وارد مرحله وارد کردن آیدی مالک)
        data_store.update_user_state(user_id, "bot_creator_menu")
        bot.send_message(user_id, "منوی ربات ساز را انتخاب کنید:", reply_markup=get_bot_creator_menu())
        return True

    if text == "👥 مدیریت کاربران":
        if not is_owner(user_id):
            bot.send_message(user_id, "⛔️ فقط اونر به این بخش دسترسی دارد.", reply_markup=get_main_menu(user_id))
            return True
        data_store.update_user_state(user_id, "admin_management")
        bot.send_message(user_id, "👤 مدیریت ادمین‌ها:", reply_markup=get_admin_management_menu())
        return True

    if text == "⚡️ امکانات اجباری":
        perm = data_store.admin_permissions.get(str(user_id), {}) if is_admin(user_id) else {}
        if not (is_owner(user_id) or (is_admin(user_id) and perm.get("forced_management", False))):
            bot.send_message(user_id, "⛔️ فقط مالک یا ادمین با دسترسی امکانات اجباری می‌تواند این بخش را مشاهده کند.", reply_markup=get_main_menu(user_id))
            return True
        bot.send_message(user_id, "⚡️ امکانات اجباری:\n\nبرای مدیریت چنل اجباری و سین اجباری یکی از دکمه‌های زیر را انتخاب کنید.", reply_markup=get_forced_features_menu())
        data_store.update_user_state(user_id, "forced_features_menu")
        return True

    if text == "🛒 کرکفای":
        handle_character_marketplace(type("msg", (), {"from_user": type("u", (), {"id": user_id}), "text": text})())
        return True

    if text == "🏛 تنظیمات ربات":
        # فقط اونر یا ادمینی که options_management دارد
        perm = data_store.admin_permissions.get(str(user_id), {}) if is_admin(user_id) else {}
        if not (is_owner(user_id) or (is_admin(user_id) and perm.get("options_management", False))):
            bot.send_message(user_id, "⛔️ فقط مالک یا ادمین با دسترسی تنظیمات می‌تواند این بخش را مشاهده کند.", reply_markup=get_main_menu(user_id))
            return True
        bot.send_message(user_id, "🏛 تنظیمات ربات:", reply_markup=get_settings_menu(user_id))
        data_store.update_user_state(user_id, "settings_menu")
        return True

    if text == "👤 حساب کاربری":
        handle_user_account(type("msg", (), {"from_user": type("u", (), {"id": user_id}), "text": text})())
        return True

    if text == f"🤖 بات دستیار نسخه {BOT_VERSION}":
        bot.send_message(user_id, f"🤖 این بات دستیار نسخه {BOT_VERSION} است.\nتوسعه توسط @py_zon", reply_markup=get_main_menu(user_id))
        return True

    return False

# مدیریت امضاها
def handle_signature_management(user_id, text):
    user_state = data_store.get_user_state(user_id)
    state = user_state["state"]

    if text == "👀 مشاهده امضاها":
        signatures_text = f"📋 لیست امضاها:\n\n"
        if not data_store.signatures:
            signatures_text += "هیچ امضایی وجود ندارد.\n"
        else:
            for sig_name, sig_data in data_store.signatures.items():
                template = sig_data["template"]
                variables = sig_data["variables"]
                preview_content = template
                for var in variables:
                    var_format = data_store.variables.get(var, {}).get("format") or data_store.controls.get(var, {}).get("format", "Simple")
                    if var_format == "Link":
                        preview_content = preview_content.replace(f"{{{var}}}", f"<a href='https://pyzon.ir'>{{var}}</a>")
                    elif var_format == "Bold":
                        preview_content = preview_content.replace(f"{{{var}}}", f"<b>{{var}}</b>")
                    elif var_format == "Italic":
                        preview_content = preview_content.replace(f"{{{var}}}", f"<i>{{var}}</i>")
                    elif var_format == "Code":
                        preview_content = preview_content.replace(f"{{{var}}}", f"<code>{{var}}</code>")
                    elif var_format == "Strike":
                        preview_content = preview_content.replace(f"{{{var}}}", f"<s>{{var}}</s>")
                    elif var_format == "Underline":
                        preview_content = preview_content.replace(f"{{{var}}}", f"<u>{{var}}</u>")
                    elif var_format == "Spoiler":
                        preview_content = preview_content.replace(f"{{{var}}}", f"<tg-spoiler>{{var}}</tg-spoiler>")
                    elif var_format == "BlockQuote":
                        preview_content = preview_content.replace(f"{{{var}}}", f"<blockquote>{{var}}</blockquote>")
                    else:
                        preview_content = preview_content.replace(f"{{{var}}}", f"{{var}}")
                signatures_text += f"🔹 امضا: {sig_name}\n📝 متن:\n{preview_content}\n\n"
        msg = bot.send_message(user_id, signatures_text, reply_markup=get_signature_management_menu(), parse_mode="HTML")
        data_store.last_message_id[user_id] = msg.message_id

    elif text == "➕ افزودن امضای جدید":
        data_store.update_user_state(user_id, "new_signature_name")
        msg = bot.send_message(user_id, f"✏️ نام امضای جدید را وارد کنید:", reply_markup=get_back_menu())
        data_store.last_message_id[user_id] = msg.message_id
    
    elif text == "🗑️ حذف امضا":
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        for sig_name in data_store.signatures.keys():
            markup.add(types.KeyboardButton(sig_name))
        markup.add(types.KeyboardButton("🔙 بازگشت به منوی اصلی"))
        data_store.update_user_state(user_id, "delete_signature")
        msg = bot.send_message(user_id, f"🗑️ امضای مورد نظر برای حذف را انتخاب کنید:", reply_markup=markup)
        data_store.last_message_id[user_id] = msg.message_id

# مدیریت کنترل‌ها
def get_variable_management_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    view_btn = types.KeyboardButton("👀 مشاهده متغیرها")
    add_btn = types.KeyboardButton("➕ افزودن متغیر")
    remove_btn = types.KeyboardButton("➖ حذف متغیر")
    back_btn = types.KeyboardButton("🔙 بازگشت به تنظیمات ربات")
    markup.add(view_btn, add_btn)
    markup.add(remove_btn, back_btn)
    return markup

def get_text_format_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    formats = [
        "Bold", "Italic", "Code", "Strike",
        "Underline", "Spoiler", "BlockQuote", "Simple", "Link"
    ]
    for fmt in formats:
        markup.add(types.KeyboardButton(fmt))
    markup.add(types.KeyboardButton("🔙 بازگشت به منوی اصلی"))
    return markup

def handle_variable_management(user_id, text):
    user_state = data_store.get_user_state(user_id)
    state = user_state["state"]
    
    if text == "👀 مشاهده متغیرها":
        variables_text = f"⚙️ متغیرها:\n\n"
        if not data_store.variables:
            variables_text += "هیچ متغیری وجود ندارد.\n"
        else:
            for var_name, var_data in data_store.variables.items():
                variables_text += f"🔹 {var_name}: نوع {var_data['format']}\n"
        msg = bot.send_message(user_id, variables_text, reply_markup=get_variable_management_menu())
        data_store.last_message_id[user_id] = msg.message_id
    
    elif text == "➕ افزودن متغیر":
        data_store.update_user_state(user_id, "select_variable_format")
        msg = bot.send_message(user_id, f"🖊️ نوع متغیر را انتخاب کنید:", reply_markup=get_text_format_menu())
        data_store.last_message_id[user_id] = msg.message_id
    
    elif text == "➖ حذف متغیر":
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        for var_name in data_store.variables.keys():
            markup.add(types.KeyboardButton(var_name))
        markup.add(types.KeyboardButton("🔙 بازگشت به منوی اصلی"))
        data_store.update_user_state(user_id, "remove_variable")
        msg = bot.send_message(user_id, f"🗑️ متغیری که می‌خواهید حذف کنید را انتخاب کنید:", reply_markup=markup)
        data_store.last_message_id[user_id] = msg.message_id
            
    elif state == "select_variable_format":
        if text in ["Bold", "Italic", "Code", "Strike", "Underline", "Spoiler", "BlockQuote", "Simple", "Link"]:
            data_store.update_user_state(user_id, "add_variable", {"selected_format": text})
            try:
                bot.send_message(
                    user_id,
                    f"🖊️ نام متغیر جدید را وارد کنید (به انگلیسی، بدون فاصله):",
                    reply_markup=get_back_menu()
                )
            except Exception as e:
                logger.error(f"خطا در ارسال پیام درخواست نام متغیر: {e}")
            return
        else:
            try:
                bot.send_message(
                    user_id,
                    f"⚠️ نوع نامعتبر! لطفاً یکی از گزینه‌های منو را انتخاب کنید.",
                    reply_markup=get_text_format_menu()
                )
            except Exception as e:
                logger.error(f"خطا در ارسال پیام نوع نامعتبر: {e}")
            return
        
    elif user_state["state"] == "add_variable":
        if not re.match(r'^[a-zA-Z0-9_]+$', text):
            msg = bot.send_message(user_id, f"⚠️ نام متغیر باید به انگلیسی و بدون فاصله باشد!", reply_markup=get_back_menu())
            data_store.last_message_id[user_id] = msg.message_id
            return
        if text in data_store.variables:
            msg = bot.send_message(user_id, f"⚠️ این نام متغیر قبلاً وجود دارد!", reply_markup=get_back_menu())
            data_store.last_message_id[user_id] = msg.message_id
            return
        data_store.variables[text] = {"format": user_state["data"]["selected_format"]}
        data_store.save_data()
        msg = bot.send_message(user_id, f"✅ متغیر '{text}' با نوع {user_state['data']['selected_format']} اضافه شد.\n⚙️ مدیریت متغیرها:", reply_markup=get_variable_management_menu())
        data_store.last_message_id[user_id] = msg.message_id
        data_store.update_user_state(user_id, "variable_management")
    
    elif user_state["state"] == "remove_variable":
        if text in data_store.variables:
            del data_store.variables[text]
            data_store.save_data()
            msg = bot.send_message(user_id, f"✅ متغیر '{text}' حذف شد.\n⚙️ مدیریت متغیرها:", reply_markup=get_variable_management_menu())
            data_store.last_message_id[user_id] = msg.message_id
        else:
            msg = bot.send_message(user_id, f"⚠️ متغیر انتخاب‌شده وجود ندارد.", reply_markup=get_variable_management_menu())
            data_store.last_message_id[user_id] = msg.message_id
        data_store.update_user_state(user_id, "variable_management")

    elif user_state["state"] == "remove_variable":
        if text in data_store.variables:
            # چک کن که متغیر توی هیچ امضایی استفاده نشده باشه
            used_in_signatures = []
            for sig_name, sig_data in data_store.signatures.items():
                if text in sig_data["variables"]:
                    used_in_signatures.append(sig_name)
            if used_in_signatures:
                msg = bot.send_message(user_id, f"⚠️ متغیر '{text}' در امضاهای {', '.join(used_in_signatures)} استفاده شده است. ابتدا این امضاها را ویرایش یا حذف کنید.", reply_markup=get_variable_management_menu())
                data_store.last_message_id[user_id] = msg.message_id
                return
            del data_store.variables[text]
            data_store.save_data()

def super_stable_connection_monitor(bot: telebot.TeleBot, check_interval: int = 5):
    """
    مانیتورینگ بسیار پایدار polling با auto-recover و اطلاع‌رسانی به OWNER.
    اگر حتی یک لحظه ارتباط قطع شود یا polling کرش کند، خودش بی‌وقفه ری‌استارت می‌شود.
    """
    def is_telegram_alive():
        try:
            resp = requests.get(f"https://api.telegram.org/bot{bot.token}/getMe", timeout=20)
            ok = resp.status_code == 200 and resp.json().get("ok", False)
            if not ok:
                logger.warning(f"[CHECK] getMe failed: {resp.status_code} {resp.text}")
            return ok
        except Exception as e:
            logger.warning(f"[CHECK] getMe Exception: {e}")
            return False

    def polling_forever():
        """این ترد تا ابد polling را اجرا می‌کند، اگر کرش کند خودش ری‌استارت می‌شود."""
        while True:
            try:
                logger.info("⏳ [POLLING] شروع polling ...")
                bot.polling(non_stop=True, interval=3, timeout=20, long_polling_timeout=30)
            except Exception as e:
                logger.error(f"❌ [POLLING] Exception: {e}\n{traceback.format_exc()}")
                time.sleep(5)

    # فقط یکبار این ترد را اجرا کن!
    polling_thread = threading.Thread(target=polling_forever, daemon=True)
    polling_thread.start()

    # مانیتورینگ: اگر ارتباط واقعا قطع شد/ترد polling مرد، اطلاع بده و ری‌استارت کن
    def monitor():
        nonlocal polling_thread
        last_status = True
        notified_down = False
        while True:
            alive = polling_thread.is_alive() and is_telegram_alive()
            if alive:
                if not last_status:
                    # تازه وصل شده
                    logger.info("✅ [MONITOR] ارتباط دوباره برقرار شد.")
                    try:
                        bot.send_message(OWNER_ID, f"✅ ربات دوباره آنلاین شد! نسخه {BOT_VERSION}")
                    except: pass
                last_status = True
                notified_down = False
            else:
                logger.warning("❌ [MONITOR] ارتباط/ترد polling قطع است. تلاش برای ری‌استارت ...")
                if not notified_down:
                    try:
                        bot.send_message(OWNER_ID, f"❌ ربات آفلاین شد! تلاش برای ری‌استارت... نسخه {BOT_VERSION}")
                    except: pass
                    notified_down = True
                # ری‌استارت ترد polling اگر مرده
                if not polling_thread.is_alive():
                    try:
                        polling_thread2 = threading.Thread(target=polling_forever, daemon=True)
                        polling_thread2.start()
                        polling_thread = polling_thread2
                        logger.info("[MONITOR] ترد جدید polling استارت شد.")
                    except Exception as e:
                        logger.error(f"❌ [MONITOR] ری‌استارت ترد polling: {e}")
                last_status = False
            # اجرای زمان‌بندی schedule if needed
            try:
                schedule.run_pending()
            except Exception as e:
                logger.error(f"❌ [MONITOR] خطا در schedule: {e}")
            time.sleep(check_interval)

    monitor_thread = threading.Thread(target=monitor, daemon=True)
    monitor_thread.start()
    logger.info(f"[MONITOR] ترد مانیتورینگ و polling با فاصله {check_interval} ثانیه استارت شد.")

# ---- MAIN ----
def update_uploader_stats():
    uploader_files_total = 0
    uploader_files_total_size = 0
    for file_info in data_store.uploader_file_map.values():
        ch_link = file_info.get("channel_link")
        if ch_link:
            uploader_files_total += 1
            msg_id = int(ch_link.split("/")[-1])
            for ext in ['jpg', 'jpeg', 'png', 'mp4', 'mov', 'mkv', 'pdf', 'docx', 'zip']:
                fpath = os.path.join("medias", f"{msg_id}.{ext}")
                if os.path.exists(fpath):
                    uploader_files_total_size += os.path.getsize(fpath)
                    break
    uploader_files_total_size_mb = uploader_files_total_size / (1024*1024)
    stats_path = os.path.join("central_data", "stats.json")
    stats = {
        "uploader_files_total": uploader_files_total,
        "uploader_files_total_size_mb": uploader_files_total_size_mb
    }
    with open(stats_path, "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=4)

def periodic_stats_update(interval=300):
    def loop():
        while True:
            update_uploader_stats()
            time.sleep(interval)
    threading.Thread(target=loop, daemon=True).start()
    
def safe_format(template_code, API_TOKEN="", OWNER_USER="", BOT_VERSION="4.2.4", BOT_CHILD_NAME=""):
    if not isinstance(template_code, str):
        raise TypeError("template_code must be str not Message object")
    out = template_code
    out = out.replace("{API_TOKEN}", API_TOKEN if API_TOKEN is not None else "")
    out = out.replace("{OWNER_USER}", str(OWNER_USER) if OWNER_USER is not None else "")
    out = out.replace("{BOT_VERSION}", BOT_VERSION if BOT_VERSION else "4.2.4")
    out = out.replace("{BOT_CHILD_NAME}", BOT_CHILD_NAME if BOT_CHILD_NAME else "")
    return out

def kill_previous_baby_bots(folder):
    """
    همه پروسه‌های python3 bot.py که cwd آنها برابر folder است را می‌بندد.
    """
    killed_count = 0
    for proc in psutil.process_iter(attrs=["pid", "cmdline", "cwd"]):
        try:
            cmdline = proc.info["cmdline"]
            cwd = proc.info["cwd"]
            if not cmdline or not cwd:
                continue
            # بررسی python3 bot.py در cwd موردنظر
            if (
                len(cmdline) >= 2
                and ("python" in cmdline[0] or "python3" in cmdline[0])
                and "bot.py" in cmdline[1]
                and os.path.abspath(cwd) == os.path.abspath(folder)
            ):
                logger.warning(f"[{folder}] پروسه قبلی با PID {proc.pid} پیدا شد. در حال terminate.")
                proc.terminate()
                try:
                    proc.wait(timeout=10)
                except Exception:
                    proc.kill()
                killed_count += 1
        except Exception as ex:
            logger.error(f"[{folder}] خطا در بستن پروسه قبلی: {ex}")
    return killed_count

def update_and_run_all_children_bots():
    """
    همه بچه‌ها رو با نسخه جدید baby_bot.py آپدیت و همیشه ران نگه می‌دارد.
    هر بار قبل از ران، پروسه‌های قبلی هر بچه بسته می‌شود.
    """
    logger.info("در حال خواندن قالب baby_bot.py ...")
    with open("baby_bot.py", "r", encoding="utf-8") as f:
        template_code = f.read()

    base = "."
    child_folders = []

    for folder in os.listdir(base):
        if folder.startswith("bot_") and os.path.isdir(folder):
            config_path = os.path.join(folder, "config.json")
            bot_path = os.path.join(folder, "bot.py")
            logger.info(f"[{folder}] بررسی پوشه بچه...")
            if not os.path.exists(config_path):
                logger.warning(f"[{folder}] فاقد config.json است، رد شد.")
                continue
            try:
                logger.info(f"[{folder}] خواندن config.json ...")
                with open(config_path, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                if os.path.exists(bot_path):
                    logger.info(f"[{folder}] حذف bot.py قدیمی ...")
                    os.remove(bot_path)
                else:
                    logger.info(f"[{folder}] bot.py وجود نداشت، نیازی به حذف نبود.")
                api_token = cfg.get("API_TOKEN", "")
                bot_code = safe_format(
                    template_code,
                    API_TOKEN=api_token,
                    OWNER_USER=cfg.get("OWNER_USER", ""),
                    BOT_CHILD_NAME=cfg.get("BOT_CHILD_NAME", folder)
                )
                logger.info(f"[{folder}] در حال ساخت bot.py جدید ...")
                try:
                    with open(bot_path, "w", encoding="utf-8") as f2:
                        f2.write(bot_code)
                except Exception as e:
                    out = template_code
                    for k, v in cfg.items():
                        out = out.replace("{" + str(k) + "}", str(v))
                    with open(bot_path, "w", encoding="utf-8") as f2:
                        f2.write(out)
                logger.info(f"[{folder}] bot.py جدید ساخته شد.")
                # لاگ اضافه: آپدیت شدن بچه
                logger.info(f"[{folder}] ✅ ربات بچه آپدیت شد.")
                child_folders.append(folder)
            except Exception as e:
                logger.error(f"❌ خطا در {folder}: {e}")

    def run_forever(folder):
        config_path = os.path.join(folder, "config.json")
        owner_id = None
        bot_name = folder
        try:
            if os.path.exists(config_path):
                with open(config_path, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                owner_id = cfg.get("OWNER_USER")
                bot_name = cfg.get("BOT_CHILD_NAME", folder)
        except:
            pass

        error_count = 0
        MAX_ERRORS = 10
        while True:
            try:
                # قبل از ران، پروسه‌های قبلی را terminate کن
                killed = kill_previous_baby_bots(folder)
                logger.info(f"[{folder}] {killed} پروسه قبلی ربات بچه قبل از ران کشته شد.")
                logger.info(f"[{folder}] اجرای bot.py تازه ...")
                proc = subprocess.Popen(
                    ["python3", "bot.py"],
                    cwd=folder,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
                out, err = proc.communicate()
                logger.info(f"[{folder}] اجرا تمام شد. کد خروج: {proc.returncode}")
                # فقط اگر خطای واقعی برنامه بود اطلاع بده، نه توکن
                if err and owner_id:
                    msg = f"❌ خطا یا توقف در ربات بچه <b>{bot_name}</b>:\n<code>{err.decode('utf-8')[:3500]}</code>"
                    try:
                        bot.send_message(owner_id, msg, parse_mode="HTML")
                    except: pass

                if proc.returncode == 0:
                    error_count = 0
                else:
                    error_count += 1
                    if error_count >= MAX_ERRORS:
                        logger.error(f"[{folder}] اجرای bot.py بیش از {MAX_ERRORS} بار ارور داد. توقف اجرا تا رفع مشکل.")
                        if owner_id:
                            try:
                                bot.send_message(owner_id, f"❌ ربات بچه <b>{bot_name}</b> بیش از {MAX_ERRORS} بار کرش کرد! لطفاً رفع مشکل کنید.", parse_mode="HTML")
                            except: pass
                        break
                    time.sleep(30)
            except Exception as e:
                logger.error(f"❌ خطا در اجرای {folder}/bot.py: {e}")
                if owner_id:
                    try:
                        bot.send_message(owner_id, f"❌ اجرای ربات بچه <b>{bot_name}</b> ناموفق بود:\n<code>{str(e)}</code>", parse_mode="HTML")
                    except: pass
                time.sleep(30)

    for folder in child_folders:
        logger.info(f"شروع ترد اجرای دائمی برای {folder}")
        t = threading.Thread(target=run_forever, args=(folder,), daemon=True)
        t.start()
        
def clean_host_junk_files():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    safe_files = {
        "baby_bot.py", "mother_bot.py",
        "coin.py", "dlc.py", "keys.tsv", "list.txt", "PlayFab.py", "tsv.py", "nohup.out", "app_portal.py"
    }
    safe_dirs_prefix = ("central_data", "bot_")
    for name in os.listdir(base_dir):
        full_path = os.path.join(base_dir, name)
        # فایل‌های مهم را نگه دار
        if name in safe_files:
            continue
        # فولدرهای مجاز (bot_*, central_data) را نگه دار
        if any(name.startswith(prefix) for prefix in safe_dirs_prefix):
            continue
        try:
            if os.path.isfile(full_path) or os.path.islink(full_path):
                os.remove(full_path)
            elif os.path.isdir(full_path):
                shutil.rmtree(full_path)
        except Exception as e:
            logger.error(f"[clean_host_junk_files] Error removing {full_path}: {e}")

def save_user_stages_periodically(interval=5):
    def loop():
        while True:
            for uid, state in data_store.user_states.items():
                user_info = data_store.user_data.get(str(uid))
                if user_info:
                    user_info["stage"] = state.get("state", "unknown")
                    user_info["status"] = "online"
            data_store.save_data()
            time.sleep(interval)
    threading.Thread(target=loop, daemon=True).start()

#اپلودر سراسری
# helper: extract a minimal serializable info from incoming message
def _extract_pending_info_from_message(message):
    info = {"content_type": message.content_type}
    if message.content_type == "document" and hasattr(message, "document"):
        info["document"] = {
            "file_id": message.document.file_id,
            "file_name": getattr(message.document, "file_name", None),
            "file_size": getattr(message.document, "file_size", None)
        }
    elif message.content_type == "photo" and hasattr(message, "photo"):
        info["photo"] = [{"file_id": p.file_id} for p in message.photo]
    elif message.content_type == "video" and hasattr(message, "video"):
        info["video"] = {"file_id": message.video.file_id}
    elif message.content_type == "audio" and hasattr(message, "audio"):
        info["audio"] = {"file_id": message.audio.file_id}
    elif message.content_type == "voice" and hasattr(message, "voice"):
        info["voice"] = {"file_id": message.voice.file_id}
    elif message.content_type == "animation" and hasattr(message, "animation"):
        info["animation"] = {"file_id": message.animation.file_id}
    return info


@bot.message_handler(
    func=lambda m: (
        (data_store.get_user_state(m.from_user.id)["state"] in [None, "settings_menu"])
        and m.content_type in ['document', 'photo', 'video', 'audio', 'voice', 'animation']
        and (not m.caption or not m.caption.strip())
    ),
    content_types=['document', 'photo', 'video', 'audio', 'voice', 'animation']
)
def handle_upload_choice_in_main_or_settings(message):
    user_id = message.from_user.id
    # استخراج و ذخیرهٔ کم‌حجم به‌جای message.json کامل
    pending_info = _extract_pending_info_from_message(message)
    data_store.update_user_state(user_id, "upload_choice_waiting", {
        "pending_file_type": message.content_type,
        "pending_message_id": message.message_id,
        "pending_file_info": pending_info
    })
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("⬆️ اپلود دیلیت فایل", callback_data="mainmenu_upload_delete_file"),
        types.InlineKeyboardButton("⬆️ اپلود فایل", callback_data="mainmenu_upload_file"),
        types.InlineKeyboardButton("❌ انصراف", callback_data="mainmenu_upload_cancel")
    )
    bot.send_message(
        user_id,
        "لطفا یکی از گزینه‌های زیر را برای فایل ارسالی انتخاب کنید:",
        reply_markup=markup
    )


@bot.callback_query_handler(func=lambda call: call.data and call.data.startswith("mainmenu_upload_"))
def handle_upload_choice_callback(call):
    user_id = call.from_user.id
    state = data_store.get_user_state(user_id)
    if not state or state.get("state") != "upload_choice_waiting":
        bot.answer_callback_query(call.id, "⏱️ زمان انتخاب تمام شده یا وضعیت نامعتبر است.")
        return

    pending = state.get("data", {}).get("pending_file_info")
    if not pending:
        bot.answer_callback_query(call.id, "❌ اطلاعات فایل پیدا نشد.")
        data_store.update_user_state(user_id, "main_menu", {})
        return

    if call.data == "mainmenu_upload_cancel":
        data_store.update_user_state(user_id, "main_menu", {})
        try:
            bot.edit_message_text("⛔️ عملیات آپلود کنسل شد.", chat_id=user_id, message_id=call.message.message_id)
        except Exception:
            pass
        bot.answer_callback_query(call.id, "کنسل شد.")
        return

    # تعیین حالت اصلی: آپلود عادی یا آپلود با حذف خودکار
    original_state = "uploader_file_upload" if call.data == "mainmenu_upload_file" else "uploader_delete_file_upload"

    # payload برای مرحلهٔ تایید لیست سفید
    payload = {
        "pending_upload_info": pending,
        "original_state": original_state
    }
    # انتقال به state تایید لیست سفید تا هندلر confirm_whitelist_upload آن را بگیرد
    data_store.update_user_state(user_id, "confirm_whitelist_upload", payload)

    # کیبورد و پیغام تایید whitelist (همان شکلی که confirm_whitelist_upload انتظار دارد)
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(types.KeyboardButton("✅ بله"), types.KeyboardButton("❌ خیر"))
    markup.add(types.KeyboardButton("🔙 بازگشت به اپلودر"))
    bot.send_message(user_id, "آیا می‌خواهید این فایل لیست سفید شود؟\n(اگر لیست سفید شود، فقط اونر/ادمین‌ها یا کاربران اضافه‌شده قادر به دانلود خواهند بود.)", reply_markup=markup)
    bot.answer_callback_query(call.id, "ادامه در مرحلهٔ تایید لیست‑سفید...")
    
@bot.callback_query_handler(func=lambda call: call.data in ["mainmenu_upload_file", "mainmenu_upload_delete_file", "mainmenu_upload_cancel"])
def handle_upload_action_in_main_or_settings(call):
    user_id = call.from_user.id
    user_state = data_store.get_user_state(user_id)
    file_info = user_state["data"].get("pending_file_info")
    if not file_info:
        bot.answer_callback_query(call.id, "❌ فایل یافت نشد یا منقضی شده است.", show_alert=True)
        data_store.reset_user_state(user_id)
        return

    # بازیابی شی پیام تلگرام از داده‌های json
    class DummyMessage:
        def __init__(self, info):
            self.__dict__ = info
            for k, v in info.items():
                setattr(self, k, v)
            # پوشش انواع فایل
            if 'document' in info:
                self.document = type('dummy', (), info['document'])()
            if 'photo' in info:
                self.photo = [type('dummy', (), p)() for p in info['photo']]
            if 'video' in info:
                self.video = type('dummy', (), info['video'])()
            if 'audio' in info:
                self.audio = type('dummy', (), info['audio'])()
            if 'voice' in info:
                self.voice = type('dummy', (), info['voice'])()
            if 'animation' in info:
                self.animation = type('dummy', (), info['animation'])()
            # شبیه‌سازی سایر فیلدهای لازم
            self.content_type = info.get('content_type', 'document')
            self.from_user = type('dummy', (), {"id": user_id})()

    msg_obj = DummyMessage(file_info)

    if call.data == "mainmenu_upload_cancel":
        bot.answer_callback_query(call.id, "❌ فایل نادیده گرفته شد.")
        data_store.reset_user_state(user_id)
        return

    # فراخوانی هندلر مناسب اپلود فایل یا اپلود دیلیت فایل (با state مناسب)
    if call.data == "mainmenu_upload_file":
        data_store.update_user_state(user_id, "uploader_file_upload", {"uploaded_files": []})
        bot.answer_callback_query(call.id, "در حال اپلود فایل...")
        handle_uploader_files(msg_obj)
    elif call.data == "mainmenu_upload_delete_file":
        data_store.update_user_state(user_id, "uploader_delete_file_upload", {"uploaded_files": []})
        bot.answer_callback_query(call.id, "در حال اپلود دیلیت فایل...")
        handle_uploader_files(msg_obj)
    data_store.reset_user_state(user_id)

# هندلر قابلیت‌های جدید
@bot.callback_query_handler(func=lambda call: call.data.startswith("new_features_"))
def handle_new_features_callback(call):
    user_id = call.from_user.id  # اضافه شد
    features_text = (
        " ربات هوشیار (نسخه 2.9.98.19) \n✅ رفع باگ جزئی مربوط به مدیریت کاربران \n✅ رفع باگ مربوط دسترشی ادمین ها از منوی اصلی"
    )
    data_store.user_data[str(user_id)]["maram"] = True
    data_store.save_data()
    bot.answer_callback_query(call.id, "ویژگی‌های جدید با موفقیت نمایش داده شد!")
    bot.send_message(user_id, features_text)
        
#=====================لاگر ایرور ها====================
class TelegramErrorHandler(logging.Handler):
    def emit(self, record):
        try:
            log_entry = self.format(record)
            if record.levelno >= logging.ERROR:
                bot.send_message(OWNER_ID, f"❌ یه ایرور شناسایی کردم لطفا اینو به مهرشاد فراورد کن:\n<blockquote><code>{log_entry}</code></blockquote>", parse_mode="HTML")
        except Exception:
            pass

# --- کد جدید: تابع امن و سبک برای بررسی کانال‌های اجتماعی (افزودن این تابع در کنار periodic_stats_update) ---
def check_social_channels_periodically(interval: int = 300):
    """
    اجرا به صورت ترد داِم برای بررسی سبک کانال‌های اجتماعی (x_channels, youtube_channels).
    - محل قرارگیری: در همان محدودهٔ توابع periodics قبل از if __name__ == "__main__"
    - کار: فقط تعداد/در دسترس بودن کانال‌ها را لاگ می‌کند و از هرگونه فراخوانی سنگین یا بلاک‌کننده اجتناب می‌کند.
    """
    def _worker():
        while True:
            try:
                x_chs = getattr(data_store, "x_channels", []) or []
                yt_chs = getattr(data_store, "youtube_channels", []) or []
                logger.info(f"[SOCIAL_CHECK] checking social channels: x={len(x_chs)} yt={len(yt_chs)}")
                # تلاش به صورت محافظه‌کارانه برای درخواست متادیتا (بدون قطع شدن در صورت خطا)
                for ch in x_chs[:50]:  # محدودیت تعداد هر بار برای ایمنی
                    try:
                        bot.get_chat(ch)
                    except Exception:
                        # نادیده بگیر هر خطا؛ این فقط یک چک سبک است
                        pass
                for ch in yt_chs[:50]:
                    try:
                        bot.get_chat(ch)
                    except Exception:
                        pass
            except Exception as e:
                logger.error(f"[SOCIAL_CHECK] unexpected error: {e}")
            try:
                time.sleep(interval)
            except Exception:
                # اگر sleep با خطا مواجه شد، فقط ادامه بده
                time.sleep(60)
    t = threading.Thread(target=_worker, daemon=True)
    t.start()

# اضافه کردن هندلر خطا به لاگر ربات
error_handler = TelegramErrorHandler()
error_handler.setLevel(logging.ERROR)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
error_handler.setFormatter(formatter)
logger.addHandler(error_handler)

if __name__ == "__main__":
    CENTRAL_DATA = "central_data"
    if not os.path.exists(CENTRAL_DATA):
        print("central_data directory not found!")
        exit(1)
    
    logger.info("بات در حال شروع است...")
    save_user_stages_periodically(interval=5)
    # تعریف لیست کاربران بلاک‌شده
    blocked_users = set()
    try:
        # ارسال پیام ران اولیه فقط به کاربران فعال و غیر بلاک
        all_user_ids = list(data_store.user_data.keys())
        for uid in all_user_ids:
            user_info = data_store.user_data.get(str(uid), {})
            if uid in blocked_users or not user_info.get("is_active", True):
                continue
            try:
                bot.send_message(
                    int(uid),
                    f"🤖 ربات هوشیار با موفقیت راه‌اندازی شد!\nنسخه: {BOT_VERSION}\nبرای مشاهده قابلیت‌های جدید روی دکمه زیر بزنید.",
                    reply_markup=types.InlineKeyboardMarkup().add(
                        types.InlineKeyboardButton("قابلیت‌های جدید", callback_data=f"new_features_{uid}")
                    )
                )
                data_store.user_data[str(uid)]["is_active"] = True
                logger.info(f"ارسال موفق پیام شروع به کاربر {uid}")
            except telebot.apihelper.ApiTelegramException as e:
                if e.error_code == 403:
                    logger.warning(f"کاربر {uid} اجازه ارسال پیام ندارد، احتمالاً بات را استارت نکرده است.")
                    data_store.user_data[str(uid)]["is_active"] = False
                else:
                    logger.error(f"خطا در ارسال پیام به کاربر {uid}: {e}")
            except Exception as ex:
                logger.error(f"خطا ارسال پیام به کاربر {uid}: {ex}")
                data_store.user_data[str(uid)]["is_active"] = False
        data_store.save_data()
    except Exception as e:
        logger.error(f"خطا در ارسال پیام شروع به همه اعضا: {e}")
    update_and_run_all_children_bots()
    check_social_channels_periodically()
    start_channel_security()
    super_stable_connection_monitor(bot, check_interval=5)
    try:
        while True:
            time.sleep(10)
    except KeyboardInterrupt:
        logger.info("🛑 برنامه متوقف شد.")