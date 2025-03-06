import requests
import json
import re
import os
from urllib.parse import urlparse, urlunparse

# URL template with {username} as a placeholder
URL_TEMPLATE = "http://api-magicframe.automusic.win/collection/list/{username}/company/null/1/20/{page}/null"

def extract_urls_from_json(json_data):
    """
    Extract all URLs from the JSON data.
    Returns a list of URLs found in the 'poster' fields.
    """
    url_list = []
    
    try:
        data = json.loads(json_data)
        
        # Iterate through each entry in the JSON array
        for entry in data:
            # Get the 'data' field which contains the JSON string with resources
            resources_str = entry.get('data', '')
            
            # Parse the nested JSON string in 'data'
            resources = json.loads(resources_str)
            
            # Extract URLs from the 'data' array within the nested JSON
            for resource in resources.get('data', []):
                poster_url = resource.get('poster', '')
                if poster_url:
                    url_list.append(poster_url)
                    
        return url_list
    
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON: {e}")
        return []
    except Exception as e:
        print(f"An error occurred: {e}")
        return []

def estimate_total_pages(base_url):
    """
    Estimate total pages by checking responses until an empty page is found.
    """
    page = 1
    while True:
        # Construct URL for the current page
        current_url = base_url.format(page=page)
        try:
            response = requests.get(current_url)
            response.raise_for_status()
            data = json.loads(response.text)
            
            if not data:  # Empty response means no more pages
                return page - 1
            
            page += 1
        except requests.RequestException:
            return page - 1  # Return last valid page if request fails

def fetch_and_extract_all_urls(username):
    """
    Fetch and extract unique URLs from all pages for a given username.
    """
    all_urls = set()  # Use a set to automatically remove duplicates
    
    # Construct base URL for page 1
    base_url = URL_TEMPLATE.replace("{username}", username)
    
    # Get total number of pages
    total_pages = estimate_total_pages(base_url)
    print(f"Detected {total_pages} pages to crawl for user '{username}'.\n")
    
    # Fetch each page and extract URLs
    for page in range(1, total_pages + 1):
        current_url = base_url.format(page=page)
        print(f"Fetching page {page}")
        
        try:
            response = requests.get(current_url)
            response.raise_for_status()
            
            # Extract URLs from this page and add to set
            page_urls = extract_urls_from_json(response.text)
            all_urls.update(page_urls)  # Add URLs to set (duplicates are ignored)
            print(f"Found {len(page_urls)} URLs on page {page}\n")
            
        except requests.RequestException as e:
            print(f"Error fetching page {page}: {e}")
        except Exception as e:
            print(f"An error occurred on page {page}: {e}\n")
    
    return list(all_urls)  # Convert set back to list for output

def main():
    while True:
        # Get username from user input
        username = input("Please enter the username: ")
        
        # Fetch and extract unique URLs from all pages for the given username
        urls = fetch_and_extract_all_urls(username)
        
        # Print all found URLs
        print(f"\nTotal unique URLs found across all pages for user '{username}': {len(urls)}")
        for i, url in enumerate(urls, 1):
            print(f"{i}. {url}")
        
        # Optionally save to file
        if urls:
            save_to_file = input("Would you like to save the URLs to a file? (y/n): ").lower()
            if save_to_file == 'y':
                while True:
                    base_name = input("Enter the name for the TXT file: ").strip()
                    if base_name:
                        break
                    print("Please enter a valid name.")
                filename = base_name + ".txt"
                directory = os.path.dirname(filename)
                if directory and not os.path.exists(directory):
                    os.makedirs(directory)
                with open(filename, 'w', encoding='utf-8') as f:
                    for url in urls:
                        f.write(url + '\n')
                print(f"URLs saved to {filename}")
        
        # Ask if the user wants to rerun
        rerun = input("\nWould you like to run the script again? (y/n): ").lower()
        if rerun != 'y':
            print("Exiting script.")
            break

if __name__ == "__main__":
    main()