# encoding = utf-8
import os
import sys
import time
import datetime
import json
from datetime import datetime, timedelta
from ta_egnyte_connect_utility import *
import ta_egnyte_connect_constants as tec
import splunk.rest as rest
APP_NAME = os.path.abspath(__file__).split(os.sep)[-3]

import splunklib.client as client

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

def get_checkpoint(helper, key, start_date=None):
    checkpoint = helper.get_check_point(key)
    if checkpoint is None:
        checkpoint = {}
    
    if start_date is None or start_date == "":
        # If start_date is not provided or is an empty string, set it to 1 day ago
        start_date = datetime.utcnow() - timedelta(days=1)
        start_date = start_date.strftime('%Y-%m-%dT%H:%M:%SZ')
        checkpoint['start_date'] = start_date
    else:
        # If start_date is provided (not None and not empty), update it in the checkpoint
        checkpoint['start_date'] = start_date
    
    # Convert the start_date from the checkpoint to a datetime object
    start_date_dt = datetime.strptime(checkpoint['start_date'], '%Y-%m-%dT%H:%M:%SZ')
    
    # Calculate the date 7 days ago from the current date
    seven_days_ago = datetime.utcnow() - timedelta(days=7)
    
    # If the start_date from the checkpoint is older than 7 days ago, update it to the current date
    if start_date_dt <= seven_days_ago:
        checkpoint['start_date'] = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
           

    return checkpoint

def set_checkpoint(helper, key, checkpoint):
    return helper.save_check_point(key, checkpoint)

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
    checkpoint = get_checkpoint(helper, key=account_name, start_date=start_date) or dict()

    service = client.connect(host='localhost', port=8089,
                             username='admin', password='admin123')

    # Going to take access/refresh token if it is not available in the checkpoint
    if not checkpoint or str(checkpoint.get("code")) != str(code):
        helper.log_info("Checkpoint is not available or code changed from setup page. Hence requesting new access token.")
        try:
            response = generate_or_refresh_token(helper=helper, auth_url=auth_url, clientid=clientid, client_secret=client_secret, code=code, redirect_uri=REDIRECT_URI)
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
                checkpoint["code"] = code
                set_checkpoint(helper, key=account_name, checkpoint=checkpoint)

                storage_passwords = service.storage_passwords
                try:
                    # Retrieve existing password. This is safeguard in case of any racing condition.
                    # updating token is not necessary as it is deterministic based on client_id, secret & domain
                    body = storage_passwords.get(account_name + "/" + code)["body"]
                except HTTPError:
                    storage_passwords.create(response.get("access_token"), account_name + "/" + code)
                    helper.log_debug("New storage password entry created for {}".format(response.get("access_token")))
        except Exception as e:
            raise e
    
    checkpoint_for_input = get_checkpoint(helper, key=stanza_name, start_date=start_date)
    data_url = ""
    end_date = datetime.utcnow().isoformat() + "Z"
    data = {}
    
    start_date_done = True
    params = {}
    if checkpoint_for_input.get("nextCursor"):
        params['nextCursor']=checkpoint_for_input.get("nextCursor")

    token = get_token_from_secure_password(account_name, code, service, helper, checkpoint, checkpoint_for_input)

    while start_date_done:
        try:
            # collecting issues from the Egnyte server
            params['startDate'] = checkpoint_for_input.get("start_date")
            params['endDate'] = end_date
            params['auditType'] = data_type
            if params.get("nextCursor"):
                params.pop("startDate")
                params.pop("endDate")
            data_url = str(egnyte_domain_url) + "/pubapi/v2/audit/stream"

            data, response_text = collect_issues(helper, token, data_url, params)

            if data == 401:
                helper.log_error("Please generate new code and update the input with new code.")
                sys.exit(1)
            if data == 400:
                helper.log_error("Error while collecting data. The message from API: {}".format(data, response_text))
        except Exception as e:
            raise e
        if data.get("events", ""):
            events = data.get("events")
            event_count = len(events)
            event_time = time.time()
            index = stanza.get("index", "main")
            source = "egnyte"
            sourcetype = "egnyte:connect:audit:{}".format(mapping_data_type.get(data_type))
            moreEventsflag = data.get("moreEvents")
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

    checkpoint_for_input["nextCursor"] = data.get("nextCursor")
    set_checkpoint(helper, key=stanza_name, checkpoint=checkpoint_for_input)
