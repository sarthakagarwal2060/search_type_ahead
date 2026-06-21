import urllib.request
import csv
import os

NORVIG_URL = "http://norvig.com/ngrams/count_1w.txt"
OUTPUT_FILE = "dataset/queries.csv"

def generate_dataset():
    print(f"Downloading Peter Norvig's N-Gram Dataset from {NORVIG_URL}...")
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    
    req = urllib.request.Request(NORVIG_URL, headers={'User-Agent': 'Mozilla/5.0'})
    
    try:
        response = urllib.request.urlopen(req)
        lines = response.read().decode('utf-8').splitlines()
    except Exception as e:
        print(f"Failed to download Norvig dataset: {e}")
        return

    print("Parsing dataset and formatting for PostgreSQL...")
    
    with open(OUTPUT_FILE, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['query', 'count'])
        for line in lines:
            parts = line.strip().split('\t')
            if len(parts) == 2:
                word = parts[0].strip()
                count = parts[1].strip()
                if word and count.isdigit():
                    writer.writerow([word, int(count)])
            
    print(f"Successfully processed {len(lines)} English words into {OUTPUT_FILE}!")

if __name__ == "__main__":
    generate_dataset()
