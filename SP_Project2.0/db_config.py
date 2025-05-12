import mysql.connector
from mysql.connector import Error

# MySQL 연결 정보 (본인의 환경에 맞게 수정하세요)
DB_CONFIG = {
    'host': 'localhost',       # MySQL 서버 주소 (대부분 localhost)
    'user': 'root',   # MySQL 사용자 이름
    'password': '1200', # MySQL 사용자 비밀번호
    'database': 'backtest_db'  # 이전에 생성한 데이터베이스 이름
}

def get_db_connection():
    """MySQL 데이터베이스 연결을 생성하고 반환합니다."""
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        if conn.is_connected():
            # print('MySQL 데이터베이스에 성공적으로 연결되었습니다.')
            return conn
    except Error as e:
        print(f"MySQL 연결 오류: {e}")
        return None

if __name__ == '__main__':
    # 연결 테스트
    conn = get_db_connection()
    if conn and conn.is_connected():
        print('get_db_connection() 테스트 성공.')
        conn.close()