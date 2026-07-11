# ExamLabPlatform - Windows 考试镜像配置脚本
# 以管理员身份运行 PowerShell，逐段粘贴执行

# ============================================================
# 第 1 段：配置远程桌面和防火墙
# ============================================================

# 启用远程桌面
Set-ItemProperty -Path 'HKLM:\System\CurrentControlSet\Control\Terminal Server' -Name "fDenyTSConnections" -Value 0
Enable-NetFirewallRule -DisplayGroup "Remote Desktop"
Write-Host "[OK] Remote Desktop enabled" -ForegroundColor Green

# 放行 RDP 3389（确保有规则）
$rdpRule = Get-NetFirewallRule -DisplayName "Remote Desktop" -ErrorAction SilentlyContinue
if (-not $rdpRule) {
    New-NetFirewallRule -DisplayName "Remote Desktop" -Direction Inbound -Protocol TCP -LocalPort 3389 -Action Allow
    Write-Host "[OK] RDP 3389 firewall rule added" -ForegroundColor Green
} else {
    Write-Host "[OK] RDP 3389 already allowed" -ForegroundColor Green
}

# 放行出站 SSH 22（连接 Linux 用）
New-NetFirewallRule -DisplayName "SSH Out" -Direction Outbound -Protocol TCP -RemotePort 22 -Action Allow -ErrorAction SilentlyContinue
Write-Host "[OK] SSH outbound allowed" -ForegroundColor Green


# ============================================================
# 第 2 段：安装 Chocolatey（Windows 包管理器）
# ============================================================

Set-ExecutionPolicy Bypass -Scope Process -Force
[System.Net.ServicePointManager]::SecurityProtocol = [System.Net.SecurityProtocolType]::Tls12
Invoke-Expression ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))
Write-Host "[OK] Chocolatey installed" -ForegroundColor Green


# ============================================================
# 第 3 段：安装必要软件
# ============================================================

# Google Chrome
choco install googlechrome -y
Write-Host "[OK] Chrome installed" -ForegroundColor Green

# OpenSSH Client（Windows Server 2019+ 可跳过）
$ssh = Get-WindowsCapability -Online | Where-Object Name -like 'OpenSSH.Client*'
if ($ssh.State -ne 'Installed') {
    Add-WindowsCapability -Online -Name OpenSSH.Client~~~~0.0.1.0
    Write-Host "[OK] OpenSSH Client installed" -ForegroundColor Green
} else {
    Write-Host "[OK] OpenSSH Client already installed" -ForegroundColor Green
}

# VS Code（可选，不需要可注释掉）
choco install vscode -y
Write-Host "[OK] VS Code installed" -ForegroundColor Green

# Notepad++（可选）
choco install notepadplusplus -y
Write-Host "[OK] Notepad++ installed" -ForegroundColor Green


# ============================================================
# 第 4 段：创建考试脚本目录
# ============================================================

New-Item -ItemType Directory -Path C:\ExamScripts -Force

@"
@echo off
echo ============================================
echo   Exam Lab - Linux Server Connections
echo ============================================
echo.
echo Usage: SSH to your assigned Linux servers
echo   ssh exam@<Linux-IP>
echo.
echo Your Linux IPs will be displayed on the
echo exam dashboard after login.
echo ============================================
pause
"@ | Out-File -FilePath C:\ExamScripts\exam-info.bat -Encoding ASCII

Write-Host "[OK] Exam scripts created in C:\ExamScripts" -ForegroundColor Green


# ============================================================
# 第 5 段：验证配置
# ============================================================

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "  Configuration Summary" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 检查远程桌面
$rdp = (Get-ItemProperty -Path 'HKLM:\System\CurrentControlSet\Control\Terminal Server').fDenyTSConnections
if ($rdp -eq 0) {
    Write-Host "[PASS] Remote Desktop: Enabled" -ForegroundColor Green
} else {
    Write-Host "[FAIL] Remote Desktop: Disabled" -ForegroundColor Red
}

# 检查防火墙
$fw = Get-NetFirewallRule -DisplayName "Remote Desktop" -ErrorAction SilentlyContinue
if ($fw.Enabled -eq 'True') {
    Write-Host "[PASS] RDP Firewall: Open" -ForegroundColor Green
} else {
    Write-Host "[FAIL] RDP Firewall: Not found" -ForegroundColor Red
}

# 检查 SSH 客户端
$sshPath = Get-Command ssh -ErrorAction SilentlyContinue
if ($sshPath) {
    Write-Host "[PASS] SSH Client: $($sshPath.Source)" -ForegroundColor Green
} else {
    Write-Host "[WARN] SSH Client: Not found (may need reboot)" -ForegroundColor Yellow
}

# 检查 Chrome
$chrome = Get-Item "C:\Program Files\Google\Chrome\Application\chrome.exe" -ErrorAction SilentlyContinue
if ($chrome) {
    Write-Host "[PASS] Chrome: Installed" -ForegroundColor Green
} else {
    Write-Host "[WARN] Chrome: Not found" -ForegroundColor Yellow
}

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "  All checks passed! Ready to Sysprep." -ForegroundColor Cyan
Write-Host "  Run: C:\Windows\System32\Sysprep\sysprep.exe /oobe /generalize /shutdown" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
