#!/usr/bin/env bash
# Interactive chat REPL for the advisor agent.
#
# Usage:
#   ./scripts/chat.sh
#   ./scripts/chat.sh --url https://advisor-agent.yourapp.azurecontainerapps.io
#   ./scripts/chat.sh --session-id "my-test-session"
#
# Commands during chat:
#   /new   start a fresh session
#   /id    print current session ID
#   /help  show command reference
#   exit   quit

set -euo pipefail

# ---------------------------------------------------------------------------
# Defaults & arg parsing
# ---------------------------------------------------------------------------

URL="http://localhost:8088"
SESSION_ID=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --url)         URL="$2";        shift 2 ;;
        --session-id)  SESSION_ID="$2"; shift 2 ;;
        *) echo "Unknown option: $1" >&2; exit 1 ;;
    esac
done

# ---------------------------------------------------------------------------
# Colour helpers (gracefully degrade if no terminal)
# ---------------------------------------------------------------------------

if [ -t 1 ]; then
    C_CYAN="\033[0;36m"
    C_GREEN="\033[0;32m"
    C_YELLOW="\033[0;33m"
    C_WHITE="\033[0;97m"
    C_GRAY="\033[0;90m"
    C_RED="\033[0;31m"
    C_RESET="\033[0m"
else
    C_CYAN="" C_GREEN="" C_YELLOW="" C_WHITE="" C_GRAY="" C_RED="" C_RESET=""
fi

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

new_session_id() {
    # Use uuidgen if available, fall back to /proc/sys/kernel/random/uuid
    if command -v uuidgen &>/dev/null; then
        uuidgen | tr '[:upper:]' '[:lower:]'
    else
        cat /proc/sys/kernel/random/uuid
    fi
}

print_banner() {
    local border
    border="$(printf '─%.0s' {1..62})"
    echo ""
    echo -e "  ${C_CYAN}┌${border}┐${C_RESET}"
    echo -e "  ${C_CYAN}│$(printf '%21s' '')Advisor Agent Chat$(printf '%21s' '')│${C_RESET}"
    echo -e "  ${C_CYAN}└${border}┘${C_RESET}"
    echo ""
    echo -e "  ${C_GRAY}Endpoint : ${URL}${C_RESET}"
    echo -e "  ${C_GRAY}Commands : /new  start a new session${C_RESET}"
    echo -e "  ${C_GRAY}         : /id   print current session ID${C_RESET}"
    echo -e "  ${C_GRAY}         : exit  quit${C_RESET}"
    echo ""
}

assert_agent_reachable() {
    local health_status
    health_status=$(curl -sf --max-time 8 "${URL}/health" 2>/dev/null) || {
        echo ""
        echo -e "  ${C_RED}✘  Cannot reach advisor agent at ${URL}${C_RESET}"
        echo -e "  ${C_RED}   Make sure docker-compose is running:  docker-compose up${C_RESET}"
        echo -e "  ${C_RED}   Or pass a different URL:  ./scripts/chat.sh --url <url>${C_RESET}"
        echo ""
        exit 1
    }

    local status
    status=$(echo "$health_status" | python3 -c "import sys,json; print(json.load(sys.stdin).get('status',''))" 2>/dev/null || true)
    if [[ "$status" != "ok" ]]; then
        echo ""
        echo -e "  ${C_RED}✘  Unhealthy response from agent: ${health_status}${C_RESET}"
        echo ""
        exit 1
    fi
}

send_message() {
    local base_url="$1"
    local sess_id="$2"
    local user_msg="$3"

    local body
    body=$(printf '{"message":%s,"session_id":%s}' \
        "$(python3 -c "import sys,json; print(json.dumps(sys.stdin.read()))" <<< "$user_msg")" \
        "$(python3 -c "import sys,json; print(json.dumps(sys.stdin.read()))" <<< "$sess_id")")

    curl -sf --max-time 120 \
        -X POST "${base_url}/chat" \
        -H "Content-Type: application/json" \
        -d "$body"
}

# Word-wrap text to $1 columns, with $2 as the indent prefix for continuation lines.
word_wrap() {
    local max_width="$1"
    local indent="$2"
    local text="$3"
    local first=true

    # Process line-by-line (handles embedded \n in the reply)
    while IFS= read -r paragraph; do
        local line=""
        for word in $paragraph; do
            if (( ${#line} + ${#word} + 1 > max_width && ${#line} > 0 )); then
                if $first; then
                    echo -e "${C_WHITE}${line}${C_RESET}"
                    first=false
                else
                    echo -e "${C_WHITE}${indent}${line}${C_RESET}"
                fi
                line="$word"
            else
                line="${line:+$line }$word"
            fi
        done
        # Flush remaining content
        if [[ -n "$line" ]]; then
            if $first; then
                echo -e "${C_WHITE}${line}${C_RESET}"
                first=false
            else
                echo -e "${C_WHITE}${indent}${line}${C_RESET}"
            fi
        fi
    done <<< "$text"
}

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

assert_agent_reachable
print_banner

CURRENT_SESSION_ID="${SESSION_ID:-$(new_session_id)}"
echo -e "  ${C_GRAY}Session  : ${CURRENT_SESSION_ID}${C_RESET}"
echo ""

while true; do
    echo -ne "${C_GREEN}You  > ${C_RESET}"
    IFS= read -r user_input || { echo ""; break; }  # handle Ctrl-D

    # Skip blank input
    [[ -z "${user_input// }" ]] && continue

    # Built-in commands
    case "${user_input}" in
        exit|quit)
            echo -e "\n  Goodbye!\n"
            exit 0
            ;;
        /new)
            CURRENT_SESSION_ID="$(new_session_id)"
            echo -e "  ${C_YELLOW}↺  New session started: ${CURRENT_SESSION_ID}${C_RESET}\n"
            continue
            ;;
        /id)
            echo -e "  ${C_GRAY}Session ID: ${CURRENT_SESSION_ID}${C_RESET}\n"
            continue
            ;;
        /help)
            echo ""
            echo -e "  ${C_CYAN}Commands:${C_RESET}"
            echo -e "  ${C_GRAY}  /new   Start a fresh conversation session${C_RESET}"
            echo -e "  ${C_GRAY}  /id    Print the current session ID${C_RESET}"
            echo -e "  ${C_GRAY}  exit   Quit the chat${C_RESET}"
            echo ""
            continue
            ;;
    esac

    # Send to agent
    echo -ne "${C_CYAN}Agent> ${C_RESET}"
    response=$(send_message "$URL" "$CURRENT_SESSION_ID" "$user_input" 2>&1) || {
        echo ""
        echo -e "  ${C_RED}✘  Request failed: ${response}${C_RESET}"
        echo ""
        continue
    }

    # Update session ID if the agent issued a new one
    new_sid=$(python3 -c "import sys,json; d=json.loads(sys.stdin.read()); print(d.get('session_id',''))" <<< "$response" 2>/dev/null || true)
    [[ -n "$new_sid" ]] && CURRENT_SESSION_ID="$new_sid"

    # Extract and display the reply
    reply=$(python3 -c "import sys,json; d=json.loads(sys.stdin.read()); print(d.get('reply',''))" <<< "$response" 2>/dev/null || echo "$response")

    word_wrap 80 "       " "$reply"
    echo ""
done
