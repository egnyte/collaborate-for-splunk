import requests
from splunklib.binding import HTTPError, ResponseReader
import xml.etree.ElementTree as ET


def generate_or_refresh_token(helper=None, auth_url=None, clientid=None, client_secret=None, code=None, refresh_token=None, redirect_uri=None):
    if code:
        payload = {"client_id": clientid, "client_secret": client_secret, "grant_type": "authorization_code", 
                  "redirect_uri": redirect_uri, "code": code}
    else:
        payload = {"client_id": clientid, "client_secret": client_secret, "grant_type": "refresh_token", 
                  "redirect_uri": redirect_uri, 
                  "refresh_token": refresh_token}
    response = requests.post(url=auth_url, data=payload,verify=True)
    helper.log_info("Generating token and response is there. Status Code: {}".format(response.status_code))

    return response


def get_token_from_secure_password(account_name, code, service, helper, checkpoint, checkpoint_for_input):
    storage_passwords = service.storage_passwords
    try:
        response = storage_passwords.get(account_name + "/" + code)
        reader: ResponseReader = ResponseReader(response["body"])

        xml_response_str: str = reader.read().decode("UTF-8")
        start_tag = "<s:key name=\"clear_password\">"
        end_tag = "</s:key>"
        # getting index of substrings
        idx1 = xml_response_str.index(start_tag)

        xml_data_substr = xml_response_str[idx1:]
        idx2_from_substring = xml_data_substr.index(end_tag)
        idx2 = idx1 + idx2_from_substring

        token: str = ''
        # getting elements in between
        for idx in range(idx1 + len(start_tag), idx2):
            token = token + xml_response_str[idx]

        helper.log_debug("Access token in StoragePassword already exist. Erasing eventual access token from checkpoint.")
        checkpoint_for_input.pop("access_token", None)

        return token

    except HTTPError:
        helper.log_debug("Unable to find access token in StoragePassword engine. Performing one time "
                        "migration from checkpoint.")
        token = checkpoint.get('access_token')
        try:
            storage_passwords.create(token, account_name + "/" + code)
            helper.log_debug("Access token migrated.")
        except HTTPError:
            helper.log_debug("Access token already exist. Erasing access token from checkpoint.")
            checkpoint_for_input.pop("access_token", None)


def collect_issues(helper, access_token, data_url, params):
    headers = {"Authorization": "Bearer " + str(access_token)}
    response_data = helper.send_http_request(data_url, "GET", parameters=params, payload=None,
                                          headers=headers, cookies=None, verify=True, cert=None,
                                          timeout=None, use_proxy=True)
    helper.log_info("Collecting data and response is there. Status Code: {}".format(response_data.status_code))
    helper.log_debug("Collecting data and response is there. URL is: {} and params:{}".format(data_url, params))
    if response_data.status_code == 200:
        return response_data.json(), None
    if response_data.status_code == 401:
        return response_data.status_code, None
    if response_data.status_code == 400:
        return response_data.status_code, response_data.text
    else:
        return response_data.json()