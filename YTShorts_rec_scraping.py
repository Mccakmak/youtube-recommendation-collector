from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
import pandas as pd
from itertools import chain, repeat
import time
import multiprocessing as mp
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


def main():
    # Define scroll depth and wait time and test group size
    scroll_depth = 50
    wait_time = 3
    # test_size = 100
    number_of_processes = 10

    # Get root video URLs
    folder = "seed"
    doc_name = "scs_2025_unique"
    file_name = folder + "/" + doc_name + ".csv"
    column_name = "url"
    root_video_URLs = get_URLs(file_name, column_name)

    # # Test a small group with certain size
    # root_video_URLs = root_video_URLs[:test_size]

    # Seperate root URLs into groupes according to number of desired paralell processes
    grouped_root_URLs = split_list(root_video_URLs, number_of_processes)

    processes = []
    manager = mp.Manager()
    grouped_urls_and_depth = []

    # Start a process for each group of root URLs
    for group_of_root_URLs in grouped_root_URLs:
        group_of_recommended_URLs = manager.list()
        grouped_urls_and_depth.append(group_of_recommended_URLs)
        process = mp.Process(target=YTShorts_scrape_process,
                             args=[group_of_root_URLs, group_of_recommended_URLs, scroll_depth, wait_time])
        process.start()
        processes.append(process)

    # Join the processes together
    for process in processes:
        process.join()

    # Combine the groupes of urls and depth into one list
    urls_and_depth = []
    for group_of_recommended_URLs in grouped_urls_and_depth:
        urls_and_depth.extend(group_of_recommended_URLs)

    with open(f'urls_and_depth_D{scroll_depth}_T{wait_time}.txt', "w") as file:  # Open the file in write mode
        file.writelines(string + "\n" for string in urls_and_depth)  # Write each string with a newline

    ############ THIS SECTION IS FOR OUTPUTTING URLS
    root_URLs = []
    recommended_URLs = []
    depths = []
    for string in urls_and_depth:
        data = string.split(' ')
        root_URLs.append(data[0])
        recommended_URLs.append(data[1])
        depths.append(data[2])
    ###########

    # ###########  THIS SECTION IS FOR OUTPUTTING VIDEO IDs
    # root_IDs = []
    # recommended_IDs = []
    # depths = []
    # for string in urls_and_depth:
    #     data = string.split(' ')
    #     root_IDs.append(get_ID_from_URL(data[0]))
    #     recommended_IDs.append(get_ID_from_URL(data[1]))
    #     depths.append(data[2])
    # ###########

    # Create dictionary from video id lists
    data = {"root_video_url": root_URLs, "recommended_video_url": recommended_URLs, "depth": depths}

    # Create DataFrame from the dictionary and write to CSV
    df = pd.DataFrame(data)
    df.to_csv(f'{file_name}_recommendations_D{scroll_depth}_T{wait_time}.csv', index=False)


def get_URLs(file_name, column_name):
    # Read the CSV file given
    df = pd.read_csv(file_name)

    # return the specifies column
    return list(df[column_name])


def split_list(data, n):
    # Get the length of the list and calculate the base size for sublists
    length = len(data)
    base_size = length // n

    # Initialize an empty list to store the sublists
    sublists = []

    # Create n sublists with the base size
    for _ in range(n):
        sublist = data[:base_size]
        data = data[base_size:]
        sublists.append(sublist)

    # If there are remaining elements, distribute them evenly to the last sublists
    remaining = len(data)
    for i in range(remaining):
        sublists[i % n].append(data[i])

    return sublists


def get_YTShorts_recommendations(initial_URL, scroll_depth, wait_time):


    urls_and_depth = []
    current_depth = 1

    driver = webdriver.Edge()
    driver.get(initial_URL)

    try:
        # Wait for the large play button to be visible and clickable
        wait = WebDriverWait(driver, 3)
        play_button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button.ytp-large-play-button")))
        play_button.click()
        #print("Clicked large play button (ytp-large-play-button)")
    except Exception as e:
        #print(f"Play button click failed: {e}")
        # Fallback to clicking video element
        try:
            video_element = driver.find_element(By.TAG_NAME, "video")
            ActionChains(driver).move_to_element(video_element).click().perform()
            #print("Fallback: Clicked video element")
        except:
            pass
            #print("Could not trigger playback")

    time.sleep(wait_time)

    past_URL = initial_URL
    current_URL = initial_URL

    for i in range(scroll_depth * 2):
        page = driver.find_element(By.TAG_NAME, 'html')
        page.send_keys(Keys.DOWN)

        current_URL = driver.current_url
        for i in range(20):
            time.sleep(0.05)
            current_URL = driver.current_url
            if past_URL != current_URL:
                past_URL = current_URL
                urls_and_depth.append(initial_URL + ' ' + current_URL + ' ' + str(current_depth))
                current_depth += 1
                time.sleep(wait_time)
                break

        if len(urls_and_depth) == scroll_depth:
            break

    driver.close()
    return urls_and_depth




## TODO: Remove this, it wont be necessary
def get_many_YTShorts_recommendations(video_URLs, scroll_depth, wait_time):
    # Scrape recommended URLs
    recommended_URLs = []
    recommended_depth = []
    for url in video_URLs:
        recommended_URLs.extend(get_YTShorts_recommendations(url, scroll_depth, wait_time))
    return recommended_URLs


def YTShorts_scrape_process(group_of_root_URLs, group_of_urls_and_depth, scroll_depth, wait_time):
    for url in group_of_root_URLs:
        group_of_urls_and_depth.extend(get_YTShorts_recommendations(url, scroll_depth, wait_time))


def get_IDs_from_URLs(video_URLs):
    video_IDs = [url[31:] for url in video_URLs]
    return video_IDs


def get_ID_from_URL(video_URL):
    video_ID = video_URL[31:]
    return video_ID


def expand_list(lst, factor):
    expanded_lst = list(chain.from_iterable(repeat(i, factor) for i in lst))
    return expanded_lst


if __name__ == "__main__":
    start_time = time.time()
    main()
    end_time = time.time()

    execution_time_seconds = end_time - start_time
    execution_time_hours = execution_time_seconds / 3600

    print(f"Execution time: {execution_time_hours} hours")
