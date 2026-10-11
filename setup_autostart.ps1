# 校园网自动认证 —— 开机自启设置脚本
# 创建 Windows 计划任务：登录后后台运行 campus_auth.py --loop 30
$ErrorActionPreference = "Stop"

# 本脚本所在目录（脚本与 campus_auth.py 同目录）
$scriptDir  = Split-Path -Parent $MyInvocation.MyCommand.Path
$scriptPath = Join-Path $scriptDir "campus_auth.py"
$workDir    = $scriptDir

# Python 解释器路径（pythonw.exe 后台运行无控制台；若不在 PATH 中，请改成绝对路径）
$pythonw = "pythonw.exe"

$taskName = "CampusAuth"

$action  = New-ScheduledTaskAction -Execute $pythonw -Argument ('"' + $scriptPath + '" --loop 30') -WorkingDirectory $workDir
$trigger = New-ScheduledTaskTrigger -AtLogOn -User "$env:USERDOMAIN\$env:USERNAME"
Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Description "校园网自动认证（Dr.COM）" -Force

Write-Output "已创建开机自启任务：$taskName"
