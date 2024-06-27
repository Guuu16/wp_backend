from ldap3 import Server, Connection, ALL, NTLM, ALL_ATTRIBUTES, LEVEL, SUBTREE, ServerPool
import time
import json

AUTH_LDAP_SERVER_URI = ['ldap://10.64.0.101:389']
AUTH_LDAP_BIND_DM = '@company.com'
AUTH_LDAP_SEARCH_BASE = "dc=company,dc=com"
username = 'fw_bbfv'
password = 'company@0522'


class Ldap3Util(object):

    def __init__(self, user_info, ldap_setting):
        self.username = user_info['username'] + ldap_setting['AUTH_LDAP_BIND_DM']
        self.password = user_info['password']
        self.attributes = user_info['attributes']
        self.ldap_conn = None
        self.AUTH_LDAP_SEARCH_BASE = ldap_setting['AUTH_LDAP_SEARCH_BASE']
        self.AUTH_LDAP_BIND_DM = ldap_setting['AUTH_LDAP_BIND_DM']
        self.ldap_server_pool = ServerPool(ldap_setting['AUTH_LDAP_SERVER_URI'], active=2)

    def __open_ldap(self):
        count = 0
        while count < 3:
            count += 1
            if self.ldap_conn is None:
                try:
                    self.ldap_conn = Connection(self.ldap_server_pool,
                                                user=self.username,
                                                password=self.password,
                                                check_names=True,
                                                lazy=False,
                                                receive_timeout=30,
                                                raise_exceptions=True)
                except Exception as e:
                    import traceback
                    traceback.print_exc()
                    time.sleep(1)
            else:
                break

    def auth_ldap(self):
        try:
            self.__open_ldap()
            self.ldap_conn.open()
            return self.ldap_conn.bind()
        except:
            import traceback
            traceback.print_exc()
            return None

    def search_ldap(self, search_user):
        ldap_status = self.auth_ldap()
        search_result_dict = {}
        if ldap_status:
            res = self.ldap_conn.search(
                search_base=self.AUTH_LDAP_SEARCH_BASE,
                search_filter='(sAMAccountName={})'.format(search_user),
                search_scope=SUBTREE,
                attributes=self.attributes,
                paged_size=5
            )
            if res:
                try:
                    search_result_dict = json.loads(self.ldap_conn.response_to_json())['entries'][0]
                except Exception as e:
                    import traceback
                    traceback.print_exc()
                    ldap_status = False
        return ldap_status, search_result_dict

    @staticmethod
    def init_ldap(username, password):
        try:
            attributes = ['cn', 'givenName', 'mail', 'sAMAccountName', 'department', 'name', 'telephoneNumber',
                          'directReports']
            userinfo = {'username': username, 'password': password, 'attributes': attributes}
            ldap_setting = {'AUTH_LDAP_SERVER_URI': AUTH_LDAP_SERVER_URI,
                            'AUTH_LDAP_SEARCH_BASE': AUTH_LDAP_SEARCH_BASE,
                            'AUTH_LDAP_BIND_DM': AUTH_LDAP_BIND_DM}
            return Ldap3Util(userinfo, ldap_setting)
        except Exception as e:
            import traceback
            traceback.print_exc()
            return None



def get_all_people(manager):
    ldap = Ldap3Util.init_ldap(username, password)
    if ldap.auth_ldap():
        users = ldap.search_ldap(manager)
        # print(users[0])
        return users[1]



if __name__ == '__main__':
    print(get_all_people("sunwx5"))