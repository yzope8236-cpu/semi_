import clickhouse_connect
from .config import settings

def client(): return clickhouse_connect.get_client(host=settings.clickhouse_host, port=settings.clickhouse_port, username=settings.clickhouse_user, password=settings.clickhouse_password, database="yieldscope")
def rows(sql, parameters=None):
    r=client().query(sql, parameters=parameters or {})
    return [dict(zip(r.column_names,x)) for x in r.result_rows]
def scalar(sql, parameters=None, default=0):
    r=client().query(sql, parameters=parameters or {})
    return r.result_rows[0][0] if r.result_rows else default
