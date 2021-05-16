from TradingBot import TradingBot
import datetime
import numpy as np
import pandas as pd
import multiprocessing as mp
import os

class Backtester(TradingBot):
    
    benchmark = None
    base_folder = "/home/alex/Projects/Trading-Bot-Class1" # Change this to your path
    
    def __init__(self, tickers, benchmark="SPY", **kwargs):
        self.benchmark = benchmark
        tickers.append(self.benchmark)
        super().__init__(tickers, **kwargs)
        
        # Make sure we don't trade the benchmark
        self.trade_data.loc[:,("Signal", self.benchmark)] = -1e6  
        
    def run_backtest(self, start_date, end_date):
        # Entry method for running a single backtest
        trade_data = self._filter_dates(self.trade_data, start_date, end_date)
        trades = self._run_backtest(trade_data)
        # Save
        trades.loc[:, "Bench_TRI"] = trades["Close", self.benchmark]/trades["Close", self.benchmark].iloc[0]
        f_name = f"backtest_{str(start_date)} to {str(end_date)}.csv"
        trades.to_csv(os.path.join(self.base_folder, 'output', f_name))
        return trades

    def path_dependency_test(self, start_date, end_date):
        # Entry method for running multiple backtests
        date_format = "%d-%b-%Y"
        start = datetime.datetime.strptime(start_date, date_format)
        end = datetime.datetime.strptime(end_date, date_format)
        
        dd = [start + datetime.timedelta(days=x) for x in range(0, (end-start).days, 180)]
        mesh = np.array(np.meshgrid(dd, dd))
        date_pairs = mesh.T.reshape(-1, 2)
        min_period = datetime.timedelta(365*3)
        data = []
        for comb in date_pairs:            
            if (comb[1] - comb[0]) >= min_period:
                start_str = comb[0].strftime(date_format)
                end_str = comb[1].strftime(date_format)
                trade_data = self._filter_dates(self.trade_data, start_str, end_str)
                data.append(trade_data)
        
        print(f'Running {len(data)} backtests')
        pool = mp.Pool(mp.cpu_count()*2)
        data = pool.map(self._run_backtest, data)        
        
        pool.close()
        summary = None
        for d in data:
            summary = self._make_summary_report(d, summary)
        # Save
        f_name = f"summary_{str(datetime.datetime.today())}.csv"
        pd.DataFrame(data=summary).to_csv(os.path.join(self.base_folder, 'output', f_name))
    
    def _get_query_range(self):
        # Methond to set dates for the data to be grabbed
        start_date = "1990-01-01"
        end_date = str(datetime.date.today())
        return start_date, end_date

    @staticmethod
    def _filter_dates(data, start_date, end_date):
        data = data.loc[start_date:end_date]
        return data

    def _run_backtest(self, trade_data):
        # Main method for running a single backtest
        print(f'Running backtest for {trade_data.index[0]} to {trade_data.index[-1]}')
        
        trade_data.loc[:, "Position"] = None
        trade_data.loc[:, "Port_Return"] = 0.0
        trade_data.loc[:, "Status"] = self.NO_CHANGE
        
        prev_position = None
        for date, row in trade_data.iterrows():
            next_position, status = self._make_trade_decision(row, prev_position)
            row.loc["Position"] = next_position
            row.loc["Status"] = status
            
            # New Position
            if status == self.NEW_POSITION:
                row.loc["Port_Return"] = row["Close", next_position]/row["Open", next_position]-1  
                
            # Stay in current position
            elif (status == self.NO_CHANGE) and (next_position is not None):
                row.loc["Port_Return"] = row["Close", next_position]/row["Prev_Close", prev_position]-1                      
            
            # Exit position
            elif status == self.EXIT_POSITION:
                row.loc["Port_Return"] = row["Open", prev_position]/row["Prev_Close", prev_position]-1  
            
            # Swap positions to higher momentun stock
            elif status == self.CHANGE_POSITION:
                exit_return = row["Open", prev_position]/row["Prev_Close", prev_position]-1  
                new_return = row["Open", next_position]/row["Close", next_position]-1  
                row.loc["Port_Return"] = (1+exit_return)*(1+new_return)-1
                    
            prev_position = next_position
            
            trade_data.loc[date] = row     

        trade_data.loc[:, "Port_TRI"] = trade_data.Port_Return.add(1).cumprod()
        trade_data.loc[:, "Port_Drawdown"] = trade_data["Port_TRI"].rolling(window=250).apply(self._calc_drawdown, raw=False)
        trade_data.loc[:, "BM_Drawdown"] = trade_data["Close", self.benchmark].rolling(window=250).apply(self._calc_drawdown, raw=False)
        
        return trade_data
    
    def _make_summary_report(self, trade_data, summary):                
        # Creates a summary report for the Path Dependancy Test
        if summary is None:
            summary = {"Start_Date": [],
                       "End_Date" : [],
                       "Port_Return":[],
                       "Benchmark_Return":[],
                       "Port_Return_Ann": [],
                       "Benchmark_Return_Ann": [],
                       "Port_1yr_Drawdown": [], 
                       "Benchmark_1yr_Drawdown": []}        
        
        summary['Start_Date'].append(trade_data.index[0])
        summary['End_Date'].append(trade_data.index[-1])                
        
        # Cummulative returns
        # Portfolio
        port_ret = trade_data["Port_TRI"][-1]/trade_data["Port_TRI"][0]-1
        summary['Port_Return'].append(self.to_pct(port_ret,2))
        # Benchmark
        bm_close = trade_data['Close', self.benchmark]
        bm_ret = bm_close[-1]/bm_close[0]-1
        summary['Benchmark_Return'].append(self.to_pct(bm_ret,2))
        
        # Annualized returns
        n_days = (trade_data.index[-1] - trade_data.index[0]).days        
        # Portfolio
        port_ann_ret = (port_ret+1)**(365/n_days)-1
        summary['Port_Return_Ann'].append(self.to_pct(port_ann_ret,2))
        # Benchmark
        bm_ann_ret = (bm_ret+1)**(365/n_days)-1
        summary['Benchmark_Return_Ann'].append(self.to_pct(bm_ann_ret,2))
        
        # Drawdowns
        # Portfolio
        port_dd = np.min(trade_data.loc[:, "Port_Drawdown"])
        summary['Port_1yr_Drawdown'].append(self.to_pct(port_dd,2))
        # Benchmark
        bm_dd = np.min(trade_data.loc[:, "BM_Drawdown"])
        summary['Benchmark_1yr_Drawdown'].append(self.to_pct(bm_dd,2))
        
        return summary
    
    @staticmethod
    def to_pct(number, decimals):
        number = np.round(number*100,decimals)
        return str(number) + '%'

    @staticmethod
    def _calc_drawdown(array):
        last = array[-1]
        drawdown = last/np.max(array)-1
        return drawdown
        
        