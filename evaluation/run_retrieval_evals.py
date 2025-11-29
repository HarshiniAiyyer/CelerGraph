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
    with open("retrieval_report.txt", "w", encoding="utf-8") as f:
        sys.stdout = f
        print("Starting Retrieval Quality Evaluation...")
        
        # Load the dataset.
        dataset_path = os.path.join(os.path.dirname(__file__), "golden_dataset.json")
        dataset = load_dataset(dataset_path)
        print(f"Loaded {len(dataset)} test cases.")

        print("\n" + "="*60)
        print(f"{'Query':<40} | {'Status':<6} | {'Sim':<5} | {'Recall':<6}")
        print("="*60)

        for item in dataset:
            question = item["question"]
            expected_context = item.get("context_ground_truth", [])
            
            # Call the RAG system.
            response = answer_question(question, bypass_cache=True)
            
            # Extract retrieval data.
            retrieved_data = response.get("retrieved_context", {})
            chunks = retrieved_data.get("chunks", [])
            nodes = retrieved_data.get("nodes", [])
            
            # Print first chunk and node structure for debugging.
            if chunks:
                print(f"DEBUG Chunk[0]: {json.dumps(chunks[0], default=str)}")
            if nodes:
                print(f"DEBUG Node[0]: {json.dumps(nodes[0], default=str)}")
            
            # Calculate top-k similarity.
            # Get max similarity from chunks or nodes.
            chunk_scores = [chunk["similarity"] for chunk in chunks]
            node_scores = [node["similarity"] for node in nodes]
            all_scores = chunk_scores + node_scores
            best_similarity = max(all_scores) if all_scores else 0.0
            
            # Calculate recall.
            # Check if expected files/nodes are in the retrieved set.
            retrieved_refs = set()
            
            for chunk in chunks:
                # Metadata might have 'file_path' or 'source'.
                # Debug output showed key is "file" and value is absolute path.
                meta = chunk.get("metadata", {})
                path = meta.get("file") or meta.get("file_path")
                
                if path:
                    # Normalize path separators.
                    path = path.replace("\\", "/")
                    retrieved_refs.add(path)
                    
            for node in nodes:
                # Nodes might be classes/functions. ID might be "infos.routing.APIRouter".
                retrieved_refs.add(node["id"])
            
            # Check recall.
            hits = 0
            for expected in expected_context:
                # Expected is like "infos/routing.py".
                # Check file paths (endswith to handle absolute paths).
                match = False
                for ref in retrieved_refs:
                    # Check if ref is a file path that ends with expected.
                    if ref.endswith(expected):
                        match = True
                        break
                    
                    # Check if ref is a Node ID that contains the module name.
                    # e.g. expected "infos/routing.py" -> module "routing"
                    # ref "routing.APIRouter..."
                    module_name = os.path.splitext(os.path.basename(expected))[0]
                    if module_name in ref:
                         match = True
                         break
                
                if match:
                    hits += 1
            
            recall = hits / len(expected_context) if expected_context else 0.0
            
            # Good if similarity > 0.75 AND recall > 0 (if ground truth exists).
            status = "GOOD"
            if best_similarity < 0.75:
                status = "LOW_SIM"
            if expected_context and recall == 0:
                status = "MISS"
                
            # Print row.
            short_question = (question[:37] + '...') if len(question) > 37 else question
            print(f"{short_question:<40} | {status:<6} | {best_similarity:.2f}  | {recall:.1f}")
            
            # Detailed debug if MISS
            if status == "MISS":
                print(f"  Expected: {expected_context}")
                print(f"  Top Refs: {list(retrieved_refs)[:3]}...")

        print("="*60)
    
    sys.stdout = original_stdout
    print("Report saved to retrieval_report.txt")

if __name__ == "__main__":
    main()
