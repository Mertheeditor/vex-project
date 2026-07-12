#!/bin/bash
# DEPRECATED: Replaced by pre_tool_guard.py. Not registered in Claude settings.
# Pre-tool-use hook for Vex agent boundary enforcement
# Validates tool usage against agent restrictions

set -euo pipefail

# This hook is called by the agent system before certain tool uses
# Environment variables provided:
# AGENT_NAME - name of the agent invoking the tool
# TOOL_NAME - name of the tool being invoked
# TOOL_ARGS - JSON args for the tool

AGENT="${AGENT_NAME:-unknown}"
TOOL="${TOOL_NAME:-unknown}"
ARGS="${TOOL_ARGS:-{}"

# Read-only agents
READ_ONLY_AGENTS="architect security-auditor qa-engineer diff-auditor"

# Builder agents with path restrictions
BACKEND_BUILDER="backend-builder"
FRONTEND_BUILDER="frontend-builder"

# Check if agent is read-only
if [[ "$READ_ONLY_AGENTS" =~ (^| )"$AGENT"($| ) ]]; then
    # Block write tools for read-only agents
    case "$TOOL" in
        Write|Edit|NotebookEdit)
            echo "BLOCKED: Agent '$AGENT' is read-only, cannot use '$TOOL'" >&2
            exit 1
            ;;
    esac
fi

# Check builder path restrictions
if [[ "$AGENT" == "$BACKEND_BUILDER" ]]; then
    # Extract file path from args
    FILE=$(echo "$ARGS" | python3 -c "import sys, json; print(json.load(sys.stdin).get('file_path', ''))" 2>/dev/null || echo "")
    if [[ -n "$FILE" && ! "$FILE" =~ ^vex-backend/ ]]; then
        echo "BLOCKED: backend-builder can only write to vex-backend/, got: $FILE" >&2
        exit 1
    fi
fi

if [[ "$AGENT" == "$FRONTEND_BUILDER" ]]; then
    FILE=$(echo "$ARGS" | python3 -c "import sys, json; print(json.load(sys.stdin).get('file_path', ''))" 2>/dev/null || echo "")
    if [[ -n "$FILE" && ! "$FILE" =~ ^vex-app/ ]]; then
        echo "BLOCKED: frontend-builder can only write to vex-app/, got: $FILE" >&2
        exit 1
    fi
fi

# Check for secret-like patterns in write operations
if [[ "$TOOL" =~ ^(Write|Edit)$ ]]; then
    CONTENT=$(echo "$ARGS" | python3 -c "import sys, json; print(json.load(sys.stdin).get('content', '') or json.load(sys.stdin).get('new_string', ''))" 2>/dev/null || echo "")
    if [[ -n "$CONTENT" ]] && echo "$CONTENT" | grep -qiE '(api[_-]?key|secret|token|password)\s*[=:]\s*["\047][^"\047]{10,}'; then
        echo "BLOCKED: Possible secret detected in write content" >&2
        exit 1
    fi
fi

# Allow all other cases
exit 0