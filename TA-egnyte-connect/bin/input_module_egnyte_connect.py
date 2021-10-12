# encoding = utf-8
import os
import sys
import time
import datetime
import json
from solnlib.splunkenv import get_splunkd_uri
from solnlib.credentials import (CredentialManager, CredentialNotExistException)
from datetime import datetime, timedelta
from ta_egnyte_connect_utility import *
import ta_egnyte_connect_constants as tec
import splunk.rest as rest
APP_NAME = os.path.abspath(__file__).split(os.sep)[-3]

'''
    IMPORTANT
    Edit only the validate_input and collect_events functions.
    Do not edit any other part in this file.
    This file is generated only once when creating the modular input.
'''
'''
# For advanced users, if you want to create single instance mod input, uncomment this method.
def use_single_instance_mode():
    return True
'''

def validate_input(helper, definition):
    """Implement your own validation logic to validate the input stanza configurations"""
    # This example accesses the modular input variable
    # data_type = definition.parameters.get('data_type', None)
    # global_account = definition.parameters.get('global_account', None)
    pass

def get_checkpoint(helper, stanza_name):
    return helper.get_check_point(stanza_name)

def set_checkpoint(helper, stanza_name, state):
    return helper.save_check_point(stanza_name, state)

def collect_events(helper, ew):
    # getting setup parameters
    input_name = helper.get_input_stanza_names()
    input_stanza = helper.get_input_stanza()
    global_account = helper.get_arg('global_account')
    clientid = input_stanza[input_name]['global_account']['client_id']
    account_name = input_stanza[input_name]['global_account']['name']
    client_secret = input_stanza[input_name]['global_account']['client_secret']
    code = input_stanza[input_name]['global_account']['password']
    stanza_name = list(input_stanza.keys())[0]
    stanza = list(input_stanza.values())[0]
    session_key = helper.context_meta['session_key']
    egnyte_domain_url = helper.get_arg('egnyte_domain_url')
    egnyte_domain_url = "https://{}".format(egnyte_domain_url)
    start_date = helper.get_arg('start_date')
    data_type = helper.get_arg('data_type')
    number_of_events = 0
    REDIRECT_URI = tec.REDIRECT_URI
    auth_url = str(egnyte_domain_url) + "/puboauth/token"
    mapping_data_type={"FILE_AUDIT": "file", "PERMISSION_AUDIT": "permission", "LOGIN_AUDIT": "login", "USER_AUDIT": "user", "WG_SETTINGS_AUDIT": "wg_settings", "GROUP_AUDIT": "group", "WORKFLOW_AUDIT": "workflow"}
    checkpoint = get_checkpoint(helper, account_name) or dict()
    # Going to take access/refresh token if it is not available in the checkpoint
    if not checkpoint or str(checkpoint.get("code")) != str(code):
        helper.log_info("Checkpoint is not available or code changed from setup page. Hence requesting new access token.")
        state = get_checkpoint(helper, account_name) or dict()
        try:
            response = generate_or_refresh_token(helper=helper, auth_url=auth_url, clientid=clientid, client_secret=client_secret, code=code, redirect_uri=REDIRECT_URI)
            helper.log_info("Checkpoint is not available or code changed from setup page. Hence requested new access token.")
            if response.status_code == 400:
                helper.log_error("Error while getting access/refresh token error")
                helper.log_error("Please generate new code and update the input with new code.")
                postargs = {
                        'severity': "error",
                        'name': APP_NAME,
                        'value': "Egnyte Collaborate Add-on: Please generate new code and update the input with new code."
                }
                rest.simpleRequest('/services/messages',
                                session_key, postargs=postargs)
                return
            else:
                response = response.json()
                state["access_token"] = response.get("access_token")
                state["code"] = code
                set_checkpoint(helper, account_name, state)
        except Exception as e:
            raise e
    checkpoint = get_checkpoint(helper, stanza_name) or dict()
    checkpoint_token = get_checkpoint(helper, account_name) or dict()
    data_url = ""
    end_date = datetime.utcnow().isoformat() + "Z"
    data = {}
    if checkpoint.get("start_date"):
        start_date = checkpoint.get("start_date")
    if not start_date:
        start_date = datetime.utcnow() - timedelta(days=1)
        start_date = start_date.isoformat()  + "Z"
        helper.log_debug("Setting up the default start date to 24 hours from now. Setting Value: {}".format(start_date))
    start_date_done = True
    params = {}
    while start_date_done:
        try:
            # collecting issues from the Egnyte server
            params['startDate'] = start_date
            params['endDate'] = end_date
            params['auditType'] = data_type
            if params.get("nextCursor"):
                params.pop("startDate")
                params.pop("endDate")
            data_url = str(egnyte_domain_url) + "/pubapi/v2/audit/stream"
            helper.log_debug("Final URL for Egnyte Connect is:{} and Params is:{}".format(data_url, params))
            data, response_text = collect_issues(helper, checkpoint_token.get('access_token'), data_url, params)
            if data == 401:
                helper.log_error("Please generate new code and update the input with new code.")
                sys.exit(1)
            if data == 400:
                helper.log_error("Error while collecting data. The message from API: {}".format(response_text))
        except Exception as e:
            raise e
        if data.get("events", ""):
            events = data.get("events")
            event_count = len(events)
            event_time = time.time()
            index = stanza.get("index", "main")
            source = "egnyte"
            sourcetype = "egnyte:connect:audit:{}".format(mapping_data_type.get(data_type))
            for i in events:
                event = helper.new_event(data=json.dumps(i), time=event_time, host=None, index=index,source=source, sourcetype=sourcetype, done=True,unbroken=True)
                ew.write_event(event)
            number_of_events = number_of_events + event_count
            if data.get("nextCursor"):
                params['nextCursor'] = data.get("nextCursor")
        else:
            start_date_done = False
            helper.log_info("Total indexed events into Splunk: {}".format(number_of_events))
        time.sleep(1)

    checkpoint["start_date"] = end_date
    set_checkpoint(helper, stanza_name, checkpoint)
