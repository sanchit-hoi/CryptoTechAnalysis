from flask import Flask, render_template, request
from pycoingecko import CoinGeckoAPI
import pandas as pd
import os

app = Flask(__name__)

# Define variables for currency and time
vs_currency = 'usd'  # The currency to compare against
days = 365           # Number of days to fetch data for
hdf5_filename = 'crypto_data.h5'  # HDF5 file to store data

# Function to fetch and store crypto data
def fetch_and_store_crypto_data():
    # Read the list of cryptocurrencies from the file
    with open('cryptocurrencies.txt', 'r') as file:
        cryptocurrencies = [line.strip() for line in file if line.strip()]
    
    # Initialize the CoinGecko API client
    cg = CoinGeckoAPI()
    
    # Dictionary to store DataFrames for each cryptocurrency
    data_frames = {}
    
    for coin in cryptocurrencies:
        # Fetch market data for the specified number of days
        data = cg.get_coin_market_chart_by_id(id=coin, vs_currency=vs_currency, days=days)
        
        # Convert the price data into a DataFrame
        df = pd.DataFrame(data['prices'], columns=['timestamp', 'price'])
        
        # Convert timestamps to datetime objects
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        
        # Set the timestamp as the DataFrame index
        df.set_index('timestamp', inplace=True)
        
        # Resample the data to get the daily closing price
        df_daily = df.resample('D').agg({'price': 'last'})
        
        # Store the daily DataFrame in the dictionary
        data_frames[coin] = df_daily
    
    # Store all DataFrames in an HDF5 file
    with pd.HDFStore(hdf5_filename) as store:
        for coin, df in data_frames.items():
            store.put(coin, df)

# Fetch and store data when the server starts, if the HDF5 file doesn't exist
if not os.path.exists(hdf5_filename):
    fetch_and_store_crypto_data()

@app.route('/')
def index():
    # Read the list of cryptocurrencies from the HDF5 file
    with pd.HDFStore(hdf5_filename) as store:
        cryptocurrencies = list(store.keys())
        # Remove leading slashes from keys
        cryptocurrencies = [coin.strip('/') for coin in cryptocurrencies]
    
    # Pass the list of cryptocurrencies to the template
    return render_template('index.html', cryptocurrencies=cryptocurrencies)

@app.route('/crypto/<coin>')
def show_crypto_data(coin):
    # Read the data for the selected cryptocurrency
    with pd.HDFStore(hdf5_filename) as store:
        if f'/{coin}' in store.keys():
            df = store.get(coin)
        else:
            return f"Data for {coin} not found.", 404
    
    # Get the last 10 days of data
    last_10_days = df.tail(365)
    last_10_days.reset_index(inplace=True)
    last_10_days['timestamp'] = last_10_days['timestamp'].dt.strftime('%Y-%m-%d')
    
    # Convert the DataFrame to a list of dictionaries for rendering
    data = last_10_days.to_dict(orient='records')
    
    # Pass the data and vs_currency to the template
    return render_template('crypto.html', coin=coin.capitalize(), data=data, vs_currency=vs_currency)


if __name__ == '__main__':
    app.run(debug=True)
