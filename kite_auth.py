
import datetime
import json
import os
from kiteconnect import KiteConnect

class KiteAuthenticator:
    def __init__(self, api_key, api_secret):
        self.api_key = api_key
        self.api_secret = api_secret
        self.kite = KiteConnect(api_key=self.api_key)
        self.access_token_file = "configs/access_token.json"
        self._try_load_access_token()

    def _try_load_access_token(self):
        if os.path.exists(self.access_token_file):
            with open(self.access_token_file, 'r') as f:
                try:
                    token_data = json.load(f)
                    stored_date = datetime.datetime.strptime(token_data.get('date'), '%Y-%m-%d').date()
                    if stored_date == datetime.date.today():
                        access_token = token_data.get('access_token')
                        if access_token:
                            self.kite.set_access_token(access_token)
                            print("Access token loaded from file.")
                except (json.JSONDecodeError, KeyError, TypeError):
                    # Invalid file format, proceed to generate a new token
                    pass

    def get_login_url(self):
        return self.kite.login_url()

    def generate_and_set_access_token(self, request_token):
        try:
            data = self.kite.generate_session(request_token, api_secret=self.api_secret)
            self.kite.set_access_token(data["access_token"])
            token_data = {
                'date': datetime.date.today().strftime('%Y-%m-%d'),
                'access_token': data['access_token']
            }
            with open(self.access_token_file, 'w') as f:
                json.dump(token_data, f)
            print("Access token generated and saved.")
            return data["access_token"]
        except Exception as e:
            print(f"Error generating access token: {e}")
            return None

    def is_authenticated(self):
        return self.kite.access_token is not None


def load_api_config():
    try:
        with open('configs/api_config.json', 'r') as f:
            config = json.load(f)
        return config['API_KEY'], config['API_SECRET']
    except FileNotFoundError:
        print("Error: api_config.json not found. Please create it with API_KEY and API_SECRET.")
        exit()
    except KeyError:
        print("Error: API_KEY or API_SECRET not found in api_config.json.")
        exit()

if __name__ == '__main__':
    API_KEY, API_SECRET = load_api_config()

    if API_KEY == "YOUR_API_KEY" or API_SECRET == "YOUR_API_SECRET":
        print("Please replace 'YOUR_API_KEY' and 'YOUR_API_SECRET' with your actual credentials.")
    else:
        auth = KiteAuthenticator(api_key=API_KEY, api_secret=API_SECRET)
        print(auth.is_authenticated())
        print(auth)

        if not auth.is_authenticated():
            print("Please go to this URL and authorize the app:", auth.get_login_url())
            request_token_from_url = input("Enter the request_token from the redirect URL: ")
            
            if request_token_from_url:
                access_token = auth.generate_and_set_access_token(request_token_from_url)
                if access_token:
                    print("Successfully authenticated!")
                else:
                    print("Authentication failed.")
        else:
            print("Already authenticated for today.")

        # Example of using the kite object
        if auth.is_authenticated():
            try:
                # Fetch user profile to verify connection
                profile = auth.kite.profile()
                print("\nUser Profile:")
                print(json.dumps(profile, indent=4))
            except Exception as e:
                print(f"\nError fetching profile: {e}")
                print("Your access token might be invalid or expired. Please re-run the script to authenticate.")

