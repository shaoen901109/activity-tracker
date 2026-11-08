English | [繁體中文](README.zh-TW.md)

> 📖 **Step-by-step tutorial (Traditional Chinese):** https://shao-en.com/blog/activity-tracker-guide.html — not sure how to set it up? Hand the article to Claude or ChatGPT and let it walk you through.

# activity-tracker

A small background tool for Windows that logs when you step away from the computer and, for long absences, asks the Gemini API to guess why (sleeping, going out, a reboot...). Everything is written to a local CSV file.

## What it records

One row per event in `log/activity_log.csv` (UTF-8 with BOM), with four columns: timestamp (with weekday), event state, minutes not using the computer, and the guessed reason.

- Idle for less than 10 minutes: nothing is logged.
- Idle 10 to under 30 minutes: logged as "回歸(短暫離席)" (short absence), no AI call.
- Idle 30 minutes or more: logged as "回歸(長時離席)" (long absence) when you come back, and the AI guesses the reason.
- Boot: when the last row is a shutdown record, the shutdown row is removed and a boot row with the offline duration and an AI-guessed reason is written.

The state labels and the AI reason are written in Traditional Chinese (the prompt is in Chinese).

Idle time is measured with the Windows `GetLastInputInfo` call (checked every 15 seconds). No keystrokes, window titles or screenshots are captured.

## Where data is stored, and privacy

- The log and weekly backups (`activity_log_backup_YYYY-MM-DD.csv`, made automatically when the newest backup is 7 or more days old) stay in the `log/` folder next to the script. The log is never truncated.
- Nothing is uploaded by the tool itself, with one exception: when it asks the AI for a reason, the prompt contains the timestamps, the duration, your optional `TRACKER_USER_CONTEXT`, and **the last 200 lines of your log** (including earlier reasons), and it is sent to the Google Gemini API. If you do not want that, do not set `GOOGLE_API_KEY`; the tool still logs, and the reason column will show "分析中...".
- The log is a record of your daily routine. `log/` and `.env` are in `.gitignore`; never commit or share them.

## Requirements

- Windows 10/11 (uses pywin32 and Windows Task Scheduler)
- Python 3.10+ (the author uses 3.12)
- Python packages: `google-genai`, `pywin32`, `python-dotenv`
- Optional: a Gemini API key from Google AI Studio

## Install

```
pip install -r requirements.txt
copy .env.example .env
```

Edit `.env`:

| Variable | Meaning |
| --- | --- |
| `GOOGLE_API_KEY` | Gemini API key (optional; without it no AI reasons are produced). It may also be set as a system environment variable. |
| `GEMINI_MODEL` | Model name; default `gemini-3-flash-preview`. |
| `TRACKER_USER_CONTEXT` | Optional one-line description of you, added to the prompt. |

Register the startup task (runs at logon with highest privilege, using `pythonw.exe`, then starts it immediately):

```
python setup_scheduler.py
```

This creates a Windows scheduled task named `UserActivityTracker`. You may need to run it from an elevated terminal. Note that `setup_scheduler.py` only warns if the `GOOGLE_API_KEY` system environment variable is missing; a key in `.env` is still loaded by the tracker.

## Usage

- Run in the foreground for testing: `python activity_tracker.py`
- Restart the background task after changing `.env` or the code: `schtasks /run /tn "UserActivityTracker"`
- View records: open `log/activity_log.csv` in Excel or any editor. You can correct reasons by hand; the last 200 rows (including your corrections) are fed to the AI as context.

## Uninstall

```
schtasks /delete /tn "UserActivityTracker" /f
```

Then end any running `pythonw.exe` process for the tracker (Task Manager) and delete the folder. Delete `log/` if you no longer want the records.

## Verify your download

Download `activity-tracker-v1.0.0.zip` and `SHA256SUMS.txt` from [Releases](https://github.com/shaoen901109/activity-tracker/releases) (use the version you actually downloaded).

1. Compare the checksum in PowerShell:

   ```powershell
   Get-FileHash .\activity-tracker-v1.0.0.zip -Algorithm SHA256
   ```

   The `Hash` must match the string in `SHA256SUMS.txt` (letter case does not matter).

2. Verify where it was built (needs [GitHub CLI](https://cli.github.com/)):

   ```powershell
   gh attestation verify .\activity-tracker-v1.0.0.zip --repo shaoen901109/activity-tracker
   ```

   A successful result means GitHub Actions built this zip from this repository's source and it was not swapped along the way.

Commits marked **Verified** on GitHub are signed by the author.

## Credits

| Purpose | Component | License |
|---|---|---|
| AI summaries of screen activity | Google Gemini API via [google-genai](https://github.com/googleapis/python-genai) | SDK: Apache-2.0; API: Google terms |
| Windows API access | [pywin32](https://github.com/mhammond/pywin32) | PSF |
| Reading `.env` settings | [python-dotenv](https://github.com/theskumar/python-dotenv) | BSD-3-Clause |
| Scheduling | Windows Task Scheduler (`schtasks`) | part of Windows |

Developed with the help of [Claude Code](https://claude.com/claude-code) (Anthropic).

## Author

- Website: https://shaoenstudio.com
- Email: shaoenstudio@gmail.com
- GitHub: [@shaoen901109](https://github.com/shaoen901109)

## License

MIT, see [LICENSE](LICENSE).
