import json
import os
import sys
import asyncio

# Fix for Windows asyncio event loop closed error
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.graphrag import answer_question

def load_dataset(path):
    with open(path, "r") as f:
        return json.load(f)

def main():
    # Redirect stdout to file
    original_stdout = sys.stdout
    with open("latency_report.txt", "w", encoding="utf-8") as f:
        sys.stdout = f
        print("Starting Latency & Confidence Monitoring...")
        
        # Thresholds
        MAX_RETRIEVAL_MS = 1500 # Relaxed for local/first run
        TARGET_RETRIEVAL_MS = 150
        TARGET_SIMILARITY = 0.65
        
        # Load the dataset.
        dataset_path = os.path.join(os.path.dirname(__file__), "golden_dataset.json")
        dataset = load_dataset(dataset_path)
        print(f"Loaded {len(dataset)} test cases.")

        print("\n" + "="*80)
        print(f"{'Query':<30} | {'Ret(ms)':<8} | {'Gen(ms)':<8} | {'Sim':<5} | {'Status':<6}")
        print("="*80)

        for item in dataset:
            question = item["question"]
            
            # Call the RAG system.
            response = answer_question(question, bypass_cache=True)
            
            metrics = response.get("metrics", {})
            retrieval_ms = metrics.get("retrieval_latency_ms", 0)
            generation_ms = metrics.get("generation_latency_ms", 0)
            avg_similarity = metrics.get("avg_similarity_score", 0.0)
            
            # Evaluate status.
            status = "PASS"
            if retrieval_ms > TARGET_RETRIEVAL_MS:
                status = "SLOW_R" # Slow Retrieval
            if avg_similarity < TARGET_SIMILARITY:
                status = "LOW_SIM"
                
            # Print row.
            short_question = (question[:27] + '...') if len(question) > 27 else question
            print(f"{short_question:<30} | {retrieval_ms:8.1f} | {generation_ms:8.1f} | {avg_similarity:.2f}  | {status:<6}")

        print("="*80)
        print(f"\nThresholds: Retrieval < {TARGET_RETRIEVAL_MS}ms, Similarity >= {TARGET_SIMILARITY}")
    
    sys.stdout = original_stdout
    print("Report saved to latency_report.txt")

if __name__ == "__main__":
    main()
