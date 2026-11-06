import os
import csv
import time
import ctypes
import datetime
import threading
from dotenv import load_dotenv
from google import genai
from google.genai import types
import win32gui
import win32con
import win32api

# --- 配置區 ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))  # 排程啟動時工作目錄不固定，要寫完整路徑
MODEL_ID = os.getenv("GEMINI_MODEL", "gemini-3-flash-preview")
LOG_DIR = os.path.join(BASE_DIR, "log")
LOG_FILE = os.path.join(LOG_DIR, "activity_log.csv")
USER_CONTEXT = os.getenv("TRACKER_USER_CONTEXT", "")  # optional: a short description of you, to help the AI guess

# 門檻定義 (秒)
SHORT_THRESHOLD_SEC = 10 * 60  # 10 分鐘
LONG_THRESHOLD_SEC = 30 * 60   # 30 分鐘
CHECK_INTERVAL = 15            # 15 秒檢查一次

class ActivityTrackerV2:
    def __init__(self, api_key=None):
        self.last_idle_sec = 0
        self.is_running = True
        
        # 從環境變數或參數獲取 API Key
        self.api_key = api_key or os.environ.get("GOOGLE_API_KEY")
        
        if self.api_key:
            self.client = genai.Client(api_key=self.api_key)
        else:
            self.client = None
        
        if not os.path.exists(LOG_DIR):
            os.makedirs(LOG_DIR)
        
        self._check_backup()
        self._init_csv()

    def _check_backup(self):
        """檢查上次備份時間，若超過 7 天則複製一份當前 log 作為備份"""
        if not os.path.exists(LOG_FILE):
            return

        try:
            # 尋找現有的備份檔案，格式為 activity_log_backup_YYYY-MM-DD.csv
            backups = [f for f in os.listdir(LOG_DIR) if f.startswith("activity_log_backup_") and f.endswith(".csv")]
            
            should_backup = False
            if not backups:
                # 如果從未備份過，則進行第一次備份
                should_backup = True
            else:
                # 取得最新的一份備份檔
                backups.sort(reverse=True)
                latest_backup = os.path.join(LOG_DIR, backups[0])
                
                # 檢查該檔案的修改時間
                mtime = os.path.getmtime(latest_backup)
                last_backup_date = datetime.datetime.fromtimestamp(mtime)
                
                if (datetime.datetime.now() - last_backup_date).days >= 7:
                    should_backup = True
            
            if should_backup:
                import shutil
                today_str = datetime.datetime.now().strftime('%Y-%m-%d')
                backup_name = os.path.join(LOG_DIR, f"activity_log_backup_{today_str}.csv")
                
                # 只有當今天還沒備份過時才執行（防呆）
                if not os.path.exists(backup_name):
                    shutil.copy2(LOG_FILE, backup_name)
        except Exception as e:
            pass

    def _init_csv(self):
        """確保 CSV 存在且具備正確表頭"""
        if not os.path.exists(LOG_FILE):
            with open(LOG_FILE, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f)
                writer.writerow(["時間戳記(含星期幾)", "事件狀態", "此次未使用電腦時長(分)", "離席原因"])

    def _get_timestamp(self, dt=None):
        """取得格式化時間戳記"""
        days = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
        target_dt = dt or datetime.datetime.now()
        return target_dt.strftime(f"%Y-%m-%d %H:%M:%S ({days[target_dt.weekday()]})")

    def log_event(self, state, duration="", reason=""):
        """單一寫入點：寫入紀錄到 CSV"""
        timestamp = self._get_timestamp()
        try:
            with open(LOG_FILE, 'a', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f)
                writer.writerow([timestamp, state, duration, reason])
        except Exception as e:
            # 後台程式不噴錯，安靜重試或略過
            pass

    def get_last_200_logs_str(self):
        """讀取最後 200 筆紀錄用於 Prompt 脈絡"""
        if not os.path.exists(LOG_FILE):
            return "無歷史紀錄"
        try:
            with open(LOG_FILE, 'r', encoding='utf-8-sig') as f:
                lines = f.readlines()
                # 取得最後 200 行內容
                return "".join(lines[-200:])
        except:
            return "讀取紀錄失敗"

    def get_gemini_reason(self, start_time, end_time, duration_min, is_boot=False):
        """呼叫 Gemini API 推測離席原因"""
        history = self.get_last_200_logs_str()
        
        rule_reboot = "【極重要判斷規則】：如果這是一次『開機』事件，且計算出的總時長極短（例如小於 10 分鐘），請優先判斷為『系統重啟』，絕對不要判斷為『睡覺』。若是半夜且時長達數小時，則高機率為『睡覺』。"
        
        prompt = f"""你是一個作息分析助手。請根據以下使用者的電腦狀態紀錄，推測使用者剛結束的這段時間去做了什麼。

此次離席資訊：
- 離席開始/關機時間：{start_time}
- 回歸/開機時間：{end_time}
- 總時長：{duration_min} 分鐘

使用者背景參考：{USER_CONTEXT}

{rule_reboot if is_boot else ""}

以下是最近 200 筆歷史紀錄（包含他過去手動修正過的真實原因）：
{history}

請參考上述資訊、時間脈絡與歷史規律。你只需要回覆最可能的一個『離席原因』，字數控制在 10 個字以內，絕對不要輸出任何其他解釋或對話。"""
        
        try:
            response = self.client.models.generate_content(
                model=MODEL_ID,
                contents=prompt
            )
            return response.text.strip()
        except:
            return "分析中..."

    def get_idle_sec(self):
        """獲取系統閒置秒數"""
        class LASTINPUTINFO(ctypes.Structure):
            _fields_ = [("cbSize", ctypes.c_uint), ("dwTime", ctypes.c_uint)]
        lii = LASTINPUTINFO()
        lii.cbSize = ctypes.sizeof(LASTINPUTINFO)
        ctypes.windll.user32.GetLastInputInfo(ctypes.byref(lii))
        millis = ctypes.windll.kernel32.GetTickCount() - lii.dwTime
        return max(0, millis / 1000.0)

    def on_boot(self):
        """開機啟動邏輯：僅當上次紀錄是『關機』時才紀錄"""
        last_event = None
        last_shutdown_time = None
        all_rows = []
        
        if os.path.exists(LOG_FILE):
            try:
                with open(LOG_FILE, 'r', encoding='utf-8-sig') as f:
                    all_rows = list(csv.reader(f))
                    if len(all_rows) > 1:
                        last_row = all_rows[-1]
                        last_event = last_row[1]
                        # 往前找最近的一次關機
                        for row in reversed(all_rows):
                            if len(row) > 1 and row[1] == "關機":
                                last_shutdown_time = row[0]
                                break
            except:
                pass
        
        # 核心防呆：如果最後一筆紀錄不是「關機」，則判定為「腳本重啟」而非「系統開機」
        if last_event and last_event != "關機":
            self.last_state = "使用中"
            return 
            
        # 如果最後一筆是關機，則準備移除它
        if last_event == "關機":
            all_rows.pop() # 移除最後一筆
            try:
                with open(LOG_FILE, 'w', newline='', encoding='utf-8-sig') as f:
                    writer = csv.writer(f)
                    writer.writerows(all_rows)
            except:
                pass

        now_ts = self._get_timestamp()
        duration_min = ""
        reason = ""
        
        if last_shutdown_time:
            try:
                # 解析上次關機時間
                t_str = last_shutdown_time.split(' (')[0]
                t_old = datetime.datetime.strptime(t_str, "%Y-%m-%d %H:%M:%S")
                t_now = datetime.datetime.now()
                diff_sec = (t_now - t_old).total_seconds()
                diff_min = int(diff_sec / 60)
                duration_min = str(diff_min)
                reason = self.get_gemini_reason(last_shutdown_time, now_ts, diff_min, is_boot=True)
            except:
                pass
        
        self.log_event("開機", duration_min, reason)
        self.last_state = "使用中"

    def run(self):
        """主迴圈：執行事後結算邏輯"""
        self.on_boot()
        
        while self.is_running:
            current_idle_sec = self.get_idle_sec()
            
            # 偵測到使用者回歸 (閒置時間歸零或大幅下降)
            if current_idle_sec < self.last_idle_sec:
                # 結算剛剛那段完整的閒置總時長
                total_idle_sec = self.last_idle_sec
                total_idle_min = int(total_idle_sec / 60)
                
                if total_idle_min >= 10:
                    start_dt = datetime.datetime.now() - datetime.timedelta(seconds=total_idle_sec)
                    start_ts = self._get_timestamp(start_dt)
                    now_ts = self._get_timestamp()
                    
                    if total_idle_min >= 30:
                        state = "回歸(長時離席)"
                        reason = self.get_gemini_reason(start_ts, now_ts, total_idle_min)
                    else:
                        state = "回歸(短暫離席)"
                        reason = "" # 短暫離席不觸發 API
                    
                    self.log_event(state, str(total_idle_min), reason)
                
                # 回歸後重置追蹤
                self.last_idle_sec = 0
            else:
                # 閒置持續中，僅紀錄最高峰值，不寫入檔案
                self.last_idle_sec = current_idle_sec
                
            time.sleep(CHECK_INTERVAL)

# --- 關機攔截視窗 ---
def create_hidden_window(tracker):
    def wnd_proc(hwnd, msg, wparam, lparam):
        if msg == win32con.WM_QUERYENDSESSION:
            tracker.log_event("關機")
            return True
        return win32gui.DefWindowProc(hwnd, msg, wparam, lparam)

    wc = win32gui.WNDCLASS()
    wc.lpfnWndProc = wnd_proc
    wc.lpszClassName = "ActivityTrackerV2Node"
    wc.hInstance = win32api.GetModuleHandle(None)
    
    class_atom = win32gui.RegisterClass(wc)
    hwnd = win32gui.CreateWindow(
        class_atom, "HiddenTrackerV2", 0, 0, 0, 0, 0, 0, 0, wc.hInstance, None
    )
    return hwnd

if __name__ == "__main__":
    tracker = ActivityTrackerV2()
    
    # 建立隱藏視窗監聽關機訊號
    hwnd = create_hidden_window(tracker)
    
    # 啟動主邏輯執行緒
    t = threading.Thread(target=tracker.run)
    t.daemon = True
    t.start()
    
    # 訊息迴圈
    win32gui.PumpMessages()
