FROM python:3
LABEL authors="GGwM"
COPY . /macd
WORKDIR /macd
RUN pip install -r requirements.txt
CMD ["python3", "macd_psar.py"]