import pandas as pd

# Sample input data
input_data = [
    ["19.05.23 23:16:45", "26884.08755829904", "LONG"],
    ["19.05.23 23:45:35", "26890.02964334705", "SHORT"],
    ["19.05.23 23:46:01", "26892.779135802473", "LONG"],
    ["19.05.23 23:47:05", "26890.01975308642", "SHORT"],
    ["20.05.23 00:03:51", "26880.75451303155", "LONG"],
    ["20.05.23 00:15:40", "26892.3729218107", "SHORT"],
    ["20.05.23 00:30:01", "26880.550288065846", "SHORT"],
    ["20.05.23 00:30:58", "26884.259135802473", "LONG"],
    ["20.05.23 01:00:07", "26845.551755829903", "SHORT"],
    ["20.05.23 01:15:01", "26852.38989026063", "LONG"],
]

# Convert input data to pandas DataFrame
df = pd.DataFrame(input_data, columns=["datetime", "symbol", "direction"])

# Convert datetime column to pandas datetime format
df["datetime"] = pd.to_datetime(df["datetime"], format="%y.%m.%d %H:%M:%S")

# Sort DataFrame by datetime
df = df.sort_values("datetime")


def backtest_strategy(data):  # Define a function to backtest your strategy
    # Get the current symbol value
    current_symbol = float(data["symbol"])
    # Get the previous symbol value
    previous_data = df.loc[df["datetime"] < data["datetime"]]
    if previous_data.empty:
        previous_symbol = current_symbol
    else:
        previous_symbol = float(previous_data.iloc[-1]["symbol"])

    # Calculate profit or loss based on the direction
    if data["direction"] == "SHORT":
        result = current_symbol - previous_symbol
    elif data["direction"] == "LONG":
        result = previous_symbol - current_symbol
    else:
        result = 0  # No action if direction is not specified
    return result


# Apply the backtest_strategy function to each row in the DataFrame
df["result"] = df.apply(backtest_strategy, axis=1)
df["cumulative_result"] = 1000 + df["result"].cumsum()

# Print the backtest results
print(df)
