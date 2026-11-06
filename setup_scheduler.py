import os
import sys
import subprocess
import time

def setup_task():
    # 獲取當前腳本目錄與 pythonw.exe 路徑
    current_dir = os.path.dirname(os.path.abspath(__file__))
    script_path = os.path.join(current_dir, "activity_tracker.py")
    
    # 檢查 API KEY
    if not os.environ.get("GOOGLE_API_KEY"):
        print("警告：偵測到環境變數中缺少 GOOGLE_API_KEY。")
        print("排程任務雖然會建立，但在啟動時可能會失敗。請確保已在系統變數中設定。")

    # 尋找 pythonw.exe
    python_dir = os.path.dirname(sys.executable)
    pythonw_path = os.path.join(python_dir, "pythonw.exe")
    
    if not os.path.exists(pythonw_path):
        pythonw_path = os.path.join(python_dir, "Scripts", "pythonw.exe")

    if not os.path.exists(pythonw_path):
        print(f"錯誤：找不到 pythonw.exe (嘗試過: {pythonw_path})")
        return

    task_name = "UserActivityTracker"
    
    # 1. 先停止並刪除舊任務 (避免狀態衝突)
    print(f"正在清理舊任務 {task_name}...")
    subprocess.run(["schtasks", "/delete", "/tn", task_name, "/f"], capture_output=True)
    
    # 2. 建立新任務
    # /sc ONLOGON: 登入時啟動
    # /rl HIGHEST: 最高權限
    # /tr: 執行指令
    command = [
        "schtasks", "/create", "/tn", task_name,
        "/tr", f'"{pythonw_path}" "{script_path}"',
        "/sc", "ONLOGON",
        "/rl", "HIGHEST",
        "/f"
    ]
    
    print(f"正在註冊任務...")
    try:
        subprocess.run(command, capture_output=True, text=True, check=True)
        print("成功！已註冊到 Windows 工作排程器。")
        
        # 3. 立即啟動測試
        print("正在啟動任務...")
        subprocess.run(["schtasks", "/run", "/tn", task_name], check=True)
        print("任務已啟動。請查看 log 資料夾確認紀錄。")
        
    except subprocess.CalledProcessError as e:
        print(f"操作失敗：{e.stderr}")

if __name__ == "__main__":
    setup_task()
