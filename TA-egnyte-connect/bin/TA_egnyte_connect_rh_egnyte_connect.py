
import ta_egnyte_connect_declare

from splunktaucclib.rest_handler.endpoint import (
    field,
    validator,
    RestModel,
    DataInputModel,
)
from splunktaucclib.rest_handler import admin_external, util
from splunk_aoblib.rest_migration import ConfigMigrationHandler
from ta_egnyte_connect_utils import IntervalValidator,StartDatetimeValidator

util.remove_http_proxy_env_vars()


fields = [
    field.RestField(
        'interval',
        required=True,
        encrypted=False,
        default=None,
        validator=IntervalValidator()
    ), 
    field.RestField(
        'index',
        required=True,
        encrypted=False,
        default='default',
        validator=validator.String(
            min_len=1, 
            max_len=80, 
        )
    ), 
    field.RestField(
        'data_type',
        required=True,
        encrypted=False,
        default='FILE_AUDIT',
        validator=None
    ), 
    field.RestField(
        'global_account',
        required=True,
        encrypted=False,
        default=None,
        validator=None
    ),
    field.RestField(
        'start_date',
        required=False,
        encrypted=False,
        default=None,
        validator=StartDatetimeValidator()
    ),
    field.RestField(
        'egnyte_domain_url',
        required=True,
        encrypted=False,
        default=None,
        validator=validator.String(
            min_len=1, 
            max_len=200, 
        )
    ), 

    field.RestField(
        'disabled',
        required=False,
        validator=None
    )

]
model = RestModel(fields, name=None)



endpoint = DataInputModel(
    'egnyte_connect',
    model,
)


if __name__ == '__main__':
    admin_external.handle(
        endpoint,
        handler=ConfigMigrationHandler,
    )
