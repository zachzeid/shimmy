import yaml

import boto3


def lambda_handler(event, context):
    """Start of the lambda function shimmy. """
    def read_config():
        """This is where I read in the config file."""
        with open('settings.config', 'r') as file_name:
            try:
                settings = yaml.load(file_name)
            except yaml.YAMLError as exc:
                print(exc)
        return settings

    # This is defined so we can instantiate credentials to the account we want to do things to.

    def cross_role_session(role_arn, region):
        """ This instantiates a session with the provided cross account role. """
        # This is here so we can avoid auth errors.
        start_session = boto3.Session()
        role_arn = role_arn
        sts_client = start_session.client('sts')
        session = sts_client.assume_role(
            RoleArn=role_arn,
            RoleSessionName="invokedByLambda"
        )
        # I don't see a reason to have this outside this function, as we're going to be using this
        # repeatedly.

        cross_role_session = boto3.Session(
            aws_access_key_id=session['Credentials']['AccessKeyId'],
            aws_secret_access_key=session['Credentials']['SecretAccessKey'],
            aws_session_token=session['Credentials']['SessionToken'],
            region_name=region
        )
        return cross_role_session

    # Here we push the parameter to the account as defined in the settings.config file
    # TODO:  Have lambda function pull settings from S3 instead of being inside of lambda function

    def push_parameter(accountid, session, parameter_name, parameter_type, parameter_value, key):
        """push_parameter() takes the value of local parameter in parameter store and
        pushes it to remote AWS Account. """
        client = session.client('ssm')
        if key:
            response = client.put_parameter(
                Name=parameter_name,
                Description='Parameter pushed from %s' % accountid,
                Value=parameter_value,
                Type=parameter_type,
                KeyId=key,
                Overwrite=True
            )
        else:
            response = client.put_parameter(
                Name=parameter_name,
                Description='Parameter pushed from %s' % accountid,
                Value=parameter_value,
                Type=parameter_type,
                Overwrite=True
            )
        return response
    # We have the name of the parameter, but we need to get the value of that
    # parameter to push to a new account

    def get_parameter(parameter_name, parameter_type, region):
        """get_parameter() gets the value of the parameter, decrypts (if necessary)
        and feeds value to put_parameter(). """
        ssm_client = boto3.client('ssm', region_name=region)
        if parameter_type == 'SecureString':
            try:
                get_parameter = ssm_client.get_parameter(
                    Name=parameter_name,
                    WithDecryption=True
                )
            except ValueError:
                return "Parameter not found."
        else:
            try:
                get_parameter = ssm_client.get_parameter(
                    Name=parameter_name,
                    WithDecryption=False
                )
            except ValueError:
                return "parameter name not found."
        return get_parameter['Parameter']['Value']

    settings = read_config()
    for account_number, parameters in settings['Accounts'].items():
        for parameter_keys, parameter_attrs in parameters.items():
            key = ""
            if parameter_keys == 'role_arn':
                role_arn = parameter_attrs
            else:
                parameter = parameter_keys
                # Get the parameter value
                if 'key' in parameter_attrs:
                    key = parameter_attrs['key']
                    parameter_type = 'SecureString'
                    print(
                        "%s provided as key, using SecureString as parameter type." % key)
                else:
                    print('no key provided, parameter set to String')
                    parameter_type = 'String'
                region = parameter_attrs['region']

                parameter_value = get_parameter(
                    parameter_name=parameter,
                    parameter_type=parameter_type,
                    region=region
                )

        # Region's are 1:1 so cross-region pushes aren't a thing
        # TODO: Make cross-region pushes a thing.

                cross_account = cross_role_session(role_arn, region)
                if key:
                    print(push_parameter(
                        accountid=account_number, session=cross_account,
                        parameter_name=parameter,
                        parameter_type=parameter_type,
                        parameter_value=parameter_value,
                        key=key
                    ))
                else:
                    print(push_parameter(
                        accountid=account_number, session=cross_account,
                        parameter_name=parameter,
                        parameter_type=parameter_type,
                        parameter_value=parameter_value,
                        key=key
                    ))
