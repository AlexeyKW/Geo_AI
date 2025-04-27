import httpx
import os
from prefect import flow, task

@task
def check_file(file_path: str):
    file_info = os.path.isfile(file_path)
    return file_info


@task
def write_file(file_info: str):
    if file_info == True:
        f = open("E:\demofile2.txt", "a")
        f.write("Now the file has more content!")
        f.close()
        result = 'True'
    else: 
        result = 'False'
    return result


@flow(name="File Info", log_prints=True)
def file_info(file_path: str = "E:\install.exe"):
    file_info = check_file(file_path)
    print(f"Test1")

    result_write = write_file(file_info, wait_for=[file_info])
    print(f"Test2 "+result_write)


if __name__ == "__main__":
    # create your first deployment
    file_info.serve(name="my-first-deployment")