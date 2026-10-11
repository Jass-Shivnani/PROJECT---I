' ==============================================================================
'   DIONE AI -- Native Background Windows Launcher
'   Launches the Edge WebView2 Studio Desktop App silently without terminal popup
' ==============================================================================

Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
strPath = fso.GetParentFolderName(WScript.ScriptFullName)

Dim pyExe
If fso.FileExists(strPath & "\.venv\Scripts\pythonw.exe") Then
    pyExe = strPath & "\.venv\Scripts\pythonw.exe"
ElseIf fso.FileExists(strPath & "\.venv\Scripts\python.exe") Then
    pyExe = strPath & "\.venv\Scripts\python.exe"
Else
    pyExe = "pythonw"
End If

cmd = """" & pyExe & """ -m server.cli.dione_cli app"
WshShell.CurrentDirectory = strPath
WshShell.Run cmd, 0, False
