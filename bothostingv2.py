# -*- coding: utf-8 -*-
import telebot
import subprocess
import os
import zipfile
import tempfile
import shutil
from telebot import types
import time
from datetime import datetime, timedelta
import psutil
import sqlite3
import json
import logging
import signal
import threading
import re
import sys
import atexit
import requests
from flask import request, render_template_string, redirect, url_for, session, abort
from flask_session import Session
import secrets
from dotenv import load_dotenv
import random
import string
import hashlib
import platform
import socket
import uuid
import base64

def parse_duration(duration_str):
    duration_str = duration_str.strip().lower()
    if duration_str in ('lifetime', 'forever', '∞', '0'):
        return None
    match = re.match(r'^(\d+)([dhwmy])$', duration_str)
    if match:
        num = int(match.group(1))
        unit = match.group(2)
        if unit == 'd':
            return timedelta(days=num)
        elif unit == 'h':
            return timedelta(hours=num)
        elif unit == 'm':
            return timedelta(minutes=num)
        elif unit == 'w':
            return timedelta(weeks=num)
        elif unit == 'y':
            return timedelta(days=num*365)
    if duration_str.isdigit():
        return timedelta(days=int(duration_str))
    raise ValueError("Invalid duration format")

load_dotenv()

from flask import Flask
from threading import Thread

app = Flask('')
app.config['SECRET_KEY'] = secrets.token_hex(16)
app.config['SESSION_TYPE'] = 'filesystem'
Session(app)

@app.route('/')
def home():
    return "cuervoontoppp@gmail.com"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run_flask)
    t.daemon = True
    t.start()
    print("Flask Keep-Alive server started.")

TOKEN = os.getenv('TOKEN', '8243955105:AAHdG1ILXVdkbOQAM0XYJISgkR5wSQoniP0')
OWNER_ID = int(os.getenv('OWNER_ID', 8962068652))
ADMIN_ID = int(os.getenv('ADMIN_ID', 8013610670))
YOUR_USERNAME = os.getenv('YOUR_USERNAME', 'godofallbeings')
UPDATE_CHANNEL = os.getenv('UPDATE_CHANNEL', '@hahhahahhahahw')

FREE_USER_LIMIT = int(os.getenv('FREE_USER_LIMIT', 1))
SUBSCRIBED_USER_LIMIT = int(os.getenv('SUBSCRIBED_USER_LIMIT', 3))
ADMIN_LIMIT = int(os.getenv('ADMIN_LIMIT', 20))
OWNER_LIMIT = float('inf')

REFERRAL_REWARD_LIMIT = int(os.getenv('REFERRAL_REWARD_LIMIT', 5))
REFERRAL_REWARD_DAYS = int(os.getenv('REFERRAL_REWARD_DAYS', 7))

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
UPLOAD_BOTS_DIR = os.path.join(BASE_DIR, 'upload_bots')
IROTECH_DIR = os.path.join(BASE_DIR, 'inf')
DATABASE_PATH = os.path.join(IROTECH_DIR, 'bot_data.db')

os.makedirs(UPLOAD_BOTS_DIR, exist_ok=True)
os.makedirs(IROTECH_DIR, exist_ok=True)

bot = telebot.TeleBot(TOKEN)

bot_scripts = {}
user_subscriptions = {}
user_files = {}
active_users = set()
admin_ids = {ADMIN_ID, OWNER_ID}
banned_users = set()
user_limits = {}
bot_locked = False
pending_modules = {}
manual_install_requests = {}
mandatory_channels = {}
pending_zip_files = {}
referral_codes = {}
referral_counts = {}
referral_rewards = {}
referral_used_by = {}

class PermanentDatabase:
    def __init__(self, db_path):
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        conn = sqlite3.connect(self.db_path, check_same_thread=False, timeout=30)
        c = conn.cursor()
        c.execute('PRAGMA journal_mode=WAL')
        c.execute('PRAGMA synchronous=NORMAL')
        c.execute('''CREATE TABLE IF NOT EXISTS permanent_users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            join_date TEXT,
            last_seen TEXT,
            status TEXT DEFAULT 'active',
            is_banned INTEGER DEFAULT 0,
            ban_reason TEXT,
            ban_date TEXT,
            warn_count INTEGER DEFAULT 0,
            is_premium INTEGER DEFAULT 0,
            premium_expiry TEXT,
            file_limit INTEGER DEFAULT -1,
            role TEXT DEFAULT 'user',
            referral_code TEXT UNIQUE,
            referred_by INTEGER,
            referral_count INTEGER DEFAULT 0,
            referral_extra_limit INTEGER DEFAULT 0
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS permanent_files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            file_name TEXT,
            file_type TEXT,
            file_size INTEGER,
            upload_date TEXT,
            last_modified TEXT,
            is_running INTEGER DEFAULT 0,
            process_id INTEGER,
            start_time TEXT,
            UNIQUE(user_id, file_name)
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS permanent_subscriptions (
            user_id INTEGER PRIMARY KEY,
            subscription_type TEXT,
            expiry_date TEXT,
            activated_date TEXT,
            activated_by INTEGER,
            is_active INTEGER DEFAULT 1
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS permanent_keys (
            key_id INTEGER PRIMARY KEY AUTOINCREMENT,
            key_code TEXT UNIQUE,
            key_type TEXT,
            limit_value INTEGER,
            expiry_date TEXT,
            is_used INTEGER DEFAULT 0,
            used_by INTEGER,
            used_date TEXT,
            created_by INTEGER,
            created_date TEXT,
            is_lifetime INTEGER DEFAULT 0
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS permanent_channels (
            channel_id TEXT PRIMARY KEY,
            channel_username TEXT,
            channel_name TEXT,
            added_by INTEGER,
            added_date TEXT,
            is_mandatory INTEGER DEFAULT 1
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS permanent_logs (
            log_id INTEGER PRIMARY KEY AUTOINCREMENT,
            log_type TEXT,
            user_id INTEGER,
            action TEXT,
            details TEXT,
            timestamp TEXT
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS permanent_feedback (
            feedback_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            feedback TEXT,
            rating INTEGER,
            timestamp TEXT,
            status TEXT DEFAULT 'pending'
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS permanent_scripts (
            script_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            script_name TEXT,
            script_code TEXT,
            script_type TEXT,
            created_date TEXT,
            modified_date TEXT,
            is_active INTEGER DEFAULT 1,
            UNIQUE(user_id, script_name)
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS permanent_settings (
            setting_key TEXT PRIMARY KEY,
            setting_value TEXT,
            updated_by INTEGER,
            updated_date TEXT
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS permanent_admin_logs (
            log_id INTEGER PRIMARY KEY AUTOINCREMENT,
            admin_id INTEGER,
            action TEXT,
            target_user INTEGER,
            details TEXT,
            timestamp TEXT
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS permanent_daily_stats (
            stat_date TEXT PRIMARY KEY,
            new_users INTEGER DEFAULT 0,
            total_users INTEGER DEFAULT 0,
            new_files INTEGER DEFAULT 0,
            total_files INTEGER DEFAULT 0,
            new_scripts INTEGER DEFAULT 0,
            total_scripts INTEGER DEFAULT 0,
            new_referrals INTEGER DEFAULT 0,
            total_referrals INTEGER DEFAULT 0
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS permanent_referral_rewards (
            reward_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            reward_type TEXT,
            reward_value INTEGER,
            given_date TEXT,
            expires_date TEXT,
            is_claimed INTEGER DEFAULT 0,
            claimed_date TEXT
        )''')
        c.execute('INSERT OR IGNORE INTO permanent_settings (setting_key, setting_value, updated_date) VALUES (?, ?, ?)',
                  ('bot_locked', 'false', datetime.now().isoformat()))
        c.execute('INSERT OR IGNORE INTO permanent_settings (setting_key, setting_value, updated_date) VALUES (?, ?, ?)',
                  ('maintenance_mode', 'false', datetime.now().isoformat()))
        owner_code = self.generate_referral_code(OWNER_ID)
        c.execute('INSERT OR IGNORE INTO permanent_users (user_id, username, join_date, role, referral_code) VALUES (?, ?, ?, ?, ?)',
                  (OWNER_ID, 'owner', datetime.now().isoformat(), 'owner', owner_code))
        if ADMIN_ID != OWNER_ID:
            admin_code = self.generate_referral_code(ADMIN_ID)
            c.execute('INSERT OR IGNORE INTO permanent_users (user_id, username, join_date, role, referral_code) VALUES (?, ?, ?, ?, ?)',
                      (ADMIN_ID, 'admin', datetime.now().isoformat(), 'admin', admin_code))
        conn.commit()
        conn.close()
        print("✅ Permanent database initialized successfully with referral system!")
    
    def generate_referral_code(self, user_id):
        code = f"REF{user_id}{random.randint(1000, 9999)}"
        return code
    
    def save_user(self, user_id, username=None, first_name=None, last_name=None, referral_code=None, referred_by=None):
        conn = sqlite3.connect(self.db_path, check_same_thread=False, timeout=30)
        c = conn.cursor()
        try:
            current_time = datetime.now().isoformat()
            c.execute('SELECT user_id FROM permanent_users WHERE user_id = ?', (user_id,))
            exists = c.fetchone()
            if exists:
                c.execute('''UPDATE permanent_users 
                           SET username = COALESCE(?, username),
                               first_name = COALESCE(?, first_name),
                               last_name = COALESCE(?, last_name),
                               last_seen = ?
                           WHERE user_id = ?''',
                         (username, first_name, last_name, current_time, user_id))
            else:
                if not referral_code:
                    referral_code = self.generate_referral_code(user_id)
                c.execute('''INSERT INTO permanent_users 
                           (user_id, username, first_name, last_name, join_date, last_seen, status, referral_code, referred_by)
                           VALUES (?, ?, ?, ?, ?, ?, 'active', ?, ?)''',
                         (user_id, username, first_name, last_name, current_time, current_time, referral_code, referred_by))
                today = datetime.now().strftime('%Y-%m-%d')
                c.execute('''INSERT INTO permanent_daily_stats (stat_date, new_users, total_users)
                           VALUES (?, 1, 1)
                           ON CONFLICT(stat_date) DO UPDATE SET
                           new_users = new_users + 1,
                           total_users = (SELECT COUNT(*) FROM permanent_users WHERE status = 'active')''',
                         (today,))
                if referred_by:
                    self.give_referral_reward(referred_by)
                    c.execute('''UPDATE permanent_users 
                               SET referral_count = referral_count + 1
                               WHERE user_id = ?''',
                             (referred_by,))
                    c.execute('''INSERT INTO permanent_daily_stats (stat_date, new_referrals, total_referrals)
                               VALUES (?, 1, 1)
                               ON CONFLICT(stat_date) DO UPDATE SET
                               new_referrals = new_referrals + 1,
                               total_referrals = (SELECT SUM(referral_count) FROM permanent_users)''',
                             (today,))
            conn.commit()
            return True
        except Exception as e:
            print(f"Error saving user: {e}")
            return False
        finally:
            conn.close()
    
    def give_referral_reward(self, user_id):
        conn = sqlite3.connect(self.db_path, check_same_thread=False, timeout=30)
        c = conn.cursor()
        try:
            c.execute('''UPDATE permanent_users 
                       SET referral_extra_limit = referral_extra_limit + ?
                       WHERE user_id = ?''',
                     (REFERRAL_REWARD_LIMIT, user_id))
            if REFERRAL_REWARD_DAYS > 0:
                current_expiry = None
                c.execute('SELECT premium_expiry FROM permanent_users WHERE user_id = ?', (user_id,))
                result = c.fetchone()
                if result and result[0]:
                    try:
                        current_expiry = datetime.fromisoformat(result[0])
                    except:
                        pass
                if current_expiry and current_expiry > datetime.now():
                    new_expiry = current_expiry + timedelta(days=REFERRAL_REWARD_DAYS)
                else:
                    new_expiry = datetime.now() + timedelta(days=REFERRAL_REWARD_DAYS)
                c.execute('''UPDATE permanent_users 
                           SET is_premium = 1, premium_expiry = ?
                           WHERE user_id = ?''',
                         (new_expiry.isoformat(), user_id))
                c.execute('''INSERT OR REPLACE INTO permanent_subscriptions 
                           (user_id, subscription_type, expiry_date, activated_date, is_active)
                           VALUES (?, 'referral_reward', ?, ?, 1)''',
                         (user_id, new_expiry.isoformat(), datetime.now().isoformat()))
            conn.commit()
            return True
        except Exception as e:
            print(f"Error giving referral reward: {e}")
            return False
        finally:
            conn.close()
    
    def get_user(self, user_id):
        conn = sqlite3.connect(self.db_path, check_same_thread=False, timeout=30)
        c = conn.cursor()
        try:
            c.execute('SELECT * FROM permanent_users WHERE user_id = ?', (user_id,))
            return c.fetchone()
        except Exception as e:
            print(f"Error getting user: {e}")
            return None
        finally:
            conn.close()
    
    def get_user_by_referral_code(self, referral_code):
        conn = sqlite3.connect(self.db_path, check_same_thread=False, timeout=30)
        c = conn.cursor()
        try:
            c.execute('SELECT user_id FROM permanent_users WHERE referral_code = ?', (referral_code,))
            result = c.fetchone()
            return result[0] if result else None
        except Exception as e:
            print(f"Error getting user by referral code: {e}")
            return None
        finally:
            conn.close()
    
    def get_referral_stats(self, user_id):
        conn = sqlite3.connect(self.db_path, check_same_thread=False, timeout=30)
        c = conn.cursor()
        try:
            c.execute('SELECT referral_count, referral_extra_limit FROM permanent_users WHERE user_id = ?', (user_id,))
            result = c.fetchone()
            if result:
                return {'count': result[0], 'extra_limit': result[1]}
            return {'count': 0, 'extra_limit': 0}
        except Exception as e:
            print(f"Error getting referral stats: {e}")
            return {'count': 0, 'extra_limit': 0}
        finally:
            conn.close()
    
    def get_referred_users(self, user_id):
        conn = sqlite3.connect(self.db_path, check_same_thread=False, timeout=30)
        c = conn.cursor()
        try:
            c.execute('SELECT user_id, username, join_date FROM permanent_users WHERE referred_by = ?', (user_id,))
            return c.fetchall()
        except Exception as e:
            print(f"Error getting referred users: {e}")
            return []
        finally:
            conn.close()
    
    def get_top_referrers(self, limit=10):
        conn = sqlite3.connect(self.db_path, check_same_thread=False, timeout=30)
        c = conn.cursor()
        try:
            c.execute('''SELECT user_id, username, referral_count, referral_extra_limit 
                       FROM permanent_users 
                       WHERE referral_count > 0 
                       ORDER BY referral_count DESC 
                       LIMIT ?''', (limit,))
            return c.fetchall()
        except Exception as e:
            print(f"Error getting top referrers: {e}")
            return []
        finally:
            conn.close()
    
    def ban_user(self, user_id, reason=None, banned_by=None):
        conn = sqlite3.connect(self.db_path, check_same_thread=False, timeout=30)
        c = conn.cursor()
        try:
            c.execute('''UPDATE permanent_users 
                       SET is_banned = 1, ban_reason = ?, ban_date = ?
                       WHERE user_id = ?''',
                     (reason, datetime.now().isoformat(), user_id))
            conn.commit()
            return True
        except Exception as e:
            print(f"Error banning user: {e}")
            return False
        finally:
            conn.close()
    
    def unban_user(self, user_id):
        conn = sqlite3.connect(self.db_path, check_same_thread=False, timeout=30)
        c = conn.cursor()
        try:
            c.execute('''UPDATE permanent_users 
                       SET is_banned = 0, ban_reason = NULL, ban_date = NULL
                       WHERE user_id = ?''',
                     (user_id,))
            conn.commit()
            return True
        except Exception as e:
            print(f"Error unbanning user: {e}")
            return False
        finally:
            conn.close()
    
    def is_user_banned(self, user_id):
        conn = sqlite3.connect(self.db_path, check_same_thread=False, timeout=30)
        c = conn.cursor()
        try:
            c.execute('SELECT is_banned FROM permanent_users WHERE user_id = ?', (user_id,))
            result = c.fetchone()
            return result and result[0] == 1
        except Exception as e:
            print(f"Error checking ban: {e}")
            return False
        finally:
            conn.close()
    
    def save_file(self, user_id, file_name, file_type, file_size=0):
        conn = sqlite3.connect(self.db_path, check_same_thread=False, timeout=30)
        c = conn.cursor()
        try:
            current_time = datetime.now().isoformat()
            c.execute('''INSERT OR REPLACE INTO permanent_files 
                       (user_id, file_name, file_type, file_size, upload_date, last_modified)
                       VALUES (?, ?, ?, ?, ?, ?)''',
                     (user_id, file_name, file_type, file_size, current_time, current_time))
            conn.commit()
            return True
        except Exception as e:
            print(f"Error saving file: {e}")
            return False
        finally:
            conn.close()
    
    def delete_file(self, user_id, file_name):
        conn = sqlite3.connect(self.db_path, check_same_thread=False, timeout=30)
        c = conn.cursor()
        try:
            c.execute('DELETE FROM permanent_files WHERE user_id = ? AND file_name = ?',
                     (user_id, file_name))
            conn.commit()
            return True
        except Exception as e:
            print(f"Error deleting file: {e}")
            return False
        finally:
            conn.close()
    
    def get_user_files(self, user_id):
        conn = sqlite3.connect(self.db_path, check_same_thread=False, timeout=30)
        c = conn.cursor()
        try:
            c.execute('SELECT file_name, file_type FROM permanent_files WHERE user_id = ?',
                     (user_id,))
            return c.fetchall()
        except Exception as e:
            print(f"Error getting files: {e}")
            return []
        finally:
            conn.close()
    
    def save_subscription(self, user_id, expiry_date, sub_type='premium', activated_by=None):
        conn = sqlite3.connect(self.db_path, check_same_thread=False, timeout=30)
        c = conn.cursor()
        try:
            expiry_str = expiry_date.isoformat() if expiry_date else None
            c.execute('''INSERT OR REPLACE INTO permanent_subscriptions 
                       (user_id, subscription_type, expiry_date, activated_date, activated_by, is_active)
                       VALUES (?, ?, ?, ?, ?, 1)''',
                     (user_id, sub_type, expiry_str, datetime.now().isoformat(), activated_by))
            c.execute('''UPDATE permanent_users 
                       SET is_premium = 1, premium_expiry = ?
                       WHERE user_id = ?''',
                     (expiry_str, user_id))
            conn.commit()
            return True
        except Exception as e:
            print(f"Error saving subscription: {e}")
            return False
        finally:
            conn.close()
    
    def remove_subscription(self, user_id):
        conn = sqlite3.connect(self.db_path, check_same_thread=False, timeout=30)
        c = conn.cursor()
        try:
            c.execute('DELETE FROM permanent_subscriptions WHERE user_id = ?', (user_id,))
            c.execute('''UPDATE permanent_users 
                       SET is_premium = 0, premium_expiry = NULL
                       WHERE user_id = ?''',
                     (user_id,))
            conn.commit()
            return True
        except Exception as e:
            print(f"Error removing subscription: {e}")
            return False
        finally:
            conn.close()
    
    def save_key(self, key_code, key_type, limit_value, expiry_date, created_by, is_lifetime=0):
        conn = sqlite3.connect(self.db_path, check_same_thread=False, timeout=30)
        c = conn.cursor()
        try:
            expiry_str = expiry_date.isoformat() if expiry_date else None
            c.execute('''INSERT INTO permanent_keys 
                       (key_code, key_type, limit_value, expiry_date, created_by, created_date, is_lifetime)
                       VALUES (?, ?, ?, ?, ?, ?, ?)''',
                     (key_code, key_type, limit_value, expiry_str, created_by,
                      datetime.now().isoformat(), is_lifetime))
            conn.commit()
            return True
        except Exception as e:
            print(f"Error saving key: {e}")
            return False
        finally:
            conn.close()
    
    def redeem_key(self, key_code, user_id):
        conn = sqlite3.connect(self.db_path, check_same_thread=False, timeout=30)
        c = conn.cursor()
        try:
            c.execute('''SELECT key_id, key_type, limit_value, expiry_date, is_lifetime 
                       FROM permanent_keys 
                       WHERE key_code = ? AND is_used = 0''',
                     (key_code,))
            result = c.fetchone()
            if not result:
                return False, "Invalid or already used key"
            key_id, key_type, limit_value, expiry_date, is_lifetime = result
            if expiry_date and not is_lifetime:
                expiry = datetime.fromisoformat(expiry_date)
                if expiry < datetime.now():
                    return False, "Key has expired"
            c.execute('''UPDATE permanent_keys 
                       SET is_used = 1, used_by = ?, used_date = ?
                       WHERE key_id = ?''',
                     (user_id, datetime.now().isoformat(), key_id))
            c.execute('''UPDATE permanent_users 
                       SET file_limit = ?
                       WHERE user_id = ?''',
                     (limit_value, user_id))
            if key_type == 'premium':
                expiry = datetime.fromisoformat(expiry_date) if expiry_date and not is_lifetime else None
                self.save_subscription(user_id, expiry, 'premium')
            conn.commit()
            return True, f"Key redeemed! File limit set to {limit_value}"
        except Exception as e:
            print(f"Error redeeming key: {e}")
            return False, "Error redeeming key"
        finally:
            conn.close()
    
    def add_admin(self, user_id, added_by):
        conn = sqlite3.connect(self.db_path, check_same_thread=False, timeout=30)
        c = conn.cursor()
        try:
            c.execute('''UPDATE permanent_users 
                       SET role = 'admin'
                       WHERE user_id = ?''',
                     (user_id,))
            conn.commit()
            return True
        except Exception as e:
            print(f"Error adding admin: {e}")
            return False
        finally:
            conn.close()
    
    def remove_admin(self, user_id):
        conn = sqlite3.connect(self.db_path, check_same_thread=False, timeout=30)
        c = conn.cursor()
        try:
            c.execute('''UPDATE permanent_users 
                       SET role = 'user'
                       WHERE user_id = ? AND role != 'owner''',
                     (user_id,))
            conn.commit()
            return True
        except Exception as e:
            print(f"Error removing admin: {e}")
            return False
        finally:
            conn.close()
    
    def get_admins(self):
        conn = sqlite3.connect(self.db_path, check_same_thread=False, timeout=30)
        c = conn.cursor()
        try:
            c.execute('SELECT user_id FROM permanent_users WHERE role IN ("admin", "owner")')
            return [row[0] for row in c.fetchall()]
        except Exception as e:
            print(f"Error getting admins: {e}")
            return []
        finally:
            conn.close()
    
    def set_user_limit(self, user_id, limit):
        conn = sqlite3.connect(self.db_path, check_same_thread=False, timeout=30)
        c = conn.cursor()
        try:
            c.execute('''UPDATE permanent_users 
                       SET file_limit = ?
                       WHERE user_id = ?''',
                     (limit, user_id))
            conn.commit()
            return True
        except Exception as e:
            print(f"Error setting limit: {e}")
            return False
        finally:
            conn.close()
    
    def get_user_limit(self, user_id):
        conn = sqlite3.connect(self.db_path, check_same_thread=False, timeout=30)
        c = conn.cursor()
        try:
            c.execute('SELECT file_limit FROM permanent_users WHERE user_id = ?', (user_id,))
            result = c.fetchone()
            return result[0] if result else -1
        except Exception as e:
            print(f"Error getting limit: {e}")
            return -1
        finally:
            conn.close()
    
    def log_action(self, user_id, action, details=None, log_type='info'):
        conn = sqlite3.connect(self.db_path, check_same_thread=False, timeout=30)
        c = conn.cursor()
        try:
            c.execute('''INSERT INTO permanent_logs 
                       (log_type, user_id, action, details, timestamp)
                       VALUES (?, ?, ?, ?, ?)''',
                     (log_type, user_id, action, details, datetime.now().isoformat()))
            conn.commit()
            return True
        except Exception as e:
            print(f"Error logging action: {e}")
            return False
        finally:
            conn.close()
    
    def save_feedback(self, user_id, feedback, rating=None):
        conn = sqlite3.connect(self.db_path, check_same_thread=False, timeout=30)
        c = conn.cursor()
        try:
            c.execute('''INSERT INTO permanent_feedback 
                       (user_id, feedback, rating, timestamp)
                       VALUES (?, ?, ?, ?)''',
                     (user_id, feedback, rating, datetime.now().isoformat()))
            conn.commit()
            return True
        except Exception as e:
            print(f"Error saving feedback: {e}")
            return False
        finally:
            conn.close()
    
    def save_script(self, user_id, script_name, script_code, script_type='py'):
        conn = sqlite3.connect(self.db_path, check_same_thread=False, timeout=30)
        c = conn.cursor()
        try:
            current_time = datetime.now().isoformat()
            c.execute('''INSERT OR REPLACE INTO permanent_scripts 
                       (user_id, script_name, script_code, script_type, created_date, modified_date)
                       VALUES (?, ?, ?, ?, ?, ?)''',
                     (user_id, script_name, script_code, script_type, current_time, current_time))
            conn.commit()
            return True
        except Exception as e:
            print(f"Error saving script: {e}")
            return False
        finally:
            conn.close()
    
    def get_script(self, user_id, script_name):
        conn = sqlite3.connect(self.db_path, check_same_thread=False, timeout=30)
        c = conn.cursor()
        try:
            c.execute('SELECT script_code FROM permanent_scripts WHERE user_id = ? AND script_name = ?',
                     (user_id, script_name))
            result = c.fetchone()
            return result[0] if result else None
        except Exception as e:
            print(f"Error getting script: {e}")
            return None
        finally:
            conn.close()
    
    def get_all_users(self):
        conn = sqlite3.connect(self.db_path, check_same_thread=False, timeout=30)
        c = conn.cursor()
        try:
            c.execute('SELECT user_id, username, first_name, role, is_banned, is_premium, referral_count FROM permanent_users')
            return c.fetchall()
        except Exception as e:
            print(f"Error getting users: {e}")
            return []
        finally:
            conn.close()
    
    def get_stats(self):
        conn = sqlite3.connect(self.db_path, check_same_thread=False, timeout=30)
        c = conn.cursor()
        try:
            stats = {}
            c.execute('SELECT COUNT(*) FROM permanent_users')
            stats['total_users'] = c.fetchone()[0]
            week_ago = (datetime.now() - timedelta(days=7)).isoformat()
            c.execute('SELECT COUNT(*) FROM permanent_users WHERE last_seen > ?', (week_ago,))
            stats['active_users'] = c.fetchone()[0]
            c.execute('SELECT COUNT(*) FROM permanent_users WHERE is_banned = 1')
            stats['banned_users'] = c.fetchone()[0]
            c.execute('SELECT COUNT(*) FROM permanent_users WHERE is_premium = 1')
            stats['premium_users'] = c.fetchone()[0]
            c.execute('SELECT COUNT(*) FROM permanent_users WHERE role IN ("admin", "owner")')
            stats['admins'] = c.fetchone()[0]
            c.execute('SELECT COUNT(*) FROM permanent_files')
            stats['total_files'] = c.fetchone()[0]
            c.execute('SELECT COUNT(*) FROM permanent_scripts')
            stats['total_scripts'] = c.fetchone()[0]
            c.execute('SELECT COUNT(*) FROM permanent_feedback')
            stats['total_feedback'] = c.fetchone()[0]
            c.execute('SELECT SUM(referral_count) FROM permanent_users')
            result = c.fetchone()
            stats['total_referrals'] = result[0] if result and result[0] else 0
            return stats
        except Exception as e:
            print(f"Error getting stats: {e}")
            return {}
        finally:
            conn.close()

PERMANENT_DB = PermanentDatabase(DATABASE_PATH)

def fix_database_issue():
    print("="*60)
    print("🔧 DATABASE REPAIR - RUNNING FIX...")
    print("="*60)
    try:
        test_file = os.path.join(IROTECH_DIR, '.write_test')
        try:
            with open(test_file, 'w') as f:
                f.write('test')
            os.remove(test_file)
            print("✅ Directory is writable")
        except Exception as e:
            print(f"❌ Directory NOT writable: {e}")
            try:
                os.chmod(IROTECH_DIR, 0o777)
                print("✅ Fixed permissions with chmod 777")
            except:
                print("⚠️ Could not chmod. Try: sudo chmod -R 777 " + IROTECH_DIR)
                sys.exit(1)
        PERMANENT_DB._init_database()
        print("="*60)
        print("✅ DATABASE FIX COMPLETE!")
        print("📁 Database: " + DATABASE_PATH)
        print("="*60)
        return True
    except Exception as e:
        print(f"❌ CRITICAL DATABASE ERROR: {e}")
        sys.exit(1)

fix_database_issue()

def load_permanent_data():
    print("🔄 Loading permanent data from database...")
    try:
        users = PERMANENT_DB.get_all_users()
        for user in users:
            user_id = user[0]
            active_users.add(user_id)
            if user[4] == 1:
                banned_users.add(user_id)
        admin_list = PERMANENT_DB.get_admins()
        admin_ids.update(admin_list)
        conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False, timeout=30)
        c = conn.cursor()
        c.execute('SELECT user_id, expiry_date FROM permanent_subscriptions WHERE is_active = 1')
        subs = c.fetchall()
        for user_id, expiry_str in subs:
            if expiry_str:
                try:
                    expiry = datetime.fromisoformat(expiry_str)
                    if expiry > datetime.now():
                        user_subscriptions[user_id] = {'expiry': expiry}
                    else:
                        PERMANENT_DB.remove_subscription(user_id)
                except:
                    pass
        c.execute('SELECT user_id, file_name, file_type FROM permanent_files')
        files = c.fetchall()
        for user_id, file_name, file_type in files:
            if user_id not in user_files:
                user_files[user_id] = []
            user_files[user_id].append((file_name, file_type))
        c.execute('SELECT user_id, file_limit FROM permanent_users WHERE file_limit > 0')
        limits = c.fetchall()
        for user_id, limit in limits:
            user_limits[user_id] = limit
        c.execute('SELECT channel_id, channel_username, channel_name FROM permanent_channels WHERE is_mandatory = 1')
        channels = c.fetchall()
        for channel_id, channel_username, channel_name in channels:
            mandatory_channels[channel_id] = {
                'username': channel_username,
                'name': channel_name
            }
        c.execute('SELECT setting_value FROM permanent_settings WHERE setting_key = ?', ('bot_locked',))
        result = c.fetchone()
        if result:
            global bot_locked
            bot_locked = result[0].lower() == 'true'
        c.execute('SELECT user_id, referral_code, referred_by, referral_count, referral_extra_limit FROM permanent_users')
        ref_data = c.fetchall()
        for user_id, ref_code, referred_by, ref_count, ref_extra in ref_data:
            if ref_code:
                referral_codes[user_id] = ref_code
            if ref_count > 0:
                referral_counts[user_id] = ref_count
            if ref_extra > 0:
                referral_rewards[user_id] = ref_extra
            if referred_by:
                referral_used_by[ref_code] = referred_by if ref_code else None
        conn.close()
        print(f"✅ Loaded {len(active_users)} users, {len(admin_ids)} admins, {len(user_subscriptions)} subscriptions")
        print(f"✅ Loaded {sum(len(f) for f in user_files.values())} files, {len(mandatory_channels)} channels")
        print(f"✅ Loaded {len(referral_codes)} referral codes, {len(referral_counts)} users with referrals")
    except Exception as e:
        print(f"❌ Error loading permanent data: {e}")

load_permanent_data()

def is_user_banned(user_id):
    return PERMANENT_DB.is_user_banned(user_id)

def ban_user_db(user_id, reason, banned_by):
    if PERMANENT_DB.ban_user(user_id, reason, banned_by):
        banned_users.add(user_id)
        return True
    return False

def unban_user_db(user_id):
    if PERMANENT_DB.unban_user(user_id):
        banned_users.discard(user_id)
        return True
    return False

def get_user_file_limit(user_id):
    if user_id == OWNER_ID:
        return OWNER_LIMIT
    if user_id in admin_ids:
        return ADMIN_LIMIT
    custom_limit = PERMANENT_DB.get_user_limit(user_id)
    if custom_limit > 0:
        return custom_limit
    if user_id in user_limits:
        return user_limits[user_id]
    ref_stats = PERMANENT_DB.get_referral_stats(user_id)
    base_limit = FREE_USER_LIMIT
    if user_id in user_subscriptions:
        expiry = user_subscriptions[user_id].get('expiry')
        if expiry and expiry > datetime.now():
            base_limit = SUBSCRIBED_USER_LIMIT
    extra_limit = ref_stats.get('extra_limit', 0)
    return base_limit + extra_limit

def get_user_folder(user_id):
    user_folder = os.path.join(UPLOAD_BOTS_DIR, str(user_id))
    os.makedirs(user_folder, exist_ok=True)
    return user_folder

def get_user_file_count(user_id):
    return len(user_files.get(user_id, []))

def save_user_file(user_id, file_name, file_type='py'):
    file_path = os.path.join(get_user_folder(user_id), file_name)
    file_size = os.path.getsize(file_path) if os.path.exists(file_path) else 0
    if PERMANENT_DB.save_file(user_id, file_name, file_type, file_size):
        if user_id not in user_files:
            user_files[user_id] = []
        user_files[user_id] = [(fn, ft) for fn, ft in user_files[user_id] if fn != file_name]
        user_files[user_id].append((file_name, file_type))
        return True
    return False

def remove_user_file_db(user_id, file_name):
    if PERMANENT_DB.delete_file(user_id, file_name):
        if user_id in user_files:
            user_files[user_id] = [f for f in user_files[user_id] if f[0] != file_name]
            if not user_files[user_id]:
                del user_files[user_id]
        return True
    return False

def save_subscription(user_id, expiry):
    if PERMANENT_DB.save_subscription(user_id, expiry):
        user_subscriptions[user_id] = {'expiry': expiry}
        return True
    return False

def remove_subscription_db(user_id):
    if PERMANENT_DB.remove_subscription(user_id):
        if user_id in user_subscriptions:
            del user_subscriptions[user_id]
        return True
    return False

def add_admin_db(user_id, added_by):
    if PERMANENT_DB.add_admin(user_id, added_by):
        admin_ids.add(user_id)
        return True
    return False

def remove_admin_db(user_id):
    if PERMANENT_DB.remove_admin(user_id):
        admin_ids.discard(user_id)
        return True
    return False

def set_user_limit_db(user_id, limit, set_by):
    if PERMANENT_DB.set_user_limit(user_id, limit):
        user_limits[user_id] = limit
        return True
    return False

def remove_user_limit_db(user_id):
    if PERMANENT_DB.set_user_limit(user_id, -1):
        if user_id in user_limits:
            del user_limits[user_id]
        return True
    return False

def log_action(user_id, action, details=None, log_type='info'):
    return PERMANENT_DB.log_action(user_id, action, details, log_type)

def save_feedback(user_id, feedback, rating=None):
    return PERMANENT_DB.save_feedback(user_id, feedback, rating)

def save_script_permanent(user_id, script_name, script_code, script_type='py'):
    return PERMANENT_DB.save_script(user_id, script_name, script_code, script_type)

def get_script_permanent(user_id, script_name):
    return PERMANENT_DB.get_script(user_id, script_name)

def get_stats_permanent():
    return PERMANENT_DB.get_stats()

def save_mandatory_channel(channel_id, channel_username, channel_name, added_by):
    conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False, timeout=30)
    c = conn.cursor()
    try:
        c.execute('INSERT OR REPLACE INTO permanent_channels (channel_id, channel_username, channel_name, added_by, added_date, is_mandatory) VALUES (?, ?, ?, ?, ?, 1)',
                  (channel_id, channel_username, channel_name, added_by, datetime.now().isoformat()))
        conn.commit()
        mandatory_channels[channel_id] = {'username': channel_username, 'name': channel_name}
        return True
    except Exception as e:
        print(f"Error saving channel: {e}")
        return False
    finally:
        conn.close()

def remove_mandatory_channel_db(channel_id):
    conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False, timeout=30)
    c = conn.cursor()
    try:
        c.execute('DELETE FROM permanent_channels WHERE channel_id = ?', (channel_id,))
        conn.commit()
        if channel_id in mandatory_channels:
            del mandatory_channels[channel_id]
        return True
    except Exception as e:
        print(f"Error removing channel: {e}")
        return False
    finally:
        conn.close()

def generate_key(limit_value, duration=None, created_by=OWNER_ID):
    while True:
        num = str(random.randint(100000, 999999))
        key_code = f"PREMIUM-{num}"
        conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False, timeout=30)
        c = conn.cursor()
        c.execute('SELECT 1 FROM permanent_keys WHERE key_code = ?', (key_code,))
        if not c.fetchone():
            conn.close()
            break
        conn.close()
    expiry = None if duration is None else (datetime.now() + duration)
    if PERMANENT_DB.save_key(key_code, 'premium', limit_value, expiry, created_by, 1 if duration is None else 0):
        return key_code
    return None

def redeem_key(user_id, key_code):
    return PERMANENT_DB.redeem_key(key_code, user_id)

def get_user_referral_code(user_id):
    conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False, timeout=30)
    c = conn.cursor()
    try:
        c.execute('SELECT referral_code FROM permanent_users WHERE user_id = ?', (user_id,))
        result = c.fetchone()
        if result and result[0]:
            return result[0]
        code = PERMANENT_DB.generate_referral_code(user_id)
        c.execute('UPDATE permanent_users SET referral_code = ? WHERE user_id = ?', (code, user_id))
        conn.commit()
        return code
    except Exception as e:
        print(f"Error getting referral code: {e}")
        return None
    finally:
        conn.close()

def process_referral(user_id, referral_code):
    try:
        referrer_id = PERMANENT_DB.get_user_by_referral_code(referral_code)
        if not referrer_id or referrer_id == user_id:
            return False, "Invalid referral code or self-referral"
        conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False, timeout=30)
        c = conn.cursor()
        c.execute('SELECT referred_by FROM permanent_users WHERE user_id = ?', (user_id,))
        result = c.fetchone()
        if result and result[0]:
            conn.close()
            return False, "You already have a referrer"
        c.execute('UPDATE permanent_users SET referred_by = ? WHERE user_id = ?', (referrer_id, user_id))
        conn.commit()
        conn.close()
        PERMANENT_DB.give_referral_reward(referrer_id)
        conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False, timeout=30)
        c = conn.cursor()
        c.execute('UPDATE permanent_users SET referral_count = referral_count + 1 WHERE user_id = ?', (referrer_id,))
        conn.commit()
        conn.close()
        try:
            referrer_name = "User"
            try:
                referrer_info = bot.get_chat(referrer_id)
                referrer_name = referrer_info.first_name or "User"
            except:
                pass
            bot.send_message(referrer_id, 
                f"🎉 **New Referral!**\n\n"
                f"Someone joined using your referral link!\n\n"
                f"📊 **Your Stats:**\n"
                f"• Total Referrals: {PERMANENT_DB.get_referral_stats(referrer_id)['count'] + 1}\n"
                f"• Extra File Limit: {REFERRAL_REWARD_LIMIT} per referral\n"
                f"• Premium Days: {REFERRAL_REWARD_DAYS} days\n\n"
                f"Keep sharing your referral link for more rewards!",
                parse_mode='Markdown'
            )
        except:
            pass
        return True, "Referral successful!"
    except Exception as e:
        print(f"Error processing referral: {e}")
        return False, "Error processing referral"

def get_referral_stats(user_id):
    return PERMANENT_DB.get_referral_stats(user_id)

def get_referred_users(user_id):
    return PERMANENT_DB.get_referred_users(user_id)

def get_top_referrers(limit=10):
    return PERMANENT_DB.get_top_referrers(limit)

def check_code_security(file_path, file_type):
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        dangerous_patterns = [
            r'\bos\.system\b', r'\bos\.remove\b', r'\bos\.unlink\b',
            r'\bsubprocess\b', r'\beval\b', r'\bexec\b', r'\b__import__\b',
            r'\bctypes\b', r'\bshutil\.rmtree\b', r'\brm\s+-rf',
            r'\bdd\s+if=', r'\bmkfs\b', r'\bfdisk\b', r'\bchmod\s+777'
        ]
        found_patterns = []
        for pattern in dangerous_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                found_patterns.append(pattern)
        if found_patterns:
            return False, f"Code contains dangerous patterns: {', '.join(found_patterns[:3])}"
        return True, "Code is safe"
    except Exception as e:
        return False, f"Security check error: {str(e)}"

def scan_zip_security(zip_path):
    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            for file_info in zip_ref.infolist():
                if file_info.filename.endswith(('.py', '.js', '.sh', '.bat')):
                    with zip_ref.open(file_info.filename) as f:
                        try:
                            content = f.read().decode('utf-8', errors='ignore')
                        except:
                            continue
                        dangerous_patterns = [
                            r'rm\s+-rf', r'os\.system', r'subprocess',
                            r'eval', r'exec', r'__import__', r'ctypes'
                        ]
                        for pattern in dangerous_patterns:
                            if re.search(pattern, content, re.IGNORECASE):
                                return False, f"File {file_info.filename} contains dangerous content"
        return True, "Archive is safe"
    except Exception as e:
        return False, f"Error scanning archive: {str(e)}"

def is_user_member(user_id, channel_id):
    try:
        chat_member = bot.get_chat_member(channel_id, user_id)
        return chat_member.status in ['member', 'administrator', 'creator']
    except Exception as e:
        return False

def check_mandatory_subscription(user_id):
    if not mandatory_channels:
        return True, []
    not_joined = []
    for channel_id, channel_info in mandatory_channels.items():
        if not is_user_member(user_id, channel_id):
            not_joined.append((channel_id, channel_info))
    if not_joined:
        return False, not_joined
    return True, []

def create_subscription_check_message(not_joined_channels):
    message = "📢 **Important: Join Our Channels First:**\n\n"
    markup = types.InlineKeyboardMarkup()
    for channel_id, channel_info in not_joined_channels:
        channel_username = channel_info.get('username', '')
        channel_name = channel_info.get('name', 'Channel')
        if channel_username:
            channel_link = f"https://t.me/{channel_username.replace('@', '')}"
        else:
            channel_link = f"https://t.me/c/{channel_id.replace('-100', '')}"
        message += f"• {channel_name}\n"
        markup.add(types.InlineKeyboardButton(f"Join {channel_name}", url=channel_link))
    markup.add(types.InlineKeyboardButton("✅ Verify Subscription", callback_data='check_subscription_status'))
    return message, markup

def is_bot_running(script_owner_id, file_name):
    script_key = f"{script_owner_id}_{file_name}"
    script_info = bot_scripts.get(script_key)
    if script_info and script_info.get('process'):
        try:
            proc = psutil.Process(script_info['process'].pid)
            return proc.is_running() and proc.status() != psutil.STATUS_ZOMBIE
        except psutil.NoSuchProcess:
            if script_key in bot_scripts:
                del bot_scripts[script_key]
            return False
        except:
            return False
    return False

def kill_process_tree(process_info):
    try:
        if 'log_file' in process_info and hasattr(process_info['log_file'], 'close'):
            try:
                process_info['log_file'].close()
            except:
                pass
        process = process_info.get('process')
        if process and hasattr(process, 'pid'):
            try:
                parent = psutil.Process(process.pid)
                children = parent.children(recursive=True)
                for child in children:
                    try:
                        child.terminate()
                    except:
                        try:
                            child.kill()
                        except:
                            pass
                try:
                    parent.terminate()
                except:
                    try:
                        parent.kill()
                    except:
                        pass
            except psutil.NoSuchProcess:
                pass
    except Exception as e:
        print(f"Error killing process: {e}")

def run_script(script_path, script_owner_id, user_folder, file_name, message_obj_for_reply, attempt=1):
    max_attempts = 2
    if attempt > max_attempts:
        bot.reply_to(message_obj_for_reply, f"❌ Failed to run '{file_name}' after {max_attempts} attempts.")
        return
    script_key = f"{script_owner_id}_{file_name}"
    try:
        if not os.path.exists(script_path):
            bot.reply_to(message_obj_for_reply, f"❌ Error: Script '{file_name}' not found!")
            remove_user_file_db(script_owner_id, file_name)
            return
        if attempt == 1:
            check_command = [sys.executable, script_path]
            check_proc = None
            try:
                check_proc = subprocess.Popen(check_command, cwd=user_folder, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8', errors='ignore')
                stdout, stderr = check_proc.communicate(timeout=5)
                if check_proc.returncode != 0 and stderr:
                    match_py = re.search(r"ModuleNotFoundError: No module named '(.+?)'", stderr)
                    if match_py:
                        module_name = match_py.group(1).strip().strip("'\"")
                        success, _ = attempt_install_pip(module_name, message_obj_for_reply)
                        if success:
                            bot.reply_to(message_obj_for_reply, f"🔄 Install successful. Retrying '{file_name}'...")
                            time.sleep(2)
                            threading.Thread(target=run_script, args=(script_path, script_owner_id, user_folder, file_name, message_obj_for_reply, attempt + 1)).start()
                            return
                        else:
                            bot.reply_to(message_obj_for_reply, f"❌ Install failed. Cannot run '{file_name}'.")
                            return
            except subprocess.TimeoutExpired:
                if check_proc and check_proc.poll() is None:
                    check_proc.kill()
                    check_proc.communicate()
            except:
                pass
            finally:
                if check_proc and check_proc.poll() is None:
                    check_proc.kill()
                    check_proc.communicate()
        log_file_path = os.path.join(user_folder, f"{os.path.splitext(file_name)[0]}.log")
        log_file = open(log_file_path, 'w', encoding='utf-8', errors='ignore')
        process = subprocess.Popen(
            [sys.executable, script_path], cwd=user_folder, stdout=log_file, stderr=log_file,
            stdin=subprocess.PIPE, encoding='utf-8', errors='ignore'
        )
        bot_scripts[script_key] = {
            'process': process, 'log_file': log_file, 'file_name': file_name,
            'chat_id': message_obj_for_reply.chat.id,
            'script_owner_id': script_owner_id,
            'start_time': datetime.now(), 'user_folder': user_folder, 'type': 'py', 'script_key': script_key
        }
        bot.reply_to(message_obj_for_reply, f"✅ Python script '{file_name}' started! (PID: {process.pid})")
    except Exception as e:
        error_msg = f"❌ Error starting Python script '{file_name}': {str(e)}"
        print(error_msg)
        bot.reply_to(message_obj_for_reply, error_msg)
        if script_key in bot_scripts:
            kill_process_tree(bot_scripts[script_key])
            del bot_scripts[script_key]

def run_js_script(script_path, script_owner_id, user_folder, file_name, message_obj_for_reply, attempt=1):
    max_attempts = 2
    if attempt > max_attempts:
        bot.reply_to(message_obj_for_reply, f"❌ Failed to run '{file_name}' after {max_attempts} attempts.")
        return
    script_key = f"{script_owner_id}_{file_name}"
    try:
        if not os.path.exists(script_path):
            bot.reply_to(message_obj_for_reply, f"❌ Error: Script '{file_name}' not found!")
            remove_user_file_db(script_owner_id, file_name)
            return
        if attempt == 1:
            check_command = ['node', script_path]
            check_proc = None
            try:
                check_proc = subprocess.Popen(check_command, cwd=user_folder, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8', errors='ignore')
                stdout, stderr = check_proc.communicate(timeout=5)
                if check_proc.returncode != 0 and stderr:
                    match_js = re.search(r"Cannot find module '(.+?)'", stderr)
                    if match_js:
                        module_name = match_js.group(1).strip().strip("'\"")
                        if not module_name.startswith('.') and not module_name.startswith('/'):
                            success, _ = attempt_install_npm(module_name, user_folder, message_obj_for_reply)
                            if success:
                                bot.reply_to(message_obj_for_reply, f"🔄 NPM Install successful. Retrying '{file_name}'...")
                                time.sleep(2)
                                threading.Thread(target=run_js_script, args=(script_path, script_owner_id, user_folder, file_name, message_obj_for_reply, attempt + 1)).start()
                                return
                            else:
                                bot.reply_to(message_obj_for_reply, f"❌ NPM Install failed. Cannot run '{file_name}'.")
                                return
            except subprocess.TimeoutExpired:
                if check_proc and check_proc.poll() is None:
                    check_proc.kill()
                    check_proc.communicate()
            except:
                pass
            finally:
                if check_proc and check_proc.poll() is None:
                    check_proc.kill()
                    check_proc.communicate()
        log_file_path = os.path.join(user_folder, f"{os.path.splitext(file_name)[0]}.log")
        log_file = open(log_file_path, 'w', encoding='utf-8', errors='ignore')
        process = subprocess.Popen(
            ['node', script_path], cwd=user_folder, stdout=log_file, stderr=log_file,
            stdin=subprocess.PIPE, encoding='utf-8', errors='ignore'
        )
        bot_scripts[script_key] = {
            'process': process, 'log_file': log_file, 'file_name': file_name,
            'chat_id': message_obj_for_reply.chat.id,
            'script_owner_id': script_owner_id,
            'start_time': datetime.now(), 'user_folder': user_folder, 'type': 'js', 'script_key': script_key
        }
        bot.reply_to(message_obj_for_reply, f"✅ JS script '{file_name}' started! (PID: {process.pid})")
    except Exception as e:
        error_msg = f"❌ Error starting JS script '{file_name}': {str(e)}"
        print(error_msg)
        bot.reply_to(message_obj_for_reply, error_msg)
        if script_key in bot_scripts:
            kill_process_tree(bot_scripts[script_key])
            del bot_scripts[script_key]

TELEGRAM_MODULES = {
    'telebot': 'pyTelegramBotAPI',
    'telegram': 'python-telegram-bot',
    'aiogram': 'aiogram',
    'pyrogram': 'pyrogram',
    'telethon': 'telethon',
    'requests': 'requests',
    'pillow': 'Pillow',
    'cv2': 'opencv-python',
    'yaml': 'PyYAML',
    'dotenv': 'python-dotenv',
    'psutil': 'psutil',
    'flask': 'Flask',
    'sqlalchemy': 'SQLAlchemy',
}

def attempt_install_pip(module_name, message, manual_request=False):
    package_name = TELEGRAM_MODULES.get(module_name.lower(), module_name)
    if package_name is None:
        return False, "Core module - no installation needed"
    try:
        if manual_request:
            bot.reply_to(message, f"🔄 Manual installation requested for `{module_name}` -> `{package_name}`...", parse_mode='Markdown')
        else:
            bot.reply_to(message, f"🐍 Module `{module_name}` not found. Installing `{package_name}`...", parse_mode='Markdown')
        command = [sys.executable, '-m', 'pip', 'install', package_name]
        result = subprocess.run(command, capture_output=True, text=True, check=False, encoding='utf-8', errors='ignore')
        if result.returncode == 0:
            log_msg = f"Installed {package_name}. Output:\n{result.stdout}"
            bot.reply_to(message, f"✅ Package `{package_name}` installed successfully.", parse_mode='Markdown')
            return True, log_msg
        else:
            error_msg = f"❌ Failed to install `{package_name}`.\nLog:\n```\n{result.stderr or result.stdout}\n```"
            if len(error_msg) > 4000:
                error_msg = error_msg[:4000] + "\n... (Log truncated)"
            bot.reply_to(message, error_msg, parse_mode='Markdown')
            return False, error_msg
    except Exception as e:
        error_msg = f"❌ Error installing `{package_name}`: {str(e)}"
        bot.reply_to(message, error_msg)
        return False, error_msg

def attempt_install_npm(module_name, user_folder, message, manual_request=False):
    try:
        if manual_request:
            bot.reply_to(message, f"🔄 Manual Node package installation requested for `{module_name}`...", parse_mode='Markdown')
        else:
            bot.reply_to(message, f"🟠 Node package `{module_name}` not found. Installing locally...", parse_mode='Markdown')
        command = ['npm', 'install', module_name]
        result = subprocess.run(command, capture_output=True, text=True, check=False, cwd=user_folder, encoding='utf-8', errors='ignore')
        if result.returncode == 0:
            log_msg = f"Installed {module_name}. Output:\n{result.stdout}"
            bot.reply_to(message, f"✅ Node package `{module_name}` installed locally.", parse_mode='Markdown')
            return True, log_msg
        else:
            error_msg = f"❌ Failed to install Node package `{module_name}`.\nLog:\n```\n{result.stderr or result.stdout}\n```"
            if len(error_msg) > 4000:
                error_msg = error_msg[:4000] + "\n... (Log truncated)"
            bot.reply_to(message, error_msg, parse_mode='Markdown')
            return False, error_msg
    except FileNotFoundError:
        error_msg = "❌ Error: 'npm' not found. Ensure Node.js/npm are installed."
        bot.reply_to(message, error_msg)
        return False, error_msg
    except Exception as e:
        error_msg = f"❌ Error installing Node package `{module_name}`: {str(e)}"
        bot.reply_to(message, error_msg)
        return False, error_msg

def manual_install_module_init(message):
    user_id = message.from_user.id
    if is_user_banned(user_id):
        bot.reply_to(message, "❌ You are banned from using this bot.")
        return
    is_subscribed, not_joined = check_mandatory_subscription(user_id)
    if not is_subscribed and user_id not in admin_ids:
        subscription_message, markup = create_subscription_check_message(not_joined)
        bot.reply_to(message, subscription_message, reply_markup=markup, parse_mode='Markdown')
        return
    if bot_locked and user_id not in admin_ids:
        bot.reply_to(message, "⚠️ Bot locked by admin. Try later.")
        return
    msg = bot.reply_to(message, "📦 Send module name to install (e.g., `requests` or `pillow`)\nFor Node.js: `npm:module_name`\n/cancel to cancel")
    bot.register_next_step_handler(msg, process_manual_install_module)

def process_manual_install_module(message):
    user_id = message.from_user.id
    if is_user_banned(user_id):
        bot.reply_to(message, "❌ You are banned from using this bot.")
        return
    if message.text.lower() == '/cancel':
        bot.reply_to(message, "❌ Installation cancelled.")
        return
    module_name = message.text.strip()
    if module_name.lower().startswith('npm:'):
        module_name = module_name[4:].strip()
        user_folder = get_user_folder(user_id)
        success, log = attempt_install_npm(module_name, user_folder, message, manual_request=True)
    else:
        success, log = attempt_install_pip(module_name, message, manual_request=True)
    if success:
        log_action(user_id, f"Installed module: {module_name}", log, 'module')

def handle_zip_file(downloaded_file_content, file_name_zip, message):
    user_id = message.from_user.id
    user_folder = get_user_folder(user_id)
    temp_dir = None
    try:
        temp_dir = tempfile.mkdtemp(prefix=f"user_{user_id}_zip_")
        zip_path = os.path.join(temp_dir, file_name_zip)
        with open(zip_path, 'wb') as new_file:
            new_file.write(downloaded_file_content)
        is_safe, security_msg = scan_zip_security(zip_path)
        if not is_safe:
            print(f"⚠️ Unsafe ZIP from {user_id}: {security_msg}")
        process_zip_file(zip_path, user_id, user_folder, file_name_zip, message, temp_dir)
    except zipfile.BadZipFile as e:
        bot.reply_to(message, f"❌ Error: Invalid/corrupted ZIP. {e}")
    except Exception as e:
        bot.reply_to(message, f"❌ Error processing zip: {str(e)}")
    finally:
        if temp_dir and os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir)
            except:
                pass

def process_zip_file(zip_path, user_id, user_folder, file_name_zip, message, temp_dir=None):
    cleanup_temp = False
    if temp_dir is None:
        temp_dir = tempfile.mkdtemp(prefix=f"user_{user_id}_zip_")
        cleanup_temp = True
    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            for member in zip_ref.infolist():
                member_path = os.path.abspath(os.path.join(temp_dir, member.filename))
                if not member_path.startswith(os.path.abspath(temp_dir)):
                    raise zipfile.BadZipFile(f"Zip has unsafe path: {member.filename}")
            zip_ref.extractall(temp_dir)
        extracted_items = os.listdir(temp_dir)
        py_files = [f for f in extracted_items if f.endswith('.py')]
        js_files = [f for f in extracted_items if f.endswith('.js')]
        req_file = 'requirements.txt' if 'requirements.txt' in extracted_items else None
        pkg_json = 'package.json' if 'package.json' in extracted_items else None
        if req_file:
            req_path = os.path.join(temp_dir, req_file)
            bot.reply_to(message, f"🔄 Installing Python deps from `{req_file}`...")
            try:
                command = [sys.executable, '-m', 'pip', 'install', '-r', req_path]
                result = subprocess.run(command, capture_output=True, text=True, check=True, encoding='utf-8', errors='ignore')
                bot.reply_to(message, f"✅ Python deps from `{req_file}` installed.")
            except Exception as e:
                bot.reply_to(message, f"❌ Failed to install Python deps: {str(e)}")
                return
        if pkg_json:
            bot.reply_to(message, f"🔄 Installing Node deps from `{pkg_json}`...")
            try:
                command = ['npm', 'install']
                result = subprocess.run(command, capture_output=True, text=True, check=True, cwd=temp_dir, encoding='utf-8', errors='ignore')
                bot.reply_to(message, f"✅ Node deps from `{pkg_json}` installed.")
            except Exception as e:
                bot.reply_to(message, f"❌ Failed to install Node deps: {str(e)}")
                return
        main_script_name = None
        file_type = None
        preferred_py = ['main.py', 'bot.py', 'app.py']
        preferred_js = ['index.js', 'main.js', 'bot.js', 'app.js']
        for p in preferred_py:
            if p in py_files:
                main_script_name = p
                file_type = 'py'
                break
        if not main_script_name:
            for p in preferred_js:
                if p in js_files:
                    main_script_name = p
                    file_type = 'js'
                    break
        if not main_script_name:
            if py_files:
                main_script_name = py_files[0]
                file_type = 'py'
            elif js_files:
                main_script_name = js_files[0]
                file_type = 'js'
        if not main_script_name:
            bot.reply_to(message, "❌ No `.py` or `.js` script found in archive!")
            return
        for item_name in os.listdir(temp_dir):
            src_path = os.path.join(temp_dir, item_name)
            dest_path = os.path.join(user_folder, item_name)
            if os.path.isdir(dest_path):
                shutil.rmtree(dest_path)
            elif os.path.exists(dest_path):
                os.remove(dest_path)
            shutil.move(src_path, dest_path)
        save_user_file(user_id, main_script_name, file_type)
        main_script_path = os.path.join(user_folder, main_script_name)
        bot.reply_to(message, f"✅ Files extracted. Starting main script: `{main_script_name}`...", parse_mode='Markdown')
        if file_type == 'py':
            threading.Thread(target=run_script, args=(main_script_path, user_id, user_folder, main_script_name, message)).start()
        elif file_type == 'js':
            threading.Thread(target=run_js_script, args=(main_script_path, user_id, user_folder, main_script_name, message)).start()
    except Exception as e:
        bot.reply_to(message, f"❌ Error processing zip: {str(e)}")
    finally:
        if cleanup_temp and temp_dir and os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir)
            except:
                pass

def handle_py_file(file_path, script_owner_id, user_folder, file_name, message):
    try:
        save_user_file(script_owner_id, file_name, 'py')
        threading.Thread(target=run_script, args=(file_path, script_owner_id, user_folder, file_name, message)).start()
    except Exception as e:
        bot.reply_to(message, f"❌ Error processing Python file: {str(e)}")

def handle_js_file(file_path, script_owner_id, user_folder, file_name, message):
    try:
        save_user_file(script_owner_id, file_name, 'js')
        threading.Thread(target=run_js_script, args=(file_path, script_owner_id, user_folder, file_name, message)).start()
    except Exception as e:
        bot.reply_to(message, f"❌ Error processing JS file: {str(e)}")

def send_host_notification(user_id, file_name, file_type, is_safe=True, security_msg=""):
    try:
        user = bot.get_chat(user_id)
        user_name = user.first_name or "Unknown"
        user_username = f"@{user.username}" if user.username else "No username"
        safe_emoji = "✅" if is_safe else "⚠️"
        safe_text = "Safe" if is_safe else "Risky (Auto-hosted)"
        notification = (
            f"🤖 **New Bot Hosted!**\n\n"
            f"👤 **User:** {user_name}\n"
            f"🆔 **User ID:** `{user_id}`\n"
            f"📛 **Username:** {user_username}\n"
            f"📁 **File:** `{file_name}`\n"
            f"📂 **Type:** {file_type.upper()}\n"
            f"🛡️ **Security:** {safe_emoji} {safe_text}\n"
            f"⏰ **Time:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        )
        if not is_safe and security_msg:
            notification += f"⚠️ **Warning:** {security_msg}\n"
        notification += "\n📌 Bot is now live and running."
        for admin_id in admin_ids:
            try:
                bot.send_message(admin_id, notification, parse_mode='Markdown')
            except:
                pass
    except Exception as e:
        print(f"Error sending notification: {e}")

def create_main_menu_inline(user_id):
    markup = types.InlineKeyboardMarkup(row_width=2)
    buttons = [
        types.InlineKeyboardButton('📢 Updates', url=f'https://t.me/{UPDATE_CHANNEL.replace("@", "")}'),
        types.InlineKeyboardButton('📤 Upload', callback_data='upload'),
        types.InlineKeyboardButton('📂 Files', callback_data='check_files'),
        types.InlineKeyboardButton('⚡ Speed', callback_data='speed'),
        types.InlineKeyboardButton('📦 Install', callback_data='manual_install'),
        types.InlineKeyboardButton('🔗 Referrals', callback_data='referrals'),
        types.InlineKeyboardButton('📞 Contact', url=f'https://t.me/{YOUR_USERNAME.replace("@", "")}')
    ]
    if user_id in admin_ids:
        admin_buttons = [
            types.InlineKeyboardButton('💳 Subscriptions', callback_data='subscription'),
            types.InlineKeyboardButton('📊 Stats', callback_data='stats'),
            types.InlineKeyboardButton('🔒 Lock' if not bot_locked else '🔓 Unlock',
                                     callback_data='lock_bot' if not bot_locked else 'unlock_bot'),
            types.InlineKeyboardButton('📢 Broadcast', callback_data='broadcast'),
            types.InlineKeyboardButton('👑 Admin', callback_data='admin_panel'),
            types.InlineKeyboardButton('🟢 Run All', callback_data='run_all_scripts'),
            types.InlineKeyboardButton('📢 Channel Add', callback_data='manage_mandatory_channels'),
            types.InlineKeyboardButton('👥 Users', callback_data='user_management'),
            types.InlineKeyboardButton('🛠️ Install', callback_data='admin_install'),
            types.InlineKeyboardButton('⚙️ Settings', callback_data='admin_settings'),
            types.InlineKeyboardButton('🔑 Manage Keys', callback_data='manage_keys'),
            types.InlineKeyboardButton('🔗 Referral Stats', callback_data='admin_referrals')
        ]
        markup.add(buttons[0])
        markup.add(buttons[1], buttons[2])
        markup.add(buttons[3], admin_buttons[0])
        markup.add(admin_buttons[1], admin_buttons[3])
        markup.add(admin_buttons[2], admin_buttons[5])
        markup.add(admin_buttons[6], admin_buttons[8])
        markup.add(admin_buttons[7], admin_buttons[9])
        markup.add(admin_buttons[4])
        markup.add(admin_buttons[10])
        markup.add(buttons[5])
        markup.add(buttons[6])
        markup.add(admin_buttons[11])
    else:
        markup.add(buttons[0])
        markup.add(buttons[1], buttons[2])
        markup.add(buttons[3], buttons[4])
        markup.add(types.InlineKeyboardButton('📊 Stats', callback_data='stats'))
        markup.add(types.InlineKeyboardButton('🎫 Redeem Key', callback_data='redeem_key'))
        markup.add(types.InlineKeyboardButton('👤 Profile', callback_data='profile'))
        markup.add(buttons[5])
        markup.add(buttons[6])
    return markup

def create_control_buttons(script_owner_id, file_name, is_running=True):
    markup = types.InlineKeyboardMarkup(row_width=2)
    if is_running:
        markup.row(
            types.InlineKeyboardButton("🔴 Stop", callback_data=f'stop_{script_owner_id}_{file_name}'),
            types.InlineKeyboardButton("🔄 Restart", callback_data=f'restart_{script_owner_id}_{file_name}')
        )
        markup.row(
            types.InlineKeyboardButton("🗑️ Delete", callback_data=f'delete_{script_owner_id}_{file_name}'),
            types.InlineKeyboardButton("📜 Logs", callback_data=f'logs_{script_owner_id}_{file_name}')
        )
    else:
        markup.row(
            types.InlineKeyboardButton("🟢 Start", callback_data=f'start_{script_owner_id}_{file_name}'),
            types.InlineKeyboardButton("🗑️ Delete", callback_data=f'delete_{script_owner_id}_{file_name}')
        )
        markup.row(
            types.InlineKeyboardButton("📜 View Logs", callback_data=f'logs_{script_owner_id}_{file_name}')
        )
    markup.add(types.InlineKeyboardButton("🔙 Back to Files", callback_data='check_files'))
    return markup

def create_admin_panel():
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.row(
        types.InlineKeyboardButton('➕ Add Admin', callback_data='add_admin'),
        types.InlineKeyboardButton('➖ Remove Admin', callback_data='remove_admin')
    )
    markup.row(types.InlineKeyboardButton('📋 List Admins', callback_data='list_admins'))
    markup.row(types.InlineKeyboardButton('🔙 Back to Main', callback_data='back_to_main'))
    return markup

def create_user_management_menu():
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.row(
        types.InlineKeyboardButton('🚫 Ban User', callback_data='ban_user'),
        types.InlineKeyboardButton('✅ Unban User', callback_data='unban_user')
    )
    markup.row(
        types.InlineKeyboardButton('📊 User Info', callback_data='user_info'),
        types.InlineKeyboardButton('👥 All Users', callback_data='all_users')
    )
    markup.row(
        types.InlineKeyboardButton('🔧 Set Limit', callback_data='set_user_limit'),
        types.InlineKeyboardButton('🗑️ Remove Limit', callback_data='remove_user_limit')
    )
    markup.row(types.InlineKeyboardButton('🔙 Back to Main', callback_data='back_to_main'))
    return markup

def create_subscription_menu():
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.row(
        types.InlineKeyboardButton('➕ Add Subscription', callback_data='add_subscription'),
        types.InlineKeyboardButton('➖ Remove Subscription', callback_data='remove_subscription')
    )
    markup.row(types.InlineKeyboardButton('🔍 Check Subscription', callback_data='check_subscription'))
    markup.row(types.InlineKeyboardButton('🔙 Back to Main', callback_data='back_to_main'))
    return markup

def create_admin_settings_menu():
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.row(
        types.InlineKeyboardButton('📊 System Info', callback_data='system_info'),
        types.InlineKeyboardButton('📈 Performance', callback_data='bot_performance')
    )
    markup.row(
        types.InlineKeyboardButton('🧹 Cleanup', callback_data='cleanup_files'),
        types.InlineKeyboardButton('📋 Install Logs', callback_data='install_logs')
    )
    markup.row(types.InlineKeyboardButton('🔙 Back to Main', callback_data='back_to_main'))
    return markup

def create_mandatory_channels_menu():
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.row(
        types.InlineKeyboardButton('➕ Add Channel', callback_data='add_mandatory_channel'),
        types.InlineKeyboardButton('➖ Remove Channel', callback_data='remove_mandatory_channel')
    )
    markup.row(types.InlineKeyboardButton('📋 List Channels', callback_data='list_mandatory_channels'))
    markup.row(types.InlineKeyboardButton('🔙 Back to Main', callback_data='back_to_main'))
    return markup

def create_key_management_menu():
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.row(
        types.InlineKeyboardButton('🎫 Generate Key', callback_data='gen_key_admin'),
        types.InlineKeyboardButton('📋 List Keys', callback_data='list_keys_admin')
    )
    markup.row(types.InlineKeyboardButton('🔙 Back to Main', callback_data='back_to_main'))
    return markup

def create_referral_menu(user_id):
    ref_stats = get_referral_stats(user_id)
    ref_code = get_user_referral_code(user_id)
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton('🔗 My Referral Link', callback_data='my_referral_link'),
        types.InlineKeyboardButton('📊 Referral Stats', callback_data='referral_stats')
    )
    markup.add(
        types.InlineKeyboardButton('🏆 Top Referrers', callback_data='top_referrers'),
        types.InlineKeyboardButton('📋 Referred Users', callback_data='referred_users')
    )
    markup.add(types.InlineKeyboardButton('🔙 Back to Main', callback_data='back_to_main'))
    return markup

def create_admin_referral_menu():
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton('📊 All Referral Stats', callback_data='admin_referral_stats'),
        types.InlineKeyboardButton('🏆 Top Referrers', callback_data='admin_top_referrers')
    )
    markup.add(types.InlineKeyboardButton('🔙 Back to Main', callback_data='back_to_main'))
    return markup

USER_COMMAND_BUTTONS_LAYOUT = [
    ["📢 Updates Channel", "🎁 Rewards"],
    ["📤 Upload File", "📂 Check Files"],
    ["⚡ Bot Speed", "📊 Statistics"],
    ["🎫 Redeem Key", "📦 Manual Install"],
    ["🔗 Referrals", "👤 My Profile"],
    ["📞 Contact Owner", "🆘 Help"],
    ["📋 My Scripts", "⭐ Premium"],
    ["🔔 Notifications", "📚 Tutorial"],
    ["🎮 Commands", "💡 Tips"],
    ["📢 Announcements", "❓ FAQ"],
    ["📝 Feedback", "🎯 Quick Start"]
]

ADMIN_COMMAND_BUTTONS_LAYOUT = [
    ["📢 Updates Channel", "🎁 Rewards"],
    ["📤 Upload File", "📂 Check Files"],
    ["⚡ Bot Speed", "📊 Statistics"],
    ["💳 Subscriptions", "📢 Broadcast"],
    ["🔒 Lock Bot", "🟢 Running All Code"],
    ["👑 Admin Panel", "📞 Contact Owner"],
    ["📢 Channel Add", "🛠️ Manual Install"],
    ["👥 User Management", "⚙️ Settings"],
    ["📊 Dashboard", "📈 Analytics"],
    ["🔑 Manage Keys", "🎫 Generate Key"],
    ["🔗 Referral Stats", "📋 Audit Logs"],
    ["🧹 Cleanup", "🔄 Restart Bot"],
    ["💾 Backup", "📚 Help Docs"],
    ["🎮 Commands", "💡 Tips"],
    ["📢 Announcements", "👤 My Profile"],
    ["⭐ Premium", "❓ FAQ"],
    ["📝 Feedback", "🔗 Referrals"]
]

def create_reply_keyboard_main_menu(user_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    layout_to_use = ADMIN_COMMAND_BUTTONS_LAYOUT if user_id in admin_ids else USER_COMMAND_BUTTONS_LAYOUT
    for row_buttons_text in layout_to_use:
        markup.add(*[types.KeyboardButton(text) for text in row_buttons_text])
    return markup

@bot.message_handler(commands=['start', 'help'])
def command_send_welcome(message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    user_name = message.from_user.first_name
    if is_user_banned(user_id):
        bot.send_message(chat_id, "❌ You are banned from using this bot.")
        return
    is_subscribed, not_joined = check_mandatory_subscription(user_id)
    if not is_subscribed and user_id not in admin_ids:
        subscription_message, markup = create_subscription_check_message(not_joined)
        bot.send_message(chat_id, subscription_message, reply_markup=markup, parse_mode='Markdown')
        return
    if bot_locked and user_id not in admin_ids:
        bot.send_message(chat_id, "⚠️ Bot locked by admin. Try later.")
        return
    user = bot.get_chat(user_id)
    PERMANENT_DB.save_user(
        user_id,
        user.username,
        user.first_name,
        user.last_name
    )
    if user_id not in active_users:
        add_active_user(user_id)
        try:
            owner_notification = f"🎉 New user!\n👤 Name: {user_name}\n🆔 ID: `{user_id}`"
            bot.send_message(OWNER_ID, owner_notification, parse_mode='Markdown')
        except Exception as e:
            print(f"Failed to notify owner about new user {user_id}: {e}")
    if message.text and ' ' in message.text:
        parts = message.text.split(' ', 1)
        if len(parts) > 1 and parts[1].startswith('ref_'):
            referral_code = parts[1]
            success, msg = process_referral(user_id, referral_code)
            if success:
                bot.send_message(chat_id, f"✅ {msg}")
    file_limit = get_user_file_limit(user_id)
    current_files = get_user_file_count(user_id)
    limit_str = str(file_limit) if file_limit != float('inf') else "Unlimited"
    ref_stats = get_referral_stats(user_id)
    ref_count = ref_stats.get('count', 0)
    if user_id == OWNER_ID:
        user_status = "👑 Owner"
    elif user_id in admin_ids:
        user_status = "🛡️ Admin"
    elif user_id in user_subscriptions:
        expiry_date = user_subscriptions[user_id].get('expiry')
        if expiry_date and expiry_date > datetime.now():
            days_left = (expiry_date - datetime.now()).days
            user_status = f"⭐ Premium ({days_left} days left)"
        else:
            user_status = "🆓 Free User (Expired Sub)"
    else:
        user_status = "🆓 Free User"
    welcome_msg = (
        f"〽️ Welcome, {user_name}!\n\n"
        f"🆔 ID: `{user_id}`\n"
        f"🔰 Status: {user_status}\n"
        f"📁 Files: {current_files} / {limit_str}\n"
        f"🔗 Referrals: {ref_count}\n\n"
        f"🤖 Host & run Python (`.py`) or JS (`.js`) scripts.\n"
        f"📦 Manual module installation available\n"
        f"🔗 Invite friends and earn rewards!\n\n"
        f"👇 Use buttons or type commands."
    )
    main_reply_markup = create_reply_keyboard_main_menu(user_id)
    try:
        bot.send_message(chat_id, welcome_msg, reply_markup=main_reply_markup, parse_mode='Markdown')
    except Exception as e:
        print(f"Error sending welcome to {user_id}: {e}")

@bot.message_handler(commands=['profile'])
def command_profile(message):
    user_id = message.from_user.id
    if is_user_banned(user_id):
        bot.reply_to(message, "❌ You are banned from using this bot.")
        return
    is_subscribed, not_joined = check_mandatory_subscription(user_id)
    if not is_subscribed and user_id not in admin_ids:
        subscription_message, markup = create_subscription_check_message(not_joined)
        bot.reply_to(message, subscription_message, reply_markup=markup, parse_mode='Markdown')
        return
    user = bot.get_chat(user_id)
    user_name = user.first_name or "Unknown"
    username = f"@{user.username}" if user.username else "No username"
    file_count = get_user_file_count(user_id)
    file_limit = get_user_file_limit(user_id)
    limit_str = str(file_limit) if file_limit != float('inf') else "Unlimited"
    running_scripts = sum(1 for f, _ in user_files.get(user_id, []) if is_bot_running(user_id, f[0]))
    ref_stats = get_referral_stats(user_id)
    ref_code = get_user_referral_code(user_id)
    ref_count = ref_stats.get('count', 0)
    ref_extra = ref_stats.get('extra_limit', 0)
    if user_id == OWNER_ID:
        status = "👑 Owner"
    elif user_id in admin_ids:
        status = "🛡️ Admin"
    elif user_id in banned_users:
        status = "🚫 Banned"
    elif user_id in user_subscriptions:
        expiry = user_subscriptions[user_id].get('expiry')
        if expiry and expiry > datetime.now():
            days_left = (expiry - datetime.now()).days
            status = f"⭐ Premium ({days_left} days left)"
        else:
            status = "🆓 Free (Expired)"
    else:
        status = "🆓 Free"
    join_date = "Unknown"
    try:
        conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False, timeout=30)
        c = conn.cursor()
        c.execute('SELECT join_date FROM permanent_users WHERE user_id = ?', (user_id,))
        result = c.fetchone()
        if result:
            join_date = result[0][:10] if result[0] else "Unknown"
        conn.close()
    except:
        pass
    profile_msg = f"""
👤 **User Profile**

📛 **Name:** {user_name}
🆔 **ID:** `{user_id}`
📌 **Username:** {username}
🔰 **Status:** {status}
📅 **Joined:** {join_date}

📁 **Files:** {file_count} / {limit_str}
🤖 **Running Scripts:** {running_scripts}

🔗 **Referral System:**
┣ 🔗 Your Code: `{ref_code}`
┣ 👥 Referrals: {ref_count}
┗ 📈 Extra Limit: +{ref_extra}

📊 **Total Active Users:** {len(active_users)}
🔢 **Total Files:** {sum(len(f) for f in user_files.values())}
"""
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("📂 My Files", callback_data='check_files'),
        types.InlineKeyboardButton("🎫 Redeem Key", callback_data='redeem_key')
    )
    markup.add(
        types.InlineKeyboardButton("⭐ Premium", callback_data='premium_info'),
        types.InlineKeyboardButton("🔗 Referrals", callback_data='referrals')
    )
    markup.add(types.InlineKeyboardButton("🔄 Refresh", callback_data='refresh_profile'))
    markup.add(types.InlineKeyboardButton("🔙 Back to Main", callback_data='back_to_main'))
    bot.reply_to(message, profile_msg, reply_markup=markup, parse_mode='Markdown')

@bot.message_handler(commands=['referral', 'referrals'])
def command_referral(message):
    user_id = message.from_user.id
    if is_user_banned(user_id):
        bot.reply_to(message, "❌ You are banned from using this bot.")
        return
    is_subscribed, not_joined = check_mandatory_subscription(user_id)
    if not is_subscribed and user_id not in admin_ids:
        subscription_message, markup = create_subscription_check_message(not_joined)
        bot.reply_to(message, subscription_message, reply_markup=markup, parse_mode='Markdown')
        return
    ref_code = get_user_referral_code(user_id)
    ref_stats = get_referral_stats(user_id)
    ref_count = ref_stats.get('count', 0)
    ref_extra = ref_stats.get('extra_limit', 0)
    referral_link = f"https://t.me/{bot.get_me().username}?start=ref_{ref_code}"
    referral_msg = f"""
🔗 **Referral System**

**Your Referral Link:**
`{referral_link}`

**Share this link** with your friends and earn rewards!

**Rewards per Referral:**
┣ 📁 +{REFERRAL_REWARD_LIMIT} File Limit
┗ ⭐ +{REFERRAL_REWARD_DAYS} Premium Days

**Your Stats:**
┣ 👥 Total Referrals: {ref_count}
┣ 📈 Extra File Limit: +{ref_extra}
┗ 🔗 Your Code: `{ref_code}`

**Top Referrers:**
"""
    top_refs = get_top_referrers(5)
    if top_refs:
        for i, (uid, username, count, extra) in enumerate(top_refs, 1):
            name = username or f"User {uid}"
            referral_msg += f"\n{i}. {name} - {count} referrals"
    else:
        referral_msg += "\nNo referrers yet. Be the first!"
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("📋 Referred Users", callback_data='referred_users'),
        types.InlineKeyboardButton("🏆 Top Referrers", callback_data='top_referrers')
    )
    markup.add(
        types.InlineKeyboardButton("📤 Share Link", callback_data='share_referral'),
        types.InlineKeyboardButton("🔄 Refresh", callback_data='refresh_referral')
    )
    markup.add(types.InlineKeyboardButton("🔙 Back to Main", callback_data='back_to_main'))
    bot.reply_to(message, referral_msg, reply_markup=markup, parse_mode='Markdown')

@bot.message_handler(commands=['premium'])
def command_premium(message):
    user_id = message.from_user.id
    if is_user_banned(user_id):
        bot.reply_to(message, "❌ You are banned from using this bot.")
        return
    is_subscribed, not_joined = check_mandatory_subscription(user_id)
    if not is_subscribed and user_id not in admin_ids:
        subscription_message, markup = create_subscription_check_message(not_joined)
        bot.reply_to(message, subscription_message, reply_markup=markup, parse_mode='Markdown')
        return
    is_premium = False
    expiry_str = "None"
    if user_id in user_subscriptions:
        expiry = user_subscriptions[user_id].get('expiry')
        if expiry and expiry > datetime.now():
            is_premium = True
            days_left = (expiry - datetime.now()).days
            expiry_str = f"{days_left} days left (expires {expiry.strftime('%Y-%m-%d')})"
    premium_msg = f"""
⭐ **Premium Subscription**

{'✅ You are currently a Premium user!' if is_premium else '🔄 You are on Free plan'}

**Premium Benefits:**
┣ 📁 **Higher File Limit:** 3 files (vs 1 for free)
┣ ⚡ **Priority Support:** Faster response times
┣ 🎯 **Early Access:** New features first
┣ 📊 **Advanced Analytics:** Detailed bot stats
┣ 🛡️ **Enhanced Security:** Extra protection
┗ 🌟 **Exclusive Badge:** Show your status

{'📅 **Your Subscription:** ' + expiry_str if is_premium else ''}

**How to get Premium:**
1️⃣ Get a key from an admin
2️⃣ Use /redeem <KEY> to activate
3️⃣ Enjoy premium features!

**Get Free Premium!**
Use the referral system to earn premium days!
Each referral gives you {REFERRAL_REWARD_DAYS} premium days!
"""
    markup = types.InlineKeyboardMarkup(row_width=2)
    if not is_premium:
        markup.add(types.InlineKeyboardButton("🎫 Redeem Key", callback_data='redeem_key'))
    markup.add(
        types.InlineKeyboardButton("🔗 Referrals", callback_data='referrals'),
        types.InlineKeyboardButton("📞 Contact", url=f'https://t.me/{YOUR_USERNAME.replace("@", "")}')
    )
    markup.add(types.InlineKeyboardButton("🔙 Back", callback_data='back_to_main'))
    bot.reply_to(message, premium_msg, reply_markup=markup, parse_mode='Markdown')

@bot.message_handler(commands=['commands'])
def command_commands(message):
    user_id = message.from_user.id
    if is_user_banned(user_id):
        bot.reply_to(message, "❌ You are banned from using this bot.")
        return
    is_subscribed, not_joined = check_mandatory_subscription(user_id)
    if not is_subscribed and user_id not in admin_ids:
        subscription_message, markup = create_subscription_check_message(not_joined)
        bot.reply_to(message, subscription_message, reply_markup=markup, parse_mode='Markdown')
        return
    commands_msg = """
🎮 **Command List**

**📌 User Commands:**
/start - Start the bot
/help - Show help
/profile - View your profile
/premium - Premium info
/redeem - Redeem a key
/ping - Check bot latency
/status - Show bot status
/commands - Show this menu
/faq - Frequently asked questions
/feedback - Send feedback
/tips - Helpful tips
/announcements - Latest announcements
/referral - Referral system

**📁 File Management:**
/upload - Upload a file
/files - List your files
/clean - Clean old logs
/deleteall - Delete all your files

**📦 Module Management:**
/install - Manual install
/nodeinstall - Install Node package
/pipinstall - Install Python package
/modules - List installed modules

**📢 Info:**
/stats - Bot statistics
/channels - Show channels
/tutorial - Get tutorial
/botinfo - Bot information
/uptime - Bot uptime

**👑 Admin Commands:**
/admin - Admin panel
/ban - Ban user
/unban - Unban user
/broadcast - Send broadcast
/setlimit - Set user limit
/genkey - Generate key
/listkeys - List keys
/backup - Backup database
/restore - Restore database
/logs - Show logs
/cleanup - Clean temp files
/addadmin - Add admin
/removeadmin - Remove admin
/userinfo - Get user info
/allusers - List all users
/serverstats - Server statistics

**🆘 Need Help?**
Contact: @{YOUR_USERNAME}
Updates: {UPDATE_CHANNEL}
"""
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("📚 Tutorial", callback_data='tutorial'),
        types.InlineKeyboardButton("❓ FAQ", callback_data='faq')
    )
    markup.add(
        types.InlineKeyboardButton("📝 Feedback", callback_data='feedback'),
        types.InlineKeyboardButton("🔙 Back", callback_data='back_to_main')
    )
    bot.reply_to(message, commands_msg, reply_markup=markup, parse_mode='Markdown')

@bot.message_handler(commands=['tutorial'])
def command_tutorial(message):
    user_id = message.from_user.id
    if is_user_banned(user_id):
        bot.reply_to(message, "❌ You are banned from using this bot.")
        return
    is_subscribed, not_joined = check_mandatory_subscription(user_id)
    if not is_subscribed and user_id not in admin_ids:
        subscription_message, markup = create_subscription_check_message(not_joined)
        bot.reply_to(message, subscription_message, reply_markup=markup, parse_mode='Markdown')
        return
    tutorial_msg = """
📚 **Hosting Bot Tutorial**

**🚀 Getting Started:**
1️⃣ Join the updates channel
2️⃣ Upload your script (.py or .js)
3️⃣ Your bot auto-starts!

**📁 File Upload Guide:**
• Single file: Upload .py or .js
• Multiple files: Upload .zip
• Requirements: Add requirements.txt
• Node.js: Add package.json

**🔧 Auto Features:**
• Auto-install missing modules
• Auto-start after upload
• Auto-restart on crash
• Auto-cleanup old logs

**💡 Pro Tips:**
• Use main.py or bot.py as entry point
• Keep scripts lightweight
• Check logs for errors
• Contact owner for help

**⚠️ Security Notes:**
• No harmful commands allowed
• Scripts are scanned automatically
• Suspicious files are flagged
• Report issues to admin

**Need More Help?**
Contact: @{YOUR_USERNAME}
"""
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("📤 Upload Guide", callback_data='upload_guide'),
        types.InlineKeyboardButton("⚙️ Settings Help", callback_data='settings_help')
    )
    markup.add(
        types.InlineKeyboardButton("🎮 Commands", callback_data='commands_list'),
        types.InlineKeyboardButton("🔙 Back", callback_data='back_to_main')
    )
    bot.reply_to(message, tutorial_msg, reply_markup=markup, parse_mode='Markdown')

@bot.message_handler(commands=['faq'])
def command_faq(message):
    user_id = message.from_user.id
    if is_user_banned(user_id):
        bot.reply_to(message, "❌ You are banned from using this bot.")
        return
    is_subscribed, not_joined = check_mandatory_subscription(user_id)
    if not is_subscribed and user_id not in admin_ids:
        subscription_message, markup = create_subscription_check_message(not_joined)
        bot.reply_to(message, subscription_message, reply_markup=markup, parse_mode='Markdown')
        return
    faq_msg = """
❓ **Frequently Asked Questions**

**Q: How do I upload a file?**
A: Click "📤 Upload File" or use /upload

**Q: What file types are supported?**
A: .py (Python) and .js (JavaScript) and .zip archives

**Q: How many files can I upload?**
A: Free users: 1, Premium users: 3, Admins: 20

**Q: What happens if my script crashes?**
A: It auto-restarts automatically!

**Q: How do I get premium?**
A: Get a key from admin and use /redeem <KEY>

**Q: Can I install custom modules?**
A: Yes! Use "📦 Manual Install" or /install

**Q: Where can I see my script logs?**
A: Click on your file in "📂 Check Files"

**Q: Is my code safe?**
A: Yes! All code is scanned for security

**Q: Can I run multiple scripts?**
A: Yes, up to your file limit

**Q: What if I need help?**
A: Contact @{YOUR_USERNAME}

**Q: How does the referral system work?**
A: Share your referral link, earn rewards per referral!

**More questions?** Use /feedback
"""
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("📝 Feedback", callback_data='feedback'),
        types.InlineKeyboardButton("📞 Contact", url=f'https://t.me/{YOUR_USERNAME.replace("@", "")}')
    )
    markup.add(types.InlineKeyboardButton("🔙 Back", callback_data='back_to_main'))
    bot.reply_to(message, faq_msg, reply_markup=markup, parse_mode='Markdown')

@bot.message_handler(commands=['feedback'])
def command_feedback(message):
    user_id = message.from_user.id
    if is_user_banned(user_id):
        bot.reply_to(message, "❌ You are banned from using this bot.")
        return
    is_subscribed, not_joined = check_mandatory_subscription(user_id)
    if not is_subscribed and user_id not in admin_ids:
        subscription_message, markup = create_subscription_check_message(not_joined)
        bot.reply_to(message, subscription_message, reply_markup=markup, parse_mode='Markdown')
        return
    msg = bot.reply_to(message, "📝 Send your feedback or suggestion.\n/cancel to cancel")
    bot.register_next_step_handler(msg, process_feedback)

def process_feedback(message):
    user_id = message.from_user.id
    if message.text and message.text.lower() == '/cancel':
        bot.reply_to(message, "❌ Feedback cancelled.")
        return
    feedback_text = message.text
    try:
        conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False, timeout=30)
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS feedback
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      user_id INTEGER,
                      feedback TEXT,
                      date TEXT)''')
        c.execute('INSERT INTO feedback (user_id, feedback, date) VALUES (?, ?, ?)',
                  (user_id, feedback_text, datetime.now().isoformat()))
        conn.commit()
        conn.close()
    except:
        pass
    bot.reply_to(message, "✅ Thank you for your feedback! We'll review it.")
    for admin_id in admin_ids:
        try:
            bot.send_message(admin_id, f"📝 **New Feedback**\nFrom: `{user_id}`\n\n{feedback_text}", parse_mode='Markdown')
        except:
            pass

@bot.message_handler(commands=['upload'])
def command_upload(message):
    _logic_upload_file(message)

@bot.message_handler(commands=['files'])
def command_files(message):
    _logic_check_files(message)

@bot.message_handler(commands=['stats'])
def command_stats(message):
    _logic_statistics(message)

@bot.message_handler(commands=['ping'])
def command_ping(message):
    start_ping_time = time.time()
    msg = bot.reply_to(message, "Pong!")
    latency = round((time.time() - start_ping_time) * 1000, 2)
    bot.edit_message_text(f"Pong! Latency: {latency} ms", message.chat.id, msg.message_id)

@bot.message_handler(commands=['status'])
def command_status(message):
    _logic_statistics(message)

@bot.message_handler(commands=['uptime'])
def command_uptime(message):
    user_id = message.from_user.id
    if is_user_banned(user_id):
        bot.reply_to(message, "❌ You are banned from using this bot.")
        return
    is_subscribed, not_joined = check_mandatory_subscription(user_id)
    if not is_subscribed and user_id not in admin_ids:
        subscription_message, markup = create_subscription_check_message(not_joined)
        bot.reply_to(message, subscription_message, reply_markup=markup, parse_mode='Markdown')
        return
    boot_time = psutil.boot_time()
    uptime_seconds = time.time() - boot_time
    uptime_str = str(timedelta(seconds=int(uptime_seconds)))
    uptime_msg = f"""
⏱️ **Bot Uptime**

🕐 **System Uptime:** {uptime_str}

📊 **Bot Status:**
• Running: ✅
• Active Users: {len(active_users)}
• Running Scripts: {len(bot_scripts)}

🔒 **Bot Lock:** {'🔴 Locked' if bot_locked else '🟢 Unlocked'}

📅 **Started:** {datetime.fromtimestamp(boot_time).strftime('%Y-%m-%d %H:%M:%S')}
"""
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🔄 Refresh", callback_data='refresh_uptime'))
    markup.add(types.InlineKeyboardButton("🔙 Back", callback_data='back_to_main'))
    bot.reply_to(message, uptime_msg, reply_markup=markup, parse_mode='Markdown')

@bot.message_handler(commands=['botinfo'])
def command_botinfo(message):
    user_id = message.from_user.id
    if is_user_banned(user_id):
        bot.reply_to(message, "❌ You are banned from using this bot.")
        return
    is_subscribed, not_joined = check_mandatory_subscription(user_id)
    if not is_subscribed and user_id not in admin_ids:
        subscription_message, markup = create_subscription_check_message(not_joined)
        bot.reply_to(message, subscription_message, reply_markup=markup, parse_mode='Markdown')
        return
    bot_info = f"""
🤖 **Bot Information**

📛 **Name:** Digital World Hosting Bot
🔰 **Version:** 3.0.0
👑 **Owner:** @{YOUR_USERNAME}
📢 **Channel:** {UPDATE_CHANNEL}

📊 **Statistics:**
• Active Users: {len(active_users)}
• Running Scripts: {len(bot_scripts)}
• Total Files: {sum(len(f) for f in user_files.values())}
• Admins: {len(admin_ids)}
• Banned Users: {len(banned_users)}
• Total Referrals: {PERMANENT_DB.get_stats().get('total_referrals', 0)}

⚡ **Features:**
• Python & JS hosting
• Auto-installation
• Premium system
• Key redemption
• Referral system
• Rich UI

🛡️ **Security:**
• Code scanning
• File validation
• User management
• Anti-abuse

📅 **Uptime:** {time.strftime('%H:%M:%S', time.gmtime(time.time() - psutil.boot_time()))}

**Support:** @{YOUR_USERNAME}
"""
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("📢 Updates", url=f'https://t.me/{UPDATE_CHANNEL.replace("@", "")}'),
        types.InlineKeyboardButton("📞 Contact", url=f'https://t.me/{YOUR_USERNAME.replace("@", "")}')
    )
    markup.add(types.InlineKeyboardButton("🔙 Back", callback_data='back_to_main'))
    bot.reply_to(message, bot_info, reply_markup=markup, parse_mode='Markdown')

@bot.message_handler(commands=['redeem'])
def command_redeem(message):
    user_id = message.from_user.id
    if is_user_banned(user_id):
        bot.reply_to(message, "❌ You are banned.")
        return
    parts = message.text.split()
    if len(parts) != 2:
        bot.reply_to(message, "⚠️ Usage: /redeem <KEY>")
        return
    key_code = parts[1].strip().upper()
    success, msg = redeem_key(user_id, key_code)
    bot.reply_to(message, f"{'✅' if success else '❌'} {msg}")

@bot.message_handler(commands=['genkey'])
def command_genkey(message):
    if message.from_user.id not in admin_ids:
        bot.reply_to(message, "⚠️ Admin only.")
        return
    parts = message.text.split()
    if len(parts) < 2:
        bot.reply_to(message, "⚠️ Usage: /genkey <limit> [duration]\n"
                              "Examples:\n"
                              "  /genkey 10 30d    → 30 days\n"
                              "  /genkey 5 2h      → 2 hours\n"
                              "  /genkey 3 90m     → 90 minutes\n"
                              "  /genkey 8 1w      → 1 week\n"
                              "  /genkey 4 6m      → 6 months\n"
                              "  /genkey 2 1y      → 1 year\n"
                              "  /genkey 15 lifetime → never expires")
        return
    try:
        limit_value = int(parts[1])
        if limit_value <= 0:
            raise ValueError("Limit must be positive")
        if len(parts) >= 3:
            duration = parse_duration(parts[2])
        else:
            duration = timedelta(days=30)
        key_code = generate_key(limit_value, duration, message.from_user.id)
        if not key_code:
            bot.reply_to(message, "❌ Failed to generate key. Check logs.")
            return
        if duration is None:
            validity = "🌟 Lifetime"
        else:
            total_seconds = int(duration.total_seconds())
            days = total_seconds // 86400
            hours = (total_seconds % 86400) // 3600
            minutes = (total_seconds % 3600) // 60
            if days > 0:
                validity = f"⏳ {days}d"
                if hours: validity += f" {hours}h"
            elif hours > 0:
                validity = f"⏳ {hours}h"
                if minutes: validity += f" {minutes}m"
            else:
                validity = f"⏳ {minutes}m" if minutes > 0 else "⏳ (instant)"
        created_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        rich_msg = (
            f"🎉 **ᴋᴇʏ ɢᴇɴᴇʀᴀᴛᴇᴅ sᴜᴄᴄᴇssғᴜʟʟʏ!**\n\n"
            f"🔑 **ᴋᴇʏ ᴅᴇᴛᴀɪʟs**\n"
            f"┣ 🎫 ᴀᴄᴄᴇss ᴋᴇʏ: `{key_code}`\n"
            f"┣ 📦 ʙᴏᴛ ʟɪᴍɪᴛ: **{limit_value}**\n"
            f"┣ ⏳ ᴠᴀʟɪᴅɪᴛʏ: {validity}\n"
            f"┣ 📝 sᴛᴀᴛᴜs: ᴏɴᴇ-ᴛɪᴍᴇ ᴜsᴇ\n"
            f"┣ 📅 ᴄʀᴇᴀᴛᴇᴅ: {created_time}\n\n"
            f"🛡️ **sᴇᴄᴜʀɪᴛʏ ɴᴏᴛᴇs**\n"
            f"┣ ✦ sɪɴɢʟᴇ-ᴀᴄᴛɪᴠᴀᴛɪᴏɴ ᴏɴʟʏ\n"
            f"┣ ✦ ᴀᴜᴛᴏ-ᴇxᴘɪʀʏ ᴇɴᴀʙʟᴇᴅ\n"
            f"┣ ✦ ɴᴏɴ-ᴛʀᴀɴsғᴇʀᴀʙʟᴇ\n\n"
            f"📤 **ᴅɪsᴛʀɪʙᴜᴛɪᴏɴ**\n"
            f"sʜᴀʀᴇ ᴛʜɪs ᴋᴇʏ ᴡɪᴛʜ ʏᴏᴜʀ ᴜsᴇʀ ᴛᴏ ɢʀᴀɴᴛ ᴘʀᴇᴍɪᴜᴍ ᴀᴄᴄᴇss!"
        )
        bot.reply_to(message, rich_msg, parse_mode='Markdown')
    except ValueError as e:
        bot.reply_to(message, f"⚠️ Error: {e}")
    except Exception as e:
        print(f"Error in genkey: {e}")
        bot.reply_to(message, f"❌ Error: {str(e)}")

@bot.message_handler(commands=['listkeys'])
def command_listkeys(message):
    if message.from_user.id not in admin_ids:
        bot.reply_to(message, "⚠️ Admin only.")
        return
    conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False, timeout=30)
    c = conn.cursor()
    c.execute('''SELECT key_id, key_code, limit_value, expiry_date, is_used, used_by, created_date
                 FROM permanent_keys ORDER BY key_id DESC LIMIT 20''')
    keys = c.fetchall()
    conn.close()
    if not keys:
        bot.reply_to(message, "📭 No keys generated yet.")
        return
    lines = ["🔑 **ʀᴇᴄᴇɴᴛ ᴋᴇʏs (ʟᴀsᴛ 20):**\n"]
    for k in keys:
        key_id, key_code, limit_value, expiry_str, used, used_by, created_at = k
        used_icon = "✅ ᴜsᴇᴅ" if used else "🟢 ᴀᴄᴛɪᴠᴇ"
        used_by_info = f" (ʙʏ `{used_by}`)" if used else ""
        if expiry_str:
            expiry = datetime.fromisoformat(expiry_str)
            expiry_display = f"🟡 ᴇxᴘɪʀᴇs {expiry.strftime('%Y-%m-%d')}"
            if expiry < datetime.now():
                expiry_display = "🔴 ᴇxᴘɪʀᴇᴅ"
        else:
            expiry_display = "🌟 ʟɪғᴇᴛɪᴍᴇ"
        lines.append(
            f"┣ `{key_code}`\n"
            f"┣ 📦 ʟɪᴍɪᴛ: {limit_value}\n"
            f"┣ {used_icon}{used_by_info}\n"
            f"┣ {expiry_display}\n"
        )
    bot.reply_to(message, "\n".join(lines), parse_mode='Markdown')

@bot.message_handler(commands=['broadcast'])
def command_broadcast(message):
    if message.from_user.id not in admin_ids:
        bot.reply_to(message, "⚠️ Admin permissions required.")
        return
    msg = bot.reply_to(message, "📢 Send message to broadcast to all active users.\n/cancel to abort.")
    bot.register_next_step_handler(msg, process_broadcast_message)

def process_broadcast_message(message):
    admin_id = message.from_user.id
    if admin_id not in admin_ids:
        bot.reply_to(message, "⚠️ Not authorized.")
        return
    if message.text and message.text.lower() == '/cancel':
        bot.reply_to(message, "Broadcast cancelled.")
        return
    broadcast_content = message.text
    if not broadcast_content:
        bot.reply_to(message, "⚠️ Cannot broadcast empty message.")
        return
    target_count = len(active_users)
    markup = types.InlineKeyboardMarkup()
    markup.row(types.InlineKeyboardButton("✅ Confirm & Send", callback_data=f"confirm_broadcast_{message.message_id}"),
               types.InlineKeyboardButton("❌ Cancel", callback_data="cancel_broadcast"))
    preview_text = broadcast_content[:1000].strip() if broadcast_content else "(Media message)"
    bot.reply_to(message, f"⚠️ Confirm Broadcast:\n\n```\n{preview_text}\n```\n" 
                          f"To **{target_count}** users. Sure?", reply_markup=markup, parse_mode='Markdown')

@bot.message_handler(commands=['ban'])
def command_ban(message):
    if message.from_user.id not in admin_ids:
        bot.reply_to(message, "⚠️ Admin permissions required.")
        return
    parts = message.text.split()
    if len(parts) < 2:
        bot.reply_to(message, "⚠️ Usage: /ban <user_id> [reason]")
        return
    try:
        user_id = int(parts[0])
        reason = ' '.join(parts[1:]) if len(parts) > 1 else "No reason provided"
        if user_id <= 0:
            raise ValueError("ID must be positive")
        if user_id == OWNER_ID:
            bot.reply_to(message, "⚠️ Cannot ban owner.")
            return
        if user_id in admin_ids:
            bot.reply_to(message, "⚠️ Cannot ban admin.")
            return
        if ban_user_db(user_id, reason, message.from_user.id):
            bot.reply_to(message, f"✅ User `{user_id}` banned.\nReason: {reason}")
            for file_name, _ in user_files.get(user_id, []):
                script_key = f"{user_id}_{file_name}"
                if script_key in bot_scripts:
                    kill_process_tree(bot_scripts[script_key])
                    del bot_scripts[script_key]
            try:
                bot.send_message(user_id, f"🚫 You have been banned from using this bot.\nReason: {reason}")
            except:
                pass
        else:
            bot.reply_to(message, "❌ Failed to ban user.")
    except ValueError:
        bot.reply_to(message, "⚠️ Invalid user ID. Must be a number.")
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {str(e)}")

@bot.message_handler(commands=['unban'])
def command_unban(message):
    if message.from_user.id not in admin_ids:
        bot.reply_to(message, "⚠️ Admin permissions required.")
        return
    parts = message.text.split()
    if len(parts) != 2:
        bot.reply_to(message, "⚠️ Usage: /unban <user_id>")
        return
    try:
        user_id = int(parts[1])
        if user_id <= 0:
            raise ValueError("ID must be positive")
        if user_id not in banned_users:
            bot.reply_to(message, f"ℹ️ User `{user_id}` is not banned.")
            return
        if unban_user_db(user_id):
            bot.reply_to(message, f"✅ User `{user_id}` unbanned.")
            try:
                bot.send_message(user_id, "✅ Your ban has been lifted. You can now use the bot again.")
            except:
                pass
        else:
            bot.reply_to(message, "❌ Failed to unban user.")
    except ValueError:
        bot.reply_to(message, "⚠️ Invalid user ID. Must be a number.")
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {str(e)}")

@bot.message_handler(commands=['setlimit'])
def command_setlimit(message):
    if message.from_user.id not in admin_ids:
        bot.reply_to(message, "⚠️ Admin permissions required.")
        return
    parts = message.text.split()
    if len(parts) != 3:
        bot.reply_to(message, "⚠️ Usage: /setlimit <user_id> <limit>")
        return
    try:
        user_id = int(parts[1])
        limit = int(parts[2])
        if user_id <= 0 or limit <= 0:
            raise ValueError("ID and limit must be positive")
        if set_user_limit_db(user_id, limit, message.from_user.id):
            bot.reply_to(message, f"✅ Set file limit {limit} for user `{user_id}`")
            try:
                bot.send_message(user_id, f"⚙️ Your file upload limit has been set to {limit}")
            except:
                pass
        else:
            bot.reply_to(message, "❌ Failed to set limit.")
    except ValueError:
        bot.reply_to(message, "⚠️ Invalid input. Format: /setlimit <user_id> <limit>")
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {str(e)}")

@bot.message_handler(commands=['addadmin'])
def command_addadmin(message):
    if message.from_user.id != OWNER_ID:
        bot.reply_to(message, "⚠️ Owner permissions required.")
        return
    parts = message.text.split()
    if len(parts) != 2:
        bot.reply_to(message, "⚠️ Usage: /addadmin <user_id>")
        return
    try:
        new_admin_id = int(parts[1])
        if new_admin_id in admin_ids:
            bot.reply_to(message, f"⚠️ User {new_admin_id} is already an admin.")
            return
        add_admin_db(new_admin_id, OWNER_ID)
        bot.reply_to(message, f"✅ User {new_admin_id} is now an admin!")
        try:
            bot.send_message(new_admin_id, "🎉 You have been promoted to Admin!")
        except:
            pass
    except:
        bot.reply_to(message, "❌ Invalid user ID.")

@bot.message_handler(commands=['removeadmin'])
def command_removeadmin(message):
    if message.from_user.id != OWNER_ID:
        bot.reply_to(message, "⚠️ Owner permissions required.")
        return
    parts = message.text.split()
    if len(parts) != 2:
        bot.reply_to(message, "⚠️ Usage: /removeadmin <user_id>")
        return
    try:
        admin_id_remove = int(parts[1])
        if admin_id_remove == OWNER_ID:
            bot.reply_to(message, "⚠️ Cannot remove owner.")
            return
        if admin_id_remove not in admin_ids:
            bot.reply_to(message, f"⚠️ User {admin_id_remove} is not an admin.")
            return
        if remove_admin_db(admin_id_remove):
            bot.reply_to(message, f"✅ Admin {admin_id_remove} removed.")
            try:
                bot.send_message(admin_id_remove, "ℹ️ You are no longer an admin.")
            except:
                pass
        else:
            bot.reply_to(message, "❌ Failed to remove admin.")
    except:
        bot.reply_to(message, "❌ Invalid user ID.")

@bot.message_handler(commands=['userinfo'])
def command_userinfo(message):
    if message.from_user.id not in admin_ids:
        bot.reply_to(message, "⚠️ Admin permissions required.")
        return
    parts = message.text.split()
    if len(parts) != 2:
        bot.reply_to(message, "⚠️ Usage: /userinfo <user_id>")
        return
    try:
        user_id = int(parts[1])
        user = bot.get_chat(user_id)
        user_name = user.first_name or "Unknown"
        username = f"@{user.username}" if user.username else "No username"
        file_count = get_user_file_count(user_id)
        file_limit = get_user_file_limit(user_id)
        limit_str = str(file_limit) if file_limit != float('inf') else "Unlimited"
        running_scripts = sum(1 for f, _ in user_files.get(user_id, []) if is_bot_running(user_id, f[0]))
        ref_stats = get_referral_stats(user_id)
        ref_count = ref_stats.get('count', 0)
        ref_extra = ref_stats.get('extra_limit', 0)
        if user_id == OWNER_ID:
            status = "👑 Owner"
        elif user_id in admin_ids:
            status = "🛡️ Admin"
        elif user_id in banned_users:
            status = "🚫 Banned"
        elif user_id in user_subscriptions:
            expiry = user_subscriptions[user_id].get('expiry')
            if expiry and expiry > datetime.now():
                days_left = (expiry - datetime.now()).days
                status = f"⭐ Premium ({days_left} days left)"
            else:
                status = "🆓 Free (Expired)"
        else:
            status = "🆓 Free"
        info_msg = f"""
👤 **User Information**

📛 **Name:** {user_name}
🆔 **ID:** `{user_id}`
📌 **Username:** {username}
🔰 **Status:** {status}

📁 **Files:** {file_count} / {limit_str}
🤖 **Running Scripts:** {running_scripts}
📊 **Active:** {'Yes' if user_id in active_users else 'No'}
🚫 **Banned:** {'Yes' if user_id in banned_users else 'No'}

🔗 **Referral Stats:**
┣ 👥 Referrals: {ref_count}
┗ 📈 Extra Limit: +{ref_extra}

📅 **Joined:** {datetime.now().strftime('%Y-%m-%d')}
"""
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("🚫 Ban", callback_data=f'ban_{user_id}'),
            types.InlineKeyboardButton("✅ Unban", callback_data=f'unban_{user_id}')
        )
        markup.add(
            types.InlineKeyboardButton("📁 Files", callback_data=f'user_files_{user_id}'),
            types.InlineKeyboardButton("🔙 Back", callback_data='back_to_main')
        )
        bot.reply_to(message, info_msg, reply_markup=markup, parse_mode='Markdown')
    except:
        bot.reply_to(message, "❌ Invalid user ID or user not found.")

@bot.message_handler(commands=['allusers'])
def command_allusers(message):
    if message.from_user.id not in admin_ids:
        bot.reply_to(message, "⚠️ Admin permissions required.")
        return
    users = PERMANENT_DB.get_all_users()
    if not users:
        bot.reply_to(message, "👥 No users registered yet.")
        return
    msg = "👥 **All Users:**\n\n"
    for user in users[:20]:
        user_id, username, first_name, role, is_banned, is_premium, ref_count = user
        name = first_name or username or f"User {user_id}"
        status = "🔴" if is_banned else "🟢"
        premium = "⭐" if is_premium else "🆓"
        msg += f"{status} `{user_id}` - {name} ({role}) {premium} 📊{ref_count}\n"
    if len(users) > 20:
        msg += f"\n... and {len(users) - 20} more users"
    bot.reply_to(message, msg, parse_mode='Markdown')

@bot.message_handler(commands=['cleanup'])
def command_cleanup(message):
    if message.from_user.id not in admin_ids:
        bot.reply_to(message, "⚠️ Admin permissions required.")
        return
    bot.reply_to(message, "🧹 Cleaning up temporary files...")
    try:
        cleaned_dirs = 0
        cleaned_files = 0
        for user_dir in os.listdir(UPLOAD_BOTS_DIR):
            user_path = os.path.join(UPLOAD_BOTS_DIR, user_dir)
            if os.path.isdir(user_path):
                if not os.listdir(user_path):
                    try:
                        os.rmdir(user_path)
                        cleaned_dirs += 1
                    except:
                        pass
                else:
                    for file_name in os.listdir(user_path):
                        if file_name.endswith('.log'):
                            file_path = os.path.join(user_path, file_name)
                            try:
                                file_age = time.time() - os.path.getmtime(file_path)
                                if file_age > 7 * 24 * 3600:
                                    os.remove(file_path)
                                    cleaned_files += 1
                            except:
                                pass
        result_msg = f"🧹 **Cleanup Complete:**\n• Removed empty directories: {cleaned_dirs}\n• Cleared old log files: {cleaned_files}"
        bot.reply_to(message, result_msg)
    except Exception as e:
        bot.reply_to(message, f"❌ Cleanup error: {str(e)}")

@bot.message_handler(commands=['statsjson'])
def command_statsjson(message):
    if message.from_user.id not in admin_ids:
        bot.reply_to(message, "⚠️ Admin permissions required.")
        return
    stats = get_stats_permanent()
    bot.reply_to(message, f"📊 **Bot Statistics (JSON):**\n```json\n{json.dumps(stats, indent=2)}\n```", parse_mode='Markdown')

@bot.message_handler(commands=['backup'])
def command_backup(message):
    if message.from_user.id not in admin_ids:
        bot.reply_to(message, "⚠️ Admin permissions required.")
        return
    try:
        backup_path = os.path.join(IROTECH_DIR, f'backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.db')
        shutil.copy2(DATABASE_PATH, backup_path)
        bot.reply_to(message, f"✅ Database backed up to: `{backup_path}`", parse_mode='Markdown')
    except Exception as e:
        bot.reply_to(message, f"❌ Backup failed: {str(e)}")

@bot.message_handler(commands=['logs'])
def command_logs(message):
    if message.from_user.id not in admin_ids:
        bot.reply_to(message, "⚠️ Admin permissions required.")
        return
    conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False, timeout=30)
    c = conn.cursor()
    c.execute('SELECT log_id, log_type, user_id, action, details, timestamp FROM permanent_logs ORDER BY log_id DESC LIMIT 20')
    logs = c.fetchall()
    conn.close()
    if not logs:
        bot.reply_to(message, "📋 No logs found.")
        return
    msg = "📋 **Recent Logs (Last 20):**\n\n"
    for log in logs:
        log_id, log_type, user_id, action, details, timestamp = log
        emoji = "ℹ️" if log_type == 'info' else "⚠️" if log_type == 'warning' else "❌"
        msg += f"{emoji} `{timestamp[:19]}` - User `{user_id}`: {action}\n"
        if details:
            msg += f"   📝 {details[:100]}\n"
    bot.reply_to(message, msg[:4000], parse_mode='Markdown')

@bot.message_handler(commands=['serverstats'])
def command_serverstats(message):
    if message.from_user.id not in admin_ids:
        bot.reply_to(message, "⚠️ Admin permissions required.")
        return
    try:
        cpu = psutil.cpu_percent(interval=1)
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        stats_msg = f"""
📊 **Server Statistics:**

🖥️ **CPU:** {cpu}%
💾 **Memory:** {mem.percent}% ({mem.used // (1024**3)}GB / {mem.total // (1024**3)}GB)
💿 **Disk:** {disk.percent}% ({disk.used // (1024**3)}GB / {disk.total // (1024**3)}GB)

📈 **Bot Stats:**
• Active Users: {len(active_users)}
• Running Scripts: {len(bot_scripts)}
• Total Files: {sum(len(f) for f in user_files.values())}
• Premium Users: {PERMANENT_DB.get_stats().get('premium_users', 0)}
"""
        bot.reply_to(message, stats_msg, parse_mode='Markdown')
    except Exception as e:
        bot.reply_to(message, f"❌ Error getting stats: {str(e)}")

def _logic_upload_file(message):
    user_id = message.from_user.id
    if is_user_banned(user_id):
        bot.reply_to(message, "❌ You are banned from using this bot.")
        return
    is_subscribed, not_joined = check_mandatory_subscription(user_id)
    if not is_subscribed and user_id not in admin_ids:
        subscription_message, markup = create_subscription_check_message(not_joined)
        bot.reply_to(message, subscription_message, reply_markup=markup, parse_mode='Markdown')
        return
    if bot_locked and user_id not in admin_ids:
        bot.reply_to(message, "⚠️ Bot locked by admin, cannot accept files.")
        return
    file_limit = get_user_file_limit(user_id)
    current_files = get_user_file_count(user_id)
    if current_files >= file_limit:
        limit_str = str(file_limit) if file_limit != float('inf') else "Unlimited"
        bot.reply_to(message, f"⚠️ File limit ({current_files}/{limit_str}) reached. Delete files first.")
        return
    bot.reply_to(message, "📤 Send your Python (`.py`), JS (`.js`), or ZIP (`.zip`) file.")

def _logic_check_files(message):
    user_id = message.from_user.id
    if is_user_banned(user_id):
        bot.reply_to(message, "❌ You are banned from using this bot.")
        return
    is_subscribed, not_joined = check_mandatory_subscription(user_id)
    if not is_subscribed and user_id not in admin_ids:
        subscription_message, markup = create_subscription_check_message(not_joined)
        bot.reply_to(message, subscription_message, reply_markup=markup, parse_mode='Markdown')
        return
    user_files_list = user_files.get(user_id, [])
    if not user_files_list:
        bot.reply_to(message, "📂 Your files:\n\n(No files uploaded yet)")
        return
    markup = types.InlineKeyboardMarkup(row_width=1)
    for file_name, file_type in sorted(user_files_list):
        is_running = is_bot_running(user_id, file_name)
        status_icon = "🟢 Running" if is_running else "🔴 Stopped"
        btn_text = f"{file_name} ({file_type}) - {status_icon}"
        markup.add(types.InlineKeyboardButton(btn_text, callback_data=f'file_{user_id}_{file_name}'))
    bot.reply_to(message, "📂 Your files:\nClick to manage.", reply_markup=markup, parse_mode='Markdown')

def _logic_statistics(message):
    user_id = message.from_user.id
    if is_user_banned(user_id):
        bot.reply_to(message, "❌ You are banned from using this bot.")
        return
    is_subscribed, not_joined = check_mandatory_subscription(user_id)
    if not is_subscribed and user_id not in admin_ids:
        subscription_message, markup = create_subscription_check_message(not_joined)
        bot.reply_to(message, subscription_message, reply_markup=markup, parse_mode='Markdown')
        return
    total_users = len(active_users)
    total_files_records = sum(len(files) for files in user_files.values())
    running_bots_count = 0
    user_running_bots = 0
    for script_key_iter, script_info_iter in list(bot_scripts.items()):
        s_owner_id, _ = script_key_iter.split('_', 1)
        if is_bot_running(int(s_owner_id), script_info_iter['file_name']):
            running_bots_count += 1
            if int(s_owner_id) == user_id:
                user_running_bots += 1
    stats_msg_base = (f"📊 Bot Statistics:\n\n"
                      f"👥 Total Users: {total_users}\n"
                      f"🚫 Banned Users: {len(banned_users)}\n"
                      f"📂 Total File Records: {total_files_records}\n"
                      f"🟢 Total Active Bots: {running_bots_count}\n")
    if user_id in admin_ids:
        stats_msg_admin = (f"🔒 Bot Status: {'🔴 Locked' if bot_locked else '🟢 Unlocked'}\n"
                           f"📢 Mandatory Channels: {len(mandatory_channels)}\n"
                           f"⚙️ Custom Limits: {len(user_limits)}\n"
                           f"🤖 Your Running Bots: {user_running_bots}")
        stats_msg = stats_msg_base + stats_msg_admin
    else:
        stats_msg = stats_msg_base + f"🤖 Your Running Bots: {user_running_bots}"
    bot.reply_to(message, stats_msg)

@bot.message_handler(func=lambda message: message.text in ["📢 Updates Channel", "📤 Upload File", "📂 Check Files", "⚡ Bot Speed", "📊 Statistics", "📞 Contact Owner", "🆘 Help", "👤 My Profile", "📋 My Scripts", "⭐ Premium", "🔔 Notifications", "📚 Tutorial", "🎮 Commands", "💡 Tips", "📢 Announcements", "❓ FAQ", "📝 Feedback", "🎯 Quick Start", "🔗 Referrals", "🎁 Rewards"])
def handle_button_text(message):
    text = message.text
    if text == "📢 Updates Channel":
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton('📢 Updates Channel', url=f'https://t.me/{UPDATE_CHANNEL.replace("@", "")}'))
        bot.reply_to(message, "Visit our Updates Channel:", reply_markup=markup)
    elif text == "📤 Upload File":
        _logic_upload_file(message)
    elif text == "📂 Check Files":
        _logic_check_files(message)
    elif text == "⚡ Bot Speed":
        _logic_bot_speed(message)
    elif text == "📊 Statistics":
        _logic_statistics(message)
    elif text == "📞 Contact Owner":
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton('📞 Contact Owner', url=f'https://t.me/{YOUR_USERNAME.replace("@", "")}'))
        bot.reply_to(message, "Click to contact Owner:", reply_markup=markup)
    elif text == "🆘 Help":
        _logic_help(message)
    elif text == "👤 My Profile":
        command_profile(message)
    elif text == "📋 My Scripts":
        _logic_check_files(message)
    elif text == "⭐ Premium":
        command_premium(message)
    elif text == "🔔 Notifications":
        command_announcements(message)
    elif text == "📚 Tutorial":
        command_tutorial(message)
    elif text == "🎮 Commands":
        command_commands(message)
    elif text == "💡 Tips":
        command_tips(message)
    elif text == "📢 Announcements":
        command_announcements(message)
    elif text == "❓ FAQ":
        command_faq(message)
    elif text == "📝 Feedback":
        command_feedback(message)
    elif text == "🎯 Quick Start":
        command_tutorial(message)
    elif text == "🔗 Referrals":
        command_referral(message)
    elif text == "🎁 Rewards":
        command_referral(message)

def _logic_bot_speed(message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    if is_user_banned(user_id):
        bot.reply_to(message, "❌ You are banned from using this bot.")
        return
    is_subscribed, not_joined = check_mandatory_subscription(user_id)
    if not is_subscribed and user_id not in admin_ids:
        subscription_message, markup = create_subscription_check_message(not_joined)
        bot.reply_to(message, subscription_message, reply_markup=markup, parse_mode='Markdown')
        return
    start_time_ping = time.time()
    wait_msg = bot.reply_to(message, "🏃 Testing speed...")
    try:
        bot.send_chat_action(chat_id, 'typing')
        response_time = round((time.time() - start_time_ping) * 1000, 2)
        status = "🔓 Unlocked" if not bot_locked else "🔒 Locked"
        if user_id == OWNER_ID:
            user_level = "👑 Owner"
        elif user_id in admin_ids:
            user_level = "🛡️ Admin"
        elif user_id in user_subscriptions and user_subscriptions[user_id].get('expiry', datetime.min) > datetime.now():
            user_level = "⭐ Premium"
        else:
            user_level = "🆓 Free User"
        speed_msg = (f"⚡ Bot Speed & Status:\n\n⏱️ API Response Time: {response_time} ms\n"
                     f"🚦 Bot Status: {status}\n"
                     f"👤 Your Level: {user_level}")
        bot.edit_message_text(speed_msg, chat_id, wait_msg.message_id)
    except Exception as e:
        print(f"Error during speed test (cmd): {e}")
        bot.edit_message_text("❌ Error during speed test.", chat_id, wait_msg.message_id)

def _logic_help(message):
    help_text = """
🤖 **Digital World Hosting Bot Help Guide**

**📌 Basic Commands:**
• /start - Start the bot
• /help - Show this help message
• /status - Show bot statistics

**📁 File Management:**
• Upload `.py` or `.js` files directly
• Upload `.zip` archives with multiple files
• Auto-installs dependencies from `requirements.txt` or `package.json`

**📦 Module Installation:**
• Auto-install missing Python/Node modules
• Manual install via "📦 Manual Install" button
• Admin can install modules for users

**👑 Admin Features:**
• User management (ban/unban)
• Set custom file limits
• Manage mandatory channels
• Broadcast messages
• Run all user scripts
• Key generation system

**🔗 Referral System:**
• Share your referral link
• Earn file limit and premium days
• Track your referrals
• Top referrers leaderboard

**⚙️ Tips:**
1. Make sure your scripts don't contain dangerous commands
2. Join all required channels
3. Contact owner for subscription upgrades

**Support:** @{YOUR_USERNAME}
**Updates:** {UPDATE_CHANNEL}
"""
    bot.reply_to(message, help_text, parse_mode='Markdown')

@bot.message_handler(content_types=['document'])
def handle_file_upload_doc(message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    if is_user_banned(user_id):
        bot.reply_to(message, "❌ You are banned from using this bot.")
        return
    is_subscribed, not_joined = check_mandatory_subscription(user_id)
    if not is_subscribed and user_id not in admin_ids:
        subscription_message, markup = create_subscription_check_message(not_joined)
        bot.reply_to(message, subscription_message, reply_markup=markup, parse_mode='Markdown')
        return
    doc = message.document
    if bot_locked and user_id not in admin_ids:
        bot.reply_to(message, "⚠️ Bot locked, cannot accept files.")
        return
    file_limit = get_user_file_limit(user_id)
    current_files = get_user_file_count(user_id)
    if current_files >= file_limit:
        limit_str = str(file_limit) if file_limit != float('inf') else "Unlimited"
        bot.reply_to(message, f"⚠️ File limit ({current_files}/{limit_str}) reached. Delete files via /files.")
        return
    file_name = doc.file_name
    if not file_name:
        bot.reply_to(message, "⚠️ No file name. Ensure file has a name.")
        return
    file_ext = os.path.splitext(file_name)[1].lower()
    if file_ext not in ['.py', '.js', '.zip']:
        bot.reply_to(message, "⚠️ Unsupported type! Only `.py`, `.js`, `.zip` allowed.")
        return
    max_file_size = 20 * 1024 * 1024
    if doc.file_size > max_file_size:
        bot.reply_to(message, f"⚠️ File too large (Max: {max_file_size // 1024 // 1024} MB).")
        return
    try:
        try:
            bot.forward_message(OWNER_ID, chat_id, message.message_id)
            bot.send_message(OWNER_ID, f"⬆️ File '{file_name}' from {message.from_user.first_name} (`{user_id}`)", parse_mode='Markdown')
        except Exception as e:
            print(f"Failed to forward uploaded file to OWNER_ID {OWNER_ID}: {e}")
        download_wait_msg = bot.reply_to(message, f"⏳ Downloading `{file_name}`...")
        file_info_tg_doc = bot.get_file(doc.file_id)
        downloaded_file_content = bot.download_file(file_info_tg_doc.file_path)
        bot.edit_message_text(f"✅ Downloaded `{file_name}`. Processing...", chat_id, download_wait_msg.message_id)
        user_folder = get_user_folder(user_id)
        if file_ext == '.zip':
            handle_zip_file(downloaded_file_content, file_name, message)
        else:
            file_path = os.path.join(user_folder, file_name)
            with open(file_path, 'wb') as f:
                f.write(downloaded_file_content)
            is_safe, security_msg = check_code_security(file_path, file_ext[1:])
            if not is_safe:
                print(f"⚠️ Unsafe script from {user_id}: {file_name} - {security_msg}")
            send_host_notification(user_id, file_name, file_ext[1:].upper(), is_safe, security_msg)
            if file_ext == '.js':
                handle_js_file(file_path, user_id, user_folder, file_name, message)
            elif file_ext == '.py':
                handle_py_file(file_path, user_id, user_folder, file_name, message)
    except Exception as e:
        print(f"❌ General error handling file for {user_id}: {e}")
        bot.reply_to(message, f"❌ Unexpected error: {str(e)}")

@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    user_id = call.from_user.id
    data = call.data
    if is_user_banned(user_id) and data not in ['back_to_main']:
        bot.answer_callback_query(call.id, "❌ You are banned from using this bot.", show_alert=True)
        return
    if data not in ['check_subscription_status', 'back_to_main', 'manual_install', 'referrals']:
        is_subscribed, not_joined = check_mandatory_subscription(user_id)
        if not is_subscribed and user_id not in admin_ids:
            subscription_message, markup = create_subscription_check_message(not_joined)
            bot.answer_callback_query(call.id)
            try:
                bot.edit_message_text(subscription_message, call.message.chat.id, call.message.message_id,
                                      reply_markup=markup, parse_mode='Markdown')
            except:
                bot.send_message(call.message.chat.id, subscription_message, reply_markup=markup,
                                 parse_mode='Markdown')
            return
    if bot_locked and user_id not in admin_ids and data not in ['back_to_main', 'speed', 'stats',
                                                                 'check_subscription_status', 'manual_install', 'referrals']:
        bot.answer_callback_query(call.id, "⚠️ Bot locked by admin.", show_alert=True)
        return
    try:
        if data == 'upload':
            upload_callback(call)
        elif data == 'check_files':
            check_files_callback(call)
        elif data.startswith('file_'):
            file_control_callback(call)
        elif data.startswith('start_'):
            start_bot_callback(call)
        elif data.startswith('stop_'):
            stop_bot_callback(call)
        elif data.startswith('restart_'):
            restart_bot_callback(call)
        elif data.startswith('delete_'):
            delete_bot_callback(call)
        elif data.startswith('logs_'):
            logs_bot_callback(call)
        elif data == 'speed':
            speed_callback(call)
        elif data == 'back_to_main':
            back_to_main_callback(call)
        elif data == 'manual_install':
            manual_install_callback(call)
        elif data == 'profile':
            profile_callback(call)
        elif data == 'refresh_profile':
            refresh_profile_callback(call)
        elif data == 'premium_info':
            premium_info_callback(call)
        elif data == 'redeem_key':
            redeem_key_callback(call)
        elif data == 'referrals':
            referrals_callback(call)
        elif data == 'my_referral_link':
            my_referral_link_callback(call)
        elif data == 'referral_stats':
            referral_stats_callback(call)
        elif data == 'top_referrers':
            top_referrers_callback(call)
        elif data == 'referred_users':
            referred_users_callback(call)
        elif data == 'share_referral':
            share_referral_callback(call)
        elif data == 'refresh_referral':
            refresh_referral_callback(call)
        elif data == 'admin_referrals':
            admin_referrals_callback(call)
        elif data == 'admin_referral_stats':
            admin_referral_stats_callback(call)
        elif data == 'admin_top_referrers':
            admin_top_referrers_callback(call)
        elif data == 'subscription':
            admin_required_callback(call, subscription_management_callback)
        elif data == 'stats':
            stats_callback(call)
        elif data == 'lock_bot':
            admin_required_callback(call, lock_bot_callback)
        elif data == 'unlock_bot':
            admin_required_callback(call, unlock_bot_callback)
        elif data == 'run_all_scripts':
            admin_required_callback(call, run_all_scripts_callback)
        elif data == 'broadcast':
            admin_required_callback(call, broadcast_init_callback)
        elif data == 'admin_panel':
            admin_required_callback(call, admin_panel_callback)
        elif data == 'add_admin':
            owner_required_callback(call, add_admin_init_callback)
        elif data == 'remove_admin':
            owner_required_callback(call, remove_admin_init_callback)
        elif data == 'list_admins':
            admin_required_callback(call, list_admins_callback)
        elif data == 'add_subscription':
            admin_required_callback(call, add_subscription_init_callback)
        elif data == 'remove_subscription':
            admin_required_callback(call, remove_subscription_init_callback)
        elif data == 'check_subscription':
            admin_required_callback(call, check_subscription_init_callback)
        elif data == 'user_management':
            admin_required_callback(call, user_management_callback)
        elif data == 'ban_user':
            admin_required_callback(call, ban_user_callback)
        elif data == 'unban_user':
            admin_required_callback(call, unban_user_callback)
        elif data == 'user_info':
            admin_required_callback(call, user_info_callback)
        elif data == 'all_users':
            admin_required_callback(call, all_users_callback)
        elif data == 'set_user_limit':
            admin_required_callback(call, set_user_limit_callback)
        elif data == 'remove_user_limit':
            admin_required_callback(call, remove_user_limit_callback)
        elif data == 'admin_settings':
            admin_required_callback(call, admin_settings_callback)
        elif data == 'system_info':
            admin_required_callback(call, system_info_callback)
        elif data == 'bot_performance':
            admin_required_callback(call, bot_performance_callback)
        elif data == 'cleanup_files':
            admin_required_callback(call, cleanup_files_callback)
        elif data == 'install_logs':
            admin_required_callback(call, install_logs_callback)
        elif data == 'admin_install':
            admin_required_callback(call, admin_install_callback)
        elif data == 'manage_keys':
            admin_required_callback(call, manage_keys_callback)
        elif data == 'list_keys_admin':
            list_keys_admin_callback(call)
        elif data == 'gen_key_admin':
            gen_key_admin_callback(call)
        elif data == 'manage_mandatory_channels':
            admin_required_callback(call, manage_mandatory_channels_callback)
        elif data == 'add_mandatory_channel':
            admin_required_callback(call, add_mandatory_channel_callback)
        elif data == 'remove_mandatory_channel':
            admin_required_callback(call, remove_mandatory_channel_callback)
        elif data == 'list_mandatory_channels':
            admin_required_callback(call, list_mandatory_channels_callback)
        elif data == 'check_subscription_status':
            check_subscription_status_callback(call)
        else:
            bot.answer_callback_query(call.id, "Unknown action.")
            print(f"Unhandled callback data: {data} from user {user_id}")
    except Exception as e:
        print(f"Error handling callback '{data}' for {user_id}: {e}")
        try:
            bot.answer_callback_query(call.id, "Error processing request.", show_alert=True)
        except:
            pass

def upload_callback(call):
    user_id = call.from_user.id
    if is_user_banned(user_id):
        bot.answer_callback_query(call.id, "❌ You are banned from using this bot.", show_alert=True)
        return
    is_subscribed, not_joined = check_mandatory_subscription(user_id)
    if not is_subscribed and user_id not in admin_ids:
        subscription_message, markup = create_subscription_check_message(not_joined)
        bot.answer_callback_query(call.id)
        try:
            bot.edit_message_text(subscription_message, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode='Markdown')
        except:
            bot.send_message(call.message.chat.id, subscription_message, reply_markup=markup, parse_mode='Markdown')
        return
    file_limit = get_user_file_limit(user_id)
    current_files = get_user_file_count(user_id)
    if current_files >= file_limit:
        limit_str = str(file_limit) if file_limit != float('inf') else "Unlimited"
        bot.answer_callback_query(call.id, f"⚠️ File limit ({current_files}/{limit_str}) reached.", show_alert=True)
        return
    bot.answer_callback_query(call.id)
    bot.send_message(call.message.chat.id, "📤 Send your Python (`.py`), JS (`.js`), or ZIP (`.zip`) file.")

def check_files_callback(call):
    user_id = call.from_user.id
    if is_user_banned(user_id):
        bot.answer_callback_query(call.id, "❌ You are banned from using this bot.", show_alert=True)
        return
    is_subscribed, not_joined = check_mandatory_subscription(user_id)
    if not is_subscribed and user_id not in admin_ids:
        subscription_message, markup = create_subscription_check_message(not_joined)
        bot.answer_callback_query(call.id)
        try:
            bot.edit_message_text(subscription_message, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode='Markdown')
        except:
            bot.send_message(call.message.chat.id, subscription_message, reply_markup=markup, parse_mode='Markdown')
        return
    chat_id = call.message.chat.id
    user_files_list = user_files.get(user_id, [])
    if not user_files_list:
        bot.answer_callback_query(call.id, "⚠️ No files uploaded.", show_alert=True)
        try:
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("🔙 Back to Main", callback_data='back_to_main'))
            bot.edit_message_text("📂 Your files:\n\n(No files uploaded)", chat_id, call.message.message_id, reply_markup=markup)
        except Exception as e:
            print(f"Error editing msg for empty file list: {e}")
        return
    bot.answer_callback_query(call.id)
    markup = types.InlineKeyboardMarkup(row_width=1)
    for file_name, file_type in sorted(user_files_list):
        is_running = is_bot_running(user_id, file_name)
        status_icon = "🟢 Running" if is_running else "🔴 Stopped"
        btn_text = f"{file_name} ({file_type}) - {status_icon}"
        markup.add(types.InlineKeyboardButton(btn_text, callback_data=f'file_{user_id}_{file_name}'))
    markup.add(types.InlineKeyboardButton("🔙 Back to Main", callback_data='back_to_main'))
    try:
        bot.edit_message_text("📂 Your files:\nClick to manage.", chat_id, call.message.message_id, reply_markup=markup, parse_mode='Markdown')
    except Exception as e:
        print(f"Error editing msg for file list: {e}")

def file_control_callback(call):
    try:
        _, script_owner_id_str, file_name = call.data.split('_', 2)
        script_owner_id = int(script_owner_id_str)
        requesting_user_id = call.from_user.id
        if not (requesting_user_id == script_owner_id or requesting_user_id in admin_ids):
            bot.answer_callback_query(call.id, "⚠️ You can only manage your own files.", show_alert=True)
            check_files_callback(call)
            return
        user_files_list = user_files.get(script_owner_id, [])
        if not any(f[0] == file_name for f in user_files_list):
            bot.answer_callback_query(call.id, "⚠️ File not found.", show_alert=True)
            check_files_callback(call)
            return
        bot.answer_callback_query(call.id)
        is_running = is_bot_running(script_owner_id, file_name)
        status_text = '🟢 Running' if is_running else '🔴 Stopped'
        file_type = next((f[1] for f in user_files_list if f[0] == file_name), '?')
        try:
            bot.edit_message_text(
                f"⚙️ Controls for: `{file_name}` ({file_type}) of User `{script_owner_id}`\nStatus: {status_text}",
                call.message.chat.id, call.message.message_id,
                reply_markup=create_control_buttons(script_owner_id, file_name, is_running),
                parse_mode='Markdown'
            )
        except Exception as e:
            print(f"Error editing controls: {e}")
    except Exception as e:
        print(f"Error in file_control_callback: {e}")
        bot.answer_callback_query(call.id, "An error occurred.", show_alert=True)

def start_bot_callback(call):
    try:
        _, script_owner_id_str, file_name = call.data.split('_', 2)
        script_owner_id = int(script_owner_id_str)
        requesting_user_id = call.from_user.id
        chat_id_for_reply = call.message.chat.id
        if not (requesting_user_id == script_owner_id or requesting_user_id in admin_ids):
            bot.answer_callback_query(call.id, "⚠️ Permission denied.", show_alert=True)
            return
        user_files_list = user_files.get(script_owner_id, [])
        file_info = next((f for f in user_files_list if f[0] == file_name), None)
        if not file_info:
            bot.answer_callback_query(call.id, "⚠️ File not found.", show_alert=True)
            check_files_callback(call)
            return
        file_type = file_info[1]
        user_folder = get_user_folder(script_owner_id)
        file_path = os.path.join(user_folder, file_name)
        if not os.path.exists(file_path):
            bot.answer_callback_query(call.id, f"⚠️ Error: File `{file_name}` missing!", show_alert=True)
            remove_user_file_db(script_owner_id, file_name)
            check_files_callback(call)
            return
        if is_bot_running(script_owner_id, file_name):
            bot.answer_callback_query(call.id, f"⚠️ Script '{file_name}' already running.", show_alert=True)
            try:
                bot.edit_message_reply_markup(chat_id_for_reply, call.message.message_id, reply_markup=create_control_buttons(script_owner_id, file_name, True))
            except:
                pass
            return
        bot.answer_callback_query(call.id, f"⏳ Attempting to start {file_name}...")
        if file_type == 'py':
            threading.Thread(target=run_script, args=(file_path, script_owner_id, user_folder, file_name, call.message)).start()
        elif file_type == 'js':
            threading.Thread(target=run_js_script, args=(file_path, script_owner_id, user_folder, file_name, call.message)).start()
        else:
            bot.send_message(chat_id_for_reply, f"❌ Error: Unknown file type '{file_type}'.")
            return
        time.sleep(1.5)
        is_now_running = is_bot_running(script_owner_id, file_name)
        status_text = '🟢 Running' if is_now_running else '🟡 Starting (or failed)'
        try:
            bot.edit_message_text(
                f"⚙️ Controls for: `{file_name}` ({file_type}) of User `{script_owner_id}`\nStatus: {status_text}",
                chat_id_for_reply, call.message.message_id,
                reply_markup=create_control_buttons(script_owner_id, file_name, is_now_running), parse_mode='Markdown'
            )
        except:
            pass
    except Exception as e:
        print(f"Error in start_bot_callback: {e}")
        bot.answer_callback_query(call.id, "Error starting script.", show_alert=True)

def stop_bot_callback(call):
    try:
        _, script_owner_id_str, file_name = call.data.split('_', 2)
        script_owner_id = int(script_owner_id_str)
        requesting_user_id = call.from_user.id
        chat_id_for_reply = call.message.chat.id
        if not (requesting_user_id == script_owner_id or requesting_user_id in admin_ids):
            bot.answer_callback_query(call.id, "⚠️ Permission denied.", show_alert=True)
            return
        user_files_list = user_files.get(script_owner_id, [])
        file_info = next((f for f in user_files_list if f[0] == file_name), None)
        if not file_info:
            bot.answer_callback_query(call.id, "⚠️ File not found.", show_alert=True)
            check_files_callback(call)
            return
        file_type = file_info[1]
        script_key = f"{script_owner_id}_{file_name}"
        if not is_bot_running(script_owner_id, file_name):
            bot.answer_callback_query(call.id, f"⚠️ Script '{file_name}' already stopped.", show_alert=True)
            try:
                bot.edit_message_text(
                    f"⚙️ Controls for: `{file_name}` ({file_type}) of User `{script_owner_id}`\nStatus: 🔴 Stopped",
                    chat_id_for_reply, call.message.message_id,
                    reply_markup=create_control_buttons(script_owner_id, file_name, False), parse_mode='Markdown')
            except:
                pass
            return
        bot.answer_callback_query(call.id, f"⏳ Stopping {file_name}...")
        process_info = bot_scripts.get(script_key)
        if process_info:
            kill_process_tree(process_info)
            if script_key in bot_scripts:
                del bot_scripts[script_key]
        try:
            bot.edit_message_text(
                f"⚙️ Controls for: `{file_name}` ({file_type}) of User `{script_owner_id}`\nStatus: 🔴 Stopped",
                chat_id_for_reply, call.message.message_id,
                reply_markup=create_control_buttons(script_owner_id, file_name, False), parse_mode='Markdown'
            )
        except:
            pass
    except Exception as e:
        print(f"Error in stop_bot_callback: {e}")
        bot.answer_callback_query(call.id, "Error stopping script.", show_alert=True)

def restart_bot_callback(call):
    try:
        _, script_owner_id_str, file_name = call.data.split('_', 2)
        script_owner_id = int(script_owner_id_str)
        requesting_user_id = call.from_user.id
        chat_id_for_reply = call.message.chat.id
        if not (requesting_user_id == script_owner_id or requesting_user_id in admin_ids):
            bot.answer_callback_query(call.id, "⚠️ Permission denied.", show_alert=True)
            return
        user_files_list = user_files.get(script_owner_id, [])
        file_info = next((f for f in user_files_list if f[0] == file_name), None)
        if not file_info:
            bot.answer_callback_query(call.id, "⚠️ File not found.", show_alert=True)
            check_files_callback(call)
            return
        file_type = file_info[1]
        user_folder = get_user_folder(script_owner_id)
        file_path = os.path.join(user_folder, file_name)
        script_key = f"{script_owner_id}_{file_name}"
        if not os.path.exists(file_path):
            bot.answer_callback_query(call.id, f"⚠️ Error: File `{file_name}` missing!", show_alert=True)
            remove_user_file_db(script_owner_id, file_name)
            if script_key in bot_scripts:
                del bot_scripts[script_key]
            check_files_callback(call)
            return
        bot.answer_callback_query(call.id, f"⏳ Restarting {file_name}...")
        if is_bot_running(script_owner_id, file_name):
            process_info = bot_scripts.get(script_key)
            if process_info:
                kill_process_tree(process_info)
            if script_key in bot_scripts:
                del bot_scripts[script_key]
            time.sleep(1.5)
        if file_type == 'py':
            threading.Thread(target=run_script, args=(file_path, script_owner_id, user_folder, file_name, call.message)).start()
        elif file_type == 'js':
            threading.Thread(target=run_js_script, args=(file_path, script_owner_id, user_folder, file_name, call.message)).start()
        else:
            bot.send_message(chat_id_for_reply, f"❌ Unknown type '{file_type}'.")
            return
        time.sleep(1.5)
        is_now_running = is_bot_running(script_owner_id, file_name)
        status_text = '🟢 Running' if is_now_running else '🟡 Starting (or failed)'
        try:
            bot.edit_message_text(
                f"⚙️ Controls for: `{file_name}` ({file_type}) of User `{script_owner_id}`\nStatus: {status_text}",
                chat_id_for_reply, call.message.message_id,
                reply_markup=create_control_buttons(script_owner_id, file_name, is_now_running), parse_mode='Markdown'
            )
        except:
            pass
    except Exception as e:
        print(f"Error in restart_bot_callback: {e}")
        bot.answer_callback_query(call.id, "Error restarting.", show_alert=True)

def delete_bot_callback(call):
    try:
        _, script_owner_id_str, file_name = call.data.split('_', 2)
        script_owner_id = int(script_owner_id_str)
        requesting_user_id = call.from_user.id
        chat_id_for_reply = call.message.chat.id
        if not (requesting_user_id == script_owner_id or requesting_user_id in admin_ids):
            bot.answer_callback_query(call.id, "⚠️ Permission denied.", show_alert=True)
            return
        user_files_list = user_files.get(script_owner_id, [])
        if not any(f[0] == file_name for f in user_files_list):
            bot.answer_callback_query(call.id, "⚠️ File not found.", show_alert=True)
            check_files_callback(call)
            return
        bot.answer_callback_query(call.id, f"🗑️ Deleting {file_name}...")
        script_key = f"{script_owner_id}_{file_name}"
        if is_bot_running(script_owner_id, file_name):
            process_info = bot_scripts.get(script_key)
            if process_info:
                kill_process_tree(process_info)
            if script_key in bot_scripts:
                del bot_scripts[script_key]
            time.sleep(0.5)
        user_folder = get_user_folder(script_owner_id)
        file_path = os.path.join(user_folder, file_name)
        log_path = os.path.join(user_folder, f"{os.path.splitext(file_name)[0]}.log")
        deleted_disk = []
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
                deleted_disk.append(file_name)
            except:
                pass
        if os.path.exists(log_path):
            try:
                os.remove(log_path)
                deleted_disk.append(os.path.basename(log_path))
            except:
                pass
        remove_user_file_db(script_owner_id, file_name)
        deleted_str = ", ".join(f"`{f}`" for f in deleted_disk) if deleted_disk else "associated files"
        try:
            bot.edit_message_text(
                f"🗑️ Record `{file_name}` (User `{script_owner_id}`) and {deleted_str} deleted!",
                chat_id_for_reply, call.message.message_id, reply_markup=None, parse_mode='Markdown'
            )
        except:
            bot.send_message(chat_id_for_reply, f"🗑️ Record `{file_name}` deleted.", parse_mode='Markdown')
    except Exception as e:
        print(f"Error in delete_bot_callback: {e}")
        bot.answer_callback_query(call.id, "Error deleting.", show_alert=True)

def logs_bot_callback(call):
    try:
        _, script_owner_id_str, file_name = call.data.split('_', 2)
        script_owner_id = int(script_owner_id_str)
        requesting_user_id = call.from_user.id
        chat_id_for_reply = call.message.chat.id
        if not (requesting_user_id == script_owner_id or requesting_user_id in admin_ids):
            bot.answer_callback_query(call.id, "⚠️ Permission denied.", show_alert=True)
            return
        user_files_list = user_files.get(script_owner_id, [])
        if not any(f[0] == file_name for f in user_files_list):
            bot.answer_callback_query(call.id, "⚠️ File not found.", show_alert=True)
            check_files_callback(call)
            return
        user_folder = get_user_folder(script_owner_id)
        log_path = os.path.join(user_folder, f"{os.path.splitext(file_name)[0]}.log")
        if not os.path.exists(log_path):
            bot.answer_callback_query(call.id, f"⚠️ No logs for '{file_name}'.", show_alert=True)
            return
        bot.answer_callback_query(call.id)
        try:
            log_content = ""
            file_size = os.path.getsize(log_path)
            max_log_kb = 100
            if file_size == 0:
                log_content = "(Log empty)"
            elif file_size > max_log_kb * 1024:
                with open(log_path, 'rb') as f:
                    f.seek(-max_log_kb * 1024, os.SEEK_END)
                    log_bytes = f.read()
                log_content = log_bytes.decode('utf-8', errors='ignore')
                log_content = f"(Last {max_log_kb} KB)\n...\n" + log_content
            else:
                with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
                    log_content = f.read()
            if len(log_content) > 4096:
                log_content = log_content[-4096:]
                first_nl = log_content.find('\n')
                if first_nl != -1:
                    log_content = "...\n" + log_content[first_nl+1:]
                else:
                    log_content = "...\n" + log_content
            if not log_content.strip():
                log_content = "(No visible content)"
            bot.send_message(chat_id_for_reply, f"📜 Logs for `{file_name}` (User `{script_owner_id}`):\n```\n{log_content}\n```", parse_mode='Markdown')
        except Exception as e:
            print(f"Error reading log: {e}")
            bot.send_message(chat_id_for_reply, f"❌ Error reading log for `{file_name}`.")
    except Exception as e:
        print(f"Error in logs_bot_callback: {e}")
        bot.answer_callback_query(call.id, "Error fetching logs.", show_alert=True)

def speed_callback(call):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    if is_user_banned(user_id):
        bot.answer_callback_query(call.id, "❌ You are banned from using this bot.", show_alert=True)
        return
    is_subscribed, not_joined = check_mandatory_subscription(user_id)
    if not is_subscribed and user_id not in admin_ids:
        subscription_message, markup = create_subscription_check_message(not_joined)
        bot.answer_callback_query(call.id)
        try:
            bot.edit_message_text(subscription_message, chat_id, call.message.message_id, reply_markup=markup, parse_mode='Markdown')
        except:
            bot.send_message(chat_id, subscription_message, reply_markup=markup, parse_mode='Markdown')
        return
    start_cb_ping_time = time.time()
    try:
        bot.edit_message_text("🏃 Testing speed...", chat_id, call.message.message_id)
        bot.send_chat_action(chat_id, 'typing')
        response_time = round((time.time() - start_cb_ping_time) * 1000, 2)
        status = "🔓 Unlocked" if not bot_locked else "🔒 Locked"
        if user_id == OWNER_ID:
            user_level = "👑 Owner"
        elif user_id in admin_ids:
            user_level = "🛡️ Admin"
        elif user_id in user_subscriptions and user_subscriptions[user_id].get('expiry', datetime.min) > datetime.now():
            user_level = "⭐ Premium"
        else:
            user_level = "🆓 Free User"
        speed_msg = (f"⚡ Bot Speed & Status:\n\n⏱️ API Response Time: {response_time} ms\n"
                     f"🚦 Bot Status: {status}\n"
                     f"👤 Your Level: {user_level}")
        bot.answer_callback_query(call.id)
        bot.edit_message_text(speed_msg, chat_id, call.message.message_id, reply_markup=create_main_menu_inline(user_id))
    except Exception as e:
        print(f"Error during speed test (cb): {e}")
        bot.answer_callback_query(call.id, "Error in speed test.", show_alert=True)
        try:
            bot.edit_message_text("〽️ Main Menu", chat_id, call.message.message_id, reply_markup=create_main_menu_inline(user_id))
        except:
            pass

def back_to_main_callback(call):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    if is_user_banned(user_id):
        bot.answer_callback_query(call.id, "❌ You are banned from using this bot.", show_alert=True)
        return
    is_subscribed, not_joined = check_mandatory_subscription(user_id)
    if not is_subscribed and user_id not in admin_ids:
        subscription_message, markup = create_subscription_check_message(not_joined)
        bot.answer_callback_query(call.id)
        try:
            bot.edit_message_text(subscription_message, chat_id, call.message.message_id, reply_markup=markup, parse_mode='Markdown')
        except:
            bot.send_message(chat_id, subscription_message, reply_markup=markup, parse_mode='Markdown')
        return
    file_limit = get_user_file_limit(user_id)
    current_files = get_user_file_count(user_id)
    limit_str = str(file_limit) if file_limit != float('inf') else "Unlimited"
    expiry_info = ""
    if user_id == OWNER_ID:
        user_status = "👑 Owner"
    elif user_id in admin_ids:
        user_status = "🛡️ Admin"
    elif user_id in user_subscriptions:
        expiry_date = user_subscriptions[user_id].get('expiry')
        if expiry_date and expiry_date > datetime.now():
            user_status = "⭐ Premium"
            days_left = (expiry_date - datetime.now()).days
            expiry_info = f"\n⏳ Subscription expires in: {days_left} days"
        else:
            user_status = "🆓 Free User (Expired Sub)"
    else:
        user_status = "🆓 Free User"
    main_menu_text = (f"〽️ Welcome back, {call.from_user.first_name}!\n\n🆔 ID: `{user_id}`\n"
                      f"🔰 Status: {user_status}{expiry_info}\n📁 Files: {current_files} / {limit_str}\n\n"
                      f"👇 Use buttons or type commands.")
    try:
        bot.answer_callback_query(call.id)
        bot.edit_message_text(main_menu_text, chat_id, call.message.message_id,
                              reply_markup=create_main_menu_inline(user_id), parse_mode='Markdown')
    except Exception as e:
        print(f"Error handling back_to_main: {e}")

def manual_install_callback(call):
    bot.answer_callback_query(call.id)
    manual_install_module_init(call.message)

def profile_callback(call):
    bot.answer_callback_query(call.id)
    command_profile(call.message)

def refresh_profile_callback(call):
    bot.answer_callback_query(call.id, "🔄 Refreshing profile...")
    command_profile(call.message)

def premium_info_callback(call):
    bot.answer_callback_query(call.id)
    command_premium(call.message)

def redeem_key_callback(call):
    bot.answer_callback_query(call.id)
    msg = bot.send_message(call.message.chat.id, "🎫 Enter your premium key:\n/cancel to cancel")
    bot.register_next_step_handler(msg, process_redeem_key)

def process_redeem_key(message):
    user_id = message.from_user.id
    if message.text and message.text.lower() == '/cancel':
        bot.reply_to(message, "❌ Key redemption cancelled.")
        return
    key_code = message.text.strip().upper()
    success, msg = redeem_key(user_id, key_code)
    bot.reply_to(message, f"{'✅' if success else '❌'} {msg}")

def referrals_callback(call):
    bot.answer_callback_query(call.id)
    command_referral(call.message)

def my_referral_link_callback(call):
    bot.answer_callback_query(call.id)
    user_id = call.from_user.id
    ref_code = get_user_referral_code(user_id)
    referral_link = f"https://t.me/{bot.get_me().username}?start=ref_{ref_code}"
    msg = f"""
🔗 **Your Referral Link**

`{referral_link}`

📤 **Share this link** with your friends!
Each referral gives you:
┣ 📁 +{REFERRAL_REWARD_LIMIT} File Limit
┗ ⭐ +{REFERRAL_REWARD_DAYS} Premium Days
"""
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("📤 Share", callback_data='share_referral'),
        types.InlineKeyboardButton("🔙 Back", callback_data='referrals')
    )
    try:
        bot.edit_message_text(msg, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode='Markdown')
    except:
        bot.send_message(call.message.chat.id, msg, reply_markup=markup, parse_mode='Markdown')

def referral_stats_callback(call):
    bot.answer_callback_query(call.id)
    command_referral(call.message)

def top_referrers_callback(call):
    bot.answer_callback_query(call.id)
    top_refs = get_top_referrers(10)
    if not top_refs:
        msg = "🏆 No referrers yet. Be the first!"
    else:
        msg = "🏆 **Top Referrers:**\n\n"
        for i, (uid, username, count, extra) in enumerate(top_refs, 1):
            name = username or f"User {uid}"
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
            msg += f"{medal} {name} - {count} referrals (+{extra} limit)\n"
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🔙 Back", callback_data='referrals'))
    try:
        bot.edit_message_text(msg, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode='Markdown')
    except:
        bot.send_message(call.message.chat.id, msg, reply_markup=markup, parse_mode='Markdown')

def referred_users_callback(call):
    bot.answer_callback_query(call.id)
    user_id = call.from_user.id
    referred = get_referred_users(user_id)
    if not referred:
        msg = "📋 You haven't referred anyone yet."
    else:
        msg = "📋 **Your Referred Users:**\n\n"
        for uid, username, join_date in referred:
            name = username or f"User {uid}"
            msg += f"• {name} (`{uid}`) - Joined: {join_date[:10]}\n"
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🔙 Back", callback_data='referrals'))
    try:
        bot.edit_message_text(msg, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode='Markdown')
    except:
        bot.send_message(call.message.chat.id, msg, reply_markup=markup, parse_mode='Markdown')

def share_referral_callback(call):
    bot.answer_callback_query(call.id)
    user_id = call.from_user.id
    ref_code = get_user_referral_code(user_id)
    referral_link = f"https://t.me/{bot.get_me().username}?start=ref_{ref_code}"
    share_text = f"🎉 Join me on the Digital World Hosting Bot!\n\nUse my referral link and get:\n📁 Extra file limit\n⭐ Premium days\n\n🔗 {referral_link}"
    try:
        bot.send_message(call.message.chat.id, f"📤 **Share this message:**\n\n{share_text}", parse_mode='Markdown')
    except:
        bot.send_message(call.message.chat.id, f"📤 Share this link: {referral_link}")

def refresh_referral_callback(call):
    bot.answer_callback_query(call.id, "🔄 Refreshing...")
    command_referral(call.message)

def admin_referrals_callback(call):
    bot.answer_callback_query(call.id)
    try:
        bot.edit_message_text("🔗 **Admin Referral Management**\n\nView all referral stats and top referrers.",
                              call.message.chat.id, call.message.message_id,
                              reply_markup=create_admin_referral_menu(), parse_mode='Markdown')
    except:
        bot.send_message(call.message.chat.id, "🔗 **Admin Referral Management**\n\nView all referral stats and top referrers.",
                         reply_markup=create_admin_referral_menu(), parse_mode='Markdown')

def admin_referral_stats_callback(call):
    bot.answer_callback_query(call.id)
    stats = PERMANENT_DB.get_stats()
    total_refs = stats.get('total_referrals', 0)
    conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False, timeout=30)
    c = conn.cursor()
    c.execute('SELECT COUNT(DISTINCT user_id) FROM permanent_users WHERE referral_count > 0')
    users_with_refs = c.fetchone()[0]
    c.execute('SELECT AVG(referral_count) FROM permanent_users WHERE referral_count > 0')
    avg_refs = c.fetchone()[0]
    conn.close()
    msg = f"""
📊 **Referral System Stats**

📈 Total Referrals: {total_refs}
👥 Users with Referrals: {users_with_refs}
📊 Average Referrals: {avg_refs:.1f if avg_refs else 0}

🏆 Top Referrer Bonus: +{REFERRAL_REWARD_LIMIT} limit per referral
⭐ Premium Days per Referral: {REFERRAL_REWARD_DAYS} days
"""
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🏆 Top Referrers", callback_data='admin_top_referrers'))
    markup.add(types.InlineKeyboardButton("🔙 Back", callback_data='admin_referrals'))
    try:
        bot.edit_message_text(msg, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode='Markdown')
    except:
        bot.send_message(call.message.chat.id, msg, reply_markup=markup, parse_mode='Markdown')

def admin_top_referrers_callback(call):
    bot.answer_callback_query(call.id)
    top_refs = get_top_referrers(20)
    if not top_refs:
        msg = "🏆 No referrers yet."
    else:
        msg = "🏆 **Top Referrers (All Time):**\n\n"
        for i, (uid, username, count, extra) in enumerate(top_refs, 1):
            name = username or f"User {uid}"
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
            msg += f"{medal} {name} - {count} referrals (+{extra} limit)\n"
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🔙 Back", callback_data='admin_referral_stats'))
    try:
        bot.edit_message_text(msg, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode='Markdown')
    except:
        bot.send_message(call.message.chat.id, msg, reply_markup=markup, parse_mode='Markdown')

def admin_required_callback(call, func_to_run):
    if call.from_user.id not in admin_ids:
        bot.answer_callback_query(call.id, "⚠️ Admin permissions required.", show_alert=True)
        return
    func_to_run(call)

def owner_required_callback(call, func_to_run):
    if call.from_user.id != OWNER_ID:
        bot.answer_callback_query(call.id, "⚠️ Owner permissions required.", show_alert=True)
        return
    func_to_run(call)

def subscription_management_callback(call):
    bot.answer_callback_query(call.id)
    try:
        bot.edit_message_text("💳 Subscription Management\nSelect action:",
                              call.message.chat.id, call.message.message_id, reply_markup=create_subscription_menu())
    except:
        pass

def stats_callback(call):
    bot.answer_callback_query(call.id)
    _logic_statistics(call.message)
    try:
        bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id,
                                      reply_markup=create_main_menu_inline(call.from_user.id))
    except:
        pass

def lock_bot_callback(call):
    global bot_locked
    bot_locked = True
    conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False, timeout=30)
    c = conn.cursor()
    c.execute('UPDATE permanent_settings SET setting_value = ? WHERE setting_key = ?', ('true', 'bot_locked'))
    conn.commit()
    conn.close()
    bot.answer_callback_query(call.id, "🔒 Bot locked.")
    try:
        bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=create_main_menu_inline(call.from_user.id))
    except:
        pass

def unlock_bot_callback(call):
    global bot_locked
    bot_locked = False
    conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False, timeout=30)
    c = conn.cursor()
    c.execute('UPDATE permanent_settings SET setting_value = ? WHERE setting_key = ?', ('false', 'bot_locked'))
    conn.commit()
    conn.close()
    bot.answer_callback_query(call.id, "🔓 Bot unlocked.")
    try:
        bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=create_main_menu_inline(call.from_user.id))
    except:
        pass

def run_all_scripts_callback(call):
    _logic_run_all_scripts(call)

def _logic_run_all_scripts(call):
    admin_user_id = call.from_user.id
    if admin_user_id not in admin_ids:
        bot.answer_callback_query(call.id, "⚠️ Admin permissions required.", show_alert=True)
        return
    bot.answer_callback_query(call.id, "⏳ Starting all scripts...")
    bot.send_message(call.message.chat.id, "⏳ Starting process to run all user scripts...")
    started_count = 0
    attempted_users = 0
    all_user_files_snapshot = dict(user_files)
    for target_user_id, files_for_user in all_user_files_snapshot.items():
        if not files_for_user:
            continue
        attempted_users += 1
        user_folder = get_user_folder(target_user_id)
        for file_name, file_type in files_for_user:
            if not is_bot_running(target_user_id, file_name):
                file_path = os.path.join(user_folder, file_name)
                if os.path.exists(file_path):
                    try:
                        if file_type == 'py':
                            threading.Thread(target=run_script, args=(file_path, target_user_id, user_folder, file_name, call.message)).start()
                            started_count += 1
                        elif file_type == 'js':
                            threading.Thread(target=run_js_script, args=(file_path, target_user_id, user_folder, file_name, call.message)).start()
                            started_count += 1
                        time.sleep(0.5)
                    except:
                        pass
    bot.send_message(call.message.chat.id, f"✅ Started {started_count} scripts for {attempted_users} users.")

def broadcast_init_callback(call):
    bot.answer_callback_query(call.id)
    msg = bot.send_message(call.message.chat.id, "📢 Send message to broadcast.\n/cancel to abort.")
    bot.register_next_step_handler(msg, process_broadcast_message)

def admin_panel_callback(call):
    bot.answer_callback_query(call.id)
    try:
        bot.edit_message_text("👑 Admin Panel\nManage admins.",
                              call.message.chat.id, call.message.message_id, reply_markup=create_admin_panel())
    except:
        pass

def add_admin_init_callback(call):
    bot.answer_callback_query(call.id)
    msg = bot.send_message(call.message.chat.id, "👑 Enter User ID to promote to Admin.\n/cancel to abort.")
    bot.register_next_step_handler(msg, process_add_admin_id)

def process_add_admin_id(message):
    owner_id_check = message.from_user.id
    if owner_id_check != OWNER_ID:
        bot.reply_to(message, "⚠️ Owner only.")
        return
    if message.text.lower() == '/cancel':
        bot.reply_to(message, "Admin promotion cancelled.")
        return
    try:
        new_admin_id = int(message.text.strip())
        if new_admin_id <= 0:
            raise ValueError("ID must be positive")
        if new_admin_id == OWNER_ID:
            bot.reply_to(message, "⚠️ Owner is already Owner.")
            return
        if new_admin_id in admin_ids:
            bot.reply_to(message, f"⚠️ User `{new_admin_id}` already Admin.")
            return
        add_admin_db(new_admin_id, owner_id_check)
        bot.reply_to(message, f"✅ User `{new_admin_id}` promoted to Admin.")
        try:
            bot.send_message(new_admin_id, "🎉 Congrats! You are now an Admin.")
        except:
            pass
    except ValueError:
        bot.reply_to(message, "⚠️ Invalid ID. Send numerical ID or /cancel.")
        msg = bot.send_message(message.chat.id, "👑 Enter User ID to promote or /cancel.")
        bot.register_next_step_handler(msg, process_add_admin_id)
    except Exception as e:
        print(f"Error processing add admin: {e}")
        bot.reply_to(message, "Error.")

def remove_admin_init_callback(call):
    bot.answer_callback_query(call.id)
    msg = bot.send_message(call.message.chat.id, "👑 Enter User ID of Admin to remove.\n/cancel to abort.")
    bot.register_next_step_handler(msg, process_remove_admin_id)

def process_remove_admin_id(message):
    owner_id_check = message.from_user.id
    if owner_id_check != OWNER_ID:
        bot.reply_to(message, "⚠️ Owner only.")
        return
    if message.text.lower() == '/cancel':
        bot.reply_to(message, "Admin removal cancelled.")
        return
    try:
        admin_id_remove = int(message.text.strip())
        if admin_id_remove <= 0:
            raise ValueError("ID must be positive")
        if admin_id_remove == OWNER_ID:
            bot.reply_to(message, "⚠️ Owner cannot remove self.")
            return
        if admin_id_remove not in admin_ids:
            bot.reply_to(message, f"⚠️ User `{admin_id_remove}` not Admin.")
            return
        if remove_admin_db(admin_id_remove):
            bot.reply_to(message, f"✅ Admin `{admin_id_remove}` removed.")
            try:
                bot.send_message(admin_id_remove, "ℹ️ You are no longer an Admin.")
            except:
                pass
        else:
            bot.reply_to(message, f"❌ Failed to remove admin `{admin_id_remove}`.")
    except ValueError:
        bot.reply_to(message, "⚠️ Invalid ID. Send numerical ID or /cancel.")
        msg = bot.send_message(message.chat.id, "👑 Enter Admin ID to remove or /cancel.")
        bot.register_next_step_handler(msg, process_remove_admin_id)
    except Exception as e:
        print(f"Error processing remove admin: {e}")
        bot.reply_to(message, "Error.")

def list_admins_callback(call):
    bot.answer_callback_query(call.id)
    try:
        admin_list_str = "\n".join(f"- `{aid}` {'(Owner)' if aid == OWNER_ID else ''}" for aid in sorted(list(admin_ids)))
        if not admin_list_str:
            admin_list_str = "(No Owner/Admins configured!)"
        bot.edit_message_text(f"👑 Current Admins:\n\n{admin_list_str}", call.message.chat.id,
                              call.message.message_id, reply_markup=create_admin_panel(), parse_mode='Markdown')
    except:
        pass

def add_subscription_init_callback(call):
    bot.answer_callback_query(call.id)
    msg = bot.send_message(call.message.chat.id, "💳 Enter User ID & days (e.g., `12345678 30`).\n/cancel to abort.")
    bot.register_next_step_handler(msg, process_add_subscription_details)

def process_add_subscription_details(message):
    admin_id_check = message.from_user.id
    if admin_id_check not in admin_ids:
        bot.reply_to(message, "⚠️ Not authorized.")
        return
    if message.text.lower() == '/cancel':
        bot.reply_to(message, "Sub add cancelled.")
        return
    try:
        parts = message.text.split()
        if len(parts) != 2:
            raise ValueError("Incorrect format")
        sub_user_id = int(parts[0].strip())
        days = int(parts[1].strip())
        if sub_user_id <= 0 or days <= 0:
            raise ValueError("User ID/days must be positive")
        current_expiry = user_subscriptions.get(sub_user_id, {}).get('expiry')
        start_date_new_sub = datetime.now()
        if current_expiry and current_expiry > start_date_new_sub:
            start_date_new_sub = current_expiry
        new_expiry = start_date_new_sub + timedelta(days=days)
        save_subscription(sub_user_id, new_expiry)
        bot.reply_to(message, f"✅ Sub for `{sub_user_id}` by {days} days.\nNew expiry: {new_expiry.strftime('%Y-%m-%d')}")
        try:
            bot.send_message(sub_user_id, f"🎉 Sub activated/extended by {days} days! Expires: {new_expiry.strftime('%Y-%m-%d')}.")
        except:
            pass
    except ValueError as e:
        bot.reply_to(message, f"⚠️ Invalid: {e}. Format: `ID days` or /cancel.")
        msg = bot.send_message(message.chat.id, "💳 Enter User ID & days, or /cancel.")
        bot.register_next_step_handler(msg, process_add_subscription_details)
    except Exception as e:
        print(f"Error processing add sub: {e}")
        bot.reply_to(message, "Error.")

def remove_subscription_init_callback(call):
    bot.answer_callback_query(call.id)
    msg = bot.send_message(call.message.chat.id, "💳 Enter User ID to remove sub.\n/cancel to abort.")
    bot.register_next_step_handler(msg, process_remove_subscription_id)

def process_remove_subscription_id(message):
    admin_id_check = message.from_user.id
    if admin_id_check not in admin_ids:
        bot.reply_to(message, "⚠️ Not authorized.")
        return
    if message.text.lower() == '/cancel':
        bot.reply_to(message, "Sub removal cancelled.")
        return
    try:
        sub_user_id_remove = int(message.text.strip())
        if sub_user_id_remove <= 0:
            raise ValueError("ID must be positive")
        if sub_user_id_remove not in user_subscriptions:
            bot.reply_to(message, f"⚠️ User `{sub_user_id_remove}` no active sub.")
            return
        remove_subscription_db(sub_user_id_remove)
        bot.reply_to(message, f"✅ Sub for `{sub_user_id_remove}` removed.")
        try:
            bot.send_message(sub_user_id_remove, "ℹ️ Your subscription removed by admin.")
        except:
            pass
    except ValueError:
        bot.reply_to(message, "⚠️ Invalid ID. Send numerical ID or /cancel.")
        msg = bot.send_message(message.chat.id, "💳 Enter User ID to remove sub from, or /cancel.")
        bot.register_next_step_handler(msg, process_remove_subscription_id)
    except Exception as e:
        print(f"Error processing remove sub: {e}")
        bot.reply_to(message, "Error.")

def check_subscription_init_callback(call):
    bot.answer_callback_query(call.id)
    msg = bot.send_message(call.message.chat.id, "💳 Enter User ID to check sub.\n/cancel to abort.")
    bot.register_next_step_handler(msg, process_check_subscription_id)

def process_check_subscription_id(message):
    admin_id_check = message.from_user.id
    if admin_id_check not in admin_ids:
        bot.reply_to(message, "⚠️ Not authorized.")
        return
    if message.text.lower() == '/cancel':
        bot.reply_to(message, "Sub check cancelled.")
        return
    try:
        sub_user_id_check = int(message.text.strip())
        if sub_user_id_check <= 0:
            raise ValueError("ID must be positive")
        if sub_user_id_check in user_subscriptions:
            expiry_dt = user_subscriptions[sub_user_id_check].get('expiry')
            if expiry_dt:
                if expiry_dt > datetime.now():
                    days_left = (expiry_dt - datetime.now()).days
                    bot.reply_to(message, f"✅ User `{sub_user_id_check}` active sub.\nExpires: {expiry_dt.strftime('%Y-%m-%d %H:%M:%S')} ({days_left} days left).")
                else:
                    bot.reply_to(message, f"⚠️ User `{sub_user_id_check}` expired sub (On: {expiry_dt.strftime('%Y-%m-%d %H:%M:%S')}).")
                    remove_subscription_db(sub_user_id_check)
            else:
                bot.reply_to(message, f"⚠️ User `{sub_user_id_check}` in sub list, but expiry missing.")
        else:
            bot.reply_to(message, f"ℹ️ User `{sub_user_id_check}` no active sub record.")
    except ValueError:
        bot.reply_to(message, "⚠️ Invalid ID. Send numerical ID or /cancel.")
        msg = bot.send_message(message.chat.id, "💳 Enter User ID to check, or /cancel.")
        bot.register_next_step_handler(msg, process_check_subscription_id)
    except Exception as e:
        print(f"Error processing check sub: {e}")
        bot.reply_to(message, "Error.")

def user_management_callback(call):
    bot.answer_callback_query(call.id)
    try:
        bot.edit_message_text("👥 User Management\nSelect action:", call.message.chat.id,
                              call.message.message_id, reply_markup=create_user_management_menu())
    except:
        pass

def ban_user_callback(call):
    bot.answer_callback_query(call.id)
    msg = bot.send_message(call.message.chat.id, "🚫 Enter User ID to ban and reason (e.g., `12345678 Spamming`)\n/cancel to cancel")
    bot.register_next_step_handler(msg, process_ban_user)

def process_ban_user(message):
    admin_id = message.from_user.id
    if admin_id not in admin_ids:
        bot.reply_to(message, "⚠️ Not authorized.")
        return
    if message.text.lower() == '/cancel':
        bot.reply_to(message, "❌ Ban cancelled.")
        return
    try:
        parts = message.text.split()
        if len(parts) < 2:
            bot.reply_to(message, "⚠️ Format: `user_id reason`\nExample: `12345678 Spamming`")
            return
        user_id = int(parts[0])
        reason = ' '.join(parts[1:])
        if user_id <= 0:
            raise ValueError("ID must be positive")
        if user_id == OWNER_ID:
            bot.reply_to(message, "⚠️ Cannot ban owner.")
            return
        if user_id in admin_ids:
            bot.reply_to(message, "⚠️ Cannot ban admin.")
            return
        if ban_user_db(user_id, reason, admin_id):
            bot.reply_to(message, f"✅ User `{user_id}` banned.\nReason: {reason}")
            for file_name, _ in user_files.get(user_id, []):
                script_key = f"{user_id}_{file_name}"
                if script_key in bot_scripts:
                    kill_process_tree(bot_scripts[script_key])
                    del bot_scripts[script_key]
            try:
                bot.send_message(user_id, f"🚫 You have been banned from using this bot.\nReason: {reason}")
            except:
                pass
        else:
            bot.reply_to(message, "❌ Failed to ban user.")
    except ValueError:
        bot.reply_to(message, "⚠️ Invalid user ID. Must be a number.")
    except Exception as e:
        print(f"Error banning user: {e}")
        bot.reply_to(message, f"❌ Error: {str(e)}")

def unban_user_callback(call):
    bot.answer_callback_query(call.id)
    msg = bot.send_message(call.message.chat.id, "✅ Enter User ID to unban\n/cancel to cancel")
    bot.register_next_step_handler(msg, process_unban_user)

def process_unban_user(message):
    admin_id = message.from_user.id
    if admin_id not in admin_ids:
        bot.reply_to(message, "⚠️ Not authorized.")
        return
    if message.text.lower() == '/cancel':
        bot.reply_to(message, "❌ Unban cancelled.")
        return
    try:
        user_id = int(message.text.strip())
        if user_id <= 0:
            raise ValueError("ID must be positive")
        if user_id not in banned_users:
            bot.reply_to(message, f"ℹ️ User `{user_id}` is not banned.")
            return
        if unban_user_db(user_id):
            bot.reply_to(message, f"✅ User `{user_id}` unbanned.")
            try:
                bot.send_message(user_id, "✅ Your ban has been lifted. You can now use the bot again.")
            except:
                pass
        else:
            bot.reply_to(message, "❌ Failed to unban user.")
    except ValueError:
        bot.reply_to(message, "⚠️ Invalid user ID. Must be a number.")
    except Exception as e:
        print(f"Error unbanning user: {e}")
        bot.reply_to(message, f"❌ Error: {str(e)}")

def user_info_callback(call):
    bot.answer_callback_query(call.id)
    msg = bot.send_message(call.message.chat.id, "👤 Enter User ID to get info\n/cancel to cancel")
    bot.register_next_step_handler(msg, process_user_info)

def process_user_info(message):
    admin_id = message.from_user.id
    if admin_id not in admin_ids:
        bot.reply_to(message, "⚠️ Not authorized.")
        return
    if message.text.lower() == '/cancel':
        bot.reply_to(message, "❌ Info request cancelled.")
        return
    try:
        user_id = int(message.text.strip())
        if user_id <= 0:
            raise ValueError("ID must be positive")
        user = bot.get_chat(user_id)
        user_name = user.first_name or "Unknown"
        username = f"@{user.username}" if user.username else "No username"
        file_count = get_user_file_count(user_id)
        file_limit = get_user_file_limit(user_id)
        limit_str = str(file_limit) if file_limit != float('inf') else "Unlimited"
        running_scripts = sum(1 for f, _ in user_files.get(user_id, []) if is_bot_running(user_id, f[0]))
        ref_stats = get_referral_stats(user_id)
        ref_count = ref_stats.get('count', 0)
        ref_extra = ref_stats.get('extra_limit', 0)
        if user_id == OWNER_ID:
            status = "👑 Owner"
        elif user_id in admin_ids:
            status = "🛡️ Admin"
        elif user_id in banned_users:
            status = "🚫 Banned"
        elif user_id in user_subscriptions:
            expiry = user_subscriptions[user_id].get('expiry')
            if expiry and expiry > datetime.now():
                days_left = (expiry - datetime.now()).days
                status = f"⭐ Premium ({days_left} days left)"
            else:
                status = "🆓 Free (Expired)"
        else:
            status = "🆓 Free"
        info_msg = f"""
👤 **User Information**

📛 **Name:** {user_name}
🆔 **ID:** `{user_id}`
📌 **Username:** {username}
🔰 **Status:** {status}

📁 **Files:** {file_count} / {limit_str}
🤖 **Running Scripts:** {running_scripts}
📊 **Active:** {'Yes' if user_id in active_users else 'No'}
🚫 **Banned:** {'Yes' if user_id in banned_users else 'No'}

🔗 **Referral Stats:**
┣ 👥 Referrals: {ref_count}
┗ 📈 Extra Limit: +{ref_extra}

📅 **Joined:** {datetime.now().strftime('%Y-%m-%d')}
"""
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("🚫 Ban", callback_data=f'ban_{user_id}'),
            types.InlineKeyboardButton("✅ Unban", callback_data=f'unban_{user_id}')
        )
        markup.add(
            types.InlineKeyboardButton("📁 Files", callback_data=f'user_files_{user_id}'),
            types.InlineKeyboardButton("🔙 Back", callback_data='back_to_main')
        )
        bot.reply_to(message, info_msg, reply_markup=markup, parse_mode='Markdown')
    except:
        bot.reply_to(message, "❌ Invalid user ID or user not found.")

def all_users_callback(call):
    bot.answer_callback_query(call.id)
    try:
        if not active_users:
            bot.edit_message_text("👥 No active users yet.", call.message.chat.id, call.message.message_id)
            return
        users_list = list(active_users)
        chunk_size = 20
        total_pages = (len(users_list) + chunk_size - 1) // chunk_size
        display_users_list(call.message.chat.id, call.message.message_id, users_list, 0, total_pages, chunk_size)
    except Exception as e:
        print(f"Error displaying all users: {e}")
        bot.answer_callback_query(call.id, "Error displaying users.", show_alert=True)

def display_users_list(chat_id, message_id, users_list, page, total_pages, chunk_size):
    start_idx = page * chunk_size
    end_idx = min(start_idx + chunk_size, len(users_list))
    user_chunk = users_list[start_idx:end_idx]
    message_text = f"👥 **Active Users** (Page {page + 1}/{total_pages})\n\n"
    for i, user_id in enumerate(user_chunk, start=start_idx + 1):
        status = ""
        if user_id == OWNER_ID:
            status = "👑"
        elif user_id in admin_ids:
            status = "🛡️"
        elif user_id in banned_users:
            status = "🚫"
        elif user_id in user_subscriptions and user_subscriptions[user_id].get('expiry', datetime.min) > datetime.now():
            status = "⭐"
        else:
            status = "🆓"
        message_text += f"{i}. `{user_id}` {status}\n"
    markup = types.InlineKeyboardMarkup(row_width=3)
    if total_pages > 1:
        page_buttons = []
        if page > 0:
            page_buttons.append(types.InlineKeyboardButton("⬅️ Previous", callback_data=f"users_page_{page-1}"))
        page_buttons.append(types.InlineKeyboardButton(f"{page+1}/{total_pages}", callback_data="noop"))
        if page < total_pages - 1:
            page_buttons.append(types.InlineKeyboardButton("Next ➡️", callback_data=f"users_page_{page+1}"))
        markup.row(*page_buttons)
    markup.row(types.InlineKeyboardButton("🔙 Back to User Management", callback_data='user_management'))
    try:
        bot.edit_message_text(message_text, chat_id, message_id, reply_markup=markup, parse_mode='Markdown')
    except:
        pass

@bot.callback_query_handler(func=lambda call: call.data.startswith('users_page_'))
def handle_users_page(call):
    if call.from_user.id not in admin_ids:
        bot.answer_callback_query(call.id, "⚠️ Admin only.", show_alert=True)
        return
    try:
        page = int(call.data.split('_')[2])
        users_list = list(active_users)
        chunk_size = 20
        total_pages = (len(users_list) + chunk_size - 1) // chunk_size
        if 0 <= page < total_pages:
            bot.answer_callback_query(call.id)
            display_users_list(call.message.chat.id, call.message.message_id, users_list, page, total_pages, chunk_size)
    except Exception as e:
        print(f"Error handling users page: {e}")
        bot.answer_callback_query(call.id, "Error.", show_alert=True)

def set_user_limit_callback(call):
    bot.answer_callback_query(call.id)
    msg = bot.send_message(call.message.chat.id, "🔧 Enter User ID and new limit (e.g., `12345678 50`)\n/cancel to cancel")
    bot.register_next_step_handler(msg, process_set_user_limit)

def process_set_user_limit(message):
    admin_id = message.from_user.id
    if admin_id not in admin_ids:
        bot.reply_to(message, "⚠️ Not authorized.")
        return
    if message.text.lower() == '/cancel':
        bot.reply_to(message, "❌ Limit set cancelled.")
        return
    try:
        parts = message.text.split()
        if len(parts) != 2:
            raise ValueError("Format: user_id limit")
        user_id = int(parts[0])
        limit = int(parts[1])
        if user_id <= 0 or limit <= 0:
            raise ValueError("ID and limit must be positive")
        if set_user_limit_db(user_id, limit, admin_id):
            bot.reply_to(message, f"✅ Set file limit {limit} for user `{user_id}`")
            try:
                bot.send_message(user_id, f"⚙️ Your file upload limit has been set to {limit}")
            except:
                pass
        else:
            bot.reply_to(message, "❌ Failed to set limit.")
    except ValueError as e:
        bot.reply_to(message, f"⚠️ Invalid input: {e}\nFormat: `user_id limit`")
    except Exception as e:
        print(f"Error setting user limit: {e}")
        bot.reply_to(message, f"❌ Error: {str(e)}")

def remove_user_limit_callback(call):
    bot.answer_callback_query(call.id)
    msg = bot.send_message(call.message.chat.id, "🗑️ Enter User ID to remove custom limit\n/cancel to cancel")
    bot.register_next_step_handler(msg, process_remove_user_limit)

def process_remove_user_limit(message):
    admin_id = message.from_user.id
    if admin_id not in admin_ids:
        bot.reply_to(message, "⚠️ Not authorized.")
        return
    if message.text.lower() == '/cancel':
        bot.reply_to(message, "❌ Limit removal cancelled.")
        return
    try:
        user_id = int(message.text.strip())
        if user_id <= 0:
            raise ValueError("ID must be positive")
        if user_id not in user_limits:
            bot.reply_to(message, f"ℹ️ User `{user_id}` has no custom limit.")
            return
        if remove_user_limit_db(user_id):
            bot.reply_to(message, f"✅ Removed custom limit for user `{user_id}`")
            try:
                bot.send_message(user_id, "⚙️ Your custom file limit has been removed")
            except:
                pass
        else:
            bot.reply_to(message, "❌ Failed to remove limit.")
    except ValueError:
        bot.reply_to(message, "⚠️ Invalid user ID. Must be a number.")
    except Exception as e:
        print(f"Error removing user limit: {e}")
        bot.reply_to(message, f"❌ Error: {str(e)}")

def admin_settings_callback(call):
    bot.answer_callback_query(call.id)
    try:
        bot.edit_message_text("⚙️ Admin Settings\nSelect action:", call.message.chat.id,
                              call.message.message_id, reply_markup=create_admin_settings_menu())
    except:
        pass

def system_info_callback(call):
    bot.answer_callback_query(call.id)
    try:
        import platform
        info_parts = []
        info_parts.append("🤖 **Bot Information:**")
        info_parts.append(f"• Python: {platform.python_version()}")
        info_parts.append(f"• Platform: {platform.platform()}")
        info_parts.append(f"• Uptime: {time.strftime('%H:%M:%S', time.gmtime(time.time() - psutil.boot_time()))}")
        info_parts.append("\n💻 **System Information:**")
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            info_parts.append(f"• CPU Usage: {cpu_percent}%")
            info_parts.append(f"• Memory: {memory.percent}% used ({memory.used//1024//1024}MB/{memory.total//1024//1024}MB)")
            info_parts.append(f"• Disk: {disk.percent}% used ({disk.used//1024//1024}MB/{disk.total//1024//1024}MB)")
        except:
            pass
        info_parts.append("\n📊 **Bot Statistics:**")
        info_parts.append(f"• Active Users: {len(active_users)}")
        info_parts.append(f"• Running Scripts: {len(bot_scripts)}")
        info_parts.append(f"• Total Files: {sum(len(f) for f in user_files.values())}")
        info_parts.append(f"• Bot Status: {'🔒 Locked' if bot_locked else '🔓 Unlocked'}")
        info_text = "\n".join(info_parts)
        bot.edit_message_text(info_text, call.message.chat.id, call.message.message_id,
                              reply_markup=create_admin_settings_menu(), parse_mode='Markdown')
    except Exception as e:
        print(f"Error showing system info: {e}")
        bot.answer_callback_query(call.id, "Error showing system info.", show_alert=True)

def bot_performance_callback(call):
    bot.answer_callback_query(call.id)
    try:
        performance_parts = []
        running_scripts = len(bot_scripts)
        total_files = sum(len(f) for f in user_files.values())
        performance_parts.append("📈 **Bot Performance Metrics:**")
        performance_parts.append(f"• Running Scripts: {running_scripts}")
        performance_parts.append(f"• Total Scripts: {total_files}")
        if total_files > 0:
            performance_parts.append(f"• Uptime Ratio: {running_scripts}/{total_files} ({running_scripts/total_files*100:.1f}%)")
        try:
            bot_process = psutil.Process()
            memory_usage = bot_process.memory_info().rss / 1024 / 1024
            cpu_usage = bot_process.cpu_percent(interval=0.5)
            performance_parts.append(f"\n💾 **Resource Usage:**")
            performance_parts.append(f"• Memory: {memory_usage:.1f} MB")
            performance_parts.append(f"• CPU: {cpu_usage:.1f}%")
        except:
            pass
        performance_parts.append(f"\n🗄️ **Database:**")
        performance_parts.append(f"• Active Users: {len(active_users)}")
        performance_parts.append(f"• Subscriptions: {len(user_subscriptions)}")
        performance_parts.append(f"• Banned Users: {len(banned_users)}")
        performance_parts.append(f"• Custom Limits: {len(user_limits)}")
        performance_text = "\n".join(performance_parts)
        bot.edit_message_text(performance_text, call.message.chat.id, call.message.message_id,
                              reply_markup=create_admin_settings_menu(), parse_mode='Markdown')
    except Exception as e:
        print(f"Error showing performance: {e}")
        bot.answer_callback_query(call.id, "Error showing performance.", show_alert=True)

def cleanup_files_callback(call):
    bot.answer_callback_query(call.id, "🧹 Cleaning up temporary files...")
    try:
        cleaned_dirs = 0
        cleaned_files = 0
        for user_dir in os.listdir(UPLOAD_BOTS_DIR):
            user_path = os.path.join(UPLOAD_BOTS_DIR, user_dir)
            if os.path.isdir(user_path):
                if not os.listdir(user_path):
                    try:
                        os.rmdir(user_path)
                        cleaned_dirs += 1
                    except:
                        pass
                else:
                    for file_name in os.listdir(user_path):
                        if file_name.endswith('.log'):
                            file_path = os.path.join(user_path, file_name)
                            try:
                                file_age = time.time() - os.path.getmtime(file_path)
                                if file_age > 7 * 24 * 3600:
                                    os.remove(file_path)
                                    cleaned_files += 1
                            except:
                                pass
        result_msg = f"🧹 **Cleanup Complete:**\n• Removed empty directories: {cleaned_dirs}\n• Cleared old log files: {cleaned_files}"
        bot.edit_message_text(result_msg, call.message.chat.id, call.message.message_id,
                              reply_markup=create_admin_settings_menu(), parse_mode='Markdown')
    except Exception as e:
        print(f"Error during cleanup: {e}")
        bot.edit_message_text(f"❌ Cleanup error: {str(e)}", call.message.chat.id, call.message.message_id)

def install_logs_callback(call):
    bot.answer_callback_query(call.id)
    try:
        conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False, timeout=30)
        c = conn.cursor()
        c.execute('SELECT user_id, module_name, package_name, status, install_date FROM install_logs ORDER BY install_date DESC LIMIT 20')
        logs = c.fetchall()
        conn.close()
        if not logs:
            bot.edit_message_text("📋 **No installation logs found**", call.message.chat.id,
                                  call.message.message_id, reply_markup=create_admin_settings_menu())
            return
        log_text = "📋 **Recent Installation Logs (Last 20):**\n\n"
        for user_id, module_name, package_name, status, install_date in logs:
            status_icon = "✅" if status == "success" else "❌" if status == "failed" else "⚠️"
            log_text += f"{status_icon} `{user_id}`: {module_name} -> {package_name}\n"
            log_text += f"   📅 {install_date[:19]}\n\n"
        bot.edit_message_text(log_text, call.message.chat.id, call.message.message_id,
                              reply_markup=create_admin_settings_menu(), parse_mode='Markdown')
    except Exception as e:
        print(f"Error showing install logs: {e}")
        bot.answer_callback_query(call.id, "Error showing logs.", show_alert=True)

def admin_install_callback(call):
    bot.answer_callback_query(call.id)
    _logic_admin_install(call.message)

def _logic_admin_install(message):
    if message.from_user.id not in admin_ids:
        bot.reply_to(message, "⚠️ Admin permissions required.")
        return
    msg = bot.reply_to(message, "🛠️ Admin Module Installation\nSend user ID and module name (e.g., `12345678 requests`)\n/cancel to cancel")
    bot.register_next_step_handler(msg, process_admin_install)

def process_admin_install(message):
    admin_id = message.from_user.id
    if admin_id not in admin_ids:
        bot.reply_to(message, "⚠️ Not authorized.")
        return
    if message.text.lower() == '/cancel':
        bot.reply_to(message, "❌ Installation cancelled.")
        return
    try:
        parts = message.text.split()
        if len(parts) < 2:
            bot.reply_to(message, "⚠️ Format: `user_id module_name`\nExample: `12345678 requests`")
            return
        user_id = int(parts[0])
        module_name = ' '.join(parts[1:])
        if module_name.lower().startswith('npm:'):
            module_name = module_name[4:].strip()
            user_folder = get_user_folder(user_id)
            success, log = attempt_install_npm(module_name, user_folder, message, manual_request=True)
        else:
            success, log = attempt_install_pip(module_name, message, manual_request=True)
        if success:
            log_action(admin_id, f"Installed module {module_name} for user {user_id}", log, 'admin')
            try:
                bot.send_message(user_id, f"📦 Admin installed module `{module_name}` for you.")
            except:
                pass
    except ValueError:
        bot.reply_to(message, "⚠️ Invalid user ID. Must be a number.")
    except Exception as e:
        print(f"Error in admin install: {e}")
        bot.reply_to(message, f"❌ Error: {str(e)}")

def manage_keys_callback(call):
    bot.answer_callback_query(call.id)
    try:
        bot.edit_message_text("🔑 **Key Management**\n\nGenerate and manage premium keys.",
                              call.message.chat.id, call.message.message_id,
                              reply_markup=create_key_management_menu(), parse_mode='Markdown')
    except:
        pass

def list_keys_admin_callback(call):
    bot.answer_callback_query(call.id)
    conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False, timeout=30)
    c = conn.cursor()
    c.execute('''SELECT key_id, key_code, limit_value, expiry_date, is_used, used_by, created_date
                 FROM permanent_keys ORDER BY key_id DESC LIMIT 20''')
    keys = c.fetchall()
    conn.close()
    if not keys:
        bot.edit_message_text("📭 No keys generated yet.", call.message.chat.id, call.message.message_id)
        return
    lines = ["🔑 **ʀᴇᴄᴇɴᴛ ᴋᴇʏs (ʟᴀsᴛ 20):**\n"]
    for k in keys:
        key_id, key_code, limit_value, expiry_str, used, used_by, created_at = k
        used_icon = "✅ ᴜsᴇᴅ" if used else "🟢 ᴀᴄᴛɪᴠᴇ"
        used_by_info = f" (ʙʏ `{used_by}`)" if used else ""
        if expiry_str:
            expiry = datetime.fromisoformat(expiry_str)
            expiry_display = f"🟡 ᴇxᴘɪʀᴇs {expiry.strftime('%Y-%m-%d')}"
            if expiry < datetime.now():
                expiry_display = "🔴 ᴇxᴘɪʀᴇᴅ"
        else:
            expiry_display = "🌟 ʟɪғᴇᴛɪᴍᴇ"
        lines.append(
            f"┣ `{key_code}`\n"
            f"┣ 📦 ʟɪᴍɪᴛ: {limit_value}\n"
            f"┣ {used_icon}{used_by_info}\n"
            f"┣ {expiry_display}\n"
        )
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🔙 Back", callback_data='manage_keys'))
    try:
        bot.edit_message_text("\n".join(lines), call.message.chat.id, call.message.message_id,
                              reply_markup=markup, parse_mode='Markdown')
    except:
        pass

def gen_key_admin_callback(call):
    bot.answer_callback_query(call.id)
    msg = bot.send_message(call.message.chat.id, "🎫 Enter limit and duration (e.g., `10 30d` or `15 lifetime`)\n/cancel to cancel")
    bot.register_next_step_handler(msg, process_gen_key_admin)

def process_gen_key_admin(message):
    admin_id = message.from_user.id
    if admin_id not in admin_ids:
        bot.reply_to(message, "⚠️ Not authorized.")
        return
    if message.text.lower() == '/cancel':
        bot.reply_to(message, "❌ Key generation cancelled.")
        return
    try:
        parts = message.text.split()
        if len(parts) < 1:
            bot.reply_to(message, "⚠️ Usage: <limit> [duration]")
            return
        limit_value = int(parts[0])
        if limit_value <= 0:
            raise ValueError("Limit must be positive")
        if len(parts) >= 2:
            duration = parse_duration(parts[1])
        else:
            duration = timedelta(days=30)
        key_code = generate_key(limit_value, duration, admin_id)
        if not key_code:
            bot.reply_to(message, "❌ Failed to generate key.")
            return
        if duration is None:
            validity = "🌟 Lifetime"
        else:
            total_seconds = int(duration.total_seconds())
            days = total_seconds // 86400
            hours = (total_seconds % 86400) // 3600
            minutes = (total_seconds % 3600) // 60
            if days > 0:
                validity = f"⏳ {days}d"
                if hours: validity += f" {hours}h"
            elif hours > 0:
                validity = f"⏳ {hours}h"
                if minutes: validity += f" {minutes}m"
            else:
                validity = f"⏳ {minutes}m" if minutes > 0 else "⏳ (instant)"
        rich_msg = (
            f"🎉 **ᴋᴇʏ ɢᴇɴᴇʀᴀᴛᴇᴅ sᴜᴄᴄᴇssғᴜʟʟʏ!**\n\n"
            f"🔑 **ᴋᴇʏ ᴅᴇᴛᴀɪʟs**\n"
            f"┣ 🎫 ᴀᴄᴄᴇss ᴋᴇʏ: `{key_code}`\n"
            f"┣ 📦 ʙᴏᴛ ʟɪᴍɪᴛ: **{limit_value}**\n"
            f"┣ ⏳ ᴠᴀʟɪᴅɪᴛʏ: {validity}\n"
            f"┣ 📝 sᴛᴀᴛᴜs: ᴏɴᴇ-ᴛɪᴍᴇ ᴜsᴇ\n"
            f"┣ 📅 ᴄʀᴇᴀᴛᴇᴅ: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            f"📤 **ᴅɪsᴛʀɪʙᴜᴛɪᴏɴ**\n"
            f"sʜᴀʀᴇ ᴛʜɪs ᴋᴇʏ ᴡɪᴛʜ ʏᴏᴜʀ ᴜsᴇʀ!"
        )
        bot.reply_to(message, rich_msg, parse_mode='Markdown')
    except ValueError as e:
        bot.reply_to(message, f"⚠️ Error: {e}")
    except Exception as e:
        print(f"Error generating key: {e}")
        bot.reply_to(message, f"❌ Error: {str(e)}")

def manage_mandatory_channels_callback(call):
    bot.answer_callback_query(call.id)
    try:
        bot.edit_message_text("📢 Manage Mandatory Channels\nChoose desired action:",
                              call.message.chat.id, call.message.message_id,
                              reply_markup=create_mandatory_channels_menu())
    except:
        pass

def add_mandatory_channel_callback(call):
    bot.answer_callback_query(call.id)
    msg = bot.send_message(call.message.chat.id, "📢 Send channel ID or username (example: @channel_username or -1001234567890)\n/cancel to cancel")
    bot.register_next_step_handler(msg, process_add_channel)

def process_add_channel(message):
    admin_id = message.from_user.id
    if admin_id not in admin_ids:
        bot.reply_to(message, "⚠️ Not authorized.")
        return
    if message.text and message.text.lower() == '/cancel':
        bot.reply_to(message, "❌ Channel addition cancelled.")
        return
    channel_identifier = message.text.strip()
    try:
        chat = bot.get_chat(channel_identifier)
        channel_id = str(chat.id)
        channel_username = f"@{chat.username}" if chat.username else ""
        channel_name = chat.title
        try:
            bot_member = bot.get_chat_member(channel_id, bot.get_me().id)
            if bot_member.status not in ['administrator', 'creator']:
                bot.reply_to(message, f"❌ Bot is not admin in the channel!")
                return
        except:
            bot.reply_to(message, f"❌ Bot cannot access the channel!")
            return
        if save_mandatory_channel(channel_id, channel_username, channel_name, admin_id):
            bot.reply_to(message, f"✅ Mandatory channel added:\n**{channel_name}**\n{channel_username or channel_id}")
        else:
            bot.reply_to(message, "❌ Failed to add channel. Try again.")
    except Exception as e:
        print(f"Error adding channel: {e}")
        bot.reply_to(message, f"❌ Error adding channel: {str(e)}")

def remove_mandatory_channel_callback(call):
    if not mandatory_channels:
        bot.answer_callback_query(call.id, "❌ No mandatory channels.", show_alert=True)
        return
    bot.answer_callback_query(call.id)
    markup = types.InlineKeyboardMarkup()
    for channel_id, channel_info in mandatory_channels.items():
        channel_name = channel_info.get('name', 'Unknown')
        button_text = f"🗑️ {channel_name}"
        markup.add(types.InlineKeyboardButton(button_text, callback_data=f'remove_channel_{channel_id}'))
    markup.add(types.InlineKeyboardButton("🔙 Back", callback_data='manage_mandatory_channels'))
    try:
        bot.edit_message_text("📢 Choose channel to delete:",
                              call.message.chat.id, call.message.message_id,
                              reply_markup=markup)
    except:
        pass

def list_mandatory_channels_callback(call):
    bot.answer_callback_query(call.id)
    if not mandatory_channels:
        message_text = "📢 **No mandatory channels currently**"
    else:
        message_text = "📢 **Mandatory Channels:**\n\n"
        for channel_id, channel_info in mandatory_channels.items():
            channel_name = channel_info.get('name', 'Unknown')
            channel_username = channel_info.get('username', 'No username')
            message_text += f"• **{channel_name}**\n  {channel_username or channel_id}\n\n"
    try:
        bot.edit_message_text(message_text, call.message.chat.id, call.message.message_id,
                              reply_markup=create_mandatory_channels_menu(), parse_mode='Markdown')
    except:
        pass

@bot.callback_query_handler(func=lambda call: call.data.startswith('remove_channel_'))
def process_remove_channel(call):
    channel_id = call.data.replace('remove_channel_', '')
    if channel_id in mandatory_channels:
        channel_name = mandatory_channels[channel_id].get('name', 'Unknown')
        if remove_mandatory_channel_db(channel_id):
            bot.answer_callback_query(call.id, f"✅ Channel deleted: {channel_name}")
            try:
                bot.edit_message_text(f"✅ Mandatory channel deleted: **{channel_name}**",
                                      call.message.chat.id, call.message.message_id,
                                      reply_markup=create_mandatory_channels_menu(), parse_mode='Markdown')
            except:
                pass
        else:
            bot.answer_callback_query(call.id, "❌ Failed to delete channel.", show_alert=True)
    else:
        bot.answer_callback_query(call.id, "❌ Channel not found.", show_alert=True)

def check_subscription_status_callback(call):
    user_id = call.from_user.id
    is_subscribed, not_joined = check_mandatory_subscription(user_id)
    if is_subscribed or user_id in admin_ids:
        bot.answer_callback_query(call.id, "✅ You are subscribed to all required channels!", show_alert=True)
        command_send_welcome(call.message)
    else:
        bot.answer_callback_query(call.id, "❌ You haven't joined all required channels yet!", show_alert=True)
        subscription_message, markup = create_subscription_check_message(not_joined)
        try:
            bot.edit_message_text(subscription_message, call.message.chat.id,
                                  call.message.message_id, reply_markup=markup, parse_mode='Markdown')
        except:
            pass

def cleanup():
    print("Shutdown. Cleaning up processes...")
    script_keys_to_stop = list(bot_scripts.keys())
    if not script_keys_to_stop:
        print("No scripts running. Exiting.")
        return
    print(f"Stopping {len(script_keys_to_stop)} scripts...")
    for key in script_keys_to_stop:
        if key in bot_scripts:
            print(f"Stopping: {key}")
            kill_process_tree(bot_scripts[key])
        else:
            print(f"Script {key} already removed.")
    print("Cleanup finished.")

atexit.register(cleanup)

if __name__ == '__main__':
    keep_alive()
    print("🚀 Starting polling...")
    while True:
        try:
            bot.infinity_polling(logger_level=logging.INFO, timeout=60, long_polling_timeout=30)
        except requests.exceptions.ReadTimeout:
            print("Polling ReadTimeout. Restarting in 5s...")
            time.sleep(5)
        except requests.exceptions.ConnectionError as ce:
            print(f"Polling ConnectionError: {ce}. Retrying in 15s...")
            time.sleep(15)
        except Exception as e:
            print(f"💥 Unrecoverable polling error: {e}")
            print("Restarting polling in 30s due to critical error...")
            time.sleep(30)
        finally:
            print("Polling attempt finished. Will restart if in loop.")
            time.sleep(1)