from datetime import datetime

from airflow.sdk import DAG, task

from main import (
    get_market_data,
    transform_market_data,
    validate_market_data,
    get_latest_datetime,
    filter_new_candles,
    load_market_data,
)

with DAG(
    dag_id="forex_data_pipeline",
    start_date=datetime(2026, 1, 1),
    schedule=None,
    catchup=False,
) as dag:

    @task
    def extract():
        data = get_market_data("EUR/USD", "1h")

        print(f"Received {len(data['values'])} candles from Twelve Data")

        return data

    @task
    def transform(data):
        candles = transform_market_data(
            data,
            "EUR/USD",
            "1h"
        )

        print(f"Transformed {len(candles)} candles")

        return candles

    @task
    def validate(candles):
        valid_candles, invalid_candles = validate_market_data(candles)

        print(f"Valid candles: {len(valid_candles)}")
        print(f"Invalid candles: {len(invalid_candles)}")

        for candle, error in invalid_candles:
            print(error["reason"], candle)

        return valid_candles

    
    @task
    def filter(candles):

        latest_datetime = get_latest_datetime(
            "EUR/USD",
            "1h"
        )

        new_candles = filter_new_candles(
            candles,
            latest_datetime
        )

        print(f"Filtered {len(new_candles)} new candles")

        return new_candles


    @task
    def load(candles):
        result = load_market_data(candles)

        print(f"Load result: {result}")

        return result
    raw_data = extract()
    candles = transform(raw_data)
    valid_candles = validate(candles)
    new_candles = filter(valid_candles)
    load(new_candles)