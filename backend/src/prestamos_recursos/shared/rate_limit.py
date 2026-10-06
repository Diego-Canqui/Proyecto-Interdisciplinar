"""Rate limiter compartido para toda la aplicación."""

from slowapi import Limiter
from slowapi.util import get_remote_address

# Rate limiter configurado por IP
limiter = Limiter(key_func=get_remote_address)