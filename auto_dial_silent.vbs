' 静默启动自动拨号程序(无窗口)
Set objShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

' 获取脚本所在目录
scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)

' 切换到脚本目录并运行Python程序
objShell.CurrentDirectory = scriptDir
objShell.Run "py auto_dial.py", 0, False

Set objShell = Nothing
Set fso = Nothing