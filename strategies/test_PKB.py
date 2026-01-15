from openalgo import api
client = api(api_key='4c8cf77f82b8f0c196f09bf09e250c44f6b155f60326ea8cab5120854b9d211a', host='http://127.0.0.1:5000')

response = client.placeorder(
    strategy="Python",
    symbol="NHPC",
    action="BUY",
    exchange="NSE",
    price_type="MARKET",
    product="MIS",
    quantity=1
)
print(response)

# response = client.depth(symbol="SBIN", exchange="BSE")
# print(response)
