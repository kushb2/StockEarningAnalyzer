
import json
import os
from kiteconnect import KiteConnect

# Get the directory of the current script
script_dir = os.path.dirname(os.path.abspath(__file__))
# Go up one level to the project root
project_root = os.path.dirname(script_dir)

def find_instrument_tokens():
    """
    Finds and updates instrument tokens for stocks in stockSymbolDetails.json.
    Only updates tokens that are null or missing.
    """
    stock_details_path = os.path.join(project_root, 'configs', 'stockSymbolDetails.json')
    
    try:
        # Load stock symbol details
        with open(stock_details_path, 'r') as f:
            stock_details = json.load(f)
    except FileNotFoundError:
        print("Error: stockSymbolDetails.json not found.")
        return
    except (KeyError, TypeError):
        print("Error: stockSymbolDetails.json is not in the expected format.")
        return
    
    # Find symbols that need tokens (null or missing)
    symbols_to_find = []
    for stock in stock_details:
        if stock.get('instrument_token') is None:
            symbols_to_find.append(stock['symbol'])
    
    if not symbols_to_find:
        print("All stocks already have instrument tokens. Nothing to update.")
        return
    
    print(f"Found {len(symbols_to_find)} stocks without instrument tokens: {', '.join(symbols_to_find)}")

    try:
        # Load the access token from the file
        with open(os.path.join(project_root, 'configs/access_token.json'), 'r') as f:
            token_data = json.load(f)
            access_token = token_data.get('access_token')

        if not access_token:
            print("Access token not found in access_token.json")
            return

        # Load the API key from api_config.json
        try:
            with open(os.path.join(project_root, 'configs/api_config.json'), 'r') as f:
                config = json.load(f)
            api_key = config.get('API_KEY')
        except FileNotFoundError:
            print("Error: api_config.json not found. Please create it with API_KEY and API_SECRET.")
            return
        except KeyError:
            print("Error: API_KEY not found in api_config.json.")
            return

        if not api_key:
            print("API_KEY not found in api_config.json")
            return

        # Initialize KiteConnect
        kite = KiteConnect(api_key=api_key, access_token=access_token)

        # Fetch all instruments for the NSE exchange
        print("Fetching all NSE instruments...")
        instruments = kite.instruments('NSE')
        print(f"Fetched {len(instruments)} instruments.")

        # Use a set for efficient lookup of trading symbols
        symbols_set = set(symbols_to_find)
        found_tokens = {}

        # Filter the instruments efficiently
        for instrument in instruments:
            if instrument['tradingsymbol'] in symbols_set:
                found_tokens[instrument['tradingsymbol']] = instrument['instrument_token']
                # Remove the found symbol to speed up subsequent searches
                symbols_set.remove(instrument['tradingsymbol'])
                if not symbols_set:
                    break  # Stop searching once all symbols are found

        # Update stock_details with found tokens
        updated_count = 0
        for stock in stock_details:
            symbol = stock['symbol']
            if symbol in found_tokens:
                stock['instrument_token'] = found_tokens[symbol]
                updated_count += 1
                print(f"✓ Updated {symbol}: {found_tokens[symbol]}")
        
        # Report symbols not found
        if symbols_set:
            print(f"\n⚠ Warning: Could not find tokens for: {', '.join(symbols_set)}")

        # Save the updated stock details
        with open(stock_details_path, 'w') as f:
            json.dump(stock_details, f, indent=2)

        print(f"\n✓ Successfully updated {updated_count} instrument tokens.")
        print(f"✓ Results saved to {stock_details_path}")

    except FileNotFoundError as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    find_instrument_tokens()
