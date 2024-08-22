import os
import datetime
import json

import globus_sdk
from globus_sdk.tokenstorage import SimpleJSONFileAdapter
from globus_sdk.scopes import TransferScopes


class AuthorizedTranserClient:

    # I'm using my EFFIS-2 app registered to Globus for now
    GlobusAppID = "407942f2-26d5-4a06-a645-bdafe9861784"

    # I'll continue with a file in the working directory for now
    TokensFile = ".globustokens"

    # e.g. NERSC DTN requires adding a GCS "data access" to the TransferScopes (which effectively anything that does anything needs)
    ConsentRequired =  {
        #'required_scopes': None,  # This default is ["openid", "profile", "email", TransferScopes.all]
        #'required_scopes': [TransferScopes.all],  
        'required_scopes': [
            TransferScopes.all,
            "openid", "profile", "email",
            "https://auth.globus.org/scopes/actions.globus.org/hello_world",
            "https://auth.globus.org/scopes/5fac2e64-c734-4e6b-90ea-ff12ddbf9653/notification_notify",
        ]
    }

    # OLCF DTN uses such authorizations, which can be caught in exception handling, like the consents
    AuthorizationParameters =  {
        'session_required_single_domain': None,
        'session_required_identities': None,
        'session_required_policies': None,
    }

    notify_on_succeeded = False


    def GetNewTokenResponse(self):

        authorize_url = self.auth_client.oauth2_get_authorize_url(**self.AuthorizationParameters)

        print(
            "Please go to this URL and login: {0}".format(authorize_url) + "\n",
            "Please enter the code you get after login here: ",
            end=""
        )
        auth_code = input().strip()

        token_response = self.auth_client.oauth2_exchange_code_for_tokens(auth_code)

        # This saves credentials with access to the (Native) App.
        # New ones are needed if new consents are needed, but the Globus registered app appends new consents to persist (unless revoked)
        self.my_file_adapter.store(token_response)
        
        self.ByResourceServer = token_response.by_resource_server


    def ServerFromFile(self, server):
        
        # Load the tokens from the file
        tokens = self.my_file_adapter.get_token_data(server)

        try:
            self.ByResourceServer[server] = self.auth_client.oauth2_refresh_token(tokens["refresh_token"]).by_resource_server[server]
        except globus_sdk.services.auth.errors.AuthAPIError as error:
            print("The saved credentials that were loaded didn't work. Getting new ones...")
            self.GetNewTokenResponse()
        except:
            raise


    def LoadInitialTokens(self):
        self.ByResourceServer = {}

        if not self.my_file_adapter.file_exists():
            print("Did not find any saved credentials. Generating new ones.")
            self.GetNewTokenResponse()
        else:
            self.ServerFromFile("transfer.api.globus.org")
            self.ServerFromFile("auth.globus.org")
            self.ServerFromFile("actions.globus.org")


    # See https://globus-sdk-python.readthedocs.io/en/stable/tokenstorage.html#tokenstorage (if ever confidential app client needed)
    def RefreshTokenAuthorizer(self, server):
        authorizer = globus_sdk.RefreshTokenAuthorizer(
            self.ByResourceServer[server]["refresh_token"],
            self.auth_client, 
            on_refresh=self.my_file_adapter.on_refresh,
            access_token=self.ByResourceServer[server]["access_token"],
            expires_at=self.ByResourceServer[server]["expires_at_seconds"],
        )
        return authorizer


    # There are other kinds of clients too (like Group, Auth) and can take tokens from different resource servers
    def GetTransferClient(self):
        self.TransferClient = globus_sdk.TransferClient(authorizer=self.RefreshTokenAuthorizer("transfer.api.globus.org"))


    def AutoActivate(self, idhash, label):
        r = self.TransferClient.endpoint_autoactivate(idhash, if_expires_in=3600)
        url = "https://app.globus.org/file-manager?origin_id={0}".format(idhash)
        first = True
        #print(idhash, r)
        while (r['code'] == "AutoActivationFailed") or (r['code'] == "AuthenticationFailed"):
            if first:
                print("{0} endpoint requires manual activation, please open the following URL in a browser to activate the endpoint:".format(label) + "\n" + url)
                print("Submission will continue upon activation.")
                first = False
            time.sleep(5)
            r = self.TransferClient.endpoint_autoactivate(idhash, if_expires_in=3600)


    def CheckConsents(self):
        redo = False

        #for endpoint in [self.SourceEndpoint, self.DestinationEndpoint]:
        for endpoint in ([self.SourceEndpoint] + list(self.DestinationEndpoints)):

            try:
                self.TransferClient.operation_ls(endpoint, path="/")
                
            except globus_sdk.TransferAPIError as err:

                if err.info.consent_required or err.info.authorization_parameters:
                    redo = True

                    if err.info.consent_required:
                        print("{0} – Extra consents required: required_scopes-->{1}".format(endpoint, err.info.consent_required.required_scopes))
                        if self.ConsentRequired['required_scopes'] is None:
                            self.ConsentRequired['required_scopes'] = err.info.consent_required.required_scopes
                        else:
                            self.ConsentRequired['required_scopes'] += err.info.consent_required.required_scopes

                    if err.info.authorization_parameters:
                        for key in self.AuthorizationParameters:
                            entry = err.info.authorization_parameters.__dict__[key]
                            if (type(entry) is list) and (len(entry) > 0):
                                print("{0} – Extra authorizations required: {1}-->{2}".format(endpoint, key, entry))
                                if self.AuthorizationParameters[key] is None:
                                    self.AuthorizationParameters[key] = entry
                                else:
                                    self.AuthorizationParameters[key] += entry

                else:
                    raise

            except: 
                raise

        if redo:
            self.auth_client.oauth2_start_flow(refresh_tokens=True, requested_scopes=self.ConsentRequired['required_scopes'])
            self.GetNewTokenResponse()
            self.GetTransferClient()


    def __init__(self, SourceEndpoint, *DestinationEndpoints, GlobusAppID=None, TokensFile=None, notify_on_succeeded=False):

        self.SourceEndpoint = SourceEndpoint
        self.DestinationEndpoints = DestinationEndpoints

        if GlobusAppID is not None:
            self.GlobusAppID = GlobusAppID
        if TokensFile is not None:
            self.TokensFile = TokensFile
        self.notify_on_succeeded = notify_on_succeeded

        """
        # Doing this automatically if it's needed
        transfer_scope = TransferScopes.make_mutable("all")
        data_access_scope = GCSCollectionScopeBuilder(nerscdtn).make_mutable("data_access", optional=True)
        transfer_scope.add_dependency(data_access_scope)

        auth_client = globus_sdk.NativeAppAuthClient(clientid)
        auth_client.oauth2_start_flow(refresh_tokens=True, requested_scopes=transfer_scope)
        """

        self.auth_client = globus_sdk.NativeAppAuthClient(self.GlobusAppID)
        self.auth_client.oauth2_start_flow(refresh_tokens=True, requested_scopes=self.ConsentRequired['required_scopes'])

        self.my_file_adapter = SimpleJSONFileAdapter(self.TokensFile)
        self.LoadInitialTokens()
        self.GetTransferClient()

        self.AutoActivate(self.SourceEndpoint, "Host")
        for DestinationEndpoint in self.DestinationEndpoints:
            self.AutoActivate(DestinationEndpoint, "Destination")
        self.CheckConsents()

        self.Transfer = None

        self.AuthClient = globus_sdk.AuthClient(authorizer=self.RefreshTokenAuthorizer("auth.globus.org"))
        self.ActionsClient = globus_sdk.AuthClient(authorizer=self.RefreshTokenAuthorizer("actions.globus.org"))

