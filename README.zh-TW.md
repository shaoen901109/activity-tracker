[English](README.md) | 繁體中文

> 📖 **圖文教學：** https://shao-en.com/blog/activity-tracker-guide.html ——如果你不知道該如何操作，請把這篇文章交給你的 Claude 或 ChatGPT。

# activity-tracker（Windows 使用時間紀錄）

一個在 Windows 背景執行的小工具：記錄你離開電腦的時間，離席很久時，請 Gemini API 推測你去做了什麼（睡覺、出門、系統重啟……）。所有資料都寫進本機的 CSV 檔。

## 記錄哪些資料

每個事件一列，寫在 `log/activity_log.csv`（UTF-8 含 BOM），共四欄：時間戳記（含星期幾）、事件狀態、此次未使用電腦時長（分）、離席原因。

- 閒置未滿 10 分鐘：不記錄。
- 閒置 10 分鐘以上、未滿 30 分鐘：回來時記為「回歸(短暫離席)」，不呼叫 AI。
- 閒置 30 分鐘以上：回來時記為「回歸(長時離席)」，並請 AI 推測原因。
- 開機：若上一筆是「關機」紀錄，會把該筆關機紀錄移除，改寫一筆「開機」，附上離線時長與 AI 推測的原因。

閒置時間用 Windows 的 `GetLastInputInfo` 取得（每 15 秒檢查一次）。不會記錄按鍵內容、視窗標題或螢幕畫面。

## 資料存在哪、隱私提醒

- 紀錄與每週備份（`activity_log_backup_YYYY-MM-DD.csv`，最新備份已滿 7 天以上時自動複製一份）都放在腳本旁邊的 `log/` 資料夾，紀錄檔不會被清空。
- 工具本身不會上傳任何東西，唯一例外：請 AI 推測原因時，提示詞會包含時間、時長、你自訂的 `TRACKER_USER_CONTEXT`，以及**你紀錄檔的最後 200 行**（含先前的原因），並送到 Google Gemini API。不想送出就不要設定 `GOOGLE_API_KEY`，工具仍會記錄，原因欄會顯示「分析中...」。
- 這份紀錄等於你的作息表。`log/` 與 `.env` 已列入 `.gitignore`，請勿提交或分享。

## 需求

- Windows 10/11（使用 pywin32 與工作排程器）
- Python 3.10 以上（作者使用 3.12）
- Python 套件：`google-genai`、`pywin32`、`python-dotenv`
- 選用：Google AI Studio 的 Gemini API 金鑰

## 安裝

```
pip install -r requirements.txt
copy .env.example .env
```

編輯 `.env`：

| 變數 | 說明 |
| --- | --- |
| `GOOGLE_API_KEY` | Gemini API 金鑰（選用；沒有就不會有 AI 原因）。也可設成系統環境變數。 |
| `GEMINI_MODEL` | 模型名稱，預設 `gemini-3-flash-preview`。 |
| `TRACKER_USER_CONTEXT` | 選用，一句話介紹你自己，會加進提示詞幫助 AI 判斷。 |

註冊開機（登入時）自動啟動的排程（最高權限、用 `pythonw.exe`，註冊後立即啟動）：

```
python setup_scheduler.py
```

會建立名為 `UserActivityTracker` 的 Windows 排程工作，可能需要在系統管理員終端機執行。注意：`setup_scheduler.py` 只會檢查系統環境變數 `GOOGLE_API_KEY` 並警告；放在 `.env` 的金鑰追蹤程式仍會讀取。

## 使用

- 前景測試執行：`python activity_tracker.py`
- 改了 `.env` 或程式後，重新啟動背景排程：`schtasks /run /tn "UserActivityTracker"`
- 查看紀錄：用 Excel 或文字編輯器開 `log/activity_log.csv`。可手動修正原因；最後 200 列（含你的修正）會當作 AI 的參考脈絡。

## 解除安裝

```
schtasks /delete /tn "UserActivityTracker" /f
```

再到工作管理員結束正在執行的追蹤程式 `pythonw.exe`，然後刪除資料夾。不想保留紀錄就一併刪除 `log/`。

## 校驗下載檔

到 [Releases](https://github.com/shaoen901109/activity-tracker/releases) 下載 `activity-tracker-v1.0.0.zip` 和 `SHA256SUMS.txt`（版本號以你實際下載的為準）。

1. 用 PowerShell 比對指紋（SHA256，檔案的數位指紋）：

   ```powershell
   Get-FileHash .\activity-tracker-v1.0.0.zip -Algorithm SHA256
   ```

   輸出的 `Hash` 要和 `SHA256SUMS.txt` 裡的字串一致（大小寫不同沒關係）。

2. 驗證來源（需安裝 [GitHub CLI](https://cli.github.com/)）：

   ```powershell
   gh attestation verify .\activity-tracker-v1.0.0.zip --repo shaoen901109/activity-tracker
   ```

   顯示驗證成功，代表這個 zip 是 GitHub Actions 從本 repo 原始碼建出來的，中途沒有被替換。

GitHub 上標示 **Verified** 的 commit，是作者本人簽章。

## 技術來源與致謝

| 用途 | 元件 | 授權 |
|---|---|---|
| 以 AI 摘要畫面活動 | Google Gemini API via [google-genai](https://github.com/googleapis/python-genai) | SDK：Apache-2.0；API：依 Google 條款 |
| Windows API 呼叫 | [pywin32](https://github.com/mhammond/pywin32) | PSF |
| 讀取 `.env` 設定 | [python-dotenv](https://github.com/theskumar/python-dotenv) | BSD-3-Clause |
| 排程 | Windows Task Scheduler (`schtasks`) | Windows 內建 |

開發過程使用 [Claude Code](https://claude.com/claude-code)（Anthropic）協助。

## 作者

- 網站：https://shaoenstudio.com
- 聯絡信箱：shaoenstudio@gmail.com
- GitHub：[@shaoen901109](https://github.com/shaoen901109)

## 授權

MIT，見 [LICENSE](LICENSE)。
