#!/usr/bin/env python3
"""
Collation Converter for MySQL / MariaDB

(C) 2020 Privex Inc. / Someguy123

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
import argparse
import sys
import textwrap
from decimal import Decimal
from typing import List
from os import getenv as env
from privex.helpers import ErrHelpParser, empty, empty_if, is_true
from colorama import Fore
from colfixer import settings, core
import logging

GREEN = Fore.GREEN
RED = Fore.RED
BLUE = Fore.BLUE
CYAN = Fore.CYAN
YELLOW = Fore.YELLOW
MAGENTA = Fore.MAGENTA
RESET = Fore.RESET

log = logging.getLogger('colfixer.app')

CMD_DESC = {
    'list_tables': "List all tables in a given database, showing their collation and other info",
    'list_columns': "List all columns in a given table or database, showing their collation and other info",
    'convert_table': "Convert a given table to a different character set / collation",
}


def list_tables(opts):
    db = empty_if(opts.db, settings.DB_NAME, itr=True)
    print("\nTable list for database:", db, "\n")
    tables = core.get_tables(db)
    headers = ['Name', 'Char Set', 'Collation']
    # tline = "+{}+{}+{}+".format('-' * 41, '-' * 41, '-' * 41)
    tline = spaceize(3, size=41)
    print(tline)
    # print("| {:<40}| {:<40}| {:<40}|".format(*headers))
    print(columnize(*headers))
    print(tline)

    for t in tables:
        # print("| {:<40}| {:<40}| {:<40}|".format(t.table, t.character_set, t.collation))
        print(columnize(t.table, t.character_set, t.collation))
    print(tline)


def spaceize(cols=3, size=41, padder='-', spacer='+') -> str:
    cols, size = int(cols), int(size)
    spacer, padder = str(spacer), str(padder)
    ic = ((spacer + '{pad}') * cols) + spacer
    # spacers = ['-' * size for _ in range(cols)]
    return ic.format(pad=padder * size)
    

def columnize(*cols: str, size: int = 40) -> str:
    ic = "| {:<" + str(size) + "}"
    col = (ic * len(cols)) + '|'
    # log.error('ic: %s', ic)
    # log.error('col: %s', col)
    # log.error('cols: %s', cols)
    cols = [str(c) if isinstance(c, (int, float, Decimal)) or c in [None, False, True] else c for c in cols]
    return col.format(*cols)


def list_cols(opts):
    db = empty_if(opts.db, settings.DB_NAME, itr=True)
    table = empty_if(opts.table, None, itr=True)
    col_size = 30
    print("\nColumn list for database:", db, "\n")
    print("\nTable:", table, "\n")
    
    columns = core.get_columns(db, table)
    headers = ['DB', 'Table', 'ColName', 'Default', 'Null', 'Type', 'Key', 'Extra', 'Char Set', 'Collation']
    # tline = "+{}+{}+{}+".format('-' * 41, '-' * 41, '-' * 41)
    tline = spaceize(len(headers), col_size + 1)
    print(tline)
    print(columnize(*headers, size=col_size))
    print(tline)
    
    for t in columns:
        print(columnize(
            t.schema, t.table, t.column, t.default, t.nullable, t.column_type,
            t.column_key, t.extra, t.character_set, t.collation,
            size=col_size
        ))
    print(tline)


def convert_tables(opts):
    db = empty_if(opts.db, settings.DB_NAME, itr=True)
    tables = empty_if(opts.tables, [], itr=True)
    all_tables = is_true(opts.all_tables)
    conv_columns = is_true(opts.conv_columns)
    outer_tx = is_true(opts.outer_tx)
    skip_indexed = is_true(opts.skip_indexed)
    
    if not empty(db):
        core.reconnect(database=db)
    
    charset, collation = empty_if(opts.charset, 'utf8mb4', itr=True), empty_if(opts.collation, 'utf8mb4_unicode_ci', itr=True)
    # table = empty_if(opts.table, None, itr=True)
    
    if empty(tables, itr=True) and not all_tables:
        parser.error(f"\n{RED}ERROR: You must specify a table to 'convert_tables' or pass --all-tables / -a{RESET}\n")
        return sys.exit(1)

    if settings.QUIET:
        core.set_logging_level()
    else:
        core.set_logging_level(env('LOG_LEVEL', 'INFO'))
    
    if all_tables:
        tables = core.get_tables(database=db)
        tnames = [t.table for t in tables]
        print(YELLOW)
        print(f" >>> --all-tables was specified. Converting {len(tables)} tables! The tables are: {', '.join(tnames)}")
        print(RESET)
    else:
        tables = [core.get_tables(database=db, table=t)[0] for t in tables]
        tnames = [t.table for t in tables]
    
    for t in tables:
        print(f"\n{YELLOW} [...] Converting table {t.table} to charset {charset} and collation {collation}{RESET}\n")
        core.convert_table(t.table, charset=charset, collation=collation)
        print(f"\n{GREEN} [+++] Successfully converted table {t.table}{RESET}\n")

    if conv_columns:
        print(f"\n{BLUE} >>> Converting COLUMNS to charset {charset} and collation {collation} for tables: {', '.join(tnames)}{RESET}\n")
        _convert_columns(
            tables, charset=charset, collation=collation, outer_tx=outer_tx, skip_indexed=skip_indexed
        )
        print(f"\n{GREEN} [+++] Successfully converted COLUMNS inside of tables: {', '.join(tnames)}{RESET}\n")
    
    print(f"\n{GREEN} ++++++ Successfully converted {len(tables)} tables ++++++ {RESET}\n")


def _convert_columns(tables: List[core.TableResult], all_cols=True, charset="utf8mb4", collation="utf8mb4_unicode_ci", **kwargs):
    db = empty_if(kwargs.get('db'), settings.DB_NAME, itr=True)
    columns = empty_if(kwargs.get('columns'), [], itr=True)
    outer_tx = is_true(kwargs.get('outer_tx', True))
    skip_indexed = is_true(kwargs.get('skip_indexed', True))
    # all_cols = is_true(opts.all_columns)
    
    tnames = [t.table for t in tables]
    print(f"{YELLOW} >>> Converting columns in {len(tables)} tables. Tables are: {', '.join(tnames)}{RESET}\n")
    for t in tables:
        print(f"{CYAN}    [-] Converting columns in table {t.table} to charset {charset} and collation {collation}{RESET}")
        try:
            core.convert_columns(
                t.table, *columns, conv_all=all_cols, charset=charset, collation=collation,
                use_tx=outer_tx, skip_indexed=skip_indexed, database=db
            )
            print(f"{GREEN}    [+] Finished converting columns in table {t.table}{RESET}\n")

        except Exception as e:
            log.exception("Error while converting columns in table %s - %s - %s", t.table, type(e), str(e))
            return sys.exit(1)
    
    print(f"\n{GREEN} [+++] Finished converting {len(tables)} tables. Tables were: {', '.join(tnames)}{RESET}\n")


def convert_columns(opts):
    db = empty_if(opts.db, settings.DB_NAME, itr=True)
    table = empty_if(opts.table, None, itr=True)
    charset, collation = empty_if(opts.charset, 'utf8mb4', itr=True), empty_if(opts.collation, 'utf8mb4_unicode_ci', itr=True)
    columns = empty_if(opts.columns, [], itr=True)
    outer_tx = is_true(opts.outer_tx)
    skip_indexed = is_true(opts.skip_indexed)
    all_tables = is_true(opts.all_tables)
    all_cols = is_true(opts.all_columns)
    
    if not empty(db):
        core.reconnect(database=db)
    
    if empty(table) and not all_tables:
        parser.error(f"\n{RED}ERROR: You must specify a table to 'convert_columns' without -a / --all-tables{RESET}\n")
        return sys.exit(1)
    
    if all_tables and (empty(columns, itr=True) or not all_cols):
        parser.error(f"\n{RED}ERROR: You must either columns using '-c' or pass --all-columns / -k  when using -a / --all-tables{RESET}\n")
        return sys.exit(1)

    if settings.QUIET:
        core.set_logging_level()
    else:
        core.set_logging_level(env('LOG_LEVEL', 'INFO'))
    if all_tables:
        tables = core.get_tables(db)
        _convert_columns(
            tables, all_cols, charset=charset, collation=collation,
            db=db, columns=columns, outer_tx=outer_tx, skip_indexed=skip_indexed
        )
        return
    
    print(f"\n >>> Converting columns in table {table} to charset {charset} and collation {collation}\n")

    try:
        core.convert_columns(
            table, *columns, conv_all=all_cols, charset=charset, collation=collation,
            use_tx=outer_tx, skip_indexed=skip_indexed, database=db
        )
        print(f"\n [+++] Finished converting {table}.\n")
    except Exception as e:
        log.exception("Error while converting columns in table %s - %s - %s", table, type(e), str(e))
        return sys.exit(1)


helptext = f"""
{YELLOW}Basic Info:{RESET}
    
    Unless you need a specific character set / collation, you should use the defaults, as they are strongly recommended
    by most people and organisations who use MySQL/MariaDB, since 'utf8mb4' + 'utf8mb4_unicode_ci' provides broad support
    for UTF-8 characters, up to 4 bytes (32 bits) long.

    The default character set is: {GREEN}utf8mb4{RESET}
    The default collation is:     {GREEN}utf8mb4_unicode_ci{RESET}

    {CYAN}CURRENT ENV SETTINGS{RESET}
        {GREEN}
        DB_NAME={settings.DB_NAME}
        DB_HOST={settings.DB_HOST}
        DB_USER={settings.DB_USER}
        DB_PASS={settings.DB_PASS}
        DB_PORT={settings.DB_PORT}
    {RESET}
    For the safest and most reliable charset/collation conversion, by default, the `convert_tables`/`convert_columns` subcommands
    {YELLOW}disable conversion of columns which have any form of index{RESET}, such as primary keys, compound indexes,
    foreign keys etc.

    This is default for two reasons:

        - Some character sets (including utf8mb4) have limitations on how large an indexed column may be. Older versions of
          MariaDB/MySQL disallowed indexed utf8mb4 columns which have a size above 255 characters.

        - MariaDB/MySQL throws errors if you attempt to convert a column which is used in a foreign key relation.
          While it's possible to convert foreign key columns, this is explicitly disabled as part of the index skipping,
          as to prevent causing relationship integrity errors. These types of columns are best converted manually, after
          careful consideration / mitigation of any consequences of doing so.
    
    Similarly, this script will avoid converting things which don't need to be - e.g. columns which don't need/use a collation, such
    as numeric types (INT, DECIMAL etc.) - as well as columns which already match the charset + collation you're trying to convert to.

{YELLOW}Quick start:{RESET}

    By default, this script is configured to use the host 'localhost', the username 'root', port 3306, no password,
    and no database name.

    {RED}We strongly recommend configuring AT LEAST a database name in '.env',{RESET} which will prevent commands
    such as 'convert_tables' / 'convert_columns' potentially converting databases that it shouldn't be.

    Example env config:
    
        # DB_NAME is the name of the database to use by default
        DB_NAME=my_app
        DB_HOST=sql.example.com
        # While the default user is root anyway, it's good to be explicit, and saves you time figuring out the correct
        # ENV var to use later if you need to change it.
        DB_USER=root
        DB_PASS=MySup3rS33kritP@5w0rd

    {CYAN}CONVERT ALL TABLES AND THEIR COLUMNS TO utf8mb4 + utf8mb4_unicode_ci{RESET}
        
        # Convert all tables in the default database (DB_NAME) including COLUMNS to utf8mb4 + utf8mb4_unicode_ci
        {sys.argv[0]} convert_tables -a -k


{YELLOW}Example commands:{RESET}
    {GREEN} --- Show help / usage for sub-commands ---{RESET}

    {CYAN}# You can use either '-h' or '--help' in front of a sub-command to show help / usage info{RESET}
    {sys.argv[0]} list_tables -h
    {sys.argv[0]} list_tables --help

    {sys.argv[0]} list_columns -h
    {sys.argv[0]} convert_tables -h
    {sys.argv[0]} convert_columns -h

    {GREEN} --- Viewing commands for inspecting / analysing your database/tables/columns before converting ---{RESET}

    {CYAN}# List tables for the default database (DB_NAME) in .env{RESET}
    {sys.argv[0]} list_tables

    {CYAN}# List tables for the database 'myapp'{RESET}
    {sys.argv[0]} list_tables my_app

    {CYAN}# Dynamically override the database settings loaded from .env / environment vars{RESET}
    {sys.argv[0]} -s mysql.example.org -u johndoe -p MySecur3p@w0rd -d shop_db -P 33306 list_tables
    {CYAN}# Alternative with more verbose/explicit -- arguments{RESET}
    {sys.argv[0]} --host mysql.example.org --user johndoe --pass MySecur3p@w0rd --database shop_db --port 33306 list_tables

    {CYAN}# List all columns for every table in the current database{RESET}
    {sys.argv[0]} list_columns

    {CYAN}# List just the columns in the table 'auth_user'{RESET}
    {sys.argv[0]} list_columns auth_user

    {GREEN} --- Table/Column Conversion Commands ---{RESET}

    {CYAN}# Change the default character set / collation for one or more tables{RESET}
    {sys.argv[0]} convert_tables (-a|-k) [table(s)]

    {CYAN}# Convert the default charset + collation for the tables: convert_tables, auth_user, auth_user_groups, payments + messages{RESET}
    {CYAN}# NOTE: This does not change the charset + collation for the columns within the tables.{RESET}
    {sys.argv[0]} convert_tables auth_user auth_user_groups payments messages

    {CYAN}# Convert all tables default charset / collation (-a), AND convert every columns (-k) charset + collation within those
    # tables; as well as quiet mode (-q) to hide the logging, making output more readable when converting many tables.{RESET}
    {sys.argv[0]} -q convert_tables -a -k

    {CYAN}# Convert the charset + collation for just the columns 'username' and 'email' in the table 'auth_user'{RESET}
    {sys.argv[0]} convert_columns auth_user -c username email

    {CYAN}# Convert the charset + collation for ALL columns in the table 'auth_user'{RESET}
    {sys.argv[0]} convert_columns -k auth_user

    {CYAN}# Convert the charset + collation for ALL columns on every table in the database (but don't convert the tables themselves){RESET}
    {sys.argv[0]} convert_columns -k -a

{YELLOW}Copyright:{RESET}
{MAGENTA}
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
    {RESET}
    {GREEN}Official Repo:{RESET} https://github.com/Privex/collation-fixer

"""


def _configure(opts):
    settings.DB_HOST = opts.host
    settings.DB_USER = opts.user
    settings.DB_PASS = opts.password
    settings.DB_NAME = opts.database
    settings.DB_PORT = int(opts.port)
    settings.QUIET = is_true(opts.quiet)
    if settings.QUIET:
        settings.LOG_LEVEL = env('LOG_LEVEL', 'ERROR')
        core.set_logging_level('ERROR')
    core.reconnect()


# noinspection PyTypeChecker
mparser = ErrHelpParser(
    epilog=textwrap.dedent(helptext),
    formatter_class=argparse.RawDescriptionHelpFormatter
)

# mparser.add_argument('sub_command', default=None, nargs='?')

mparser.add_argument('-s', '--host', default=settings.DB_HOST, help=f'Hostname/IP of database server. Default: {settings.DB_HOST}')
mparser.add_argument('-u', '--user', default=settings.DB_USER, help=f'Username to login to database server. Default: {settings.DB_USER}')
mparser.add_argument('-p', '--pass', dest='password', default=settings.DB_PASS,
                     help=f'Password to login to database server. Default: {settings.DB_PASS}')
mparser.add_argument('-d', '--database', default=settings.DB_NAME,
                     help=f'Name of database to use for all commands when not specified. Default: {settings.DB_NAME}')
mparser.add_argument('-P', '--port', default=settings.DB_PORT, type=int,
                     help=f'Port number of database server. Default: {settings.DB_PORT}')
mparser.add_argument('-q', '--quiet', default=settings.QUIET, action='store_true',
                     help=f'Set quiet mode (less spam-like logging)')

# Take any args passed to the main parser and override `settings` + reconnect DB


parser = mparser
# parser = ErrHelpParser()
sp = parser.add_subparsers()

# ----- ----- ----- ----- ----- ----- ----- ----- ----- ----- ----- ----- ----- ----- ----- ----- ----- ----- -----

parse_lt = sp.add_parser('list_tables', description=CMD_DESC['list_tables'])
parse_lt.add_argument('db', default=None, help='MySQL database to scan', nargs='?')
parse_lt.set_defaults(func=list_tables)

# ----- ----- ----- ----- ----- ----- ----- ----- ----- ----- ----- ----- ----- ----- ----- ----- ----- ----- -----

parse_lc = sp.add_parser('list_columns', description=CMD_DESC['list_columns'])
parse_lc.add_argument('table', default=None, help='MySQL table to scan', nargs='?')
parse_lc.add_argument('db', default=None, help='MySQL database to scan', nargs='?')
parse_lc.set_defaults(func=list_cols)

# ----- ----- ----- ----- ----- ----- ----- ----- ----- ----- ----- ----- ----- ----- ----- ----- ----- ----- -----

parse_ct = sp.add_parser('convert_tables', description=CMD_DESC['convert_table'])
parse_ct.add_argument('tables', default=[], help='MySQL tables to convert', nargs='*')
parse_ct.add_argument('--db', default=None, help='MySQL database to use instead of DB_NAME', nargs='?')
parse_ct.add_argument('-a', '--all-tables', action='store_true', dest='all_tables', default=False,
                      help='Convert ALL tables in the selected/default database to use a certain character set + collation')
parse_ct.add_argument('-k', '--convert-cols', action='store_true', dest='conv_columns', default=False,
                      help='Convert all columns within the table(s) to the selected character set + collation')
parse_ct.add_argument('--charset', default='utf8mb4', help='Character set to convert columns to (default: utf8mb4)')
parse_ct.add_argument('--collation', default='utf8mb4_unicode_ci', help='Collation to convert columns to (default: utf8mb4_unicode_ci)')
parse_ct.add_argument('--no-tx', dest='outer_tx', action='store_false', default=True,
                      help='Disable outer transaction (disables auto-rollback if a single column fails)')
parse_ct.add_argument('-i', '--indexes', dest='skip_indexed', action='store_false', default=True,
                      help='Attempt to convert columns which have an index (indexed columns are skipped by default to prevent errors)')

parse_ct.set_defaults(func=convert_tables, all_tables=False, outer_tx=True, skip_indexed=True)

# ----- ----- ----- ----- ----- ----- ----- ----- ----- ----- ----- ----- ----- ----- ----- ----- ----- ----- -----

parse_cc = sp.add_parser('convert_columns', description=CMD_DESC['convert_table'])
parse_cc.add_argument('table', default=None, help='MySQL table to convert', nargs='?')
parse_cc.add_argument('-c', '--columns', dest='columns', default=[], help='Table columns to convert', nargs='*')
parse_cc.add_argument('--db', default=None, help='MySQL database to use instead of DB_NAME')
parse_cc.add_argument('--charset', default='utf8mb4', help='Character set to convert columns to (default: utf8mb4)')
parse_cc.add_argument('--collation', default='utf8mb4_unicode_ci', help='Collation to convert columns to (default: utf8mb4_unicode_ci)')
parse_cc.add_argument('--no-tx', dest='outer_tx', action='store_false', default=True,
                      help='Disable outer transaction (disables auto-rollback if a single column fails)')
parse_cc.add_argument('-i', '--indexes', dest='skip_indexed', action='store_false', default=True,
                      help='Attempt to convert columns which have an index (indexed columns are skipped by default to prevent errors)')
parse_cc.add_argument('-a', '--all-tables', dest='all_tables', action='store_true', default=False,
                      help='Convert ALL tables in the database (should be specified with -c (all columns))')
parse_cc.add_argument('-k', '--all-columns', dest='all_columns', action='store_true', default=False,
                      help='Convert ALL columns on the table(s) being converted')

# ----- ----- ----- ----- ----- ----- ----- ----- ----- ----- ----- ----- ----- ----- ----- ----- ----- ----- -----

parse_cc.set_defaults(
    func=convert_columns, outer_tx=True, skip_indexed=True, all_tables=False, all_columns=False
)


# Resolves the error "'Namespace' object has no attribute 'func'
# Taken from https://stackoverflow.com/a/54161510/2648583
try:
    args = parser.parse_args()
    log.debug('args is:', args)
    # Take any args passed to the main parser and override `settings` + reconnect DB
    _configure(args)
    # Call sub parser function if needed
    func = args.func
    func(args)
except AttributeError as e:
    parser.error(f'Too few arguments. {type(e)} - {str(e)}')
    sys.exit(1)
