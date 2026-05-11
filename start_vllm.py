import subprocess
import os

def launch_vllm():
    # --- [Parameters] ---
    # Use absolute path to avoid resolution errors
    model_path = os.path.abspath(os.path.expanduser("~/models/Qwen2.5-7B-GPTQ"))
    
    # Optimization settings for RTX GPUs
    params = [
        "/home/bensontien/Agents/.venv/bin/python3", "-m", "vllm.entrypoints.openai.api_server",
        "--model", model_path,
        # Set a simple alias for the model
        "--served-model-name", "qwen2.5-7b", 
        
        # Quantization settings
        "--quantization", "gptq", 
        
        "--gpu-memory-utilization", "0.85", # Optimization for 8GB VRAM
        "--max-model-len", "8192",          # Context length for semantic analysis
        "--max-num-seqs", "5",              # Reduce concurrency for stability
        "--port", "8000",
        "--trust-remote-code",
        # Optimization for Ada Lovelace/Blackwell architectures
        "--enforce-eager"                   # Eager mode can be more stable with limited VRAM
    ]

    print(f"vLLM server starting...")
    print(f"Loading model: {model_path}")
    print(f"API Name: qwen2.5-7b")
    print("-" * 50)

    try:
        # subprocess.run blocks until the server is closed
        subprocess.run(params, check=True)
    except KeyboardInterrupt:
        print("\nvLLM server manually stopped.")
    except Exception as e:
        print(f"Startup failed: {e}")

if __name__ == "__main__":
    launch_vllm()
