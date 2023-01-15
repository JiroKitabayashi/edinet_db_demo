from flask import request
from flask import session as user_session # SQLのsessionと名前被りするため、user_sessionとする。

def form_clear():
    clear_flag = request.args.get('form_clear', default = 0, type = int)
    if clear_flag:
        user_session['request_form'] = None