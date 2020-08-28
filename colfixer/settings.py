"""

Copyright::

    +===================================================+
    |                 © 2020 Privex Inc.                |
    |               https://www.privex.io               |
    +===================================================+
    |                                                   |
    |        MariaDB/MySQL Charset/Collation Fixer      |
    |        License: X11/MIT                           |
    |                                                   |
    |        Core Developer(s):                         |
    |                                                   |
    |          (+)  Chris (@someguy123) [Privex]        |
    |          (+)  Kale (@kryogenic) [Privex]          |
    |                                                   |
    +===================================================+
    
    Official Repo: https://github.com/Privex/collation-fixer


"""
from dotenv import load_dotenv
from os import getenv as env
from privex.helpers import env_int, env_bool

load_dotenv()

DEBUG = env_bool('DEBUG', False)
QUIET = env_bool('QUIET', False)

LOG_LEVEL = env('LOG_LEVEL', 'DEBUG' if DEBUG else 'WARNING')

if QUIET:
    LOG_LEVEL = env('LOG_LEVEL', 'ERROR')

DB_HOST = env('DB_HOST', 'localhost')
DB_USER = env('DB_USER', env('DB_USERNAME', 'root'))
DB_PASS = env('DB_PASS', env('DB_PASSWORD', ''))
DB_PORT = env_int('DB_PORT', 3306)

DB_NAME = env('DB_NAME')

