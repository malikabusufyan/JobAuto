# Launches your real Chrome with a remote-debugging port open, so JobAuto can attach to
# this already-running window (see CHROME_REMOTE_DEBUGGING_PORT in .env / jobauto/browser.py)
# instead of opening a separate browser process. Run this instead of your normal Chrome
# shortcut when you plan to use JobAuto's search/apply steps; a regular double-click on
# Chrome elsewhere still works exactly as before.
#
# Usage: right-click -> Run with PowerShell, or from a terminal:
#   powershell -ExecutionPolicy Bypass -File scripts\launch-chrome-debug.ps1
#
# IMPORTANT: Chrome only honors --remote-debugging-port on a fresh start. If any Chrome
# window is already open, this will just open a new window in that same running instance
# and silently ignore the flag. Close every Chrome window first, then run this script once -
# after that you can leave the resulting window open all day and JobAuto will attach to it.

$Port = 9222
$Profile = "Default"   # match CHROME_PROFILE_DIRECTORY in .env

$ChromePaths = @(
    "$env:ProgramFiles\Google\Chrome\Application\chrome.exe",
    "${env:ProgramFiles(x86)}\Google\Chrome\Application\chrome.exe"
)
$Chrome = $ChromePaths | Where-Object { Test-Path $_ } | Select-Object -First 1

if (-not $Chrome) {
    Write-Error "Could not find chrome.exe in the usual install locations."
    exit 1
}

Write-Host "Starting Chrome with remote debugging on port $Port (profile: $Profile)..."
Start-Process -FilePath $Chrome -ArgumentList "--remote-debugging-port=$Port", "--profile-directory=$Profile"
