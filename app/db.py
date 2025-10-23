import mysql.connector
import logging
from flask import Flask, g
from mysql.connector.pooling import MySQLConnectionPool

# init logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# init connection pool
connection_pool: MySQLConnectionPool = None

def init_db(app: Flask, user: str, password: str, host: str, database: str,
            pool_name: str = "flask_db_pool", autocommit: bool = True):
    """init database connection pool"""
    global connection_pool
    connection_pool = MySQLConnectionPool(
        user=user,
        password=password,
        host=host,
        database=database,
        pool_name=pool_name,
        autocommit=autocommit,
        pool_size=5,  # set the pool size to 10 connections
        charset='utf8mb4',  # set the charset to utf-8
        time_zone='Pacific/Auckland' # set the timezone
    )
    app.teardown_appcontext(close_db)

def get_db():
    """get current database connection"""
    if 'db' not in g:
        g.db = connection_pool.get_connection()
    return g.db

def get_cursor():
    """get cursor from current database connection"""
    return get_db().cursor(dictionary=True)

def close_db(exception=None):
    """close current database connection when app context ends"""
    db = g.pop('db', None)
    if db:
        db.close()

def query_db(query, params=None, fetch_one=False, fetch_all=False):
    """execute SELECT query and return results"""
    try:
        with get_cursor() as cursor:
            cursor.execute(query, params or ())
            if fetch_one:
                return cursor.fetchone()
            if fetch_all:
                return cursor.fetchall()
            # 如果没有指定 fetch_one 或 fetch_all，默认返回所有结果
            return cursor.fetchall()
    except mysql.connector.Error as e:
        logger.error(f"Database query error: {e}")
        return None

def execute_db(query, params=None):
    """execute INSERT / UPDATE / DELETE query and return the affected row(s)"""
    conn = get_db()
    try:
        with conn.cursor() as cursor:
            cursor.execute(query, params or ())
            conn.commit()
            return cursor.lastrowid
    except mysql.connector.Error as e:
        logger.error(f"Database execution error: {e}")
        conn.rollback()
        return None

def begin_transaction():
    """开始一个新的事务"""
    conn = get_db()
    conn.start_transaction()

def commit_transaction():
    """提交当前事务"""
    conn = get_db()
    conn.commit()

def rollback_transaction():
    """回滚当前事务"""
    conn = get_db()
    conn.rollback()