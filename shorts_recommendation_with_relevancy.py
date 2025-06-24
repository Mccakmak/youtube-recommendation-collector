import random
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
import pandas as pd
from itertools import chain, repeat
import time
import multiprocessing as mp
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from openai import OpenAI
from pydantic import BaseModel,Field

import json
def main():
    # Define scroll depth and wait time and test group size
    scroll_depth = 50
    wait_time = 3 # Initial wait time if relevancy watch time on
    test_size = 1000
    number_of_processes = 8
    # Get root video URLs
    file_name = "seed/china_short_seeds.csv"
    column_name = "url"
    root_video_URLs = get_URLs(file_name, column_name)
    # root_video_URLs = []
    # for id in root_video_IDs:
    #     url = "https://www.youtube.com/shorts/" + id
    #     root_video_URLs.append(url)
    # Test a small group with certain size
    root_video_URLs = random.sample(root_video_URLs, test_size)
    # Seperate root URLs into groupes according to number of desired paralell processes
    grouped_root_URLs = split_list(root_video_URLs, number_of_processes)
    processes = []
    manager = mp.Manager()
    grouped_urls_and_depth = []
    # Start a process for each group of root URLs
    for group_of_root_URLs in grouped_root_URLs:
        group_of_recommended_URLs = manager.list()
        grouped_urls_and_depth.append(group_of_recommended_URLs)
        process = mp.Process(target=YTShorts_scrape_process, args=[group_of_root_URLs, group_of_recommended_URLs, scroll_depth, wait_time])
        process.start()
        processes.append(process)
    # Join the processes together
    for process in processes:
        process.join()
    # Combine the groupes of urls and depth into one list
    urls_and_depth = []
    for group_of_recommended_URLs in grouped_urls_and_depth:
        urls_and_depth.extend(group_of_recommended_URLs)
    ### THIS SECTION FOR WRITING TO .txt RATHER THAN .csv
    # with open(f'urls_and_depth_D{scroll_depth}_T{wait_time}.txt', "w") as file:  # Open the file in write mode
    #     file.writelines(string + "\n" for string in urls_and_depth)  # Write each string with a newline
    ############ Convert Combined Strings into seperated lists
    root_IDs = []
    root_URLs =[]
    recommended_IDs = []
    recommended_URLs = []
    depths = []
    relevancy = []
    for string in urls_and_depth:
        data = string.split(' ')
        root_IDs.append(get_ID_from_URL(data[0]))
        root_URLs.append(data[0])
        recommended_IDs.append(get_ID_from_URL(data[1]))
        recommended_URLs.append(data[1])
        depths.append(data[2])
        relevancy.append(data[3])
    ###########
    # Create dictionary from the seperated lists
    data = {"root_video_id": root_IDs, "root_video_url": root_URLs, "recommended_video_id": recommended_IDs, "recommended_video_url": recommended_URLs, "depth": depths, "relevancy":relevancy}
    # Create DataFrame from the dictionary and write to CSV
    df = pd.DataFrame(data)
    df.to_csv(f'china_short_seeds_rec_3s.csv', index=False)
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
def get_YTShorts_recomendations(initial_URL, scroll_depth, wait_time):
    # Declare recomendations list
    urls_and_depth = []
    current_depth = 1
    ## GREATER CHINA
    system_prompt = (
        "You are an expert assistant specializing in assessing how relevant a YouTube video title is "
        "to topics surrounding China’s rise—its political ambitions, economic expansion, and military modernization."
    )
    user_prompt = (
        "For a given YouTube video title, assign a relevance score:\n"
        "- 2: Highly relevant (directly covers China’s political, economic, or military rise—e.g., Belt & Road projects, Xi Jinping’s diplomacy, PLA Navy expansion, rare earths control)\n"
        "- 1: Somewhat relevant (mentions China or Chinese context without focusing on its rise—e.g., culture, tourism, domestic news, lifestyle)\n"
        "- 0: Irrelevant (no connection to China—e.g., fruit cutting tutorials, dance covers, general DIY or entertainment unrelated to China)\n\n"
        "Examples:\n"
        "- Title: 'China Launches New Aircraft Carrier to Bolster Naval Power' → {'Score': 2}\n"
        "- Title: 'Xi Jinping Meets African Leaders to Discuss Trade Deals' → {'Score': 2}\n"
        "- Title: 'China’s GDP Grows by 6 percent in Q2 2025 Amid Global Slowdown' → {'Score': 2}\n"
        "- Title: 'Top 10 Street Foods to Try in Shanghai' → {'Score': 1}\n"
        "- Title: 'Beijing Air Pollution Reaches Hazardous Levels' → {'Score': 1}\n"
        "- Title: 'A Day in the Life of a Chinese University Student' → {'Score': 1}\n"
        "- Title: 'Perfect Mango Slicing Tutorial' → {'Score': 0}\n"
        "- Title: 'Contemporary Dance Routine Cover' → {'Score': 0}\n\n"
        "Return the result strictly as JSON: {'Score': int}."
    )
    # Initialize Chrome Driver
    driver = webdriver.Chrome()
    # Open URL
    driver.get(initial_URL)
    # Wait for page to load
    time.sleep(1)
    # Click Play Button to start watching
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
    # Wait on initial root video
    # wait_time = random.randint(3, 30)
    time.sleep(wait_time)
    # Define initial URLs
    past_URL = initial_URL
    current_URL = initial_URL
    # Start Loop for Scrolling and Collecting
    for i in range(scroll_depth * 2):
        # Loop double recuired depth to make sure entire length is scrolled (see End of Loop)
        # Scroll to next video
        page = driver.find_element(By.TAG_NAME, 'html')
        page.send_keys(Keys.DOWN)
        # Wait for new URL
        current_URL = driver.current_url
        for i in range(20): # try for 20 loops
            time.sleep(0.05) # each loop is 0.1 second
            current_URL = driver.current_url
            # if new URL found, add it to list
            if (past_URL != current_URL):
                time.sleep(0.5)
                # Get Title to check for relevancy
                for _ in range(10):
                    title = ""
                    try:
                        title_element = driver.find_element(By.CLASS_NAME, 'ytShortsVideoTitleViewModelShortsVideoTitle')
                        title = title_element.find_element(By.TAG_NAME, "span").text
                    except:
                        time.sleep(0.1)
                    if len(title) > 0:
                        break
                # Check relevancy and extract score
                relevancy = gpt_4(title, system_prompt, user_prompt)
                if type(relevancy) == dict:
                    relevancy_score = relevancy["Score"]
                else:
                    relevancy_score = 0
                print(str(relevancy_score) + " -- " + title)
                # # Determine watch time depending on relevancy
                # if relevancy_score == 2:
                #     wait_time = 60
                # elif relevancy_score == 1:
                #     wait_time = 15
                # else:
                #     wait_time = 3
                # Check if video is ad
                try:
                    ad_badge_element = driver.find_element(By.TAG_NAME, "ad-badge-view-model")
                    print("FOUND AD")
                    break
                except:
                    # IF NOT AD: Scrape recommended video and watch
                    past_URL = current_URL
                    urls_and_depth.append(initial_URL + ' ' + current_URL + ' ' + str(current_depth) + ' ' + str(relevancy_score))
                    current_depth += 1
                    time.sleep(wait_time)
                    break
        # End of Loop: Break when required scroll depth is reached
        if len(urls_and_depth) == scroll_depth: break
    # Close Chrome driver
    driver.close()
    # Prevents recommendations from convoluding
    return urls_and_depth
def YTShorts_scrape_process(group_of_root_URLs, group_of_urls_and_depth, scroll_depth, wait_time):
    for url in group_of_root_URLs:
        group_of_urls_and_depth.extend(get_YTShorts_recomendations(url, scroll_depth, wait_time))
def get_IDs_from_URLs(video_URLs):
    video_IDs = [url[31:] for url in video_URLs]
    return video_IDs
def get_ID_from_URL(video_URL):
    video_ID = video_URL[31:]
    return video_ID
def expand_list(lst, factor):
    expanded_lst =  list(chain.from_iterable(repeat(i, factor) for i in lst))
    return expanded_lst
class OutputFormat(BaseModel):
    Score: int = Field(ge=0, le=2)
client = OpenAI(api_key='')
def gpt_4(text,system,user):
    try:
        response = client.chat.completions.create(
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user+text}
            ],
            model="gpt-4.1-mini-2025-04-14",  # Specified model
            max_tokens=20,
            temperature=1,  # Deterministic output for consistent results
            response_format={
                    'type': 'json_schema',
                    'json_schema':
                    {
                        'name':'Score',
                        'schema': OutputFormat.model_json_schema()
                    }
                }
        )
        result= response.choices[0].message.content
        try:
            json_format=json.loads(result)
            validated_output = OutputFormat(**json_format)
            return json_format
        except Exception as e:
            print(e)
            return None
    except Exception as e:
        print(e)
        return 'gpt error'
if __name__ == "__main__":
    main()