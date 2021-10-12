import requests
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