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
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Optional, Tuple, Union

from privex.helpers import empty
from privex.loghelper import LogHelper
from colfixer import settings
import logging
import MySQLdb
from os import getenv as env
from MySQLdb.connections import Connection

log = logging.getLogger(__name__)


def set_logging_level(level: Union[str, int] = None, logger='colfixer'):
    global log
    if empty(level):
        level = 'ERROR' if settings.QUIET else env('LOG_LEVEL', ('DEBUG' if settings.DEBUG else 'WARNING'))
    if isinstance(level, str):
        level = logging.getLevelName(level)
    _lh = LogHelper(logger, handler_level=level)
    _lh.add_console_handler()
    if logger == 'colfixer':
        log = _lh.get_logger()
    return _lh.get_logger()


set_logging_level(settings.LOG_LEVEL)


@dataclass
class DataStore:
    connection: Connection = None

    @property
    def connected(self):
        return not empty(self.connection)


STORE = DataStore()


def _connect(**conn_override) -> Connection:
    conn_args = dict(host=settings.DB_HOST, user=settings.DB_USER, password=settings.DB_PASS, port=settings.DB_PORT)
    if not empty(settings.DB_NAME):
        conn_args['database'] = settings.DB_NAME
    conn_args = {**conn_args, **conn_override}
    return Connection(**conn_args)


def connect(new_instance=False, **conn_override) -> Connection:
    if new_instance:
        return _connect(**conn_override)
    if not STORE.connected:
        STORE.connection = _connect(**conn_override)
    return STORE.connection


def reconnect(**conn_override) -> Connection:
    disconnect()
    return connect(**conn_override)


def disconnect() -> bool:
    if STORE.connected:
        STORE.connection.close()
        STORE.connection = None
        return True
    return False


def query(stmt, *params, one=False, use_tx=True, **kwargs) -> Optional[Union[Tuple[Any, ...], str, int, float, bool, Decimal]]:
    conn = connect()
    if use_tx: conn.begin()
    
    cur = conn.cursor()
    try:
        cur.execute(stmt, tuple(list(params)))
        res = cur.fetchone() if one else list(cur.fetchall())
    except Exception as e:
        log.exception("Exception while executing query: '%s' - params: %s", stmt, list(params))
        if use_tx: conn.rollback()
        raise e
    finally:
        cur.close()
    
    if use_tx: conn.commit()
    return res


@dataclass
class TableResult:
    schema: str
    table: str
    collation: str
    character_set: str


def get_tables(database=None, table=None):
    """
    SELECT TABLE_SCHEMA, TABLE_NAME, TABLE_COLLATION
    FROM INFORMATION_SCHEMA.TABLES
    WHERE TABLE_NAME = 't_name'
    :return:
    """
    stmt = "SELECT T.TABLE_SCHEMA, T.TABLE_NAME, T.TABLE_COLLATION, CCSA.CHARACTER_SET_NAME " \
           "FROM INFORMATION_SCHEMA.TABLES T, INFORMATION_SCHEMA.COLLATION_CHARACTER_SET_APPLICABILITY CCSA " \
           "WHERE CCSA.collation_name = T.TABLE_COLLATION"
    params = []
    # if any([not empty(database), not empty(table)]):
    #     stmt += " WHERE"
    if not empty(database):
        stmt += " AND T.TABLE_SCHEMA = %s"
        params += [database]
    if not empty(table):
        stmt += " AND T.TABLE_NAME = %s"
        params += [table]
    stmt += ';'
    return [TableResult(*r) for r in query(stmt, *params)]


@dataclass
class TableColumnResult:
    schema: str
    table: str
    column: str
    default: Any
    nullable: bool
    data_type: str
    maximum_length: Optional[int]
    column_type: str
    column_key: Optional[str]
    extra: Optional[str]
    collation: str
    character_set: str
    

def get_columns(database=None, table=None):
    """
    SELECT COL.TABLE_SCHEMA, COL.TABLE_NAME, COL.COLUMN_NAME, COL.COLLATION_NAME, CCSA.CHARACTER_SET_NAME
    FROM INFORMATION_SCHEMA.COLUMNS COL, INFORMATION_SCHEMA.COLLATION_CHARACTER_SET_APPLICABILITY CCSA
WHERE CCSA.collation_name = COL.COLLATION_NAME TABLE_NAME = 't_name';
    :return:
    """
    cols = [
        'TABLE_SCHEMA', 'TABLE_NAME', 'COLUMN_NAME', 'COLUMN_DEFAULT', 'IS_NULLABLE', 'DATA_TYPE',
        'CHARACTER_MAXIMUM_LENGTH', 'COLUMN_TYPE', 'COLUMN_KEY', 'EXTRA', 'COLLATION_NAME', 'CHARACTER_SET_NAME'
    ]
    stmt = f"SELECT {', '.join(cols)} FROM INFORMATION_SCHEMA.COLUMNS"
    params = []
    if any([not empty(database), not empty(table)]):
        stmt += " WHERE"
    if not empty(database):
        stmt += " TABLE_SCHEMA = %s"
        params += [database]
        if not empty(table): stmt += ' AND'
    if not empty(table):
        stmt += " TABLE_NAME = %s"
        params += [table]
    stmt += ';'
    return [TableColumnResult(*r) for r in query(stmt, *params)]


def convert_table(table: str, charset="utf8mb4", collation="utf8mb4_unicode_ci", use_tx=True):
    # stmt = f"ALTER TABLE {table} CONVERT TO CHARACTER SET {charset} COLLATE {collation};"
    stmt = f"ALTER TABLE {table} DEFAULT CHARACTER SET {charset} DEFAULT COLLATE {collation};"
    
    return query(stmt, use_tx=use_tx)


def convert_tables(*tables: str, charset="utf8mb4", collation="utf8mb4_unicode_ci", use_tx=True):
    conn = connect()
    if use_tx:
        conn.begin()
    
    results = []
    
    for tb in tables:
        try:
            log.info("Converting table %s to charset %s and collation %s - use_tx: %s", tb, charset, collation, use_tx)
            res = convert_table(tb, charset=charset, collation=collation, use_tx=not use_tx)
            results += [(tb, res)]
        except Exception as e:
            if use_tx:
                log.error(
                    "Exception while bulk converting tables to %s, %s! Current table was: %s - Rolling back all changes to tables: %s",
                    charset, collation, tb, tables)
                conn.rollback()
                raise e
            log.warning("Exception while converting table %s to %s %s - ignoring error and moving on.", tb, charset, collation)
            results += [(tb, e)]
            continue
    
    return results


class ColumnNotFound(Exception):
    pass


def get_column(table: str, column: str, database=None, fail=False) -> Optional[TableColumnResult]:
    cols = get_columns(database=database, table=table)
    
    for c in cols:
        if c.column.lower() == column.lower():
            return c
    
    if fail:
        raise ColumnNotFound(f"Column '{column}' not found on table '{table}'")
    return None


def convert_column(table: str, column: str, charset="utf8mb4", collation="utf8mb4_unicode_ci", **kwargs):
    database = kwargs.pop('database', None)
    use_tx = kwargs.pop('use_tx', True)
    fail = kwargs.pop('fail', True)
    if not empty(database):
        reconnect(database=database)
    col = get_column(table, column, database=database, fail=fail)
    
    stmt = f"ALTER TABLE {table} MODIFY {col.column} {col.column_type} " \
           f"CHARACTER SET {charset} COLLATE {collation};"
    
    return query(stmt, one=True, use_tx=use_tx)


def convert_columns(table: str, *columns, conv_all=False, charset="utf8mb4", collation="utf8mb4_unicode_ci", **kwargs):
    database = kwargs.pop('database', None)
    use_tx = kwargs.pop('use_tx', True)
    # fail = kwargs.pop('fail', True)
    skip_indexed = kwargs.pop('skip_indexed', True)
    columns = list(columns)
    
    if all([empty(database), empty(settings.DB_NAME)]):
        raise AttributeError("No database specified in args, nor in settings.DB_NAME - cannot continue!")

    if all([empty(columns, itr=True), not conv_all]):
        raise AttributeError("No columns specified in args, and conv_fall is False - cannot continue!")

    # lencols = len(columns)
    cols = get_columns(database, table)
    
    conn = connect()
    if not empty(database):
        conn = reconnect(database=database)
    if use_tx:
        conn.begin()
    results = []
    
    for c in cols:
        try:
            if not conv_all and c.column not in columns:
                log.info("Skipping column '%s' on table '%s' - not in columns arg.", c.column, table)
                continue
            if not empty(c.column_key) and skip_indexed:
                log.info("Skipping column '%s' on table '%s' - column is an index!", c.column, table)
                continue
            if empty(c.character_set) and empty(c.collation):
                log.info("Skipping column '%s' on table '%s' - column doesn't support char sets!", c.column, table)
                continue
            if c.character_set.lower() == charset.lower() and c.collation.lower() == collation.lower():
                log.info("Skipping column '%s' on table '%s' - column is already collation '%s' and charset '%s'",
                         c.column, table, collation, charset)
                continue
            log.info("Converting column '%s' on table '%s' to charset %s and collation %s", c.column, table, charset, collation)
            convert_column(table, c.column, charset=charset, collation=collation, fail=False, use_tx=not use_tx)
            results += [(c, True)]
        except Exception as e:
            if use_tx:
                log.error(
                    "Exception while bulk converting cols to %s, %s! Current col was: %s.%s - Rolling back all changes to columns: %s",
                    charset, collation, table, c.column, columns)
                conn.rollback()
                raise e
            log.warning("Exception while converting column %s to %s %s - ignoring error and moving on.", c.column, charset, collation)
            results += [(c, e)]
    
    conn.commit()
    
    return results
