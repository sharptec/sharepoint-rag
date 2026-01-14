#!/bin/bash

# Configuration
APP_DIR="/Users/srinivasansankaranarayanan/Documents/Projects/antigravity/sharepoint_rag"
VENV_DIR="$APP_DIR/venv"
PID_FILE="$APP_DIR/app.pid"
LOG_FILE="$APP_DIR/app.log"
PORT=8000

# Ensure we are in the app directory
cd "$APP_DIR" || { echo "Directory $APP_DIR not found"; exit 1; }

case "$1" in
    start)
        if [ -f "$PID_FILE" ] && kill -0 $(cat "$PID_FILE") 2>/dev/null; then
            echo "Application is already running (PID: $(cat "$PID_FILE"))"
        else
            echo "Starting SharePoint RAG App..."
            source "$VENV_DIR/bin/activate"
            # Launch uvicorn in background
            PYTHONUNBUFFERED=1 nohup uvicorn api:app --host 127.0.0.1 --port $PORT > "$LOG_FILE" 2>&1 & 
            PID=$!
            echo $PID > "$PID_FILE"
            echo "Application started with PID $PID"
            echo "Logs are being written to $LOG_FILE"
            echo "Access at http://127.0.0.1:$PORT"
        fi
        ;;
    stop)
        if [ -f "$PID_FILE" ] && kill -0 $(cat "$PID_FILE") 2>/dev/null; then
            echo "Stopping application (PID: $(cat "$PID_FILE"))..."
            kill $(cat "$PID_FILE")
            rm "$PID_FILE"
            echo "Application stopped."
        else
            echo "Application is not running (or PID file missing)."
            # Cleanup stale pid file if it exists
            [ -f "$PID_FILE" ] && rm "$PID_FILE"
        fi
        ;;
    restart)
        $0 stop
        sleep 2
        $0 start
        ;;
    status)
        if [ -f "$PID_FILE" ] && kill -0 $(cat "$PID_FILE") 2>/dev/null; then
            echo "Application is running (PID: $(cat "$PID_FILE"))"
            echo "Tail of log file:"
            tail -n 5 "$LOG_FILE"
        else
            echo "Application is not running."
        fi
        ;;
    tail)
        tail -f "$LOG_FILE"
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status|tail}"
        exit 1
        ;;
esac
