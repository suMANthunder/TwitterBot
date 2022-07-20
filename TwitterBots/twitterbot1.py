import requests
import os
import json
import config
import preprocessor as p
from langdetect import detect
from csv import writer

from ernie import SentenceClassifier
import numpy as np

from binance.client import Client
from binance.enums import *

classifier = SentenceClassifier(model_path='./output')

in_position = False
TRADE_SYMBOL = "BTCUSDT"
TRADE_QUANTITY = 0.005

sentimentLst = []
in_position = False

#Connect to binance
client = Client(config.API_KEY, config.API_SECRET)

def order(side, quantity, symbol, order_type=ORDER_TYPE_MARKET):
    try:
        print("Sending order")
        order = client.create_order(symbol=symbol, side=side, type=order_type, quantity=quantity)
        print(order)
    except Exception as e:
        print(e)
        return False
    return True

def create_headers(bearer_token):
    headers = {"Authorization": "Bearer {}".format(bearer_token)}
    return headers


def get_rules(headers, bearer_token):
    response = requests.get(
        "https://api.twitter.com/2/tweets/search/stream/rules", headers=headers
    )
    if response.status_code != 200:
        raise Exception(
            "Cannot get rules (HTTP {}): {}".format(response.status_code, response.text)
        )
    print(json.dumps(response.json()))
    return response.json()


def delete_all_rules(headers, bearer_token, rules):
    if rules is None or "data" not in rules:
        return None

    ids = list(map(lambda rule: rule["id"], rules["data"]))
    payload = {"delete": {"ids": ids}}
    response = requests.post(
        "https://api.twitter.com/2/tweets/search/stream/rules",
        headers=headers,
        json=payload
    )
    if response.status_code != 200:
        raise Exception(
            "Cannot delete rules (HTTP {}): {}".format(
                response.status_code, response.text
            )
        )
    print(json.dumps(response.json()))


def set_rules(headers, delete, bearer_token):
    # You can adjust the rules if needed
    sample_rules = [
        {"value": "#bitcoin", "tag": "bitcoin"},
        # {"value": "cat has:images -grumpy", "tag": "cat pictures"},
    ]
    payload = {"add": sample_rules}
    response = requests.post(
        "https://api.twitter.com/2/tweets/search/stream/rules",
        headers=headers,
        json=payload,
    )
    if response.status_code != 201:
        raise Exception(
            "Cannot add rules (HTTP {}): {}".format(response.status_code, response.text)
        )
    print(json.dumps(response.json()))


def get_stream(headers, set, bearer_token):
    response = requests.get(
        "https://api.twitter.com/2/tweets/search/stream", headers=headers, stream=True,
    )
    print(response.status_code)
    if response.status_code != 200:
        raise Exception(
            "Cannot get stream (HTTP {}): {}".format(
                response.status_code, response.text
            )
        )
    for response_line in response.iter_lines():
        if response_line:
            json_response = json.loads(response_line)
            # print(json.dumps(json_response, indent=4, sort_keys=True))
            tweet = json_response['data']['text']
            tweet = p.clean(tweet)
            tweet = tweet.replace(':','')
            # print(tweet)
            try:
                if detect(tweet) == 'en':
                    print(tweet)

                    try: 
                        #-1 BEARISH 0 NEUTRAL 1 BULLISH
                        classes = ["Bearish", "Neutral", "Bullish"]
                        probabilities = classifier.predict_one(tweet)
                        polarity = classes[np.argmax(probabilities)]
                        print(polarity)
                        sentimentLst.append(polarity)

                        if len(sentimentLst) > 20:
                            endList = sentimentLst[-20:]
                            print("******** TOTAL BULLISH: " + str(endList.count('Bullish')))
                            print("******** TOTAL BEARISH: " + str(endList.count('Bearish')))

                            if endList.count('Bullish') > 15:
                                #BUY
                                if in_position:
                                    print("******** BUY ******** but we own")
                                else: 
                                    print("******** BUY ********")
                                    order_succeeded = order(SIDE_BUY, TRADE_QUANTITY, TRADE_SYMBOL)
                                    if order_succeeded:
                                        in_position = True
                            elif endList.count('Bearish') > 15:
                                #SELL
                                if in_position:
                                    order_succeeded = order(SIDE_SELL, TRADE_QUANTITY, TRADE_SYMBOL)
                                    if order_succeded:
                                        in_position = False
                                else:
                                    print('******** SELL ******** but we dont own')
                    except:
                        pass
                    # tweetLst = [tweet]

                    # with open('bitcoindata.csv', 'a+', newline='') as write_obj:
                    #     csv_writer = writer(write_obj)
                    #     csv_writer.writerow(tweetLst)
            except:
                pass

def main():
    bearer_token = config.BEARER_TOKEN
    headers = create_headers(bearer_token)
    rules = get_rules(headers, bearer_token)
    delete = delete_all_rules(headers, bearer_token, rules)
    set = set_rules(headers, delete, bearer_token)
    get_stream(headers, set, bearer_token)


if __name__ == "__main__":
    main()