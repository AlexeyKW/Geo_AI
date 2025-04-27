import httpx
import os
from prefect import flow, task
import requests
import json
import datetime
import pandas as pd
import numpy as np
import json
import rasterio
from ultralytics import YOLO
from typing import Dict
from PIL import Image
import matplotlib.pyplot as plt
import ee

def normalize(band):
    band_min, band_max = (band.min(), band.max())
    return ((band - band_min) / ((band_max - band_min)))


def brighten(band):
    alpha = 0.13
    beta = 0
    return np.clip(alpha * band + beta, 0, 255)


def crop_center(pil_img, crop_width, crop_height):
    img_width, img_height = pil_img.size
    return pil_img.crop(((img_width - crop_width) // 2,
                         (img_height - crop_height) // 2,
                         (img_width + crop_width) // 2,
                         (img_height + crop_height) // 2))

@task
def check_file(file_path: str):
    file_info = os.path.isfile(file_path)
    return file_info
    
@task
def read_file(file_path: str):
    f = open(file_path)
    coords = json.load(f)
    f.close()
    return coords

@task
def request_data(coords: dict):
    service_account = 'service-account@speech-piter.iam.gserviceaccount.com'
    credentials = ee.ServiceAccountCredentials(service_account, 'E:\\AutoGIS\\prefect\\speech-piter-c3477142281b.json')
    ee.Initialize(credentials)
    raw_file_path = ''
    points = [[coords['lon'], coords['lat']]]
    dates = [['2021-04-16', '2021-04-30'], ['2021-05-01', '2021-05-15']]
    for pnt in points:
        lon = pnt[0]
        lat = pnt[1]
        geometry = ee.Geometry.BBox(lon - 0.05, lat - 0.03, lon + 0.05, lat + 0.03)
        for date in dates:
            dataset = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED').filterDate(date[0], date[1]).filter(
                ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 20)).filterBounds(geometry).select(['B4', 'B3', 'B2'])
            images_dict = dataset.toList(1).getInfo()[0]
            print(images_dict['id'])
            img = ee.Image(images_dict['id'])
            region = ee.Geometry.BBox(lon - 0.08, lat - 0.07, lon + 0.08, lat + 0.07)
            url = img.getDownloadUrl({'bands': ['B4', 'B3', 'B2'], 'region': region, 'scale': 15, 'format': 'GEO_TIFF'})
            response = requests.get(url)
            with open(images_dict['id'][-6:] + '.tif', 'wb') as fd:
                fd.write(response.content)
                raw_file_path = images_dict['id'][-6:] + '.tif'
    return raw_file_path

@task
def RAW_processing(raw_file_path: str):
    raw = rasterio.open(raw_file_path)
    red = raw.read(1)
    green = raw.read(2)
    blue = raw.read(3)
    red_b = brighten(red)
    blue_b = brighten(blue)
    green_b = brighten(green)
    red_bn = normalize(red_b)
    green_bn = normalize(green_b)
    blue_bn = normalize(blue_b)
    rgb_composite_bn = np.dstack((red_bn, green_bn, blue_bn))
    rgb_plot = plt.imshow(rgb_composite_bn)
    plt.axis('off')
    plt.savefig(os.path.splitext(os.path.basename(raw_file_path))[0] + '.png', bbox_inches='tight', pad_inches=0)
    plt.close('all')
    im = Image.open(os.path.splitext(os.path.basename(raw_file_path))[0] + '.png')
    im_new = crop_center(im, 288, 288)
    im_new.save(os.path.splitext(os.path.basename(raw_file_path))[0] + '_crop.png')
    #PNG_image = ''
    PNG_image = os.path.splitext(os.path.basename(raw_file_path))[0] + '_crop.png'
    return PNG_image

@task
def segmentation(PNG_image: str):
    onnx_model = YOLO('best288_dynamic.onnx', task='segment')
    test = onnx_model(PNG_image)
    #result_image = ''
    for r in test:
        im_array = r.plot()
        im = Image.fromarray(im_array[..., ::-1])
        im.save(os.path.splitext(os.path.basename(PNG_image))[0] + '_result.png')
    result_image = os.path.splitext(os.path.basename(PNG_image))[0] + '_result.png'
    return result_image

@flow(name="File Info", log_prints=True)
def S2_data(file_path: str = "E:\\coords.json"):
    file_info = check_file(file_path)
    print(f"File exists")
    coords = read_file(file_path)
    print(f"Coordinates received")
    raw_file_path = request_data(coords)
    print(f"RAW image recieved")
    PNG_image = RAW_processing(raw_file_path)
    print(f"PNF file generated")
    seg_result = segmentation(PNG_image)
    print(f"Segmentation complete")


if __name__ == "__main__":
    S2_data.serve(name="S2-deployment")