#!/bin/bash
# =============================================
#   Auto-Restart Watchdog - Emote Bot
#   يشغل البوت وإذا وقف يرجعه تلقائي
# =============================================

BOT_SCRIPT="app.py"
LOG_FILE="bot_log.txt"
MAX_RESTARTS=100
RESTART_COUNT=0

cd "$(dirname "$0")"

echo "========================================" | tee -a "$LOG_FILE"
echo "  Watchdog Started - $(date)" | tee -a "$LOG_FILE"
echo "  Monitoring: $BOT_SCRIPT" | tee -a "$LOG_FILE"
echo "  Max Restarts: $MAX_RESTARTS" | tee -a "$LOG_FILE"
echo "========================================" | tee -a "$LOG_FILE"

while [ $RESTART_COUNT -lt $MAX_RESTARTS ]; do
    
    echo "" | tee -a "$LOG_FILE"
    echo "[Watchdog] Starting bot... (Restart #$RESTART_COUNT) - $(date)" | tee -a "$LOG_FILE"
    
    # تشغيل البوت
    python "$BOT_SCRIPT" 2>&1 | tee -a "$LOG_FILE"
    EXIT_CODE=$?
    
    RESTART_COUNT=$((RESTART_COUNT + 1))
    
    echo "" | tee -a "$LOG_FILE"
    echo "[Watchdog] Bot stopped with exit code: $EXIT_CODE - $(date)" | tee -a "$LOG_FILE"
    
    # انتظار قبل إعادة التشغيل
    echo "[Watchdog] Restarting in 5 seconds..." | tee -a "$LOG_FILE"
    sleep 5
    
done

echo "[Watchdog] Max restarts reached ($MAX_RESTARTS). Stopping." | tee -a "$LOG_FILE"
