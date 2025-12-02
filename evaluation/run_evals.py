import json
import os
import sys
import asyncio

# Fix for Windows asyncio event loop closed error
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pandas as pd
from phoenix.evals import (
    HallucinationEvaluator,
    QAEvaluator,
    run_evals,
    OpenAIModel,
)
from phoenix.session.evaluation import get_qa_with_reference, get_retrieved_documents
from config.settings import LLMConfig

from core.graphrag import answer_question
from config.myapikeys import GROQ_API_KEY

def load_dataset(path):
    with open(path, "r") as f:
        return json.load(f)

    # 3. Configure Evaluators (using Groq as the Judge)
    # We use the OpenAIModel wrapper but point it to Groq's OpenAI-compatible endpoint.
    
    if not GROQ_API_KEY:
        print("⚠️ GROQ_API_KEY not found. Skipping automated scoring.")
        return

    # Configure Groq as the Judge
    # Groq supports OpenAI-compatible API
    model = OpenAIModel(
        model="llama-3.3-70b-versatile", # Use a strong model for evaluation
        api_key=GROQ_API_KEY,
        base_url="https://api.groq.com/openai/v1",
        temperature=0.0,
    )
    
    hallucination_evaluator = HallucinationEvaluator(model)
    qa_evaluator = QAEvaluator(model)

    # 4. Run Evals
    print("Running automated evaluation...")
    
    # Prepare dataframe for evaluators
    # Phoenix expects 'input', 'output', 'context' (for hallucination), 'reference' (for QA)
    # We need to ensure 'context' is a list of strings or a single string
    
    # Update results with context from the RAG response
    # We need to re-run the loop or just update the logic above. 
    # Let's rewrite the loop part to be cleaner in the full file replacement or just assume we have it.
    # Wait, I am replacing the whole file content in this block? No, just a chunk.
    # I need to make sure 'results' list has 'context'.
    
    # Let's look at the previous loop in the file. It didn't capture context.
    # I need to update the loop first.
    
    pass

def main():
    print("Starting RAG Evaluation...")
    
    # Load the dataset.
    dataset_path = os.path.join(os.path.dirname(__file__), "golden_dataset.json")
    dataset = load_dataset(dataset_path)
    print(f"Loaded {len(dataset)} test cases.")

    # Run the RAG system on the dataset.
    results = []
    for item in dataset:
        question = item["question"]
        print(f"Processing: {question}")
        
        # Call the RAG system.
        response = answer_question(question, bypass_cache=True)
        answer = response["answer"]
        references = response["references"]
        context = response.get("context", "") # Now available
        
        results.append({
            "input": question,
            "output": answer,
            "context": context, # Required for Faithfulness
            "reference": item.get("ground_truth", "") # Required for QA Relevance
        })

    df = pd.DataFrame(results)

    # Configure the evaluators using Groq as the judge.
    # We use the OpenAIModel wrapper but point it to Groq's OpenAI-compatible endpoint.
    if not GROQ_API_KEY:
        print("GROQ_API_KEY not found. Skipping automated scoring.")
        return

    # Configure Groq as the Judge.
    # Groq supports OpenAI-compatible API.
    # Using llama-3.3-70b-versatile as it is a strong model suitable for judging.
    model = OpenAIModel(
        model="llama-3.3-70b-versatile", 
        api_key=GROQ_API_KEY,
        base_url="https://api.groq.com/openai/v1",
        temperature=0.0,
    )
    
    hallucination_evaluator = HallucinationEvaluator(model)
    qa_evaluator = QAEvaluator(model)

    # Run the automated evaluation.
    print("Running automated evaluation...")
    
    eval_results = run_evals(
        dataframe=df,
        evaluators=[hallucination_evaluator, qa_evaluator],
        provide_explanation=True,
    )

    # Handle return type (list vs DataFrame)
    if isinstance(eval_results, list):
        # Assuming list of DataFrames from multiple evaluators
        try:
            eval_results = pd.concat(eval_results, axis=1)
        except Exception as e:
            print(f"Error concatenating results: {e}")
            print(f"Result type: {type(eval_results)}")
            if len(eval_results) > 0:
                print(f"First item type: {type(eval_results[0])}")
            return

    print("\n=== Evaluation Report ===")
    print(eval_results.head())
    
    # Calculate aggregate metrics
    print("\n=== Aggregate Metrics ===")
    # Check column names - usually 'label' or 'score' inside the result dataframe
    # Phoenix returns a dataframe with multi-index columns if multiple evaluators
    # Flattening for simple display might be needed, but head() shows enough for now.
    
    # Save results
    output_path = os.path.join(os.path.dirname(__file__), "eval_results.csv")
    eval_results.to_csv(output_path)
    print(f"Results saved to {output_path}")

if __name__ == "__main__":
    main()
