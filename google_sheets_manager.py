# google_sheets_manager.py
import json
import os
import logging
from datetime import datetime
from google.oauth2.service_account import Credentials
import gspread

logger = logging.getLogger(__name__)

class GoogleSheetsManager:
    def __init__(self, spreadsheet_id='1suA1DLkjpzIuVwjTmbdmIxbt0XJYJHhx3SQkOXH09JQ', worksheet_name='sheet1'):
        self.credentials = None
        self.client = None
        self.spreadsheet_id = spreadsheet_id
        self.worksheet_name = worksheet_name
        self.init_google_sheets()
    
    def init_google_sheets(self):
        """初始化Google Sheets連接"""
        try:
            # 方法1: 使用環境變數中的服務帳戶金鑰
            if os.getenv('GOOGLE_SHEETS_CREDENTIALS'):
                credentials_info = json.loads(os.getenv('GOOGLE_SHEETS_CREDENTIALS'))
                self.credentials = Credentials.from_service_account_info(
                    credentials_info,
                    scopes=['https://www.googleapis.com/auth/spreadsheets']
                )
            
            # 方法2: 使用JSON文件
            elif os.path.exists('service_account.json'):
                self.credentials = Credentials.from_service_account_file(
                    'service_account.json',
                    scopes=['https://www.googleapis.com/auth/spreadsheets']
                )
            
            if self.credentials:
                self.client = gspread.authorize(self.credentials)
                logger.info("Google Sheets 連接成功")
                return True
            else:
                logger.warning("未找到Google Sheets憑證，同步功能將暫時停用")
                return False
                
        except Exception as e:
            logger.error(f"Google Sheets 初始化失敗: {e}")
            return False
    
    def sync_appointment_to_sheets(self, appointment_data, appointment_id, therapists_config, rooms_config):
        """將預約資料同步到Google Sheets"""
        if not self.client:
            logger.warning("Google Sheets 未初始化，跳過同步")
            return False
        
        try:
            # 打開工作表
            spreadsheet = self.client.open_by_key(self.spreadsheet_id)
            worksheet = spreadsheet.worksheet(self.worksheet_name)
            
            # 格式化資料
            date_obj = datetime.strptime(appointment_data['date'], '%Y-%m-%d')
            formatted_date = date_obj.strftime('%Y/%m/%d')
            weekday = ['週一', '週二', '週三', '週四', '週五', '週六', '週日'][date_obj.weekday()]
            
            # 獲取治療師和房間資訊
            therapist_info = therapists_config.get(appointment_data['therapist_id'], {})
            room_info = rooms_config.get(appointment_data['room_id'], {})
            
            # 準備要添加的行資料
            row_data = [
                appointment_id,  # 預約編號
                formatted_date,  # 日期
                weekday,  # 星期
                appointment_data['time'],  # 時間
                appointment_data['user_name'],  # 姓名
                appointment_data['phone'],  # 電話
                therapist_info.get('name', ''),  # 治療師
                room_info.get('name', ''),  # 房間
                therapist_info.get('fee', ''),  # 費用
                appointment_data.get('notes', ''),  # 備註
                'confirmed',  # 狀態
                datetime.now().strftime('%Y/%m/%d %H:%M:%S'),  # 建立時間
                appointment_data.get('created_by', 'patient')  # 建立者
            ]
            
            # 如果工作表為空，先添加標題行
            try:
                existing_headers = worksheet.row_values(1)
                if not existing_headers:
                    raise Exception("需要添加標題行")
            except:
                headers = [
                    '預約編號', '日期', '星期', '時間', '姓名', '電話', 
                    '治療師', '房間', '費用', '備註', '狀態', '建立時間', '建立者'
                ]
                worksheet.append_row(headers)
                logger.info("已添加Google Sheets標題行")
            
            # 添加預約資料
            worksheet.append_row(row_data)
            logger.info(f"預約 #{appointment_id} 已同步到Google Sheets")
            return True
            
        except Exception as e:
            logger.error(f"同步到Google Sheets失敗: {e}")
            return False
    
    def update_appointment_status_in_sheets(self, appointment_id, new_status):
        """更新Google Sheets中預約的狀態"""
        if not self.client:
            return False
        
        try:
            spreadsheet = self.client.open_by_key(self.spreadsheet_id)
            worksheet = spreadsheet.worksheet(self.worksheet_name)
            
            # 找到對應的預約記錄
            all_records = worksheet.get_all_records()
            for i, record in enumerate(all_records, start=2):  # 從第2行開始（跳過標題）
                if str(record.get('預約編號', '')) == str(appointment_id):
                    # 更新狀態欄位（第11欄）
                    worksheet.update_cell(i, 11, new_status)
                    # 添加修改時間（第14欄）
                    try:
                        worksheet.update_cell(i, 14, datetime.now().strftime('%Y/%m/%d %H:%M:%S'))
                    except:
                        # 如果第14欄不存在，跳過
                        pass
                    logger.info(f"Google Sheets中預約 #{appointment_id} 狀態已更新為 {new_status}")
                    return True
            
            logger.warning(f"在Google Sheets中找不到預約 #{appointment_id}")
            return False
            
        except Exception as e:
            logger.error(f"更新Google Sheets狀態失敗: {e}")
            return False
    
    def get_all_appointments_from_sheets(self):
        """從Google Sheets獲取所有預約記錄"""
        if not self.client:
            return []
        
        try:
            spreadsheet = self.client.open_by_key(self.spreadsheet_id)
            worksheet = spreadsheet.worksheet(self.worksheet_name)
            
            all_records = worksheet.get_all_records()
            return all_records
            
        except Exception as e:
            logger.error(f"從Google Sheets讀取資料失敗: {e}")
            return []