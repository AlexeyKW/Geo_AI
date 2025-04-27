import httpx
import os
from prefect import flow, task
import requests
import json
import datetime
import pandas as pd
import numpy as np
import json

@task
def check_file(file_path: str):
    file_info = os.path.isfile(file_path)
    return file_info
    
@task
def read_file(file_path: str):
    f = open(file_path)
    parameters = json.load(f)
    f.close()
    return parameters

@task
def request_data(parameters: dict):
    url = "https://modis.ornl.gov/rst/api/v1/"
    header = {'Accept': 'application/json'}
    lstresponse = requests.get("".join([
        url, parameters['product'], "/subset?",
        "latitude=", str(parameters['lat']),
        "&longitude=", str(parameters['lon']),
        "&band=", parameters['data_band'],
        "&startDate=", parameters['begin_date'],
        "&endDate=", parameters['end_date'],
        "&kmAboveBelow=", str(parameters['above_below']),
        "&kmLeftRight=", str(parameters['left_right'])
    ]), headers=header)
    print(json.loads(lstresponse.text)['subset'][0]['data'])
    return json.loads(lstresponse.text)['subset'][0]['data']

@flow(name="File Info", log_prints=True)
def MODIS_data(file_path: str = "E:\\modis.json"):
    file_info = check_file(file_path)
    print(f"Test1")
    parameters = read_file(file_path)
    print(f"Test2 ")
    modis_data = request_data(parameters)
    print(f"Test3 ")


if __name__ == "__main__":
    MODIS_data.serve(name="MODIS-deployment")