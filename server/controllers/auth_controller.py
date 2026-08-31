from server.services.auth_service import AuthService

def register(auth, payload): return auth.register(**payload)
def login(auth, payload): return auth.login(**payload)
