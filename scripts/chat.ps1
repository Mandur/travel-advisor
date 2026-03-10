#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Interactive chat REPL for the advisor agent.

.DESCRIPTION
    Starts a conversation loop against the advisor agent's /chat endpoint.
    Type your message and press Enter to send. Use 'exit' or 'quit' to leave,
    '/new' to start a fresh session, or '/help' for command reference.

.PARAMETER Url
    Base URL of the advisor agent. Defaults to http://localhost:8088 (docker-compose).

.PARAMETER SessionId
    Resume an existing session by providing its ID. A new UUID is generated when omitted.

.EXAMPLE
    .\scripts\chat.ps1
    .\scripts\chat.ps1 -Url https://advisor-agent.yourapp.azurecontainerapps.io
    .\scripts\chat.ps1 -SessionId "my-test-session"
#>
param(
    [string]$Url = "http://localhost:8088",
    [string]$SessionId = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

function Write-Banner {
    $width = 62
    $border = "-" * $width
    Write-Host ""
    Write-Host "  +$border+" -ForegroundColor Cyan
    Write-Host "  |$((" " * [int](($width - 20) / 2)))Advisor Agent Chat$((" " * [int][Math]::Ceiling(($width - 20) / 2)))|" -ForegroundColor Cyan
    Write-Host "  +$border+" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "  Endpoint : $Url" -ForegroundColor DarkGray
    Write-Host "  Commands : /new  start a new session" -ForegroundColor DarkGray
    Write-Host "           : /id   print current session ID" -ForegroundColor DarkGray
    Write-Host "           : exit  quit" -ForegroundColor DarkGray
    Write-Host ""
}

function New-SessionId {
    return [System.Guid]::NewGuid().ToString()
}

function Send-Message([string]$BaseUrl, [string]$SessId, [string]$UserMessage) {
    $body = @{
        message    = $UserMessage
        session_id = $SessId
    } | ConvertTo-Json -Compress

    $response = Invoke-RestMethod `
        -Uri        "$BaseUrl/chat" `
        -Method     POST `
        -Body       $body `
        -ContentType "application/json" `
        -TimeoutSec 120

    return $response
}

function Assert-AgentReachable([string]$BaseUrl) {
    try {
        $health = Invoke-RestMethod -Uri "$BaseUrl/health" -Method GET -TimeoutSec 8
        if ($health.status -ne "ok") { throw "Unhealthy response: $($health | ConvertTo-Json)" }
    }
    catch {
        Write-Host ""
        Write-Host "  X  Cannot reach advisor agent at $BaseUrl" -ForegroundColor Red
        Write-Host "     Make sure docker-compose is running:  docker-compose up" -ForegroundColor DarkRed
        Write-Host "     Or pass a different URL:  .\scripts\chat.ps1 -Url <url>" -ForegroundColor DarkRed
        Write-Host ""
        exit 1
    }
}

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

Assert-AgentReachable $Url
Write-Banner

$currentSessionId = if ($SessionId) { $SessionId } else { New-SessionId }
Write-Host "  Session  : $currentSessionId" -ForegroundColor DarkGray
Write-Host ""

while ($true) {
    # Prompt
    Write-Host "You  > " -ForegroundColor Green -NoNewline
    $userInput = Read-Host

    # Blank line - skip
    if ([string]::IsNullOrWhiteSpace($userInput)) { continue }

    # Built-in commands
    switch ($userInput.Trim().ToLower()) {
        "exit"  { Write-Host "`n  Goodbye!`n" -ForegroundColor Cyan; exit 0 }
        "quit"  { Write-Host "`n  Goodbye!`n" -ForegroundColor Cyan; exit 0 }
        "/new"  {
            $currentSessionId = New-SessionId
            Write-Host "  *  New session started: $currentSessionId`n" -ForegroundColor Yellow
            continue
        }
        "/id"   {
            Write-Host "  Session ID: $currentSessionId`n" -ForegroundColor DarkGray
            continue
        }
        "/help" {
            Write-Host ""
            Write-Host "  Commands:" -ForegroundColor Cyan
            Write-Host "    /new   Start a fresh conversation session" -ForegroundColor DarkGray
            Write-Host "    /id    Print the current session ID" -ForegroundColor DarkGray
            Write-Host "    exit   Quit the chat" -ForegroundColor DarkGray
            Write-Host ""
            continue
        }
    }

    # Send to agent
    try {
        Write-Host "Agent> " -ForegroundColor Cyan -NoNewline
        $result = Send-Message $Url $currentSessionId $userInput

        # Update session ID in case the agent issued a new one
        if ($result.session_id) { $currentSessionId = $result.session_id }

        # Word-wrap the reply to 80 chars, indented to align with "Agent> "
        $reply    = $result.reply
        $maxWidth = 80
        $indent   = "       "   # 7 spaces - same width as "Agent> "

        $words  = $reply -split ' '
        $line   = ""
        $first  = $true

        foreach ($word in $words) {
            # Handle embedded newlines
            $parts = $word -split "`n"
            foreach ($i in 0..($parts.Count - 1)) {
                $part = $parts[$i]
                if (($line.Length + $part.Length + 1) -gt $maxWidth -and $line.Length -gt 0) {
                    if ($first) { Write-Host $line -ForegroundColor White; $first = $false }
                    else        { Write-Host "$indent$line" -ForegroundColor White }
                    $line = $part
                } else {
                    $line = if ($line) { "$line $part" } else { $part }
                }
                # Newline forces a flush
                if ($i -lt ($parts.Count - 1)) {
                    if ($first) { Write-Host $line -ForegroundColor White; $first = $false }
                    else        { Write-Host "$indent$line" -ForegroundColor White }
                    $line = ""
                }
            }
        }
        if ($line) {
            if ($first) { Write-Host $line -ForegroundColor White }
            else        { Write-Host "$indent$line" -ForegroundColor White }
        }
        Write-Host ""
    }
    catch {
        Write-Host "" 
        Write-Host "  X  Request failed: $_" -ForegroundColor Red
        Write-Host ""
    }
}
