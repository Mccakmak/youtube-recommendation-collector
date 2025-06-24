import pandas as pd
import multiprocessing as mp
from tqdm import tqdm
from selenium import webdriver
from functools import partial
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException
import time


def get_top_n_recommendations(parent_video_ID, n):

    history = parent_video_ID

    if '#!#' in parent_video_ID:
        parent_video_ID = parent_video_ID.split('#!#')[-1]

    # Declare Web Driver
    driver = webdriver.Chrome()
    driver.implicitly_wait(10) # seconds

    # Get Youtube Video
    driver.get('https://www.youtube.com/watch?v=' + parent_video_ID)

    # Wait until Title has loaded to ensure page is ready
    timeout = 10
    try:
        myElem = WebDriverWait(driver, timeout).until(EC.presence_of_element_located((By.ID, 'title')))
        # print("Page is ready!")
    except TimeoutException:
        print("Loading took too much time!")
    
    # Loop to scroll to find required number of recommendations (max 5 prevent inf loop)
    for _ in range(5):
        # Wait more for good measure
        time.sleep(1)

        # Find all thumbnail elements from recommendations
        yt_recommendation_thumbnail_elements = driver.find_elements(By.ID, 'thumbnail')

        # Declare list to filter out live videos
        yt_recommendation_thumbnail_elements_filtered = []

        for element in yt_recommendation_thumbnail_elements:
            # Get parent element
            parent_element = element.find_element(By.XPATH, '..')

            # Check if parent element has 'is-live-video' attribute
            is_live_video = parent_element.get_attribute('is-live-video')

            # If it does, add it to the filtered list
            if is_live_video is None:
                yt_recommendation_thumbnail_elements_filtered.append(element)


        # Initialize a list to store the recommendation links values
        yt_recommendation_links = []

        # Iterate over the list of recommendations' thumbnail elements and add the href attribute of each element to the list
        for element in yt_recommendation_thumbnail_elements_filtered:
            try:
                href_value = element.get_attribute('href')
            except:
                href_value = "None"
                print("Link Missing")
            yt_recommendation_links.append(href_value)

        # Filter out None values from the collected links
        yt_recommendation_links = [link for link in yt_recommendation_links if link is not None]

        # Define the prefix that the valid links should start with
        valid_prefix = 'https://www.youtube.com/watch?v='

        # Filter the links that start with the valid prefix
        valid_links = [link for link in yt_recommendation_links if link.startswith(valid_prefix)]

        # Extract the video IDs from the valid links
        video_ids = [link[len(valid_prefix):] for link in valid_links]
        if len(video_ids) >= 5:
            break
        else:
            body = driver.find_element(By.TAG_NAME, "body")
            body.send_keys(Keys.PAGE_DOWN)

    driver.close()
    
    recommendations = video_ids[:n]
    print('parent_id',parent_video_ID)
    print('recommendation', recommendations)

    return [(parent_video_ID, history+'#!#'+rec_id) for rec_id in recommendations]

# Collect the recommendations in one depth for the given video IDs
def collect_recommendations(parent_video_IDs, num_processes, num_recommendations):
    with mp.Pool(processes=num_processes) as pool:
        results = pool.map(partial(get_top_n_recommendations, n=num_recommendations), parent_video_IDs)

    # Flatten the list of lists
    flat_results = [item for sublist in results for item in sublist]
    print(flat_results)
    
    # Create DataFrame
    df = pd.DataFrame(flat_results, columns=['root_video_id', 'recommended_video_id'])
    return df


def collect_recommendations_depth(root_video_ids, depth, num_processes, num_recommendations):
    # Define the dataframe for the recommendations
    columns = ['root_video_id', 'recommended_video_id', 'depth']
    recommendations_df = pd.DataFrame(columns=columns)

    for i in range(depth):
        print(f'Starting Depth {i+1}')
        result_df = collect_recommendations(root_video_ids, num_processes, num_recommendations)
        result_df['depth'] = i+1
        
        recommendations_df = pd.concat([recommendations_df, result_df], ignore_index=True)

        # The recommended videos of this batch will be the root videos of the next
        root_video_ids = result_df['recommended_video_id']
    
    return recommendations_df

def extract_column_from_csv(file_path, column_name):
    # Read the CSV file 
    df = pd.read_csv(file_path)
    
    # Extract the specified column
    column_values = df[column_name].tolist()
    
    return column_values


# Example usage
if __name__ == '__main__':
    depth = 4
    num_processes = 20
    num_recommendations = 4

    file = 'TrumpAssassination\Trump_Assassination_Relevent_Seeds.csv'
    root_video_ids = extract_column_from_csv(file, 'id')

    # Test with a sample size:
    root_video_ids = root_video_ids[:100]

    recommendations_df = collect_recommendations_depth(root_video_ids, depth, num_processes, num_recommendations)

    output_name = f'YT_reg_rec_Trump_Assassination_Relevant100_D{depth}_R{num_recommendations}.csv'
    recommendations_df.to_csv(output_name, index=False)
