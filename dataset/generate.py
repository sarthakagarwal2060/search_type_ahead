import urllib.request
import gzip
import csv
import os
import time
from collections import Counter

AOL_URLS = ["https://archive.org/download/aolsearchdata2006/user-ct-test-collection-01.txt"] + \
           [f"https://archive.org/download/aolsearchdata2006/user-ct-test-collection-{str(i).zfill(2)}.txt.gz" for i in range(2, 4)]
OUTPUT_FILE = "dataset/queries.csv"
MAX_QUERIES = None  # None means load the entire dataset

def download_with_retry(url, max_retries=3):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    }
    
    for attempt in range(max_retries):
        try:
            print(f"  Attempt {attempt + 1}/{max_retries} to download chunk...")
            req = urllib.request.Request(url, headers=headers)
            response = urllib.request.urlopen(req, timeout=30)
            return response
        except Exception as e:
            print(f"  Download attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                time.sleep(5 * (attempt + 1))  # Exponential backoff
            else:
                raise e

def generate_dataset():
    total_chunks = len(AOL_URLS)
    print(f"Downloading Real General Search Dataset (AOL Logs 2006) - {total_chunks} Chunks...")
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    
    query_counts = Counter()
    
    for i, url in enumerate(AOL_URLS, 1):
        try:
            print(f"\nProcessing chunk {i}/{total_chunks}: {url}")
            response = download_with_retry(url)
            print(f"  Counting chunk {i}...")
            
            # Handle uncompressed chunk 1 vs compressed chunks 2-10
            if url.endswith('.gz'):
                file_iterator = gzip.GzipFile(fileobj=response)
            else:
                file_iterator = response
                
            # Skip the header row
            next(file_iterator, None)
            for line in file_iterator:
                try:
                    # Tab separated: AnonID, Query, QueryTime, ItemRank, ClickURL
                    parts = line.decode('utf-8', errors='ignore').split('\t')
                    if len(parts) >= 2:
                        query = parts[1].strip().lower()
                        # Filter out empty or dash queries, and strictly remove null bytes
                        query = query.replace('\x00', '').strip()
                        if len(query) > 1 and query != '-':
                            query_counts[query] += 1
                except Exception:
                    continue
        except Exception as e:
            print(f"Failed to process chunk {i} after retries: {e}")
            continue

    if MAX_QUERIES:
        print(f"Found {len(query_counts)} unique queries. Formatting Top {MAX_QUERIES} for PostgreSQL...")
        top_queries = query_counts.most_common(MAX_QUERIES)
    else:
        print(f"Found {len(query_counts)} unique queries. Formatting ENTIRE DATASET for PostgreSQL...")
        top_queries = query_counts.most_common()
    
    with open(OUTPUT_FILE, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['query', 'count'])
        for query, count in top_queries:
            writer.writerow([query, count])
            
    print(f"Successfully processed {len(top_queries)} real multi-word search queries into {OUTPUT_FILE}!")

if __name__ == "__main__":
    generate_dataset()
