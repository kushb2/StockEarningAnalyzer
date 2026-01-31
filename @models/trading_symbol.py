
class TradingSymbol:
    def __init__(self, stock_name: str, symbol: str, description: str = ""):
        self.stock_name = stock_name
        self.symbol = symbol
        self.description = description

    def __repr__(self):
        return f"TradingSymbol(stock_name='{self.stock_name}', symbol='{self.symbol}', description='{self.description}')"
