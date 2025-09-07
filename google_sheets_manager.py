# google_sheets_manager.py
import json
import os
import logging
from datetime import datetime
from google.oauth2.service_account import Credentials
import gspread

logger = logging.getLogger(__name__)

class GoogleSheetsManager:
    def __init__(self, spreadsheet_id='1suA1DLkjpzIuVwjTmbdmIxbt0XJYJHhx3SQkOXH09JQ'):
        self.credentials = None
        self.client = None
        self.spreadsheet_id = spreadsheet_id
        self.init_google_sheets()
    
    def get_current_worksheet_name(self):
        """獲取當前月份的工作表名稱"""
        now = datetime.now()
        return f"{now.year}-{now.month:02d}"  # 格式: 2025-01, 2025-02
    
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
            
            # 方法2: 使用JSON檔案
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
    
    def ensure_monthly_worksheet_exists(self):
        """確保當前月份的工作表存在"""
        if not self.client:
            return None
        
        try:
            spreadsheet = self.client.open_by_key(self.spreadsheet_id)
            current_worksheet_name = self.get_current_worksheet_name()
            
            # 嘗試獲取當前月份的工作表
            try:
                worksheet = spreadsheet.worksheet(current_worksheet_name)
                logger.info(f"找到現有工作表: {current_worksheet_name}")
                return worksheet
            except gspread.WorksheetNotFound:
                # 工作表不存在，建立新的
                logger.info(f"建立新的月份工作表: {current_worksheet_name}")
                worksheet = spreadsheet.add_worksheet(
                    title=current_worksheet_name, 
                    rows=1000, 
                    cols=15
                )
                
                # 添加標題行
                headers = [
                    '預約編號', '日期', '星期', '時間', '姓名', '電話', 
                    '治療師', '房間', '費用', '備註', '狀態', '建立時間', '建立者', '修改時間', '症狀/診斷'
                ]
                worksheet.append_row(headers)
                logger.info(f"已建立新工作表 {current_worksheet_name} 並添加標題行")
                return worksheet
                
        except Exception as e:
            logger.error(f"確保月份工作表存在時發生錯誤: {e}")
            return None
    
    def sync_appointment_to_sheets(self, appointment_data, appointment_id, therapists_config, rooms_config):
        """將預約資料同步到Google Sheets"""
        if not self.client:
            logger.warning("Google Sheets 未初始化，跳過同步")
            return False
        
        try:
            # 確保當前月份的工作表存在
            worksheet = self.ensure_monthly_worksheet_exists()
            if not worksheet:
                logger.error("無法獲取或建立工作表")
                return False
            
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
                appointment_data.get('created_by', 'patient'),  # 建立者
                '',  # 修改時間（預留）
                appointment_data.get('notes', '')  # 症狀/診斷（複製備註內容）
            ]
            
            # 添加預約資料
            worksheet.append_row(row_data)
            logger.info(f"預約 #{appointment_id} 已同步到Google Sheets工作表 {worksheet.title}")
            return True
            
        except Exception as e:
            logger.error(f"同步到Google Sheets失敗: {e}")
            return False
    
    def update_appointment_status_in_sheets(self, appointment_id, new_status):
        """更新Google Sheets中預約的狀態"""
        if not self.client:
            return False
        
        try:
            # 取得目前月份的工作表
            worksheet = self.ensure_monthly_worksheet_exists()
            if not worksheet:
                return False
            
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
            
            # 如果在目前月份找不到，嘗試搜尋其他月份（可選）
            logger.warning(f"在目前月份工作表中找不到預約 #{appointment_id}")
            return self._search_and_update_in_other_months(appointment_id, new_status)
            
        except Exception as e:
            logger.error(f"更新Google Sheets狀態失敗: {e}")
            return False
    
    def _search_and_update_in_other_months(self, appointment_id, new_status):
        """在其他月份的工作表中搜尋並更新預約狀態"""
        try:
            spreadsheet = self.client.open_by_key(self.spreadsheet_id)
            worksheets = spreadsheet.worksheets()
            
            for worksheet in worksheets:
                # 跳過非月份格式的工作表
                if not self._is_monthly_worksheet(worksheet.title):
                    continue
                
                try:
                    all_records = worksheet.get_all_records()
                    for i, record in enumerate(all_records, start=2):
                        if str(record.get('預約編號', '')) == str(appointment_id):
                            worksheet.update_cell(i, 11, new_status)
                            try:
                                worksheet.update_cell(i, 14, datetime.now().strftime('%Y/%m/%d %H:%M:%S'))
                            except:
                                pass
                            logger.info(f"在工作表 {worksheet.title} 中找到並更新預約 #{appointment_id}")
                            return True
                except Exception as e:
                    logger.warning(f"搜尋工作表 {worksheet.title} 時出錯: {e}")
                    continue
            
            logger.warning(f"在所有工作表中都找不到預約 #{appointment_id}")
            return False
            
        except Exception as e:
            logger.error(f"搜尋其他月份工作表時出錯: {e}")
            return False
    
    def _is_monthly_worksheet(self, worksheet_name):
        """檢查工作表名稱是否符合月份格式 (YYYY-MM)"""
        try:
            parts = worksheet_name.split('-')
            if len(parts) == 2:
                year = int(parts[0])
                month = int(parts[1])
                return 2020 <= year <= 2030 and 1 <= month <= 12
        except:
            pass
        return False
    
    def get_all_appointments_from_sheets(self, month_filter=None):
        """從Google Sheets取得所有預約記錄"""
        if not self.client:
            return []
        
        try:
            spreadsheet = self.client.open_by_key(self.spreadsheet_id)
            all_appointments = []
            
            if month_filter:
                # 取得指定月份的記錄
                try:
                    worksheet = spreadsheet.worksheet(month_filter)
                    records = worksheet.get_all_records()
                    all_appointments.extend(records)
                except gspread.WorksheetNotFound:
                    logger.warning(f"找不到月份工作表: {month_filter}")
            else:
                # 取得目前月份的記錄
                worksheet = self.ensure_monthly_worksheet_exists()
                if worksheet:
                    records = worksheet.get_all_records()
                    all_appointments.extend(records)
            
            return all_appointments
            
        except Exception as e:
            logger.error(f"從Google Sheets讀取資料失敗: {e}")
            return []
    
    def get_available_months(self):
        """取得所有可用的月份工作表"""
        if not self.client:
            return []
        
        try:
            spreadsheet = self.client.open_by_key(self.spreadsheet_id)
            worksheets = spreadsheet.worksheets()
            
            months = []
            for worksheet in worksheets:
                if self._is_monthly_worksheet(worksheet.title):
                    months.append(worksheet.title)
            
            # 按時間順序排序
            months.sort(reverse=True)  # 最新的在前面
            return months
            
        except Exception as e:
            logger.error(f"取得可用月份失敗: {e}")
            return []