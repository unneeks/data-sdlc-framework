#!/usr/bin/env bash
# One-click Launcher for Agentic Data Engineering Platform (API + Web Frontend)

echo "🚀 Starting Agentic Data Engineering Platform..."

# Start FastAPI backend
echo "📦 Launching FastAPI backend server on http://localhost:8000..."
python3 apps/api/main.py &
API_PID=$!

# Start Vite frontend server
echo "💻 Launching React Web UI on http://localhost:3000..."
cd apps/web && npm run dev &
WEB_PID=$!

echo "✨ System is live!"
echo "  • Web UI: http://localhost:3000"
echo "  • REST API: http://localhost:8000"
echo "  • Gemini CLI: ./apps/cli/gemini-agent"
echo "  • Copilot CLI: ./apps/cli/gh-copilot-agent"
echo ""
echo "Press Ctrl+C to terminate all services."

trap "kill $API_PID $WEB_PID 2>/dev/null" EXIT
wait
