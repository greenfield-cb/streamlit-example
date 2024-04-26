#!/usr/bin/env python3

from decimal import Decimal
from pprint import pprint
import json
import requests
import streamlit as st
import pandas as pd
import numpy as np

url = "https://api.cow.fi/mainnet/api/v1/auction"
st.set_page_config(layout="wide")
st.markdown("<h1 style='text-align: center;'>Cow Swap Orderbook</h1>", unsafe_allow_html=True)
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

weth_addr = '0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2'
usdc_addr = '0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48'
usdt_addr = '0xdac17f958d2ee523a2206206994597c13d831ec7'
safe_addr = '0x5afe3855358e112b5647b952709e6165e1c1eeee'

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
    pprint("LOADING")
    tokens = pd.read_csv(filepath_or_buffer='cow_tokens.csv', usecols=['address', 'name', 'decimals'])
    tokens['decimals'] = tokens['decimals'].astype(float)
    tokens = tokens.rename(columns={ 'address': 'token' })
    tokens = tokens.sort_values(by=["name"], ascending=[True])
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


pprint(tokens)
i = tokens['name'].eq('Safe Token').idxmax()
pprint(f"safe token: {i}")
with left_column:
    option = st.selectbox(
        'Which coin to show?',
         tokens['name'],
         int(i)
         )

pprint(f"selected: {option}")
token_addr = tokens.loc[tokens['name'] == option, 'token'].tolist()[0]
pprint(f"token_addr = {token_addr}")

df = df.dropna()
df = df[(df.sellToken == token_addr) | (df.buyToken == token_addr)]

eth_price = prices.loc[prices['token'] == usdc_addr, 'price'].tolist()[0]


df['sellPrice'] = df['sellPrice'] / eth_price * 10 ** (df['sellDecimals'] - 6)
df['buyPrice'] = df['buyPrice'] / eth_price * 10 ** (df['buyDecimals'] - 6)

df['sellAmount'] = df['sellAmount'] / 10 ** df['sellDecimals']
df['buyAmount'] = df['buyAmount'] / 10 ** df['buyDecimals']

df.loc[df['sellToken'] == token_addr, 'Price'] = ( df['buyAmount']  * df['buyPrice'] ) / df['sellAmount']
df.loc[df['buyToken'] == token_addr, 'Price'] = ( df['sellAmount']  * df['sellPrice'] ) / df['buyAmount']

df['Price'] = df['Price'].apply({lambda x: float(round(x,3))})

df = df.sort_values(by=["Price"], ascending=[False])
df['Buy Volume'] = np.nan
df['Buy Volume'] = df['Buy Volume'].astype(float)
df.loc[df['buyToken'] == token_addr, "Buy Volume"] = df["buyAmount"]
df["Volume"] = df["Buy Volume"].fillna(0)
df.loc[df['buyToken'] == token_addr, "Buy Volume"] = df["Buy Volume"].cumsum()

df = df.sort_values(by=["Price"], ascending=[True])
df['Sell Volume'] = np.nan
df['Sell Volume'] = df['Sell Volume'].astype(float)
df.loc[df['sellToken'] == token_addr, "Sell Volume"] = df["sellAmount"]

df["Volume"] = df["Volume"] + df["Sell Volume"].fillna(0)

df.loc[df['sellToken'] == token_addr, "Sell Volume"] = df["Sell Volume"].cumsum()

df = df.sort_values(by=["Price"], ascending=[True])

#pprint(df.dtypes)

df["owner"] = 'https://etherscan.io/address/' + df['owner']


with left_column:
    st.dataframe(df[["sellName", "buyName", "Volume", "Price", "owner"]], column_config={
        "sellName": "Sell",
        "buyName": "Buy",
        "owner": st.column_config.LinkColumn(display_text="^https://etherscan.io/address/(.*)$"),
        }, use_container_width=True, hide_index=True, height=600)

with right_column:
    st.line_chart(data=df, x="Price", y=["Buy Volume", "Sell Volume"], color=["#FF0000", "#0000FF"])
    st.bar_chart(data=df, x="Price", y=["Buy Volume", "Sell Volume"], color=["#FF0000", "#0000FF"])
