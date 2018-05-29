shimmy is a lambda function designed to take parameters from one account and push them to other accounts for use.
shimmy requires the execution role to have access to the appropriate KMS keys
for decrypt operations, and the cross account role assumed by shimmy needs to be
able to access the cross account key for encrypt operations.
