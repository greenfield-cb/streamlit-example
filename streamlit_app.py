#!/usr/bin/env python3

from datetime import datetime
from decimal import Decimal
from pprint import pprint
import json
import requests
import streamlit as st
import pandas as pd
import numpy as np

url = "https://api.cow.fi/mainnet/api/v1/auction"
st.set_page_config(layout="wide")
now = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
st.markdown(f"<h3 style='text-align: center;'>Cow Swap Orderbook - {now}</h3>", unsafe_allow_html=True)
cols = st.columns([1]*15)
with cols[7]:
    st.button("Refresh", type="primary", use_container_width = True)
left_column, right_column = st.columns(2)

cols = {
    'uid': None,
    'sellToken': None,
    'buyToken': None,
    'sellAmount': None,
    'buyAmount': None,
    'protocolFees': None,
    'validTo': None,
    'kind': None,
    'receiver': None,
    'owner': None,
    'partiallyFillable': None,
    'executed': None,
    'preInteractions': None,
    'postInteractions': None,
    'sellTokenBalance': None,
    'buyTokenBalance': None,
    'class': None,
    'appData': None,
    'signingScheme': None,
    'signature': None,
    }

response = requests.get(url)
data = response.json()

df = pd.DataFrame.from_dict(data["orders"])
df['buyAmount'] = df['buyAmount'].astype(float)
df['sellAmount'] = df['sellAmount'].astype(float)

prices = pd.DataFrame({
    'token': data["prices"].keys(),
    'price': data["prices"].values(),
    })
prices['price'] = prices['price'].astype(float)

@st.cache_data
def load_tokens():
    tokens = pd.read_csv(filepath_or_buffer='cow_tokens.csv', usecols=['address', 'name', 'decimals'])
    tokens['decimals'] = tokens['decimals'].astype(float)
    tokens = tokens.rename(columns={ 'address': 'token' })
    tokens = tokens.sort_values(by=["name"], ascending=[True], ignore_index=True)
    return tokens


tokens = load_tokens()
prices = prices.merge(tokens, on='token', how='left', validate='1:1')

df = df.merge(prices, left_on='buyToken', right_on='token', how='left', validate='m:1')
df = df.rename(columns={
    'price': 'buyPrice',
    'name': 'buyName',
    'decimals': 'buyDecimals',
    })

df = df.merge(prices, left_on='sellToken', right_on='token', how='left', validate='m:1')
df = df.rename(columns={
    'price': 'sellPrice',
    'name': 'sellName',
    'decimals': 'sellDecimals',
    })


i = tokens['name'].eq('Safe Token').idxmax()
with left_column:
    option = st.selectbox(
        'Which coin to show?',
         tokens['name'],
         int(i)
         )

token_addr = tokens.loc[tokens['name'] == option, 'token'].tolist()[0]

df = df.dropna()
df = df[(df.sellToken == token_addr) | (df.buyToken == token_addr)]

usdc_addr = '0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48'
eth_price = prices.loc[prices['token'] == usdc_addr, 'price'].tolist()[0]

# table

df['sellPrice'] = df['sellPrice'] / eth_price * 10 ** (df['sellDecimals'] - 6)
df['buyPrice'] = df['buyPrice'] / eth_price * 10 ** (df['buyDecimals'] - 6)

df['sellAmount'] = df['sellAmount'] / 10 ** df['sellDecimals']
df['buyAmount'] = df['buyAmount'] / 10 ** df['buyDecimals']

df.loc[df['sellToken'] == token_addr, 'Price'] = ( df['buyAmount']  * df['buyPrice'] ) / df['sellAmount']
df.loc[df['buyToken'] == token_addr, 'Price'] = ( df['sellAmount']  * df['sellPrice'] ) / df['buyAmount']

df['Price'] = df['Price'].apply({lambda x: float(round(x,3))})
df = df.sort_values(by=["Price"], ascending=[True])

df.loc[df['buyToken'] == token_addr, "Volume"] = df["buyAmount"]
df.loc[df['sellToken'] == token_addr, "Volume"] = df["sellAmount"]

df["owner"] = 'https://etherscan.io/address/' + df['owner']


# chart

buy = df.loc[df['buyToken'] == token_addr][["buyAmount", "Price"]].copy()
sell = df.loc[df['sellToken'] == token_addr][["sellAmount", "Price"]].copy()

buy = buy.rename(columns={"buyAmount": "Buy Volume"})
sell = sell.rename(columns={"sellAmount": "Sell Volume"})

buy = buy.groupby(['Price']).sum()
sell = sell.groupby(['Price']).sum()

buy = buy.sort_values(by=["Price"], ascending=[False])
sell = sell.sort_values(by=["Price"], ascending=[True])

buy['Buy Volume'] = buy['Buy Volume'].cumsum()
sell['Sell Volume'] = sell['Sell Volume'].cumsum()

buy['Sell Volume'] = np.nan
sell['Buy Volume'] = np.nan

chart = pd.concat([buy, sell])
chart['Price'] = chart.index


# output

with left_column:
    st.dataframe(df[["sellName", "buyName", "Volume", "Price", "owner"]], column_config={
        "sellName": "Sell",
        "buyName": "Buy",
        "owner": st.column_config.LinkColumn(label="Seller", display_text="^https://etherscan.io/address/(.*)$"),
        }, use_container_width=True, hide_index=True, height=600)


with right_column:
    st.line_chart(data=chart, x="Price", y=["Buy Volume", "Sell Volume"], color=["#FF0000", "#0000FF"])
    st.bar_chart(data=chart, x="Price", y=["Buy Volume", "Sell Volume"], color=["#FF0000", "#0000FF"])
