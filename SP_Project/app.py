from flask import Flask, render_template, request, redirect, url_for
from markupsafe import Markup # Markup을 markupsafe에서 가져옵니다.
from db_config import get_db_connection
import mysql.connector
import FinanceDataReader as fdr
import pandas as pd
from datetime import datetime, timedelta


app = Flask(__name__)

# --- (이전 코드: index, list_strategies 등은 거의 그대로 유지, stock_data_view도 유지) ---
@app.route('/')
def index():
    # 세션 등을 활용하여 로그인 상태에 따라 다른 페이지를 보여줄 수도 있습니다.
    return render_template('index.html') # 홈페이지 템플릿을 보여주도록 변경

@app.route('/strategies')
def list_strategies():
    conn = None
    cursor = None
    strategies_with_conditions = []
    try:
        conn = get_db_connection()
        if conn is None:
            return "데이터베이스 연결에 실패했습니다.", 500
        
        cursor = conn.cursor(dictionary=True)
        # 전략 정보와 함께 해당 전략의 조건들도 가져오는 쿼리 (LEFT JOIN 사용)
        # 여기서는 간단히 첫 번째 조건만 가져오도록 하거나, 별도 로직으로 처리 필요
        # 지금은 우선 전략 기본 정보만 가져옵니다. 조건 표시는 상세 페이지에서 하는 것이 좋습니다.
        sql = """
            SELECT s.id, s.name, s.description, s.created_at, 
                   GROUP_CONCAT(CONCAT(c.indicator_type, ': ', c.value) SEPARATOR '; ') as conditions_summary
            FROM strategies s
            LEFT JOIN conditions c ON s.id = c.strategy_id
            GROUP BY s.id, s.name, s.description, s.created_at
            ORDER BY s.created_at DESC
        """
        cursor.execute(sql)
        strategies = cursor.fetchall()
        return render_template('strategies_list.html', strategies=strategies)
    except mysql.connector.Error as e:
        print(f"전략 목록 조회 오류: {e}")
        return "전략 목록을 가져오는 중 오류가 발생했습니다.", 500
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()


@app.route('/strategies/add', methods=['GET', 'POST'])
def add_strategy():
    if request.method == 'POST':
        # 전략 기본 정보
        strategy_name = request.form['name']
        strategy_description = request.form['description']
        
        # 조건 정보
        indicator_type = request.form.get('indicator_type') # .get()으로 None 처리 용이
        indicator_value = request.form.get('indicator_value')

        if not strategy_name:
            return "전략 이름은 필수입니다.", 400
            
        conn = None
        cursor = None
        try:
            conn = get_db_connection()
            if conn is None:
                return "데이터베이스 연결에 실패했습니다.", 500
            
            cursor = conn.cursor()
            
            # 1. strategies 테이블에 전략 저장
            sql_strategy = "INSERT INTO strategies (name, description) VALUES (%s, %s)"
            cursor.execute(sql_strategy, (strategy_name, strategy_description))
            strategy_id = cursor.lastrowid # 방금 삽입된 strategy의 ID 가져오기
            
            # 2. conditions 테이블에 조건 저장 (입력된 경우에만)
            if strategy_id and indicator_type and indicator_value:
                sql_condition = "INSERT INTO conditions (strategy_id, indicator_type, value) VALUES (%s, %s, %s)"
                cursor.execute(sql_condition, (strategy_id, indicator_type, indicator_value))
            
            conn.commit()
            # flash('전략이 성공적으로 등록되었습니다.', 'success') # 알림 메시지 (선택 사항)
            return redirect(url_for('list_strategies'))
        except mysql.connector.Error as e:
            print(f"전략 및 조건 등록 오류: {e}")
            if conn:
                conn.rollback() # 오류 발생 시 모든 변경사항 롤백
            # flash(f'등록 중 오류 발생: {e}', 'error')
            return "전략 및 조건을 등록하는 중 오류가 발생했습니다.", 500
        finally:
            if cursor:
                cursor.close()
            if conn and conn.is_connected():
                conn.close()
    else: # GET 요청일 경우
        return render_template('add_strategy.html')

# --- 주가 데이터 조회 기능 (stock_data_view)은 이전과 동일하게 유지 ---
@app.route('/stock_data', methods=['GET', 'POST'])
def stock_data_view():
    if request.method == 'POST':
        ticker = request.form.get('ticker')
        start_date_str = request.form.get('start_date')
        end_date_str = request.form.get('end_date')

        if not ticker or not start_date_str or not end_date_str:
            return render_template('stock_data.html', error="종목코드와 기간을 모두 입력해주세요.", ticker=ticker, start_date=start_date_str, end_date=end_date_str)

        try:
            df = fdr.DataReader(ticker, start_date_str, end_date_str)
            if df.empty:
                return render_template('stock_data.html', error=f"{ticker}에 대한 데이터를 가져올 수 없습니다. 종목코드나 기간을 확인해주세요.", ticker=ticker, start_date=start_date_str, end_date=end_date_str)
            data_html = Markup(df.to_html(classes='table table-striped table-hover', border=0))
            return render_template('stock_data.html', data_table=data_html, ticker=ticker, start_date=start_date_str, end_date=end_date_str)
        except Exception as e:
            print(f"주가 데이터 조회 오류: {e}")
            return render_template('stock_data.html', error=f"데이터 조회 중 오류 발생: {e}", ticker=ticker, start_date=start_date_str, end_date=end_date_str)
            
    end_date_default = datetime.now().strftime('%Y-%m-%d')
    start_date_default = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
    return render_template('stock_data.html', start_date=start_date_default, end_date=end_date_default)

@app.route('/backtest/run', methods=['GET'])
def run_backtest_page():
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        if conn is None:
            return "데이터베이스 연결 실패", 500
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id, name FROM strategies ORDER BY name ASC")
        strategies = cursor.fetchall()
        
        # 기본 날짜 설정 (예: 한달 전부터 오늘까지)
        default_end_date = datetime.now().strftime('%Y-%m-%d')
        default_start_date = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d') # 1년 전

        return render_template('run_backtest.html', strategies=strategies, default_start_date=default_start_date, default_end_date=default_end_date)
    except mysql.connector.Error as e:
        print(f"전략 목록 조회 오류 (백테스트용): {e}")
        return "전략 목록을 가져오는 중 오류 발생", 500
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()

# 백테스트 실행 로직 처리
@app.route('/backtest/execute', methods=['POST'])
def execute_backtest():
    if request.method == 'POST':
        strategy_id = request.form.get('strategy_id')
        ticker = request.form.get('ticker')
        start_date_str = request.form.get('start_date')
        end_date_str = request.form.get('end_date')

        if not all([strategy_id, ticker, start_date_str, end_date_str]):
            # flash("모든 필드를 올바르게 입력해주세요.", "error") # 알림 기능 사용 시
            return redirect(url_for('run_backtest_page'))

        conn = None
        cursor = None
        try:
            conn = get_db_connection()
            if conn is None:
                return "데이터베이스 연결 실패", 500
            
            cursor = conn.cursor(dictionary=True)

            # 1. 선택된 전략의 정보 및 조건 가져오기
            cursor.execute("SELECT name FROM strategies WHERE id = %s", (strategy_id,))
            strategy_info = cursor.fetchone()
            if not strategy_info:
                return "선택한 전략을 찾을 수 없습니다.", 404
            
            cursor.execute("SELECT indicator_type, value FROM conditions WHERE strategy_id = %s", (strategy_id,))
            conditions = cursor.fetchall()
            if not conditions:
                return f"전략 '{strategy_info['name']}'에 설정된 조건이 없습니다. 조건을 먼저 설정해주세요.", 400

            # 2. 주가 데이터 가져오기
            stock_data_df = fdr.DataReader(ticker, start_date_str, end_date_str)
            if stock_data_df.empty:
                return f"{ticker} 종목의 데이터를 기간({start_date_str} ~ {end_date_str}) 동안 가져올 수 없습니다.", 400

            # --- 여기서부터 실제 백테스팅 엔진 로직 구현 ---
            
            # 임시: 현재는 첫 번째 조건만 사용한다고 가정
            # 실제로는 여러 조건을 조합하는 로직 필요
            # 또한, conditions 리스트가 비어있지 않다는 것을 위에서 확인했으므로, 첫번째 요소 접근 가능
            current_condition = conditions[0] 
            indicator_type = current_condition['indicator_type'].upper() # 대소문자 구분 없이 비교하기 위함
            raw_value = current_condition['value']
            
            # 3. 기술적 지표 계산
            if indicator_type == 'SMA':
                try:
                    # SMA 기간 값을 정수로 변환
                    sma_period = int(raw_value)
                    if sma_period <= 0:
                        raise ValueError("SMA 기간은 양의 정수여야 합니다.")
                    # DataFrame에 SMA 컬럼 추가
                    sma_col_name = f'SMA{sma_period}'
                    stock_data_df[sma_col_name] = stock_data_df['Close'].rolling(window=sma_period).mean()
                except ValueError:
                    return f"SMA 조건 값 '{raw_value}'이(가) 올바른 숫자(기간) 형식이 아닙니다.", 400
            # TODO: 여기에 다른 지표들(RSI, MACD 등) 계산 로직 추가
            # elif indicator_type == 'RSI':
            #     # RSI 계산 로직 ...
            #     pass 
            else:
                return f"지원하지 않는 지표 타입입니다: {indicator_type}", 400

            # NaN 값 제거 (SMA 계산으로 인해 앞부분에 NaN이 생김)
            # stock_data_df.dropna(inplace=True) # NaN 있는 행 전체 제거 또는 아래처럼 특정 컬럼 기준
            if indicator_type == 'SMA' and sma_col_name in stock_data_df.columns:
                 stock_data_df.dropna(subset=[sma_col_name], inplace=True)
                 if stock_data_df.empty:
                     return f"SMA({sma_period}) 계산 후 데이터가 남지 않았습니다. 기간을 확인해주세요.", 400


            # 4. 매수/매도 신호 생성 (SMA 크로스오버 기반 예시)
            # 'Signal' 컬럼: 1 (매수), -1 (매도), 0 (유지)
            stock_data_df['Signal'] = 0 
            if indicator_type == 'SMA' and sma_col_name in stock_data_df.columns:
                # 종가가 SMA를 상향 돌파하면 매수 신호 (어제 종가 < 어제 SMA, 오늘 종가 > 오늘 SMA)
                stock_data_df.loc[(stock_data_df['Close'].shift(1) < stock_data_df[sma_col_name].shift(1)) & \
                                  (stock_data_df['Close'] > stock_data_df[sma_col_name]), 'Signal'] = 1
                
                # 종가가 SMA를 하향 돌파하면 매도 신호 (어제 종가 > 어제 SMA, 오늘 종가 < 오늘 SMA)
                stock_data_df.loc[(stock_data_df['Close'].shift(1) > stock_data_df[sma_col_name].shift(1)) & \
                                  (stock_data_df['Close'] < stock_data_df[sma_col_name]), 'Signal'] = -1
            
            # TODO: 실제 포지션 관리 로직 추가 (현재는 단순 신호만 생성)
            # 예: 한번 매수하면 매도 신호가 나올 때까지 포지션 유지 등
            
            # 5. 포트폴리오 시뮬레이션 및 성과 계산
            initial_capital = 10000000.0  # 초기 자본금 천만원
            cash = initial_capital
            shares = 0
            portfolio_value = initial_capital
            position = 0 # 0: No position, 1: Long position
            
            stock_data_df['Portfolio_Value'] = initial_capital # 포트폴리오 가치 기록용 컬럼
            stock_data_df['Return'] = 0.0 # 일일 수익률 기록용
            
            trades_count = 0
            winning_trades_count = 0
            last_buy_price = 0

            for i in range(len(stock_data_df)):
                signal = stock_data_df['Signal'].iloc[i]
                current_price = stock_data_df['Close'].iloc[i]
                
                # 포트폴리오 가치 업데이트 (주식 가치 + 현금)
                if position == 1: # 주식 보유 중
                    portfolio_value = shares * current_price + cash
                else: # 현금만 보유 중
                    portfolio_value = cash
                stock_data_df.loc[stock_data_df.index[i], 'Portfolio_Value'] = portfolio_value

                # 거래 로직 (단순화된 버전: 전량 매수/매도, 거래 비용 미고려)
                if signal == 1 and position == 0: # 매수 신호 & 현재 포지션 없음
                    shares_to_buy = cash // current_price # 현재 현금으로 살 수 있는 최대 주식 수
                    if shares_to_buy > 0:
                        shares = shares_to_buy
                        cash -= shares * current_price
                        position = 1 # 매수 포지션 진입
                        trades_count += 1
                        last_buy_price = current_price
                        # print(f"{stock_data_df.index[i].strftime('%Y-%m-%d')}: 매수 {shares}주 @ {current_price}, 현금: {cash:.0f}")

                elif signal == -1 and position == 1: # 매도 신호 & 현재 포지션 있음
                    cash += shares * current_price
                    # print(f"{stock_data_df.index[i].strftime('%Y-%m-%d')}: 매도 {shares}주 @ {current_price}, 현금: {cash:.0f}, 수익: {(current_price - last_buy_price) * shares:.0f}")
                    if current_price > last_buy_price : # 수익 본 거래
                        winning_trades_count +=1
                    shares = 0
                    position = 0 # 매도 후 포지션 없음
                    # trades_count += 1 # 매수-매도 쌍을 1 거래로 볼 경우 여기서 카운트하지 않음 (위에서 매수 시 카운트)
            
            # 최종 포트폴리오 가치 (마지막 날 종가로 모든 주식 청산 가정)
            if position == 1:
                cash += shares * stock_data_df['Close'].iloc[-1]
                shares = 0
            final_portfolio_value = cash

            # 성과 지표 계산
            total_return_pct = ((final_portfolio_value - initial_capital) / initial_capital) * 100
            
            # MDD 계산
            stock_data_df['Peak'] = stock_data_df['Portfolio_Value'].cummax()
            stock_data_df['Drawdown'] = (stock_data_df['Portfolio_Value'] - stock_data_df['Peak']) / stock_data_df['Peak']
            max_drawdown_pct = stock_data_df['Drawdown'].min() * 100 if not stock_data_df['Drawdown'].empty else 0

            win_rate_pct = (winning_trades_count / trades_count) * 100 if trades_count > 0 else 0
            
            # 6. 결과 DB에 저장 (`results` 테이블)
            # executed_at은 DATETIME 타입이므로 Python의 datetime 객체로 전달
            executed_at_dt = datetime.now()

            # 모든 컬럼명을 명시적으로 지정
            sql_insert_result = """
                INSERT INTO results (strategy_id, return_rate, mdd, win_rate, executed_at) 
                VALUES (%s, %s, %s, %s, %s)
            """
            # 소수점 처리 (예: 두 자리까지)
            # return_rate, mdd, win_rate는 DB 스키마에 맞게 float으로 저장
            cursor.execute(sql_insert_result, (
                strategy_id, 
                float(f"{total_return_pct:.2f}"), 
                float(f"{max_drawdown_pct:.2f}"), 
                float(f"{win_rate_pct:.2f}"),
                executed_at_dt 
            ))
            conn.commit()
            
            result_summary_kpis = {
                "total_return_pct": f"{total_return_pct:.2f}%",
                "max_drawdown_pct": f"{max_drawdown_pct:.2f}%",
                "win_rate_pct": f"{win_rate_pct:.2f}% ({winning_trades_count}/{trades_count})",
                "num_trades": trades_count,
                "initial_capital": f"{initial_capital:,.0f} 원",
                "final_portfolio_value": f"{final_portfolio_value:,.0f} 원",
                "strategy_name": strategy_info['name'],
                "ticker": ticker,
                "period": f"{start_date_str} ~ {end_date_str}",
                "conditions_applied": conditions
            }

            # HTML 템플릿으로 결과 전달
            return render_template('backtest_result.html', 
                                   result=result_summary_kpis, 
                                   stock_data_html=Markup(stock_data_df[['Close', sma_col_name if sma_col_name else 'Close', 'Signal', 'Portfolio_Value', 'Drawdown']].tail(20).to_html(classes="table table-sm table-striped", float_format='{:,.2f}'.format)))

        except mysql.connector.Error as e:
            print(f"백테스트 실행 중 DB 오류: {e}")
            if conn: conn.rollback()
            # flash(f"DB 오류: {e}", "error")
            return "백테스트 실행 중 데이터베이스 오류 발생", 500
        except ValueError as ve:
             print(f"백테스트 실행 중 값 오류: {ve}")
            #  flash(f"값 오류: {ve}", "error")
             return f"백테스트 실행 중 값 관련 오류 발생: {str(ve)}", 400
        except Exception as e:
            print(f"백테스트 실행 중 일반 오류: {e}")
            # flash(f"일반 오류: {e}", "error")
            return f"백테스트 실행 중 알 수 없는 오류가 발생했습니다. (오류: {type(e).__name__}: {str(e)})", 500
        finally:
            if cursor:
                cursor.close()
            if conn and conn.is_connected():
                conn.close()
    return redirect(url_for('run_backtest_page'))


# --- (home, index 등 다른 라우트들은 이전과 동일) ---
@app.route('/home')
def home():
    return render_template('index.html')

@app.route('/') # 루트 경로를 home으로 연결
def root_redirect():
    return redirect(url_for('home'))


if __name__ == '__main__':
    app.run(debug=True)