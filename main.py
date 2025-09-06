from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import *
import os
import sqlite3
from datetime import datetime, timedelta
import threading
import json
import re
import logging
from linebot.models import QuickReply, QuickReplyButton, MessageAction
from google_sheets_manager import GoogleSheetsManager
# 設定日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# LINE Bot 設定
LINE_CHANNEL_ACCESS_TOKEN = 'A6cqCsl/Yl4ZIFPoWHSRTJf4uliAJhyrZ7zlch7eMbWsaD/UqSboyPH85HhJeF+qp8ZmUDOkR4k1ZwwrFjuPgNxQQcinjdxrXQthccOuDvzDUAtMB53vjs5uqczKQV/noBQ8isK9p2bKKNvm2m8+8wdB04t89/1O/w1cDnyilFU='
LINE_CHANNEL_SECRET = '0c3350712c7747aa2236cefd56e9df8d'

line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

# 管理員設定 - 請將這些改為實際的 LINE User ID
ADMIN_USER_IDS = [
    'U5d77d25a49b2a3a2a21d78314f02dec6',  # 實際的管理員 LINE User ID
    # 'U0987654321fedcba'   # 可以設定多個管理員
]

# 治療室配置
TREATMENT_ROOMS = {
    'pink_101': {'name': '粉色101號', 'type': '粉紅', 'has_camera': False, 'capacity': 1},
    'pink_102': {'name': '粉色102號', 'type': '粉紅', 'has_camera': False, 'capacity': 1},
    'blue_101': {'name': '藍色101號', 'type': '藍色', 'has_camera': True, 'capacity': 1},
    'blue_102': {'name': '藍色102號', 'type': '藍色', 'has_camera': True, 'capacity': 1}
}

# 治療師配置
THERAPISTS = {
    'therapist_liu': {
        'name': '劉伊珊',
        'gender': '女',
        'specialties': ['運動傷害', '脊椎矯正'],
        'fee': 2000,
        'work_schedule': {
            'Monday': ['09:00', '10:00', '11:00', '14:00', '15:00', '16:00'],
            'Tuesday': ['09:00', '10:00', '11:00', '14:00', '15:00', '16:00'],
            'Wednesday': ['09:00', '10:00', '11:00', '14:00', '15:00', '16:00'],
            'Thursday': ['09:00', '10:00', '11:00', '14:00', '15:00', '16:00'],
            'Friday': ['09:00', '10:00', '11:00', '14:00', '15:00', '16:00'],
            'Saturday': ['09:00', '10:00', '11:00', '14:00', '15:00', '16:00'],
            'Sunday': []
        }
    },
    'therapist_yun': {
        'name': '運舒云',
        'gender': '女', 
        'specialties': ['產後復健', '婦女健康'],
        'fee': 2000,
        'work_schedule': {
            'Monday': ['09:00', '10:00', '11:00', '14:00', '15:00', '16:00'],
            'Tuesday': ['14:00', '15:00', '16:00'],
            'Wednesday': ['09:00', '10:00', '11:00', '14:00', '15:00', '16:00'],
            'Thursday': ['14:00', '15:00', '16:00'],
            'Friday': ['14:00', '15:00', '16:00'],
            'Saturday': ['09:00', '10:00', '11:00', '14:00', '15:00', '16:00'],
            'Sunday': []
        }
    },
    'therapist_luo': {
        'name': '羅國峰',
        'gender': '男',
        'specialties': ['骨科復健', '神經復健'],
        'fee': 2000,
        'work_schedule': {
            'Monday': [],
            'Tuesday': ['14:00', '15:00', '16:00'],
            'Wednesday': ['18:00', '19:00', '20:00'],
            'Thursday': ['14:00', '15:00', '16:00'],
            'Friday': ['18:00', '19:00', '20:00'],
            'Saturday': ['14:00', '15:00', '16:00'],
            'Sunday': []
        }
    },
    'therapist_chen': {
        'name': '陳怡汎',
        'gender': '女',
        'specialties': ['運動治療', '徒手治療'],
        'fee': 2000,
        'work_schedule': {
            'Monday': [],
            'Tuesday': ['18:00', '19:00', '20:00'],
            'Wednesday': ['18:00', '19:00', '20:00'],
            'Thursday': ['18:00', '19:00', '20:00'],
            'Friday': ['18:00', '19:00', '20:00'],
            'Saturday': ['18:00', '19:00', '20:00'],
            'Sunday': []
        }
    },
    'therapist_wang': {
        'name': '汪佳禾',
        'gender': '女',
        'specialties': ['物理治療', '復健治療'],
        'fee': 2000,
        'work_schedule': {
            'Monday': [],
            'Tuesday': ['18:00', '19:00', '20:00'],
            'Wednesday': ['18:00', '19:00', '20:00'],
            'Thursday': ['18:00', '19:00', '20:00'],
            'Friday': ['18:00', '19:00', '20:00'],
            'Saturday': ['18:00', '19:00', '20:00'],
            'Sunday': []
        }
    },
    'therapist_zhang': {
        'name': '張雅琳',
        'gender': '女',
        'specialties': ['婦女健康', '產後復健'],
        'fee': 2000,
        'work_schedule': {
            'Monday': [],
            'Tuesday': ['14:00', '15:00', '16:00', '18:00', '19:00', '20:00'],
            'Wednesday': ['14:00', '15:00', '16:00', '18:00', '19:00', '20:00'],
            'Thursday': ['14:00', '15:00', '16:00', '18:00', '19:00', '20:00'],
            'Friday': ['14:00', '15:00', '16:00', '18:00', '19:00', '20:00'],
            'Saturday': ['09:00', '10:00', '11:00', '14:00', '15:00', '16:00'],
            'Sunday': ['09:00', '10:00', '11:00', '14:00', '15:00', '16:00']
        }
    }
}

class DatabaseManager:
    def __init__(self):
        self.db_path = 'clinic.db'
        self.sheets_manager = GoogleSheetsManager()
        self.init_db()
    
    def init_db(self):
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 建立預約表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS appointments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    user_name TEXT,
                    phone TEXT,
                    therapist_id TEXT NOT NULL,
                    room_id TEXT NOT NULL,
                    appointment_date TEXT NOT NULL,
                    appointment_time TEXT NOT NULL,
                    duration INTEGER DEFAULT 60,
                    status TEXT DEFAULT 'confirmed',
                    notes TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    created_by TEXT DEFAULT 'patient'
                )
            ''')
            
            # 建立用戶資料表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id TEXT PRIMARY KEY,
                    name TEXT,
                    phone TEXT,
                    medical_history TEXT,
                    preferences TEXT
                )
            ''')
            
            conn.commit()
            logger.info("資料庫初始化成功")
        except Exception as e:
            logger.error(f"資料庫初始化失敗: {e}")
        finally:
            conn.close()
    
    def save_appointment(self, appointment_data):
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO appointments 
                (user_id, user_name, phone, therapist_id, room_id, appointment_date, appointment_time, notes, created_by)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                appointment_data['user_id'],
                appointment_data['user_name'],
                appointment_data['phone'],
                appointment_data['therapist_id'],
                appointment_data['room_id'],
                appointment_data['date'],
                appointment_data['time'],
                appointment_data['notes'],
                appointment_data.get('created_by', 'patient')
            ))
            
            appointment_id = cursor.lastrowid
            conn.commit()
            logger.info(f"預約已儲存，ID: {appointment_id}")

            sync_success = self.sheets_manager.sync_appointment_to_sheets(
                appointment_data, 
                appointment_id, 
                THERAPISTS, 
                TREATMENT_ROOMS
            )
            if sync_success:
                logger.info(f"預約 #{appointment_id} 已同步到Google Sheets")

            return appointment_id
        except Exception as e:
            logger.error(f"儲存預約失敗: {e}")
            return None
        finally:
            conn.close()
    
    def cancel_appointment(self, appointment_id, user_id=None, is_admin=False):
        """取消預約 - 支援管理員取消任何預約"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            if is_admin:
                # 管理員可以取消任何預約
                cursor.execute('''
                    SELECT * FROM appointments 
                    WHERE id = ? AND status = 'confirmed'
                ''', (appointment_id,))
            else:
                # 一般用戶只能取消自己的預約
                cursor.execute('''
                    SELECT * FROM appointments 
                    WHERE id = ? AND user_id = ? AND status = 'confirmed'
                ''', (appointment_id, user_id))
            
            appointment = cursor.fetchone()
            if not appointment:
                return False, "找不到此預約或您無權限取消此預約"
            
            # 更新預約狀態為已取消
            if is_admin:
                cursor.execute('''
                    UPDATE appointments 
                    SET status = 'cancelled' 
                    WHERE id = ?
                ''', (appointment_id,))
            else:
                cursor.execute('''
                    UPDATE appointments 
                    SET status = 'cancelled' 
                    WHERE id = ? AND user_id = ?
                ''', (appointment_id, user_id))
            
            conn.commit()
            self.sheets_manager.update_appointment_status_in_sheets(appointment_id, 'cancelled')
            
            return True, "預約已成功取消"
            
        except Exception as e:
            logger.error(f"取消預約失敗: {e}")
            return False, f"取消預約時發生錯誤: {e}"
        finally:
            conn.close()
    
    def get_booked_slots(self, date, therapist_id=None):
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            if therapist_id:
                cursor.execute('''
                    SELECT appointment_time, therapist_id, room_id 
                    FROM appointments 
                    WHERE appointment_date = ? AND therapist_id = ? AND status = 'confirmed'
                ''', (date, therapist_id))
            else:
                cursor.execute('''
                    SELECT appointment_time, therapist_id, room_id 
                    FROM appointments 
                    WHERE appointment_date = ? AND status = 'confirmed'
                ''', (date,))
            
            booked_slots = cursor.fetchall()
            return booked_slots
        except Exception as e:
            logger.error(f"查詢已預約時段失敗: {e}")
            return []
        finally:
            conn.close()
    
    def get_all_appointments(self, status=None, date_filter=None, limit=50):
        """獲取所有預約 - 管理員功能"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            query = '''
                SELECT id, user_id, user_name, phone, therapist_id, room_id, 
                       appointment_date, appointment_time, status, notes, created_at, created_by
                FROM appointments 
                WHERE 1=1
            '''
            params = []
            
            if status:
                query += ' AND status = ?'
                params.append(status)
            
            if date_filter:
                query += ' AND appointment_date = ?'
                params.append(date_filter)
            
            query += ' ORDER BY appointment_date DESC, appointment_time DESC LIMIT ?'
            params.append(limit)
            
            cursor.execute(query, params)
            appointments = cursor.fetchall()
            
            # 轉換為字典格式
            result = []
            for apt in appointments:
                result.append({
                    'id': apt[0],
                    'user_id': apt[1],
                    'user_name': apt[2],
                    'phone': apt[3],
                    'therapist_id': apt[4],
                    'room_id': apt[5],
                    'appointment_date': apt[6],
                    'appointment_time': apt[7],
                    'status': apt[8],
                    'notes': apt[9],
                    'created_at': apt[10],
                    'created_by': apt[11]
                })
            
            return result
        except Exception as e:
            logger.error(f"查詢所有預約失敗: {e}")
            return []
        finally:
            conn.close()

class AdminManager:
    def __init__(self, db_manager):
        self.db = db_manager
    
    def is_admin(self, user_id):
        """檢查用戶是否為管理員"""
        return user_id in ADMIN_USER_IDS
    
    def create_admin_menu(self):
        """建立管理員選單"""
        quick_reply = QuickReply(items=[
            QuickReplyButton(action=MessageAction(label="查看今日預約", text="管理員-查看今日預約")),
            QuickReplyButton(action=MessageAction(label="查看所有預約", text="管理員-查看所有預約")),
            QuickReplyButton(action=MessageAction(label="新增預約", text="管理員-新增預約")),
            QuickReplyButton(action=MessageAction(label="治療師排班", text="管理員-治療師排班")),
            QuickReplyButton(action=MessageAction(label="離開管理模式", text="離開管理模式")),
            QuickReplyButton(action=MessageAction(label="查看雲端表格", text="管理員-查看雲端表格")),
            QuickReplyButton(action=MessageAction(label="離開管理模式", text="離開管理模式"))
   
        ])
        return quick_reply
    
    def get_today_appointments(self):
        """取得今日預約 - 修正版"""
        today = datetime.now().strftime('%Y-%m-%d')
        # 修正：查看今日所有狀態的預約，不只是已確認的
        appointments = self.db.get_all_appointments(status=None, date_filter=today)
        return appointments

    def create_appointments_flex(self, appointments, title="預約列表"):
        """建立預約列表的 Flex Message - 增強版"""
        if not appointments:
            return TextSendMessage(text="目前沒有預約記錄。")
        
        contents = []
        confirmed_count = 0
        cancelled_count = 0
        
        for apt in appointments[:10]:  # 限制顯示前10筆
            therapist_name = THERAPISTS.get(apt['therapist_id'], {}).get('name', '未知治療師')
            room_name = TREATMENT_ROOMS.get(apt['room_id'], {}).get('name', '未知房間')
            
            # 統計數量
            if apt['status'] == 'confirmed':
                confirmed_count += 1
            elif apt['status'] == 'cancelled':
                cancelled_count += 1
            
            # 格式化日期
            date_obj = datetime.strptime(apt['appointment_date'], '%Y-%m-%d')
            formatted_date = date_obj.strftime('%m/%d')
            weekday = ['週一', '週二', '週三', '週四', '週五', '週六', '週日'][date_obj.weekday()]
            
            # 根據狀態設定顏色和文字
            if apt['status'] == 'confirmed':
                status_color = "#06C755"
                status_text = "✅ 已確認"
            elif apt['status'] == 'cancelled':
                status_color = "#FF5551"
                status_text = "❌ 已取消"
            else:
                status_color = "#888888"
                status_text = apt['status']
            
            content = {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "box",
                        "layout": "horizontal",
                        "contents": [
                            {
                                "type": "text",
                                "text": f"#{apt['id']}",
                                "size": "sm",
                                "color": "#888888",
                                "flex": 1
                            },
                            {
                                "type": "text",
                                "text": status_text,
                                "size": "sm",
                                "color": status_color,
                                "align": "end",
                                "weight": "bold"
                            }
                        ]
                    },
                    {
                        "type": "text",
                        "text": f"{formatted_date}({weekday}) {apt['appointment_time']}",
                        "size": "md",
                        "weight": "bold",
                        "margin": "sm"
                    },
                    {
                        "type": "box",
                        "layout": "horizontal",
                        "contents": [
                            {
                                "type": "text",
                                "text": f"{apt['user_name']} ({apt['phone']})",
                                "size": "sm",
                                "color": "#666666",
                                "flex": 3
                            }
                        ],
                        "margin": "sm"
                    },
                    {
                        "type": "box",
                        "layout": "horizontal",
                        "contents": [
                            {
                                "type": "text",
                                "text": f"{therapist_name} | {room_name}",
                                "size": "sm",
                                "color": "#666666"
                            }
                        ],
                        "margin": "sm"
                    }
                ],
                "paddingAll": "md",
                "spacing": "sm"
            }
            
            # 如果是已確認的預約，加入取消按鈕
            if apt['status'] == 'confirmed':
                content["contents"].append({
                    "type": "button",
                    "action": {
                        "type": "postback",
                        "label": "取消此預約",
                        "data": f"action=admin_cancel&appointment_id={apt['id']}"
                    },
                    "style": "secondary",
                    "height": "sm",
                    "margin": "md"
                })
            
            contents.append(content)
            
            # 加入分隔線
            if apt != appointments[-1] and len(contents) < 20:
                contents.append({
                    "type": "separator",
                    "margin": "md"
                })
        
        # 建立統計摘要
        summary_text = f"共 {len(appointments)} 筆"
        if confirmed_count > 0 or cancelled_count > 0:
            summary_text += f" (確認: {confirmed_count}, 取消: {cancelled_count})"
        
        flex_message = FlexSendMessage(
            alt_text=title,
            contents={
                "type": "bubble",
                "header": {
                    "type": "box",
                    "layout": "vertical",
                    "contents": [
                        {
                            "type": "text",
                            "text": title,
                            "weight": "bold",
                            "size": "lg",
                            "color": "#ffffff"
                        },
                        {
                            "type": "text",
                            "text": summary_text,
                            "size": "sm",
                            "color": "#ffffff",
                            "margin": "sm"
                        }
                    ],
                    "backgroundColor": "#FF6B35",
                    "paddingAll": "md"
                },
                "body": {
                    "type": "box",
                    "layout": "vertical",
                    "contents": contents,
                    "spacing": "none",
                    "paddingAll": "none"
                }
            }
        )
        
        return flex_message

class ScheduleManager:
    def __init__(self):
        self.db = DatabaseManager()
    
    def find_available_rooms(self, date, time):
        booked_slots = self.db.get_booked_slots(date)
        booked_rooms = [slot[2] for slot in booked_slots if slot[0] == time]
        
        available_rooms = []
        for room_id, room_info in TREATMENT_ROOMS.items():
            if room_id not in booked_rooms:
                available_rooms.append(room_id)
            elif room_info['capacity'] > 1:
                # 檢查多人房間的容量
                room_count = booked_rooms.count(room_id)
                if room_count < room_info['capacity']:
                    available_rooms.append(room_id)
        
        return available_rooms

# 修正 AIAssistant 類，確保所有回應都有適當的 Quick Reply
# 完整的 AIAssistant 類，包含缺少的 handle_admin_commands 方法
# Add this missing method to your AIAssistant class

class AIAssistant:
    def __init__(self):
        self.schedule_manager = ScheduleManager()
        self.db = DatabaseManager()
        self.admin_manager = AdminManager(self.db)
    
    def is_appointment_request(self, message):
        """檢查是否為預約請求 - 修正版，排除管理員指令"""
        # 如果是管理員指令，不當作預約請求
        if message.startswith('管理員') or message == 'admin':
            return False
            
        appointment_keywords = ['預約', '約診', '掛號', '預定', '安排', '看診', '治療時間']
        return any(keyword in message for keyword in appointment_keywords)
    
    def handle_appointment_request(self, message, user_id):
        """處理預約請求 - 修正版本"""
        # 檢查用戶是否已經在預約流程中
        if user_id not in user_states:
            user_states[user_id] = {'stage': 'chat'}
        
        # 如果是新的預約請求，開始時間選擇
        if user_states[user_id]['stage'] == 'chat':
            user_states[user_id]['stage'] = 'select_time'
            
            quick_reply = create_time_period_selection()
            return TextSendMessage(
                text="請選擇您方便的時間：",
                quick_reply=quick_reply
            )
        
        return TextSendMessage(text="請先選擇時間後再進行預約。")
    
    def get_ai_response(self, user_message, user_id):
        # 檢查管理員命令
        if self.admin_manager.is_admin(user_id):
            admin_response = self.handle_admin_commands(user_message, user_id)
            if admin_response:
                return admin_response
        
        # 檢查是否為預約相關請求
        if self.is_appointment_request(user_message):
            return self.handle_appointment_request(user_message, user_id)
        
        # 使用規則回應
        rule_response = self.get_rule_based_response(user_message)
        if rule_response:
            # 確保規則回應也有 Quick Reply
            quick_reply = create_faq_quick_reply()
            return TextSendMessage(text=rule_response, quick_reply=quick_reply)
        
        fallback_text = self.get_fallback_response(user_message)
        quick_reply = create_faq_quick_reply()
        return TextSendMessage(text=fallback_text, quick_reply=quick_reply)
    
    def handle_admin_commands(self, message, user_id):
        """處理管理員指令 - 修正版"""
        if message == "管理員模式" or message == "admin":
            quick_reply = self.admin_manager.create_admin_menu()
            return TextSendMessage(
                text="歡迎進入管理員模式！請選擇要執行的操作：",
                quick_reply=quick_reply
            )
    
        elif message == "管理員-查看今日預約":
            appointments = self.admin_manager.get_today_appointments()
            return self.admin_manager.create_appointments_flex(appointments, "今日預約")
        
        elif message == "管理員-查看所有預約":
            # 修正：移除 status 限制，查看所有預約
            appointments = self.db.get_all_appointments(status=None, limit=30)  # 增加顯示數量
            return self.admin_manager.create_appointments_flex(appointments, "所有預約")
        
        # 新增：分別查看不同狀態的預約
        elif message == "管理員-查看已確認預約":
            appointments = self.db.get_all_appointments(status='confirmed', limit=20)
            return self.admin_manager.create_appointments_flex(appointments, "已確認預約")
        
        elif message == "管理員-查看已取消預約":
            appointments = self.db.get_all_appointments(status='cancelled', limit=20)
            return self.admin_manager.create_appointments_flex(appointments, "已取消預約")
        
        elif message == "管理員-新增預約":
            # 保持原有邏輯...
            if user_id not in user_states:
                user_states[user_id] = {}
            user_states[user_id]['admin_mode'] = True
            user_states[user_id]['stage'] = 'admin_appointment_date'
            
            # 生成日期選項
            dates = []
            for i in range(7):  # 未來一週
                date = datetime.now().date() + timedelta(days=i)
                dates.append(date.strftime('%Y-%m-%d'))
            
            quick_reply_items = []
            for date_str in dates:
                date_obj = datetime.strptime(date_str, '%Y-%m-%d')
                formatted_date = date_obj.strftime('%m/%d')
                weekday = ['週一', '週二', '週三', '週四', '週五', '週六', '週日'][date_obj.weekday()]
                
                quick_reply_items.append(
                    QuickReplyButton(
                        action=MessageAction(
                            label=f"{formatted_date}({weekday})",
                            text=f"管理員選擇日期_{date_str}"
                        )
                    )
                )
            
            quick_reply = QuickReply(items=quick_reply_items)
            return TextSendMessage(
                text="請選擇預約日期：",
                quick_reply=quick_reply
            )
        
        elif message == "管理員-治療師排班":
            return self.get_therapist_schedule_info()
        
        elif message == "離開管理模式":
            if user_id in user_states:
                user_states[user_id]['admin_mode'] = False
                user_states[user_id]['stage'] = 'chat'
            return TextSendMessage(text="已離開管理員模式。")

        elif message == "管理員-查看雲端表格":
            # 提供Google Sheets連結
            sheets_url = f"https://docs.google.com/spreadsheets/d/{self.db.sheets_manager.spreadsheet_id}/edit"
            return TextSendMessage(text=f"Google Sheets 預約記錄表：\n{sheets_url}\n\n您可以在雲端表格中查看所有預約的詳細資料。")
    
        
        return None

    def get_therapist_schedule_info(self):
        """獲取治療師排班資訊 - 更新版本"""
        schedule_text = "治療師排班資訊（每小時時段）：\n\n"
        
        days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        day_names = ['週一', '週二', '週三', '週四', '週五', '週六', '週日']
        
        for i, day in enumerate(days):
            schedule_text += f"{day_names[i]}：\n"
            
            # 按時段分組顯示
            morning_therapists = []
            afternoon_therapists = []
            evening_therapists = []
            
            for therapist_id, therapist_info in THERAPISTS.items():
                times = therapist_info['work_schedule'].get(day, [])
                therapist_name = therapist_info['name']
                
                # 早上時段 (09:00-11:00)
                morning_times = [t for t in times if t in ['09:00', '10:00', '11:00']]
                if morning_times:
                    morning_therapists.append(f"{therapist_name}({','.join(morning_times)})")
                
                # 下午時段 (14:00-16:00)
                afternoon_times = [t for t in times if t in ['14:00', '15:00', '16:00']]
                if afternoon_times:
                    afternoon_therapists.append(f"{therapist_name}({','.join(afternoon_times)})")
                
                # 晚上時段 (18:00-20:00)
                evening_times = [t for t in times if t in ['18:00', '19:00', '20:00']]
                if evening_times:
                    evening_therapists.append(f"{therapist_name}({','.join(evening_times)})")
            
            if morning_therapists:
                schedule_text += f"  早上：{' | '.join(morning_therapists)}\n"
            if afternoon_therapists:
                schedule_text += f"  下午：{' | '.join(afternoon_therapists)}\n"
            if evening_therapists:
                schedule_text += f"  晚上：{' | '.join(evening_therapists)}\n"
            
            if not (morning_therapists or afternoon_therapists or evening_therapists):
                schedule_text += "  休診\n"
            
            schedule_text += "\n"
        
        return TextSendMessage(text=schedule_text)
    
    def get_rule_based_response(self, message):
        """基於規則的回應系統"""
        # 問候 - 這裡是重點修正
        if any(word in message.lower() for word in ['你好', '您好', 'hi', 'hello', 'hey']):
            return "您好，歡迎來到物理治療診所！我可以為您介紹我們的服務、收費或協助預約。請問有什麼需要幫助的嗎？"
        
        # 保險相關
        if '保險' in message:
            return "關於保險理賠：我們是全自費醫療，沒有配合健保。申請理賠需要醫生開立的診斷證明，我們會開立收據。大部分保險公司不給付，部分保險公司會給付六七成，詳細規定請您和保險業務員確認。"
        
        return None
    
    def get_fallback_response(self, message):
        """備用回應"""
        return "感謝您的詢問。我可以為您介紹診所的服務項目、收費標準、預約流程等。如果您想預約治療，請告訴我您的需求，我會為您安排合適的時間。如有其他問題，也歡迎隨時詢問。"
# 修正管理員選單，增加更多選項
def create_admin_menu(self):
    """建立管理員選單 - 增強版"""
    quick_reply = QuickReply(items=[
        QuickReplyButton(action=MessageAction(label="查看今日預約", text="管理員-查看今日預約")),
        QuickReplyButton(action=MessageAction(label="查看所有預約", text="管理員-查看所有預約")),
        QuickReplyButton(action=MessageAction(label="已確認預約", text="管理員-查看已確認預約")),
        QuickReplyButton(action=MessageAction(label="已取消預約", text="管理員-查看已取消預約")),
        QuickReplyButton(action=MessageAction(label="新增預約", text="管理員-新增預約")),
        QuickReplyButton(action=MessageAction(label="治療師排班", text="管理員-治療師排班")),
        QuickReplyButton(action=MessageAction(label="離開管理模式", text="離開管理模式")),
        QuickReplyButton(action=MessageAction(label="查看雲端表格", text="管理員-查看雲端表格")),
        QuickReplyButton(action=MessageAction(label="離開管理模式", text="離開管理模式"))
   
    ])
    return quick_reply

# 修正今日預約查詢邏輯
def get_today_appointments(self):
    """取得今日預約 - 修正版"""
    today = datetime.now().strftime('%Y-%m-%d')
    # 修正：查看今日所有狀態的預約，不只是已確認的
    appointments = self.db.get_all_appointments(status=None, date_filter=today)
    return appointments

# 增強 create_appointments_flex 函數，更好地顯示不同狀態
def create_appointments_flex(self, appointments, title="預約列表"):
    """建立預約列表的 Flex Message - 增強版"""
    if not appointments:
        return TextSendMessage(text="目前沒有預約記錄。")
    
    contents = []
    confirmed_count = 0
    cancelled_count = 0
    
    for apt in appointments[:10]:  # 限制顯示前10筆
        therapist_name = THERAPISTS.get(apt['therapist_id'], {}).get('name', '未知治療師')
        room_name = TREATMENT_ROOMS.get(apt['room_id'], {}).get('name', '未知房間')
        
        # 統計數量
        if apt['status'] == 'confirmed':
            confirmed_count += 1
        elif apt['status'] == 'cancelled':
            cancelled_count += 1
        
        # 格式化日期
        date_obj = datetime.strptime(apt['appointment_date'], '%Y-%m-%d')
        formatted_date = date_obj.strftime('%m/%d')
        weekday = ['週一', '週二', '週三', '週四', '週五', '週六', '週日'][date_obj.weekday()]
        
        # 根據狀態設定顏色和文字
        if apt['status'] == 'confirmed':
            status_color = "#06C755"
            status_text = "✅ 已確認"
        elif apt['status'] == 'cancelled':
            status_color = "#FF5551"
            status_text = "❌ 已取消"
        else:
            status_color = "#888888"
            status_text = apt['status']
        
        content = {
            "type": "box",
            "layout": "vertical",
            "contents": [
                {
                    "type": "box",
                    "layout": "horizontal",
                    "contents": [
                        {
                            "type": "text",
                            "text": f"#{apt['id']}",
                            "size": "sm",
                            "color": "#888888",
                            "flex": 1
                        },
                        {
                            "type": "text",
                            "text": status_text,
                            "size": "sm",
                            "color": status_color,
                            "align": "end",
                            "weight": "bold"
                        }
                    ]
                },
                {
                    "type": "text",
                    "text": f"{formatted_date}({weekday}) {apt['appointment_time']}",
                    "size": "md",
                    "weight": "bold",
                    "margin": "sm"
                },
                {
                    "type": "box",
                    "layout": "horizontal",
                    "contents": [
                        {
                            "type": "text",
                            "text": f"{apt['user_name']} ({apt['phone']})",
                            "size": "sm",
                            "color": "#666666",
                            "flex": 3
                        }
                    ],
                    "margin": "sm"
                },
                {
                    "type": "box",
                    "layout": "horizontal",
                    "contents": [
                        {
                            "type": "text",
                            "text": f"{therapist_name} | {room_name}",
                            "size": "sm",
                            "color": "#666666"
                        }
                    ],
                    "margin": "sm"
                }
            ],
            "paddingAll": "md",
            "spacing": "sm"
        }
        
        # 如果是已確認的預約，加入取消按鈕
        if apt['status'] == 'confirmed':
            content["contents"].append({
                "type": "button",
                "action": {
                    "type": "postback",
                    "label": "取消此預約",
                    "data": f"action=admin_cancel&appointment_id={apt['id']}"
                },
                "style": "secondary",
                "height": "sm",
                "margin": "md"
            })
        
        contents.append(content)
        
        # 加入分隔線
        if apt != appointments[-1] and len(contents) < 20:
            contents.append({
                "type": "separator",
                "margin": "md"
            })
    
    # 建立統計摘要
    summary_text = f"共 {len(appointments)} 筆"
    if confirmed_count > 0 or cancelled_count > 0:
        summary_text += f" (確認: {confirmed_count}, 取消: {cancelled_count})"
    
    flex_message = FlexSendMessage(
        alt_text=title,
        contents={
            "type": "bubble",
            "header": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": title,
                        "weight": "bold",
                        "size": "lg",
                        "color": "#ffffff"
                    },
                    {
                        "type": "text",
                        "text": summary_text,
                        "size": "sm",
                        "color": "#ffffff",
                        "margin": "sm"
                    }
                ],
                "backgroundColor": "#FF6B35",
                "paddingAll": "md"
            },
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": contents,
                "spacing": "none",
                "paddingAll": "none"
            }
        }
    )
    
    return flex_message
    
    def get_therapist_schedule_info(self):
        """獲取治療師排班資訊 - 更新版本"""
        schedule_text = "治療師排班資訊（每小時時段）：\n\n"
        
        days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        day_names = ['週一', '週二', '週三', '週四', '週五', '週六', '週日']
        
        for i, day in enumerate(days):
            schedule_text += f"{day_names[i]}：\n"
            
            # 按時段分組顯示
            morning_therapists = []
            afternoon_therapists = []
            evening_therapists = []
            
            for therapist_id, therapist_info in THERAPISTS.items():
                times = therapist_info['work_schedule'].get(day, [])
                therapist_name = therapist_info['name']
                
                # 早上時段 (09:00-11:00)
                morning_times = [t for t in times if t in ['09:00', '10:00', '11:00']]
                if morning_times:
                    morning_therapists.append(f"{therapist_name}({','.join(morning_times)})")
                
                # 下午時段 (14:00-16:00)
                afternoon_times = [t for t in times if t in ['14:00', '15:00', '16:00']]
                if afternoon_times:
                    afternoon_therapists.append(f"{therapist_name}({','.join(afternoon_times)})")
                
                # 晚上時段 (18:00-20:00)
                evening_times = [t for t in times if t in ['18:00', '19:00', '20:00']]
                if evening_times:
                    evening_therapists.append(f"{therapist_name}({','.join(evening_times)})")
            
            if morning_therapists:
                schedule_text += f"  早上：{' | '.join(morning_therapists)}\n"
            if afternoon_therapists:
                schedule_text += f"  下午：{' | '.join(afternoon_therapists)}\n"
            if evening_therapists:
                schedule_text += f"  晚上：{' | '.join(evening_therapists)}\n"
            
            if not (morning_therapists or afternoon_therapists or evening_therapists):
                schedule_text += "  休診\n"
            
            schedule_text += "\n"
        
        return TextSendMessage(text=schedule_text)
    
    def get_rule_based_response(self, message):
        """基於規則的回應系統"""
        # 問候 - 這裡是重點修正
        if any(word in message.lower() for word in ['你好', '您好', 'hi', 'hello', 'hey']):
            return "您好，歡迎來到物理治療診所！我可以為您介紹我們的服務、收費或協助預約。請問有什麼需要幫助的嗎？"
        
        # 保險相關
        if '保險' in message:
            return "關於保險理賠：我們是全自費醫療，沒有配合健保。申請理賠需要醫生開立的診斷證明，我們會開立收據。大部分保險公司不給付，部分保險公司會給付六七成，詳細規定請您和保險業務員確認。"
        
        return None
    
    def get_fallback_response(self, message):
        """備用回應"""
        return "感謝您的詢問。我可以為您介紹診所的服務項目、收費標準、預約流程等。如果您想預約治療，請告訴我您的需求，我會為您安排合適的時間。如有其他問題，也歡迎隨時詢問。"
    
    def is_appointment_request(self, message):
        appointment_keywords = ['預約', '約診', '掛號', '預定', '安排', '看診', '治療時間']
        return any(keyword in message for keyword in appointment_keywords)

# 修正 handle_message 函數中的邏輯順序
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    try:
        user_id = event.source.user_id
        user_message = event.message.text.strip()
        
        logger.info(f"收到訊息 - 用戶: {user_id}, 內容: {user_message}")
        
        # 初始化用戶狀態
        if user_id not in user_states:
            user_states[user_id] = {'stage': 'chat'}
        
        current_stage = user_states[user_id]['stage']
        reply_message = None  # 初始化回覆訊息
        
        # 處理備用治療師選擇格式
        if user_message.startswith('選擇治療師_'):
            # ... (保持原有邏輯)
            parts = user_message.replace('選擇治療師_', '').split('_')
            if len(parts) >= 3:
                therapist_id = parts[0]
                date = parts[1]
                time = parts[2]
                
                therapist_data = {
                    'therapist_id': therapist_id,
                    'date': date,
                    'time': time
                }
                
                user_states[user_id]['selected_therapist_data'] = therapist_data
                user_states[user_id]['stage'] = 'select_room'
                
                # 顯示房間選擇
                flex_message = create_room_selection_flex(therapist_data)
                if flex_message:
                    reply_message = flex_message
                else:
                    # 備用房間選擇
                    available_rooms = get_available_rooms(date, time)
                    if available_rooms:
                        quick_reply_items = []
                        for room_id in available_rooms:
                            room_info = TREATMENT_ROOMS[room_id]
                            quick_reply_items.append(
                                QuickReplyButton(
                                    action=MessageAction(
                                        label=room_info['name'],
                                        text=f"選擇房間_{room_id}_{therapist_id}_{date}_{time}"
                                    )
                                )
                            )
                        quick_reply = QuickReply(items=quick_reply_items)
                        reply_message = TextSendMessage(text="請選擇治療室：", quick_reply=quick_reply)
                    else:
                        reply_message = TextSendMessage(text="暫無可用房間，請選擇其他時段。")
        
        # 處理備用房間選擇格式
        elif user_message.startswith('選擇房間_'):
            # ... (保持原有邏輯)
            parts = user_message.replace('選擇房間_', '').split('_')
            if len(parts) >= 4:
                room_id = parts[0]
                therapist_id = parts[1]
                date = parts[2]
                time = parts[3]
                
                # 組合最終預約資料
                therapist_info = THERAPISTS[therapist_id]
                room_info = TREATMENT_ROOMS[room_id]
                
                user_states[user_id]['final_appointment_data'] = {
                    'therapist_id': therapist_id,
                    'room_id': room_id,
                    'date': date,
                    'time': time
                }
                user_states[user_id]['stage'] = 'appointment_confirm'
                
                date_obj = datetime.strptime(date, '%Y-%m-%d')
                formatted_date = date_obj.strftime('%m月%d日')
                weekday = ['週一', '週二', '週三', '週四', '週五', '週六', '週日'][date_obj.weekday()]
                
                reply_message = TextSendMessage(text=f"您的預約資訊：\n\n" \
                       f"日期：{formatted_date}({weekday})\n" \
                       f"時間：{time}\n" \
                       f"治療師：{therapist_info['name']}\n" \
                       f"房間：{room_info['name']}\n" \
                       f"費用：{therapist_info['fee']}元\n\n" \
                       f"請提供您的姓名和聯絡電話以完成預約。\n" \
                       f"格式：姓名 電話\n" \
                       f"例如：王小明 0912345678")
        
        # ===== 關鍵修正：優先處理管理員指令 =====
        # 管理員指令檢查 - 移到最前面，避免被預約流程攔截
        elif ai_assistant.admin_manager.is_admin(user_id) and (
            user_message.startswith('管理員') or 
            user_message == 'admin' or
            user_message in ['管理員模式', '離開管理模式']
        ):
            admin_response = ai_assistant.handle_admin_commands(user_message, user_id)
            if admin_response:
                reply_message = admin_response
            else:
                reply_message = TextSendMessage(text="無效的管理員指令。")
        
        # 管理員模式處理
        elif user_states[user_id].get('admin_mode', False):
            if current_stage == 'admin_appointment_date' and user_message.startswith('管理員選擇日期_'):
                reply_message = handle_admin_date_selection(user_id, user_message)
            elif current_stage == 'admin_appointment_time' and user_message.startswith('管理員選擇時間_'):
                reply_message = handle_admin_time_selection(user_id, user_message)
            elif current_stage == 'admin_select_therapist' and user_message.startswith('管理員選擇治療師_'):
                reply_message = handle_admin_therapist_selection(user_id, user_message)
            elif current_stage == 'admin_select_room' and user_message.startswith('管理員選擇房間_'):
                reply_message = handle_admin_room_selection(user_id, user_message)
            elif current_stage == 'appointment_confirm':
                appointment_data = user_states[user_id].get('final_appointment_data')
                if appointment_data:
                    reply_message = handle_final_appointment_confirmation(user_id, user_message, appointment_data)
                else:
                    reply_message = TextSendMessage(text="預約資料遺失，請重新開始預約流程。")
                    user_states[user_id]['stage'] = 'chat'
                    user_states[user_id]['admin_mode'] = False
            else:
                # 處理其他管理員指令
                admin_response = ai_assistant.handle_admin_commands(user_message, user_id)
                if admin_response:
                    reply_message = admin_response
                else:
                    reply_message = TextSendMessage(text="無效的管理員指令。")
        
        # 一般用戶模式處理 - 修正為新的時間選擇流程
        elif current_stage == 'select_time':
            reply_message = handle_time_selection(user_id, user_message)
            
        elif current_stage == 'select_date':
            reply_message = handle_date_selection_new(user_id, user_message)
            
        elif current_stage == 'appointment_confirm':
            # 使用最終預約資料進行確認
            appointment_data = user_states[user_id].get('final_appointment_data')
            if appointment_data:
                reply_message = handle_final_appointment_confirmation(user_id, user_message, appointment_data)
            else:
                reply_message = TextSendMessage(text="預約資料遺失，請重新開始預約流程。")
                user_states[user_id]['stage'] = 'chat'
            
        else:
            # 預約請求 - 但排除管理員指令
            if (ai_assistant.is_appointment_request(user_message) and 
                not user_message.startswith('管理員') and 
                not user_message.startswith('admin')):
                reply_message = ai_assistant.handle_appointment_request(user_message, user_id)
            
            # 歡迎訊息 - 包含問候語
            elif any(word in user_message for word in ['你好', '您好', 'hi', 'hello', '開始']):
                # 檢查是否為管理員
                if ai_assistant.admin_manager.is_admin(user_id):
                    welcome_text = """您好，歡迎來到物理治療診所！

我可以為您介紹：
• 診所服務項目與收費
• 預約流程與方式  
• 到府治療服務
• 保險理賠說明
• 交通停車資訊

🔧 管理員功能：輸入「管理員模式」進入管理功能

請點選下方按鈕或直接輸入您的問題"""
                else:
                    welcome_text = """您好，歡迎來到物理治療診所！

我可以為您介紹：
• 診所服務項目與收費
• 預約流程與方式  
• 到府治療服務
• 保險理賠說明
• 交通停車資訊

請點選下方按鈕或直接輸入您的問題"""
                
                quick_reply = create_faq_quick_reply()
                reply_message = TextSendMessage(text=welcome_text, quick_reply=quick_reply)
            
            # 處理常見問答 - 但排除已經被預約流程處理的訊息
            elif (not ai_assistant.is_appointment_request(user_message) or 
                  user_message.startswith('管理員')):
                faq_response = get_faq_response(user_message)
                if faq_response:
                    # 根據回覆內容選擇適當的Quick Reply
                    if any(word in user_message for word in ['預約', '約診', '掛號', '預定', '安排', '看診', '治療時間']):
                        quick_reply = create_appointment_quick_reply()
                    else:
                        quick_reply = create_faq_quick_reply()
                    reply_message = TextSendMessage(text=faq_response, quick_reply=quick_reply)
            
            # 其他詢問 - 使用備用回應
            if reply_message is None and any(word in user_message for word in ['還有其他問題', '其他問題', '別的問題']):
                reply_message = TextSendMessage(
                    text="還有什麼其他問題嗎？我可以為您介紹診所的各項服務。",
                    quick_reply=create_faq_quick_reply()
                )
            
            # 最後的備用回應 - 修正 AI 助理回應處理
            elif reply_message is None:
                # 使用AI助理處理其他對話
                reply_response = ai_assistant.get_ai_response(user_message, user_id)
                
                # 修正：確保 reply_response 已經是 TextSendMessage 物件
                if isinstance(reply_response, TextSendMessage):
                    reply_message = reply_response
                elif isinstance(reply_response, str):
                    # 如果仍然是字串，包裝成 TextSendMessage
                    quick_reply = create_faq_quick_reply()
                    reply_message = TextSendMessage(text=reply_response, quick_reply=quick_reply)
                else:
                    # 如果是其他類型的 LINE Bot 訊息物件
                    reply_message = reply_response
        
        # 確保有回覆訊息
        if reply_message is None:
            logger.warning(f"沒有產生回覆訊息，使用預設回覆")
            quick_reply = create_faq_quick_reply()
            reply_message = TextSendMessage(
                text="抱歉，我沒有理解您的需求。請選擇下方選項或重新輸入。", 
                quick_reply=quick_reply
            )
        
        # 發送回覆
        line_bot_api.reply_message(
            event.reply_token,
            reply_message
        )
        
        logger.info(f"已回覆用戶 {user_id}")
        
    except Exception as e:
        logger.error(f"處理訊息時發生錯誤: {e}")
        import traceback
        logger.error(f"錯誤詳情: {traceback.format_exc()}")
        try:
            quick_reply = create_faq_quick_reply()
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="系統暫時忙碌中，請稍後再試，謝謝您的耐心。", quick_reply=quick_reply)
            )
        except Exception as reply_error:
            logger.error(f"發送錯誤訊息失敗: {reply_error}")
            pass

# 初始化管理器
ai_assistant = AIAssistant()

# 用戶狀態管理
user_states = {}

def create_time_period_selection():
    """建立時段選擇的Quick Reply - 修正為具體時間"""
    quick_reply = QuickReply(items=[
        QuickReplyButton(action=MessageAction(label="早上 09:00", text="選擇時間_09:00")),
        QuickReplyButton(action=MessageAction(label="早上 10:00", text="選擇時間_10:00")),
        QuickReplyButton(action=MessageAction(label="早上 11:00", text="選擇時間_11:00")),
        QuickReplyButton(action=MessageAction(label="下午 14:00", text="選擇時間_14:00")),
        QuickReplyButton(action=MessageAction(label="下午 15:00", text="選擇時間_15:00")),
        QuickReplyButton(action=MessageAction(label="下午 16:00", text="選擇時間_16:00")),
        QuickReplyButton(action=MessageAction(label="晚上 18:00", text="選擇時間_18:00")),
        QuickReplyButton(action=MessageAction(label="晚上 19:00", text="選擇時間_19:00")),
        QuickReplyButton(action=MessageAction(label="晚上 20:00", text="選擇時間_20:00"))
    ])
    return quick_reply

def handle_time_selection(user_id, message):
    """處理具體時間選擇"""
    logger.info(f"處理時間選擇 - 用戶: {user_id}, 訊息: {message}")
    
    if not message.startswith('選擇時間_'):
        logger.warning(f"無效的時間選擇格式: {message}")
        return TextSendMessage(text="請選擇有效的時間。")
    
    selected_time = message.replace('選擇時間_', '')
    
    # 驗證時間格式
    valid_times = ['09:00', '10:00', '11:00', '14:00', '15:00', '16:00', '18:00', '19:00', '20:00']
    if selected_time not in valid_times:
        return TextSendMessage(text="請選擇有效的時間。")
    
    user_states[user_id]['selected_time'] = selected_time
    user_states[user_id]['stage'] = 'select_date'
    
    # 生成近7日的日期選項
    dates = []
    for i in range(7):
        date = datetime.now().date() + timedelta(days=i)
        dates.append(date.strftime('%Y-%m-%d'))
    
    user_states[user_id]['available_dates'] = dates
    
    quick_reply_items = []
    for i, date_str in enumerate(dates):
        date_obj = datetime.strptime(date_str, '%Y-%m-%d')
        formatted_date = date_obj.strftime('%m/%d')
        weekday = ['週一', '週二', '週三', '週四', '週五', '週六', '週日'][date_obj.weekday()]
        
        quick_reply_items.append(
            QuickReplyButton(
                action=MessageAction(
                    label=f"{formatted_date}({weekday})",
                    text=f"選擇日期_{date_str}"
                )
            )
        )
    
    quick_reply = QuickReply(items=quick_reply_items)
    
    # 判斷時段描述
    hour = int(selected_time.split(':')[0])
    if hour < 12:
        time_description = "早上"
    elif hour < 18:
        time_description = "下午"
    else:
        time_description = "晚上"
    
    logger.info(f"時間選擇完成，進入日期選擇階段")
    return TextSendMessage(
        text=f"您選擇了{time_description} {selected_time}，請選擇日期：",
        quick_reply=quick_reply
    )

def get_available_therapists_by_time(selected_time, date_str):
    """根據具體時間獲取可用的治療師"""
    try:
        logger.info(f"查詢治療師 - 時間: {selected_time}, 日期: {date_str}")
        
        day_name = datetime.strptime(date_str, '%Y-%m-%d').strftime('%A')
        available_therapists = []
        
        logger.info(f"目標時間: {selected_time}, 星期: {day_name}")
        
        for therapist_id, therapist_info in THERAPISTS.items():
            work_times = therapist_info['work_schedule'].get(day_name, [])
            logger.info(f"治療師 {therapist_info['name']} 工作時間: {work_times}")
            
            if selected_time in work_times:
                # 檢查該時段是否已被預約
                booked_slots = ai_assistant.db.get_booked_slots(date_str, therapist_id)
                booked_times = [slot[0] for slot in booked_slots]
                
                logger.info(f"治療師 {therapist_info['name']} 已預約時段: {booked_times}")
                
                if selected_time not in booked_times:
                    available_therapists.append({
                        'id': therapist_id,
                        'name': therapist_info['name'],
                        'gender': therapist_info['gender'],
                        'specialties': therapist_info['specialties'],
                        'fee': therapist_info['fee'],
                        'time': selected_time
                    })
                    logger.info(f"加入可用治療師: {therapist_info['name']}")
        
        logger.info(f"找到 {len(available_therapists)} 位可用治療師")
        return available_therapists
        
    except Exception as e:
        logger.error(f"查詢治療師時發生錯誤: {e}")
        return []

def create_therapist_selection_flex_new(therapists, date_str, time_description):
    """建立治療師選擇的Flex Message - 新版本"""
    logger.info(f"=== 開始建立 Flex Message ===")
    logger.info(f"治療師數量: {len(therapists)}")
    logger.info(f"日期: {date_str}, 時間描述: {time_description}")
    
    if not therapists:
        logger.warning("沒有可用治療師，無法建立 Flex Message")
        return None
    
    try:
        contents = []
        for i, therapist in enumerate(therapists):
            content = {
                "type": "box",
                "layout": "horizontal",
                "contents": [
                    {
                        "type": "text",
                        "text": f"${therapist['fee']}",
                        "size": "sm",
                        "color": "#666666",
                        "flex": 1
                    },
                    {
                        "type": "box",
                        "layout": "vertical",
                        "contents": [
                            {
                                "type": "text",
                                "text": str(therapist['name']),
                                "size": "md",
                                "weight": "bold",
                                "color": "#111111"
                            },
                            {
                                "type": "text",
                                "text": f"({therapist['gender']}性治療師)",
                                "size": "sm",
                                "color": "#666666"
                            }
                        ],
                        "flex": 3,
                        "margin": "md"
                    },
                    {
                        "type": "button",
                        "action": {
                            "type": "postback",
                            "label": "選擇",
                            "data": f"action=select_therapist&therapist_id={therapist['id']}&date={date_str}&time={therapist['time']}"
                        },
                        "style": "primary",
                        "height": "sm",
                        "flex": 2,
                        "margin": "sm"
                    }
                ],
                "spacing": "md",
                "paddingAll": "md",
                "cornerRadius": "md"
            }
            
            contents.append(content)
            
            # 如果不是最後一個，加入分隔線
            if i < len(therapists) - 1:
                contents.append({
                    "type": "separator",
                    "margin": "md"
                })
        
        # 處理日期格式
        date_obj = datetime.strptime(date_str, '%Y-%m-%d')
        formatted_date = date_obj.strftime('%m月%d日')
        weekday = ['週一', '週二', '週三', '週四', '週五', '週六', '週日'][date_obj.weekday()]
        
        # 建立完整的 Flex Message
        flex_content = {
            "type": "bubble",
            "header": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": f"{formatted_date}({weekday}) {time_description}",
                        "weight": "bold",
                        "size": "lg",
                        "color": "#ffffff"
                    },
                    {
                        "type": "text",
                        "text": "請選擇您偏好的治療師",
                        "size": "sm",
                        "color": "#ffffff",
                        "margin": "sm"
                    }
                ],
                "backgroundColor": "#27ACB2",
                "paddingAll": "md"
            },
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": contents,
                "spacing": "none",
                "paddingAll": "md"
            }
        }
        
        flex_message = FlexSendMessage(
            alt_text="選擇治療師",
            contents=flex_content
        )
        
        logger.info("=== Flex Message 建立成功 ===")
        return flex_message
        
    except Exception as e:
        logger.error(f"建立 Flex Message 時發生錯誤: {e}")
        return None

def handle_appointment_request_new(self, message, user_id):
    """處理預約請求 - 新版本"""
    # 檢查用戶是否已經在預約流程中
    if user_id not in user_states:
        user_states[user_id] = {'stage': 'chat'}
    
    # 如果是新的預約請求，開始時間選擇
    if user_states[user_id]['stage'] == 'chat':
        user_states[user_id]['stage'] = 'select_time'
        
        quick_reply = create_time_period_selection()
        return TextSendMessage(
            text="請選擇您方便的時間：",
            quick_reply=quick_reply
        )
    
    return "請先選擇時間後再進行預約。"

def handle_date_selection_new(user_id, message):
    """處理日期選擇 - 新版本"""
    logger.info(f"=== 開始處理日期選擇 ===")
    logger.info(f"用戶: {user_id}, 訊息: {message}")
    
    if not message.startswith('選擇日期_'):
        logger.warning(f"無效的日期選擇格式: {message}")
        return TextSendMessage(text="請選擇有效的日期。")
    
    date_str = message.replace('選擇日期_', '')
    selected_time = user_states[user_id]['selected_time']
    
    logger.info(f"解析結果 - 日期: {date_str}, 時間: {selected_time}")
    
    # 獲取該時間的可用治療師
    logger.info("開始查詢可用治療師...")
    therapists = get_available_therapists_by_time(selected_time, date_str)
    
    logger.info(f"查詢結果: 找到 {len(therapists)} 位可用治療師")
    for i, t in enumerate(therapists):
        logger.info(f"治療師 {i+1}: {t}")
    
    if not therapists:
        logger.warning(f"該時間沒有可用治療師")
        return TextSendMessage(text=f"很抱歉，{selected_time} 時段暫無可用治療師，請選擇其他時間。")
    
    # 更新用戶狀態
    user_states[user_id]['selected_date'] = date_str
    user_states[user_id]['stage'] = 'select_therapist'
    logger.info("用戶狀態已更新")
    
    # 建立治療師選擇 Flex Message
    hour = int(selected_time.split(':')[0])
    if hour < 12:
        time_description = "早上"
    elif hour < 18:
        time_description = "下午"
    else:
        time_description = "晚上"
    
    flex_message = create_therapist_selection_flex_new(therapists, date_str, f"{time_description} {selected_time}")
    
    if flex_message:
        logger.info("✅ Flex Message 建立成功")
        return flex_message
    else:
        logger.info("使用 Quick Reply 備用方案")
        quick_reply_items = []
        for therapist in therapists:
            quick_reply_items.append(
                QuickReplyButton(
                    action=MessageAction(
                        label=f"{therapist['name']} ({therapist['gender']}性) ${therapist['fee']}",
                        text=f"選擇治療師_{therapist['id']}_{date_str}_{therapist['time']}"
                    )
                )
            )
        
        quick_reply = QuickReply(items=quick_reply_items)
        return TextSendMessage(
            text=f"請選擇治療師：",
            quick_reply=quick_reply
        )


def get_therapists_by_time_period(time_period, date_str):
    """根據時段獲取可用的治療師"""
    try:
        logger.info(f"查詢治療師 - 時段: {time_period}, 日期: {date_str}")
        
        day_name = datetime.strptime(date_str, '%Y-%m-%d').strftime('%A')
        available_therapists = []
        
        time_mapping = {
            '早上': '09:00',
            '下午': '14:00', 
            '晚上': '18:00'
        }
        
        target_time = time_mapping.get(time_period)
        if not target_time:
            logger.warning(f"無效的時段: {time_period}")
            return []
        
        logger.info(f"目標時間: {target_time}, 星期: {day_name}")
        
        for therapist_id, therapist_info in THERAPISTS.items():
            work_times = therapist_info['work_schedule'].get(day_name, [])
            logger.info(f"治療師 {therapist_info['name']} 工作時間: {work_times}")
            
            if target_time in work_times:
                # 檢查該時段是否已被預約
                booked_slots = ai_assistant.db.get_booked_slots(date_str, therapist_id)
                booked_times = [slot[0] for slot in booked_slots]
                
                logger.info(f"治療師 {therapist_info['name']} 已預約時段: {booked_times}")
                
                if target_time not in booked_times:
                    available_therapists.append({
                        'id': therapist_id,
                        'name': therapist_info['name'],
                        'gender': therapist_info['gender'],
                        'specialties': therapist_info['specialties'],
                        'fee': therapist_info['fee'],
                        'time': target_time
                    })
                    logger.info(f"加入可用治療師: {therapist_info['name']}")
        
        logger.info(f"找到 {len(available_therapists)} 位可用治療師")
        return available_therapists
        
    except Exception as e:
        logger.error(f"查詢治療師時發生錯誤: {e}")
        return []


def create_room_selection_flex(therapist_data):
    """建立治療室選擇的Flex Message"""
    logger.info(f"建立房間選擇 Flex Message - 治療師: {therapist_data.get('therapist_id')}")
    
    # 獲取可用房間
    available_rooms = get_available_rooms(therapist_data['date'], therapist_data['time'])
    
    if not available_rooms:
        logger.warning("沒有可用房間")
        return None
    
    contents = []
    for room_id in available_rooms:
        room_info = TREATMENT_ROOMS[room_id]
        
        # 房間特色描述
        features = []
        if not room_info['has_camera']:
            features.append("無監視器")
        if room_info['type'] == '粉紅':
            features.append("粉紅色系")
        elif room_info['type'] == '藍色':
            features.append("藍色系")
        
        feature_text = "、".join(features) if features else "一般房間"
        
        content = {
            "type": "box",
            "layout": "horizontal",
            "contents": [
                {
                    "type": "box",
                    "layout": "vertical",
                    "contents": [
                        {
                            "type": "text",
                            "text": room_info['name'],
                            "size": "md",
                            "weight": "bold",
                            "color": "#111111"
                        },
                        {
                            "type": "text",
                            "text": feature_text,
                            "size": "sm",
                            "color": "#666666"
                        }
                    ],
                    "flex": 3
                },
                {
                    "type": "button",
                    "action": {
                        "type": "postback",
                        "label": "選擇",
                        "data": f"action=select_room&room_id={room_id}&therapist_id={therapist_data['therapist_id']}&date={therapist_data['date']}&time={therapist_data['time']}"
                    },
                    "style": "primary",
                    "height": "sm",
                    "flex": 2,
                    "margin": "sm"
                }
            ],
            "spacing": "md",
            "paddingAll": "md",
            "cornerRadius": "md"
        }
        
        contents.append(content)
    
    # 如果有多個房間，加入分隔線
    if len(available_rooms) > 1:
        new_contents = []
        for i, content in enumerate(contents):
            new_contents.append(content)
            if i < len(contents) - 1:
                new_contents.append({
                    "type": "separator",
                    "margin": "md"
                })
        contents = new_contents
    
    flex_message = FlexSendMessage(
        alt_text="選擇治療室",
        contents={
            "type": "bubble",
            "header": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": "選擇治療室",
                        "weight": "bold",
                        "size": "lg",
                        "color": "#ffffff"
                    },
                    {
                        "type": "text",
                        "text": "請選擇您偏好的治療室",
                        "size": "sm",
                        "color": "#ffffff",
                        "margin": "sm"
                    }
                ],
                "backgroundColor": "#27ACB2",
                "paddingAll": "md"
            },
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": contents,
                "spacing": "none",
                "paddingAll": "md"
            },
            "footer": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": "粉紅色系房間無監視器，提供更佳隱私",
                        "size": "xs",
                        "color": "#888888",
                        "align": "center"
                    }
                ],
                "paddingAll": "sm"
            }
        }
    )
    
    logger.info("房間選擇 Flex Message 建立成功")
    return flex_message

def get_available_rooms(date_str, time_str):
    """獲取指定日期時間的可用房間"""
    booked_slots = ai_assistant.db.get_booked_slots(date_str)
    booked_rooms_at_time = [slot[2] for slot in booked_slots if slot[0] == time_str]
    
    available_rooms = []
    for room_id in TREATMENT_ROOMS.keys():
        if room_id not in booked_rooms_at_time:
            available_rooms.append(room_id)
    
    logger.info(f"可用房間: {available_rooms}")
    return available_rooms

def create_appointment_confirmation_flex(appointment_data, appointment_id):
    """建立預約確認的 Flex Message"""
    try:
        date_obj = datetime.strptime(appointment_data['date'], '%Y-%m-%d')
        formatted_date = date_obj.strftime('%m月%d日')
        weekday = ['週一', '週二', '週三', '週四', '週五', '週六', '週日'][date_obj.weekday()]
        
        # 根據時段判斷時間描述
        hour = int(appointment_data['time'].split(':')[0])
        if 9 <= hour <= 12:
            time_description = "上午"
        elif 14 <= hour <= 17:
            time_description = "下午"
        elif 18 <= hour <= 21:
            time_description = "晚上"
        else:
            time_description = ""
            
        therapist_info = THERAPISTS[appointment_data['therapist_id']]
        room_info = TREATMENT_ROOMS[appointment_data['room_id']]
        
        flex_message = FlexSendMessage(
            alt_text="預約確認",
            contents={
                "type": "bubble",
                "header": {
                    "type": "box",
                    "layout": "vertical",
                    "contents": [
                        {
                            "type": "text",
                            "text": "預約完成",
                            "weight": "bold",
                            "size": "lg",
                            "color": "#ffffff"
                        },
                        {
                            "type": "text",
                            "text": "您的預約已成功建立",
                            "size": "sm",
                            "color": "#ffffff",
                            "margin": "sm"
                        }
                    ],
                    "backgroundColor": "#06C755",
                    "paddingAll": "md"
                },
                "body": {
                    "type": "box",
                    "layout": "vertical",
                    "contents": [
                        {
                            "type": "box",
                            "layout": "vertical",
                            "contents": [
                                {
                                    "type": "text",
                                    "text": f"預約編號 #{appointment_id}",
                                    "size": "sm",
                                    "color": "#666666"
                                },
                                {
                                    "type": "text",
                                    "text": f"{formatted_date}({weekday}) {time_description}{appointment_data['time']}",
                                    "size": "lg",
                                    "weight": "bold",
                                    "color": "#111111",
                                    "margin": "sm"
                                }
                            ]
                        },
                        {
                            "type": "separator",
                            "margin": "md"
                        },
                        {
                            "type": "box",
                            "layout": "vertical",
                            "contents": [
                                {
                                    "type": "box",
                                    "layout": "horizontal",
                                    "contents": [
                                        {
                                            "type": "text",
                                            "text": "治療師",
                                            "size": "sm",
                                            "color": "#555555",
                                            "flex": 2
                                        },
                                        {
                                            "type": "text",
                                            "text": therapist_info['name'],
                                            "size": "sm",
                                            "color": "#111111",
                                            "flex": 3,
                                            "align": "end"
                                        }
                                    ]
                                },
                                {
                                    "type": "box",
                                    "layout": "horizontal",
                                    "contents": [
                                        {
                                            "type": "text",
                                            "text": "房間",
                                            "size": "sm",
                                            "color": "#555555",
                                            "flex": 2
                                        },
                                        {
                                            "type": "text",
                                            "text": room_info['name'],
                                            "size": "sm",
                                            "color": "#111111",
                                            "flex": 3,
                                            "align": "end"
                                        }
                                    ],
                                    "margin": "sm"
                                },
                                {
                                    "type": "box",
                                    "layout": "horizontal",
                                    "contents": [
                                        {
                                            "type": "text",
                                            "text": "姓名",
                                            "size": "sm",
                                            "color": "#555555",
                                            "flex": 2
                                        },
                                        {
                                            "type": "text",
                                            "text": appointment_data['user_name'],
                                            "size": "sm",
                                            "color": "#111111",
                                            "flex": 3,
                                            "align": "end"
                                        }
                                    ],
                                    "margin": "sm"
                                },
                                {
                                    "type": "box",
                                    "layout": "horizontal",
                                    "contents": [
                                        {
                                            "type": "text",
                                            "text": "電話",
                                            "size": "sm",
                                            "color": "#555555",
                                            "flex": 2
                                        },
                                        {
                                            "type": "text",
                                            "text": appointment_data['phone'],
                                            "size": "sm",
                                            "color": "#111111",
                                            "flex": 3,
                                            "align": "end"
                                        }
                                    ],
                                    "margin": "sm"
                                },
                                {
                                    "type": "box",
                                    "layout": "horizontal",
                                    "contents": [
                                        {
                                            "type": "text",
                                            "text": "費用",
                                            "size": "sm",
                                            "color": "#555555",
                                            "flex": 2
                                        },
                                        {
                                            "type": "text",
                                            "text": f"${therapist_info['fee']}",
                                            "size": "sm",
                                            "color": "#111111",
                                            "flex": 3,
                                            "align": "end",
                                            "weight": "bold"
                                        }
                                    ],
                                    "margin": "sm"
                                }
                            ],
                            "margin": "md"
                        }
                    ],
                    "spacing": "md",
                    "paddingAll": "md"
                },
                "footer": {
                    "type": "box",
                    "layout": "vertical",
                    "contents": [
                        {
                            "type": "text",
                            "text": "新店區順德街1號",
                            "size": "sm",
                            "color": "#666666",
                            "align": "center"
                        },
                        {
                            "type": "text",
                            "text": "我們將於療程前一天提醒您到診",
                            "size": "xs",
                            "color": "#888888",
                            "align": "center",
                            "margin": "sm"
                        },
                        {
                            "type": "button",
                            "action": {
                                "type": "postback",
                                "label": "取消此預約",
                                "data": f"action=cancel&appointment_id={appointment_id}"
                            },
                            "style": "secondary",
                            "height": "sm",
                            "margin": "md"
                        }
                    ],
                    "paddingAll": "md"
                }
            }
        )
        
        return flex_message
        
    except Exception as e:
        logger.error(f"建立確認 Flex Message 時發生錯誤: {e}")
        return None

def create_faq_quick_reply():
    """建立常見問答的Quick Reply按鈕"""
    quick_reply = QuickReply(items=[
        QuickReplyButton(action=MessageAction(label="保險理賠", text="請問可以申請保險嗎？")),
        QuickReplyButton(action=MessageAction(label="費用說明", text="請問費用")),
        QuickReplyButton(action=MessageAction(label="到府治療", text="請問可以到府治療嗎？")),
        QuickReplyButton(action=MessageAction(label="停車場", text="附近有停車場嗎？")),
        QuickReplyButton(action=MessageAction(label="預約流程", text="請問如何預約治療")),
        QuickReplyButton(action=MessageAction(label="我要預約", text="我想要預約治療")),
        QuickReplyButton(action=MessageAction(label="診所地址", text="診所在哪裡？")),
        QuickReplyButton(action=MessageAction(label="營業時間", text="營業時間"))
    ])
    return quick_reply

def create_appointment_quick_reply():
    """建立預約相關的Quick Reply按鈕"""
    quick_reply = QuickReply(items=[
        QuickReplyButton(action=MessageAction(label="我要預約", text="我想要預約治療")),
        QuickReplyButton(action=MessageAction(label="預約流程", text="請問如何預約治療")),
        QuickReplyButton(action=MessageAction(label="費用說明", text="請問費用")),
        QuickReplyButton(action=MessageAction(label="其他問題", text="還有其他問題"))
    ])
    return quick_reply

def get_faq_response(user_message):
    """處理常見問答回覆"""
    # 保險相關
    if any(word in user_message for word in ['保險', '理賠']):
        return "申請保險理賠，需要醫生開立的診斷證明，我們診所會開立收據，但我們是全自費醫療，沒有配合健保，因此大部分保險公司並不給付，也有些保險公司會給付六七成，因此還是要以您的保險條款為準，詳細規定還是需要您和保險業務員進行確認唷，謝謝您~"
    
    # 費用相關
    elif any(word in user_message for word in ['費用', '價格', '收費', '多少錢']):
        return "初次約診費用，會依不同治療師，而有不同的收費，範圍介於1800~2200元之間，包含評估、諮詢、理學檢查，運動治療或功能訓練。之後的約診與治療費用，再由治療師評估過後跟您討論，詳情可參考：http://bit.ly/grandlifecharge"
    
    # 到府治療
    elif any(word in user_message for word in ['到府', '居家']):
        return """到府物理治療每次約1小時，
單次收費2200元，
服務範圍為新店市區，
初次到府治療，會幫您評估目前的姿態、肌力、活動能力、疼痛狀況…等，
再依據評估結果給予徒手或運動治療。"""
    
    # 停車場
    elif any(word in user_message for word in ['停車', '停車場']):
        return """我們這邊比較近的停車場有幾處：
1. CITY PARKING 城市車旅停車場 (斯馨停車場)
   電話：080 020 8333
   https://goo.gl/maps/ufjBPrpMwduTNEQy9

2. 俥亭停車場（新店中央場）
   https://maps.app.goo.gl/EseXMgPR5oLissMA9?g_st=ic"""
    
    # 預約方式 - 修改條件，只有明確問「如何預約」才回傳這個訊息
    # 移除 '預約治療' 這個關鍵字，避免衝突
    elif any(word in user_message for word in ['如何預約', '怎麼預約', '預約方法']) and not any(simple_word in user_message for simple_word in ['我要預約', '想預約', '預約治療']):
        return """您好 初次來院所，依據法規，我們需要醫生的診斷或是照會，如果您已經看過診（跟您的症狀相關，任何科別都可以），持有診斷證明書、或是任何有診斷名稱的單據來都可以，如果沒有的話可以下載健保局的「健保快易通」App，裡面的「健康存摺」功能有您近期的看診紀錄也可以代替；如果都沒有看診、不確定要掛哪一科，可以到我們合作的診所看診：
1. 安倍診所：中正路132號。
2. 達泰中醫診所：中華路43之1號。

確定預約後，我們會詢問：
• 請問您一般什麼時段比較方便？平日白天、晚上、或是週末呢？
• 請問您有指定的治療師，或是男性/女性治療師嗎？"""
    
    # 地址相關
    elif any(word in user_message for word in ['地址', '位置', '在哪', '怎麼去']):
        return "診所地址：新店區順德街1號\n附近有停車場可停車，詳細交通資訊歡迎詢問。"
    
    # 營業時間
    elif any(word in user_message for word in ['營業時間', '時間', '幾點']):
        return """營業時間：
週一至週五：09:00-21:00
週六：09:00-18:00
週日：休診

各治療師時段不同，詳細可用時段請告知您的需求，我們為您查詢。"""
    
    # 收費方式
    elif any(word in user_message for word in ['收費方式', '付款方式', '怎麼付費']):
        return "收費方式：現金/轉帳/台灣pay/街口支付（無刷卡服務）"
    
    # 就診準備
    elif any(word in user_message for word in ['準備什麼', '注意事項', '就診準備']):
        return """就診當天請您穿著輕鬆可伸展的衣褲，方便治療師檢查及評估，我們有置物櫃可以提供您放私人物品。

若有過往的診斷證明書、X光、MRI等相關資料，可於初診時一併攜帶過來，讓治療師與您討論身體狀況~"""
    
    # 基本問候
    elif any(word in user_message for word in ['你好', '您好', 'hi', 'hello']):
        return "您好，請問有什麼需求可以為您服務的嗎？"
    
    return None

def handle_time_period_selection(user_id, message):
    """處理時段選擇"""
    logger.info(f"處理時段選擇 - 用戶: {user_id}, 訊息: {message}")
    
    time_period_mapping = {
        '選擇早上時段': '早上',
        '選擇下午時段': '下午', 
        '選擇晚上時段': '晚上'
    }
    
    time_period = time_period_mapping.get(message)
    if not time_period:
        logger.warning(f"無效的時段選擇: {message}")
        return TextSendMessage(text="請選擇有效的時段。")
    
    user_states[user_id]['selected_time_period'] = time_period
    user_states[user_id]['stage'] = 'select_date'
    
    # 生成近三日的日期選項
    dates = []
    for i in range(3):
        date = datetime.now().date() + timedelta(days=i)
        dates.append(date.strftime('%Y-%m-%d'))
    
    user_states[user_id]['available_dates'] = dates
    
    quick_reply_items = []
    for i, date_str in enumerate(dates):
        date_obj = datetime.strptime(date_str, '%Y-%m-%d')
        formatted_date = date_obj.strftime('%m/%d')
        weekday = ['週一', '週二', '週三', '週四', '週五', '週六', '週日'][date_obj.weekday()]
        
        quick_reply_items.append(
            QuickReplyButton(
                action=MessageAction(
                    label=f"{formatted_date}({weekday})",
                    text=f"選擇日期_{date_str}"
                )
            )
        )
    
    quick_reply = QuickReply(items=quick_reply_items)
    
    logger.info(f"時段選擇完成，進入日期選擇階段")
    return TextSendMessage(
        text=f"您選擇了{time_period}時段，請選擇日期：",
        quick_reply=quick_reply
    )

def create_simple_therapist_flex(therapists, date_str, time_period):
    """建立簡化版的治療師選擇 Flex Message"""
    logger.info("建立簡化版 Flex Message")
    
    try:
        if not therapists:
            return None
        
        # 只取第一個治療師做測試
        therapist = therapists[0]
        
        simple_content = {
            "type": "bubble",
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": f"{time_period}時段治療師",
                        "weight": "bold",
                        "size": "lg"
                    },
                    {
                        "type": "text",
                        "text": f"{therapist['name']} ({therapist['gender']}性)",
                        "size": "md",
                        "margin": "md"
                    },
                    {
                        "type": "text",
                        "text": f"費用: ${therapist['fee']}",
                        "size": "sm",
                        "color": "#666666",
                        "margin": "sm"
                    },
                    {
                        "type": "button",
                        "action": {
                            "type": "postback",
                            "label": "選擇此治療師",
                            "data": f"action=select_therapist&therapist_id={therapist['id']}&date={date_str}&time={therapist['time']}"
                        },
                        "style": "primary",
                        "margin": "md"
                    }
                ]
            }
        }
        
        flex_message = FlexSendMessage(
            alt_text="選擇治療師",
            contents=simple_content
        )
        
        logger.info("簡化版 Flex Message 建立成功")
        return flex_message
        
    except Exception as e:
        logger.error(f"建立簡化版 Flex Message 失敗: {e}")
        return None

def create_appointment_confirmation_message(appointment_info):
    """建立預約完成確認訊息"""
    date_obj = datetime.strptime(appointment_info['date'], '%Y-%m-%d')
    formatted_date = date_obj.strftime('%m/%d')
    weekday = ['週一', '週二', '週三', '週四', '週五', '週六', '週日'][date_obj.weekday()]
    
    # 根據時間判斷時段
    hour = int(appointment_info['time'].split(':')[0])
    if hour < 12:
        time_period = "早上"
    elif hour < 18:
        time_period = "下午" 
    else:
        time_period = "晚上"
    
    therapist_info = THERAPISTS[appointment_info['therapist_id']]
    
    message = f"""您的預約已完成囉✅

預約時間：{formatted_date}({weekday}){time_period}{appointment_info['time']}
（{therapist_info['name']}治療師/費用{therapist_info['fee']}元）

我們將於療程前一天提醒您到診

若不克前來，再麻煩告知及回覆，以便將時間安排給候補的患者

▶收費方式：現金/轉帳/台灣pay/街口支付（無刷卡服務）
▶地址：新店區順德街1號
▶就診當天也請您穿著輕鬆可伸展的衣褲，方便治療師檢查及評估，我們有置物櫃可以提供您放私人物品

若有過往的診斷證明書、X光、MRI等相關資料，可於初診時一併攜帶過來，讓治療師與您討論身體狀況~"""
    
    return message
def handle_final_appointment_confirmation(user_id, user_message, appointment_data):
    """處理最終預約確認"""
    try:
        # 檢查是否為管理員模式
        is_admin_mode = user_states.get(user_id, {}).get('admin_mode', False)
        
        # 解析姓名和電話
        parts = user_message.split()
        if len(parts) >= 2:
            name = parts[0]
            phone = parts[1]
            notes = ' '.join(parts[2:]) if len(parts) > 2 else ''
            
            # 電話號碼驗證
            if not re.match(r'^09\d{8}$', phone) and not re.match(r'^0\d{1,2}-?\d{6,8}$', phone):
                return TextSendMessage(text="請提供正確的電話號碼格式（例如：0912345678）")
            
            # 儲存預約
            final_appointment_data = {
                'user_id': user_id,
                'user_name': name,
                'phone': phone,
                'therapist_id': appointment_data['therapist_id'],
                'room_id': appointment_data['room_id'],
                'date': appointment_data['date'],
                'time': appointment_data['time'],
                'notes': notes,
                'created_by': 'admin' if is_admin_mode else 'patient'
            }
            
            appointment_id = ai_assistant.db.save_appointment(final_appointment_data)
            
            if appointment_id:
                # 重置用戶狀態
                user_states[user_id]['stage'] = 'chat'
                user_states[user_id]['admin_mode'] = False
                
                # 建立確認訊息
                flex_message = create_appointment_confirmation_flex(final_appointment_data, appointment_id)
                
                return flex_message if flex_message else TextSendMessage(text="預約已完成！")
            else:
                return TextSendMessage(text="預約儲存失敗，請重新嘗試或聯繫診所。")
        else:
            return TextSendMessage(text="請提供正確格式：姓名 電話")
    except Exception as e:
        logger.error(f"確認預約時發生錯誤: {e}")
        return TextSendMessage(text="預約處理時發生錯誤，請重新嘗試。")

def handle_admin_date_selection(user_id, message):
    """處理管理員日期選擇"""
    if not message.startswith('管理員選擇日期_'):
        return TextSendMessage(text="請選擇有效的日期。")
    
    date_str = message.replace('管理員選擇日期_', '')
    user_states[user_id]['admin_selected_date'] = date_str
    user_states[user_id]['stage'] = 'admin_appointment_time'
    
    # 顯示所有時段
    times = ['09:00', '14:00', '18:00']
    quick_reply_items = []
    
    for time in times:
        time_desc = "早上" if time == '09:00' else "下午" if time == '14:00' else "晚上"
        quick_reply_items.append(
            QuickReplyButton(
                action=MessageAction(
                    label=f"{time_desc} ({time})",
                    text=f"管理員選擇時間_{time}"
                )
            )
        )
    
    quick_reply = QuickReply(items=quick_reply_items)
    
    date_obj = datetime.strptime(date_str, '%Y-%m-%d')
    formatted_date = date_obj.strftime('%m月%d日')
    weekday = ['週一', '週二', '週三', '週四', '週五', '週六', '週日'][date_obj.weekday()]
    
    return TextSendMessage(
        text=f"選擇了 {formatted_date}({weekday})，請選擇時間：",
        quick_reply=quick_reply
    )

def handle_admin_time_selection(user_id, message):
    """處理管理員時間選擇"""
    if not message.startswith('管理員選擇時間_'):
        return TextSendMessage(text="請選擇有效的時間。")
    
    time_str = message.replace('管理員選擇時間_', '')
    date_str = user_states[user_id]['admin_selected_date']
    
    user_states[user_id]['admin_selected_time'] = time_str
    user_states[user_id]['stage'] = 'admin_select_therapist'
    
    # 獲取當天工作的治療師
    day_name = datetime.strptime(date_str, '%Y-%m-%d').strftime('%A')
    available_therapists = []
    
    for therapist_id, therapist_info in THERAPISTS.items():
        work_times = therapist_info['work_schedule'].get(day_name, [])
        if time_str in work_times:
            available_therapists.append({
                'id': therapist_id,
                'name': therapist_info['name'],
                'gender': therapist_info['gender'],
                'fee': therapist_info['fee'],
                'time': time_str
            })
    
    if not available_therapists:
        return TextSendMessage(text="該時段沒有治療師排班，請選擇其他時間。")
    
    # 建立治療師選擇按鈕
    quick_reply_items = []
    for therapist in available_therapists:
        quick_reply_items.append(
            QuickReplyButton(
                action=MessageAction(
                    label=f"{therapist['name']} ({therapist['gender']})",
                    text=f"管理員選擇治療師_{therapist['id']}"
                )
            )
        )
    
    quick_reply = QuickReply(items=quick_reply_items)
    
    return TextSendMessage(
        text="請選擇治療師：",
        quick_reply=quick_reply
    )

def handle_admin_therapist_selection(user_id, message):
    """處理管理員治療師選擇"""
    if not message.startswith('管理員選擇治療師_'):
        return TextSendMessage(text="請選擇有效的治療師。")
    
    therapist_id = message.replace('管理員選擇治療師_', '')
    date_str = user_states[user_id]['admin_selected_date']
    time_str = user_states[user_id]['admin_selected_time']
    
    # 檢查治療師是否已被預約
    booked_slots = ai_assistant.db.get_booked_slots(date_str, therapist_id)
    booked_times = [slot[0] for slot in booked_slots]
    
    if time_str in booked_times:
        return TextSendMessage(text="該治療師在此時段已有預約，請選擇其他治療師或時段。")
    
    # 獲取可用房間
    available_rooms = get_available_rooms(date_str, time_str)
    
    if not available_rooms:
        return TextSendMessage(text="該時段沒有可用房間，請選擇其他時間。")
    
    user_states[user_id]['admin_selected_therapist'] = therapist_id
    user_states[user_id]['stage'] = 'admin_select_room'
    
    # 建立房間選擇按鈕
    quick_reply_items = []
    for room_id in available_rooms:
        room_info = TREATMENT_ROOMS[room_id]
        quick_reply_items.append(
            QuickReplyButton(
                action=MessageAction(
                    label=room_info['name'],
                    text=f"管理員選擇房間_{room_id}"
                )
            )
        )
    
    quick_reply = QuickReply(items=quick_reply_items)
    
    return TextSendMessage(
        text="請選擇治療室：",
        quick_reply=quick_reply
    )

def handle_admin_room_selection(user_id, message):
    """處理管理員房間選擇"""
    if not message.startswith('管理員選擇房間_'):
        return TextSendMessage(text="請選擇有效的房間。")
    
    room_id = message.replace('管理員選擇房間_', '')
    
    # 收集所有選擇的資料
    date_str = user_states[user_id]['admin_selected_date']
    time_str = user_states[user_id]['admin_selected_time']
    therapist_id = user_states[user_id]['admin_selected_therapist']
    
    # 組合預約資料
    user_states[user_id]['final_appointment_data'] = {
        'therapist_id': therapist_id,
        'room_id': room_id,
        'date': date_str,
        'time': time_str
    }
    user_states[user_id]['stage'] = 'appointment_confirm'
    
    # 顯示確認資訊
    therapist_info = THERAPISTS[therapist_id]
    room_info = TREATMENT_ROOMS[room_id]
    
    date_obj = datetime.strptime(date_str, '%Y-%m-%d')
    formatted_date = date_obj.strftime('%m月%d日')
    weekday = ['週一', '週二', '週三', '週四', '週五', '週六', '週日'][date_obj.weekday()]
    
    return TextSendMessage(text=f"管理員新增預約：\n\n" \
           f"日期：{formatted_date}({weekday})\n" \
           f"時間：{time_str}\n" \
           f"治療師：{therapist_info['name']}\n" \
           f"房間：{room_info['name']}\n" \
           f"費用：{therapist_info['fee']}元\n\n" \
           f"請輸入病患資料以完成預約：\n" \
           f"格式：姓名 電話 [備註]\n" \
           f"例如：王小明 0912345678 腰痛治療")

def handle_flex_cancellation(user_id, appointment_id):
    """處理Flex Message取消預約"""
    try:
        # 檢查是否為管理員
        is_admin = ai_assistant.admin_manager.is_admin(user_id)
        
        success, message = ai_assistant.db.cancel_appointment(
            appointment_id, 
            user_id if not is_admin else None, 
            is_admin=is_admin
        )
        
        if success:
            return TextSendMessage(text=f"預約 #{appointment_id} 已成功取消。\n{message}")
        else:
            return TextSendMessage(text=f"取消預約失敗：{message}")
            
    except Exception as e:
        logger.error(f"處理Flex取消預約錯誤: {e}")
        return TextSendMessage(text="取消預約時發生錯誤，請稍後再試。")

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        logger.error("Invalid signature")
        abort(400)
    except Exception as e:
        logger.error(f"Callback error: {e}")
        abort(500)
    
    return 'OK'

# 修正 handle_message 函數中最後的備用回應部分
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    try:
        user_id = event.source.user_id
        user_message = event.message.text.strip()
        
        logger.info(f"收到訊息 - 用戶: {user_id}, 內容: {user_message}")
        
        # 初始化用戶狀態
        if user_id not in user_states:
            user_states[user_id] = {'stage': 'chat'}
        
        current_stage = user_states[user_id]['stage']
        reply_message = None  # 初始化回覆訊息
        
        # 處理備用治療師選擇格式
        if user_message.startswith('選擇治療師_'):
            parts = user_message.replace('選擇治療師_', '').split('_')
            if len(parts) >= 3:
                therapist_id = parts[0]
                date = parts[1]
                time = parts[2]
                
                therapist_data = {
                    'therapist_id': therapist_id,
                    'date': date,
                    'time': time
                }
                
                user_states[user_id]['selected_therapist_data'] = therapist_data
                user_states[user_id]['stage'] = 'select_room'
                
                # 顯示房間選擇
                flex_message = create_room_selection_flex(therapist_data)
                if flex_message:
                    reply_message = flex_message
                else:
                    # 備用房間選擇
                    available_rooms = get_available_rooms(date, time)
                    if available_rooms:
                        quick_reply_items = []
                        for room_id in available_rooms:
                            room_info = TREATMENT_ROOMS[room_id]
                            quick_reply_items.append(
                                QuickReplyButton(
                                    action=MessageAction(
                                        label=room_info['name'],
                                        text=f"選擇房間_{room_id}_{therapist_id}_{date}_{time}"
                                    )
                                )
                            )
                        quick_reply = QuickReply(items=quick_reply_items)
                        reply_message = TextSendMessage(text="請選擇治療室：", quick_reply=quick_reply)
                    else:
                        reply_message = TextSendMessage(text="暫無可用房間，請選擇其他時段。")
        
        # 處理備用房間選擇格式
        elif user_message.startswith('選擇房間_'):
            parts = user_message.replace('選擇房間_', '').split('_')
            if len(parts) >= 4:
                room_id = parts[0]
                therapist_id = parts[1]
                date = parts[2]
                time = parts[3]
                
                # 組合最終預約資料
                therapist_info = THERAPISTS[therapist_id]
                room_info = TREATMENT_ROOMS[room_id]
                
                user_states[user_id]['final_appointment_data'] = {
                    'therapist_id': therapist_id,
                    'room_id': room_id,
                    'date': date,
                    'time': time
                }
                user_states[user_id]['stage'] = 'appointment_confirm'
                
                date_obj = datetime.strptime(date, '%Y-%m-%d')
                formatted_date = date_obj.strftime('%m月%d日')
                weekday = ['週一', '週二', '週三', '週四', '週五', '週六', '週日'][date_obj.weekday()]
                
                reply_message = TextSendMessage(text=f"您的預約資訊：\n\n" \
                       f"日期：{formatted_date}({weekday})\n" \
                       f"時間：{time}\n" \
                       f"治療師：{therapist_info['name']}\n" \
                       f"房間：{room_info['name']}\n" \
                       f"費用：{therapist_info['fee']}元\n\n" \
                       f"請提供您的姓名和聯絡電話以完成預約。\n" \
                       f"格式：姓名 電話\n" \
                       f"例如：王小明 0912345678")
        
        # 管理員模式處理
        elif user_states[user_id].get('admin_mode', False):
            if current_stage == 'admin_appointment_date' and user_message.startswith('管理員選擇日期_'):
                reply_message = handle_admin_date_selection(user_id, user_message)
            elif current_stage == 'admin_appointment_time' and user_message.startswith('管理員選擇時間_'):
                reply_message = handle_admin_time_selection(user_id, user_message)
            elif current_stage == 'admin_select_therapist' and user_message.startswith('管理員選擇治療師_'):
                reply_message = handle_admin_therapist_selection(user_id, user_message)
            elif current_stage == 'admin_select_room' and user_message.startswith('管理員選擇房間_'):
                reply_message = handle_admin_room_selection(user_id, user_message)
            elif current_stage == 'appointment_confirm':
                appointment_data = user_states[user_id].get('final_appointment_data')
                if appointment_data:
                    reply_message = handle_final_appointment_confirmation(user_id, user_message, appointment_data)
                else:
                    reply_message = TextSendMessage(text="預約資料遺失，請重新開始預約流程。")
                    user_states[user_id]['stage'] = 'chat'
                    user_states[user_id]['admin_mode'] = False
            else:
                # 處理其他管理員指令
                admin_response = ai_assistant.handle_admin_commands(user_message, user_id)
                if admin_response:
                    reply_message = admin_response
                else:
                    reply_message = TextSendMessage(text="無效的管理員指令。")
        
        # 一般用戶模式處理 - 修正為新的時間選擇流程
        elif current_stage == 'select_time':
            reply_message = handle_time_selection(user_id, user_message)
            
        elif current_stage == 'select_date':
            reply_message = handle_date_selection_new(user_id, user_message)
            
        elif current_stage == 'appointment_confirm':
            # 使用最終預約資料進行確認
            appointment_data = user_states[user_id].get('final_appointment_data')
            if appointment_data:
                reply_message = handle_final_appointment_confirmation(user_id, user_message, appointment_data)
            else:
                reply_message = TextSendMessage(text="預約資料遺失，請重新開始預約流程。")
                user_states[user_id]['stage'] = 'chat'
            
        else:
            # ===== 重要修正：將預約請求處理移到最前面 =====
            # 預約請求 - 最高優先級處理
            if ai_assistant.is_appointment_request(user_message):
                reply_message = ai_assistant.handle_appointment_request(user_message, user_id)
            
            # 歡迎訊息 - 包含問候語
            elif any(word in user_message for word in ['你好', '您好', 'hi', 'hello', '開始']):
                # 檢查是否為管理員
                if ai_assistant.admin_manager.is_admin(user_id):
                    welcome_text = """您好，歡迎來到物理治療診所！

我可以為您介紹：
• 診所服務項目與收費
• 預約流程與方式  
• 到府治療服務
• 保險理賠說明
• 交通停車資訊

🔧 管理員功能：輸入「管理員模式」進入管理功能

請點選下方按鈕或直接輸入您的問題"""
                else:
                    welcome_text = """您好，歡迎來到物理治療診所！

我可以為您介紹：
• 診所服務項目與收費
• 預約流程與方式  
• 到府治療服務
• 保險理賠說明
• 交通停車資訊

請點選下方按鈕或直接輸入您的問題"""
                
                quick_reply = create_faq_quick_reply()
                reply_message = TextSendMessage(text=welcome_text, quick_reply=quick_reply)
            
            # 處理常見問答 - 但排除已經被預約流程處理的訊息
            elif not ai_assistant.is_appointment_request(user_message):
                faq_response = get_faq_response(user_message)
                if faq_response:
                    # 根據回覆內容選擇適當的Quick Reply
                    if any(word in user_message for word in ['預約', '約診', '掛號', '預定', '安排', '看診', '治療時間']):
                        quick_reply = create_appointment_quick_reply()
                    else:
                        quick_reply = create_faq_quick_reply()
                    reply_message = TextSendMessage(text=faq_response, quick_reply=quick_reply)
            
            # 其他詢問 - 使用備用回應
            if reply_message is None and any(word in user_message for word in ['還有其他問題', '其他問題', '別的問題']):
                reply_message = TextSendMessage(
                    text="還有什麼其他問題嗎？我可以為您介紹診所的各項服務。",
                    quick_reply=create_faq_quick_reply()
                )
            
            # 最後的備用回應 - 修正 AI 助理回應處理
            elif reply_message is None:
                # 使用AI助理處理其他對話
                reply_response = ai_assistant.get_ai_response(user_message, user_id)
                
                # 修正：確保 reply_response 已經是 TextSendMessage 物件
                if isinstance(reply_response, TextSendMessage):
                    reply_message = reply_response
                elif isinstance(reply_response, str):
                    # 如果仍然是字串，包裝成 TextSendMessage
                    quick_reply = create_faq_quick_reply()
                    reply_message = TextSendMessage(text=reply_response, quick_reply=quick_reply)
                else:
                    # 如果是其他類型的 LINE Bot 訊息物件
                    reply_message = reply_response
        
        # 確保有回覆訊息
        if reply_message is None:
            logger.warning(f"沒有產生回覆訊息，使用預設回覆")
            quick_reply = create_faq_quick_reply()
            reply_message = TextSendMessage(
                text="抱歉，我沒有理解您的需求。請選擇下方選項或重新輸入。", 
                quick_reply=quick_reply
            )
        
        # 發送回覆
        line_bot_api.reply_message(
            event.reply_token,
            reply_message
        )
        
        logger.info(f"已回覆用戶 {user_id}")
        
    except Exception as e:
        logger.error(f"處理訊息時發生錯誤: {e}")
        import traceback
        logger.error(f"錯誤詳情: {traceback.format_exc()}")
        try:
            quick_reply = create_faq_quick_reply()
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="系統暫時忙碌中，請稍後再試，謝謝您的耐心。", quick_reply=quick_reply)
            )
        except Exception as reply_error:
            logger.error(f"發送錯誤訊息失敗: {reply_error}")
            pass
@handler.add(PostbackEvent)
def handle_postback(event):
    """處理Flex Message的postback事件"""
    try:
        data = event.postback.data
        user_id = event.source.user_id
        
        logger.info(f"收到Postback - 用戶: {user_id}, 數據: {data}")
        
        # 解析postback數據
        params = {}
        for param in data.split('&'):
            if '=' in param:
                key, value = param.split('=', 1)
                params[key] = value
        
        action = params.get('action')
        
        if action == 'select_therapist':
            # 處理治療師選擇
            therapist_id = params.get('therapist_id')
            date = params.get('date')
            time = params.get('time')
            
            therapist_data = {
                'therapist_id': therapist_id,
                'date': date,
                'time': time
            }
            
            user_states[user_id]['selected_therapist_data'] = therapist_data
            user_states[user_id]['stage'] = 'select_room'
            
            # 顯示房間選擇
            flex_message = create_room_selection_flex(therapist_data)
            reply_message = flex_message if flex_message else TextSendMessage(text="正在為您安排房間...")
            
        elif action == 'select_room':
            # 處理房間選擇，進入最終確認
            room_id = params.get('room_id')
            therapist_id = params.get('therapist_id')
            date = params.get('date')
            time = params.get('time')
            
            # 組合最終預約資料
            therapist_info = THERAPISTS[therapist_id]
            room_info = TREATMENT_ROOMS[room_id]
            
            user_states[user_id]['final_appointment_data'] = {
                'therapist_id': therapist_id,
                'room_id': room_id,
                'date': date,
                'time': time
            }
            user_states[user_id]['stage'] = 'appointment_confirm'
            
            date_obj = datetime.strptime(date, '%Y-%m-%d')
            formatted_date = date_obj.strftime('%m月%d日')
            weekday = ['週一', '週二', '週三', '週四', '週五', '週六', '週日'][date_obj.weekday()]
            
            reply_message = TextSendMessage(text=f"您的預約資訊：\n\n" \
                   f"日期：{formatted_date}({weekday})\n" \
                   f"時間：{time}\n" \
                   f"治療師：{therapist_info['name']}\n" \
                   f"房間：{room_info['name']}\n" \
                   f"費用：{therapist_info['fee']}元\n\n" \
                   f"請提供您的姓名和聯絡電話以完成預約。\n" \
                   f"格式：姓名 電話\n" \
                   f"例如：王小明 0912345678")
        
        elif action == 'cancel' or action == 'admin_cancel':
            # 處理取消預約
            appointment_id = int(params.get('appointment_id', 0))
            reply_message = handle_flex_cancellation(user_id, appointment_id)
            
        else:
            reply_message = TextSendMessage(text="無效的操作，請重新選擇。")
        
        line_bot_api.reply_message(
            event.reply_token,
            reply_message
        )
        
    except Exception as e:
        logger.error(f"處理Postback時發生錯誤: {e}")
        try:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="操作時發生錯誤，請稍後再試。")
            )
        except:
            pass

# 健康檢查端點
@app.route("/health", methods=['GET'])
def health_check():
    return "OK", 200

# 根目錄
@app.route("/", methods=['GET'])
def index():
    return "LINE Bot is running!", 200

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5007))
    logger.info(f"啟動 LINE Bot，監聽端口 {port}")
    app.run(host='0.0.0.0', port=port, debug=False)