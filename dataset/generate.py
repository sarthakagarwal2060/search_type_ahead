import csv
import random
import os

def generate_dataset():
    os.makedirs('dataset', exist_ok=True)
    filename = 'dataset/queries.csv'
    
    roots = [
        "iphone", "macbook", "samsung", "laptop", "shoes", "shirt", "watch", "tv", 
        "headphones", "tutorial", "course", "book", "game", "software", "app", "music", 
        "video", "camera", "lens", "bag", "wallet", "glasses", "sunglasses", "hat", 
        "jacket", "pants", "jeans", "sneakers", "boots", "dress", "sweater", "hoodie",
        "python", "java", "javascript", "react", "node", "sql", "linux", "docker",
        "kubernetes", "aws", "azure", "gcp", "cloud", "devops", "data", "science"
    ]
    
    modifiers = ["pro", "max", "ultra", "plus", "mini", "lite", "new", "used", "cheap", "best", "review", "guide", "tutorial", "for beginners", "advanced", "2023", "2024", "sale"]
    
    print("Generating unique queries...")
    queries = set()
    while len(queries) < 100000:
        parts = []
        if random.random() > 0.3:
            parts.append(random.choice(modifiers))
        parts.append(random.choice(roots))
        if random.random() > 0.5:
            parts.append(str(random.randint(1, 999)))
        if random.random() > 0.5:
            parts.append(random.choice(modifiers))
            
        q = " ".join(parts).strip()
        if len(q) > 2:
            queries.add(q)
            
    queries = list(queries)[:100000]
    
    print("Writing to CSV with Zipfian distribution...")
    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['query', 'count'])
        
        # Give a zipf-like distribution
        # Highest count ~ 1,000,000, decreasing
        for rank, query in enumerate(queries, start=1):
            # Zipf formula: freq = max_freq / (rank ^ s)
            # s = 0.8 for a slightly fatter tail
            count = int(1000000 / (rank ** 0.8))
            # Add some randomness
            count = max(1, int(count * random.uniform(0.8, 1.2)))
            writer.writerow([query, count])
            
    print(f"Generated {len(queries)} queries in {filename}")

if __name__ == "__main__":
    generate_dataset()
