from Backtester import Backtester
from TradingBot import TradingBot

#tb = TradingBot(["IWD", "IWF"])
#tb.check_for_trades("IWD")


if __name__ == "__main__":    
    
    bt = Backtester(["IWD", "IWF"], swap_positions=True)
    trade_date = bt.run_backtest("2000-05-10", "2020-01-01")