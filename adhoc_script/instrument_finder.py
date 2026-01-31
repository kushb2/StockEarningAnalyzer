
import json
import os
from kiteconnect import KiteConnect

# Get the directory of the current script
script_dir = os.path.dirname(os.path.abspath(__file__))
# Go up one level to the project root
project_root = os.path.dirname(script_dir)

def find_instrument_tokens():
    """
    Finds and stores instrument tokens for a list of trading symbols from a JSON file.
    """
    try:
        # Load trading symbols from JSON
        with open(os.path.join(project_root, 'configs', 'trading_symbols.json'), 'r') as f:
            trading_symbols_to_find = [item['symbol'] for item in json.load(f)]
    except FileNotFoundError:
        print("Error: trading_symbols.json not found.")
        return
    except (KeyError, TypeError):
        print("Error: trading_symbols.json is not in the expected format.")
        return

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
        symbols_set = set(trading_symbols_to_find)
        instrument_tokens = {}

        # Filter the instruments efficiently
        for instrument in instruments:
            if instrument['tradingsymbol'] in symbols_set:
                instrument_tokens[instrument['tradingsymbol']] = instrument['instrument_token']
                # Remove the found symbol to speed up subsequent searches
                symbols_set.remove(instrument['tradingsymbol'])
                if not symbols_set:
                    break  # Stop searching once all symbols are found

        # Save the results to a file
        output_filename = os.path.join(project_root, 'configs', 'instrument_tokens.json')
        with open(output_filename, 'w') as f:
            json.dump(instrument_tokens, f, indent=4)

        print(f"Successfully found {len(instrument_tokens)} instrument tokens.")
        print(f"Results saved to {output_filename}")

    except FileNotFoundError as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    find_instrument_tokens()
