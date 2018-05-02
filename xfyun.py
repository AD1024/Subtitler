import hashlib
import time
import requests
import base64
import contextlib
import json

URL = 'http://api.xfyun.cn/v1/service/v1/iat'


class Speech:

    def asr(self, data):
        base64_audio = base64.b64encode(data)
        app_info = json.load(open('subtitler_apikey.json', 'r'))
        x_appid = app_info['app_id']
        api_key = base64.b64decode(app_info['api_key']).decode()
        x_time = int(int(round(time.time() * 1000)) / 1000)
        param = {'engine_type': 'sms16k', 'aue': 'raw'}
        x_param = base64.b64encode(json.dumps(param).replace(' ', '').encode()).decode()
        x_checksum = hashlib.md5((api_key + str(x_time) + x_param).encode()).hexdigest()
        body = {'audio': base64_audio}
        x_header = {
            'X-Appid': x_appid,
            'X-CurTime': str(x_time),
            'X-Param': x_param,
            'X-CheckSum': x_checksum
        }
        result = requests.post(URL, data=body, headers=x_header)
        return result.text
