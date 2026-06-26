' raidlootmatrix_mplus_run.vbs
' Launches raidlootmatrix_mplus_silent.bat with a completely hidden window.
' Called by Windows Task Scheduler instead of cmd.exe directly.
Dim shell, fso, scriptDir, bat
Set shell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)
bat = scriptDir & "\raidlootmatrix_mplus_silent.bat"
' WindowStyle 0 = hidden, bWaitOnReturn = True
shell.Run "cmd.exe /c """ & bat & """", 0, True
Set shell = Nothing
Set fso = Nothing
