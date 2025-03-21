import requests
import json
import os
from urllib.parse import urlparse, urlunparse

# Updated URL template
URL_TEMPLATE = "http://api-magicframe.automusic.win/collection/list/{username}/company,{username}/null/1/20/{page}/null"

def extract_urls_from_json(json_data, page_num):
    """
    Extract all URLs and collection names from the JSON data.
    Returns a list of tuples containing (collection_name, url) found in the 'poster' fields.
    """
    result = []
    
    try:
        data = json.loads(json_data)
        
        if isinstance(data, dict):
            for key in data:
                if isinstance(data[key], list):
                    data = data[key]
                    break
            else:
                return result
        
        if not isinstance(data, list):
            return result
        
        for entry in data:
            if not isinstance(entry, dict):
                continue
                
            collection_name = entry.get('name', 'Unnamed Collection')
            resources_str = entry.get('data', '')
            
            if not resources_str:
                continue
            
            try:
                resources = json.loads(resources_str)
                if not isinstance(resources, dict):
                    continue
            except json.JSONDecodeError:
                continue
            
            resource_list = resources.get('data', [])
            if not isinstance(resource_list, list):
                continue
                
            for resource in resource_list:
                if not isinstance(resource, dict):
                    continue
                poster_url = resource.get('poster', '')
                if poster_url:
                    result.append((collection_name, poster_url))
                    
        return result
    
    except json.JSONDecodeError:
        return []
    except Exception:
        return []

def estimate_total_pages(base_url):
    """
    Estimate total pages by checking responses until an empty page is found.
    """
    page = 1
    while True:
        current_url = base_url.format(page=page)
        try:
            response = requests.get(current_url)
            response.raise_for_status()
            data = json.loads(response.text)
            
            if not data or (isinstance(data, list) and len(data) == 0):
                return page - 1
            
            page += 1
        except requests.RequestException:
            return page - 1

def fetch_and_extract_all_urls(username):
    """
    Fetch and extract unique URLs with their collection names from all pages for a given username.
    """
    all_data = []
    
    base_url = URL_TEMPLATE.replace("{username}", username)
    total_pages = estimate_total_pages(base_url)
    if total_pages < 1:
        total_pages = 1
    
    print(f"Detected {total_pages} pages to crawl for user '{username}'.\n")
    
    for page in range(1, total_pages + 1):
        current_url = base_url.format(page=page)
        print(f"Fetching page {page}")
        
        try:
            response = requests.get(current_url)
            response.raise_for_status()
            
            page_data = extract_urls_from_json(response.text, page)
            all_data.extend(page_data)
            print(f"Found {len(page_data)} URLs on page {page}\n")
            
        except requests.RequestException as e:
            print(f"Error fetching page {page}: {e}")
    
    return all_data

def main():
    while True:
        username = input("Please enter the username: ")
        data = fetch_and_extract_all_urls(username)
        
        collections = {}
        for collection_name, url in data:
            if collection_name not in collections:
                collections[collection_name] = set()
            collections[collection_name].add(url)
        
        total_urls = sum(len(urls) for urls in collections.values())
        print(f"\nTotal unique URLs found across all pages for user '{username}': {total_urls}")
        for collection_name, urls in collections.items():
            print(f"\nCollection Name: {collection_name}")
            for i, url in enumerate(sorted(urls), 1):
                print(f"{i}. {url}")
        
        if data:
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
                    for collection_name, urls in collections.items():
                        f.write(f"Collection Name: {collection_name}\n")
                        for url in sorted(urls):
                            f.write(url + '\n')
                        f.write('\n')
                print(f"URLs saved to {filename}")
        
        rerun = input("\nWould you like to run the script again? (y/n): ").lower()
        if rerun != 'y':
            print("Exiting script.")
            break

if __name__ == "__main__":
    main()
