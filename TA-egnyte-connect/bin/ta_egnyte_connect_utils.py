from splunktaucclib.rest_handler.endpoint.validator import Validator
import datetime
import re
import six

UTC_FORMAT = r"""%Y-%m-%dT%H:%M:%SZ"""

class IntervalValidator(Validator):
    def validate(self,value,data):
        interval = data.get("interval","")
        interval = int(interval)
        if interval <= 0:
            self.put_msg("Interval must be a positive integer.")
            return False
        if interval < 300:
            self.put_msg("Interval must be greater or equals to 5 minutes.")
            return False
        if 'start_date' not in data:
            data['start_date'] = datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
            return True
        return True

class StartDatetimeValidator(Validator):
    """To validate Start DateTime Field."""

    def validate(self, value, data):
        """Validate start datetime field."""
        start_datetime = data.get('start_date')

        if start_datetime and (isinstance(start_datetime, six.string_types) and start_datetime.strip() != ''):
            regex = r"""^[0-9]{4}-[0-9]{2}-[0-9]{2}[tT][0-9]{2}:[0-9]{2}:[0-9]{2}[zZ]$"""
            if not re.match(regex, start_datetime):
                self.put_msg("Invalid Start DateTime Format. Please enter valid Start DateTime.")
                return False
            start_datetime = datetime.datetime.strptime(start_datetime.upper(), UTC_FORMAT)

            if start_datetime > datetime.datetime.utcnow():
                self.put_msg("Start Date can not exceed current datetime. Please enter valid Start Date.")
                return False
            days_diff = datetime.datetime.utcnow() - start_datetime
            if days_diff.days != 0:
                self.put_msg("Start Date must be in range of last 24 hours. Please enter valid Start Date.")
                return False

            return True

        # As It is optional field, empty start_datetime will be allowed while validating.
        return True
