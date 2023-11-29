import random

from splunk_aoblib.rest_migration import ConfigMigrationHandler
from splunktaucclib.rest_handler.endpoint import SingleModel
from copy import deepcopy
from splunk import rest
ACCOUNT_STANZA_NAME = None
APP_NAME = "TA-egnyte-connect"

class AccountModel(SingleModel):
    """Account Model."""

    def validate(self, name, data, existing=None):
        """To get stanza name for future use as it can only be retrive from here."""
        global ACCOUNT_STANZA_NAME, INDEX_NAME, ENDPOINT
        ACCOUNT_STANZA_NAME = name
        INDEX_NAME = data.get("index", "main")
        ENDPOINT = data.get("egnyte_domain", "")
        super(AccountModel, self).validate(name, data, existing)

class AccountHandler(ConfigMigrationHandler):
    """Account Handler."""

    def handleCreate(self, confInfo):
        """Handle creation of account in config file."""
        super(AccountHandler, self).handleCreate(confInfo)
        self.create_inputs()

    def create_inputs(self):
        """Create given types of inputs into inputs.conf file."""

        modular_input_name = "egnyte_connect"
        input_type_list = ["FILE_AUDIT","PERMISSION_AUDIT","LOGIN_AUDIT", "USER_AUDIT","WG_SETTINGS_AUDIT", "GROUP_AUDIT", "WORKFLOW_AUDIT"]
        for i in input_type_list:
            if i == "WG_SETTINGS_AUDIT":
                input_stanza = {
                    "name": "{}://{}_{}".format(modular_input_name, ACCOUNT_STANZA_NAME, "CONFIGURATION_AUDIT"),
                    "global_account": ACCOUNT_STANZA_NAME,
                    "disabled": "true",
                    "egnyte_domain_url": ENDPOINT,
                    "index": INDEX_NAME,
                    "data_type": i,
                    "interval": str(random.randint(300, 600))
                }
            else:
                input_stanza = {
                        "name": "{}://{}_{}".format(modular_input_name, ACCOUNT_STANZA_NAME, i),
                        "global_account": ACCOUNT_STANZA_NAME,
                        "disabled": "true",
                        "egnyte_domain_url": ENDPOINT,
                        "index": INDEX_NAME,
                        "data_type": i,
                        "interval": str(random.randint(300, 600))
                    }

            # Using Splunk internal API to create default input
            try:
                rest.simpleRequest(
                    "/servicesNS/nobody/{}/configs/conf-inputs".format(
                        APP_NAME),
                    self.getSessionKey(),
                    postargs=input_stanza,
                    method="POST",
                    raiseAllErrors=True,
                )

            except Exception as e:
                if "409" in str(e):
                    e = "Account is created but Inputs are not created for it because inputs are still present for same account\
                    name. Please close this dialog box and remove the previously created inputs and create new."
                raise Exception(e)