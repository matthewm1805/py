import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
import time
import os
import re
import json
from urllib.parse import urlparse, parse_qs
from concurrent.futures import ThreadPoolExecutor

BASE_URL = 'https://artvee.com'

def requests_retry_session(retries=3, backoff_factor=0.3, status_forcelist=(500, 502, 504)):
    session = requests.Session()
    session.headers.update({'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'})
    retry = Retry(
        total=retries,
        read=retries,
        connect=retries,
        backoff_factor=backoff_factor,
        status_forcelist=status_forcelist,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session

def login(session):
    try:
        print("Đang đăng nhập Artvee")
        login_url = BASE_URL + '/login'
        response = session.get(login_url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'lxml')  # Sử dụng lxml để nhanh hơn
        nonce = soup.find('input', {'name': 'ihc_login_nonce'})['value']

        username = '55d6e3e113aec1cf8807fc4c70977787'
        password = '55d6e3e113aec1cf8807fc4c70977787'

        data = {
            'log': username,
            'pwd': password,
            'ihcaction': 'login',
            'ihc_login_nonce': nonce
        }
        response = session.post(login_url, data=data, timeout=10)
        response.raise_for_status()
        if username in response.text:
            print("Đăng nhập thành công!")
        else:
            print("Đăng nhập thất bại! Vui lòng kiểm tra thông tin đăng nhập.")
            return False
        return True
    except requests.RequestException as e:
        print(f"Lỗi đăng nhập: {str(e)}")
        return False

def sanitize_filename(filename):
    filename = filename.strip()
    sanitized = re.sub(r'[^a-zA-Z0-9 _-]', '', filename)
    sanitized = sanitized.replace('-', ' ').replace('_', ' ')
    return sanitized.title()

def get_all_artwork_info(session, page_url, page_type):
    cache_file = f"cache_{page_type}_{page_url.split('/')[-2]}.json"
    if os.path.exists(cache_file):
        print(f"Tải dữ liệu từ cache: {cache_file}")
        with open(cache_file, 'r') as f:
            return json.load(f)

    artwork_info = []
    page = 1

    # Xử lý URL cơ bản cho các loại trang khác nhau
    if page_type == 'search':
        parsed_url = urlparse(page_url)
        query_params = parse_qs(parsed_url.query)
        search_term = query_params.get('s', [''])[0]
        base_page_url = f"{BASE_URL}/main/?s={search_term}"
    elif page_type == 'category':
        category = page_url.split('/c/')[1].split('/')[0]
        base_page_url = f"{BASE_URL}/c/{category}/"
    elif page_type == 's_collection':
        collection_id = re.search(r'/s_collection/(\d+)', page_url).group(1)
        base_page_url = f"{BASE_URL}/s_collection/{collection_id}/"
    else:
        base_page_url = re.sub(r'/page/\d+/?$', '/', page_url.rstrip('/')) + '/'

    while True:
        if page_type == 'search':
            paginated_url = f"{BASE_URL}/main/page/{page}/?s={search_term}" if page > 1 else base_page_url
        elif page_type == 'category':
            paginated_url = f"{base_page_url}page/{page}/" if page > 1 else base_page_url
        elif page_type == 's_collection':
            paginated_url = f"{base_page_url}{page}/" if page > 1 else base_page_url
        else:
            paginated_url = f"{base_page_url}page/{page}/" if page > 1 else base_page_url

        print(f"Đang lấy thông tin tác phẩm từ {paginated_url}")
        try:
            response = session.get(paginated_url, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'lxml')

            # Tìm các phần tử chứa tác phẩm
            if page_type == 's_collection':
                product_items = soup.select('article.product-grid-item')
            else:
                product_items = soup.select('div.product-grid-item')

            if not product_items:
                print(f"Không tìm thấy thêm tác phẩm nào ở trang {page}. Dừng lại.")
                break

            if page_type == 's_collection':
                page_has_items = False
                for item in product_items:
                    link_tag = item.find('a', href=re.compile(r'^https://artvee.com/dl/'))
                    if link_tag:
                        page_has_items = True
                        artwork_url = link_tag['href']
                        data_id_tag = item.find('header', class_='entry-header')
                        if data_id_tag and 'data-id' in data_id_tag.attrs:
                            data_id = data_id_tag['data-id']
                            title_tag = item.find('h3', class_='product-title')
                            if title_tag:
                                title = title_tag.text.strip()
                                artwork_info.append({
                                    'url': artwork_url,
                                    'data_id': data_id,
                                    'title': title
                                })
                if not page_has_items:
                    print(f"Không tìm thấy tác phẩm hợp lệ ở trang {page}. Dừng lại.")
                    break
            else:
                for item in product_items:
                    link_tag = item.find('a', href=re.compile(r'^https://artvee.com/dl/'))
                    if link_tag:
                        artwork_url = link_tag['href']
                        data_id_tag = item.find('div', class_='product-image-link')
                        if data_id_tag and 'data-id' in data_id_tag.attrs:
                            data_id = data_id_tag['data-id']
                            title_tag = item.find('h3', class_='product-title')
                            if title_tag:
                                title = title_tag.text.strip()
                                artwork_info.append({
                                    'url': artwork_url,
                                    'data_id': data_id,
                                    'title': title
                                })

            next_page = soup.select_one('a.next.page-numbers') if page_type != 's_collection' else soup.select_one('a.nextpostslink')
            if not next_page:
                print("Không còn trang nào để lấy thêm.")
                break

            page += 1
        except requests.RequestException as e:
            print(f"Lỗi khi lấy trang {paginated_url}: {str(e)}")
            break

    # Lưu vào cache
    with open(cache_file, 'w') as f:
        json.dump(artwork_info, f)
    return artwork_info

def download_and_rename(session, download_link, artist_name, title, folder_name):
    try:
        response = session.get(download_link, stream=True, timeout=10)
        response.raise_for_status()

        filename = f"{artist_name} - {title}.jpg"
        filepath = os.path.join('Artvee Artworks', folder_name, filename)
        os.makedirs(os.path.join('Artvee Artworks', folder_name), exist_ok=True)

        if os.path.exists(filepath):
            print(f"Hình ảnh {filename} đã tồn tại trong {folder_name}. Bỏ qua tải xuống.")
            return

        print(f"Đang tải {filename} vào {folder_name}")
        with open(filepath, 'wb') as f:
            for chunk in response.iter_content(chunk_size=32768):  # Tăng chunk_size
                if chunk:
                    f.write(chunk)
        print(f"Đã lưu tại {filepath}")
    except requests.RequestException as e:
        print(f"Lỗi khi tải {download_link}: {str(e)}")

def get_folder_name(session, page_url, page_type):
    try:
        response = session.get(page_url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'lxml')

        if page_type == 'artist':
            name_elem = soup.select_one('h1.artist')
        elif page_type == 'collection' or page_type == 's_collection':
            name_elem = soup.select_one('h1.entry-title')
        elif page_type == 'books':
            name_elem = soup.select_one('h1.book-title')
        elif page_type == 'topics':
            name_elem = soup.select_one('h1.topic-title')
        elif page_type == 'culture':
            name_elem = soup.select_one('h1.culture-title')
        elif page_type == 'movement':
            name_elem = soup.select_one('h1.movement-title')
        elif page_type == 'search':
            parsed_url = urlparse(page_url)
            query_params = parse_qs(parsed_url.query)
            search_term = query_params.get('s', [''])[0]
            return sanitize_filename(f"Search {search_term}")
        elif page_type == 'category':
            category = page_url.split('/c/')[1].split('/')[0]
            return sanitize_filename(f"Category {category}")
        else:
            name_elem = None

        if name_elem:
            return sanitize_filename(name_elem.text.strip())
        return sanitize_filename(page_url.split('/')[-2])
    except requests.RequestException as e:
        print(f"Lỗi khi lấy tên thư mục từ {page_url}: {str(e)}")
        return sanitize_filename(page_url.split('/')[-2])

def process_page(session, page_url):
    try:
        # Xác định loại trang từ URL
        if '/artist/' in page_url:
            page_type = 'artist'
        elif '/collection/' in page_url:
            page_type = 'collection'
        elif '/books/' in page_url:
            page_type = 'books'
        elif '/topics/' in page_url:
            page_type = 'topics'
        elif '/culture/' in page_url:
            page_type = 'culture'
        elif '/movement/' in page_url:
            page_type = 'movement'
        elif '/s_collection/' in page_url:
            page_type = 's_collection'
        elif '/main/' in page_url and '?s=' in page_url:
            page_type = 'search'
        elif '/c/' in page_url:
            page_type = 'category'
        else:
            print(f"Không hỗ trợ loại trang cho {page_url}")
            return

        folder_name = get_folder_name(session, page_url, page_type)
        print(f"Đang xử lý {page_type}: {folder_name}")

        artwork_info_list = get_all_artwork_info(session, page_url, page_type)
        print(f"Tìm thấy {len(artwork_info_list)} tác phẩm để tải xuống.")

        def download_task(info):
            try:
                artist_name = sanitize_filename(folder_name if page_type == 'artist' else "Various Artists")
                title = sanitize_filename(info['title'])
                ajax_url = f"{BASE_URL}/erica"
                data = {'id': info['data_id'], 'action': 'woodmart_quick_view2'}
                ajax_response = session.get(ajax_url, params=data, timeout=10)
                ajax_response.raise_for_status()
                response_json = ajax_response.json()
                download_link = response_json.get('flink')

                if download_link:
                    download_and_rename(session, download_link, artist_name, title, folder_name)
                else:
                    print(f"Không lấy được đường dẫn tải xuống cho {info['url']}")
            except Exception as e:
                print(f"Lỗi khi xử lý {info['url']}: {str(e)}")

        # Sử dụng ThreadPoolExecutor để tải xuống song song
        with ThreadPoolExecutor(max_workers=5) as executor:
            executor.map(download_task, artwork_info_list)

    except Exception as e:
        print(f"Lỗi bất ngờ khi xử lý {page_url}: {str(e)}")

def main():
    with requests_retry_session() as session:
        if not login(session):
            print("Không thể đăng nhập. Thoát script.")
            return
        
        while True:
            page_url = input("Nhập URL của Artist/Collection/Books/Topic/Culture/Movement/S_Collection/Search/Category: \n")
            if page_url.lower() == 'exit':
                print("Thoát khỏi script.")
                break
            if not page_url:
                print("Bạn phải nhập URL hoặc 'exit'.")
                continue
            
            process_page(session, page_url)
            print(f"\nĐã xử lý xong {page_url}. Sẵn sàng cho URL tiếp theo...\n")
            time.sleep(2)

if __name__ == "__main__":
    main()