' raidlootmatrix_watcher_run.vbs
' Launches RLM_Companion.exe --watch-wow with a completely hidden window.
Dim shell, fso, scriptDir, exe
Set shell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)

If fso.FileExists(scriptDir & "\RLM_Companion.exe") Then
    exe = """" & scriptDir & "\RLM_Companion.exe"" --watch-wow"
Else
    exe = "pythonw """ & scriptDir & "\rlm_importer_ui.py"" --watch-wow"
End If

shell.Run exe, 0, False
Set shell = Nothing
Set fso = Nothing
