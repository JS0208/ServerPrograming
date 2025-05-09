CREATE DATABASE IF NOT EXISTS backtest_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE backtest_db;
-- users 테이블 생성 (로그인 기능 구현 시)
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(255) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL, -- 실제 운영 시에는 해시된 비밀번호를 저장해야 합니다.
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- strategies 테이블 생성
CREATE TABLE IF NOT EXISTS strategies (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    -- user_id INT, -- 사용자별 전략 관리를 위해 추가 고려 가능
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    -- FOREIGN KEY (user_id) REFERENCES users(id) -- users 테이블과 연결 시
);

-- conditions 테이블 생성 (전략별 상세 조건)
CREATE TABLE IF NOT EXISTS conditions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    strategy_id INT NOT NULL,
    indicator_type VARCHAR(50) NOT NULL, -- 예: 'SMA', 'RSI', 'MACD'
    value VARCHAR(255) NOT NULL, -- 조건 값 (예: 'period:20', 'buy_threshold:30') JSON 형태로 저장 고려
    FOREIGN KEY (strategy_id) REFERENCES strategies(id) ON DELETE CASCADE
);

-- results 테이블 생성 (백테스트 결과)
CREATE TABLE IF NOT EXISTS results (
    id INT AUTO_INCREMENT PRIMARY KEY,
    strategy_id INT NOT NULL,
    return_rate FLOAT,
    mdd FLOAT, -- Max Drawdown
    win_rate FLOAT,
    -- 추가적인 성과 지표들...
    executed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (strategy_id) REFERENCES strategies(id) ON DELETE CASCADE
);