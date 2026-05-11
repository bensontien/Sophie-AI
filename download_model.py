import os
from huggingface_hub import snapshot_download

# Set model name and storage path
model_id = "HauhauCS/Gemma-4-E4B-Uncensored-HauhauCS-Aggressive"
local_dir = os.path.expanduser("~/models/HauhauCS/Gemma-4-E4B-Uncensored-HauhauCS-Aggressive")

print(f"Starting model download: {model_id}")
print(f"Storage path: {local_dir}")

try:
    # Execute download
    path = snapshot_download(
        repo_id=model_id,
        local_dir=local_dir,
        local_dir_use_symlinks=False,  # Download physical files directly
        revision="main",                # Download main branch
        ignore_patterns=["*.msgpack", "*.h5"] # Ignore unnecessary formats to save space
    )
    print(f"\nDownload complete! Model stored at: {path}")
    
except Exception as e:
    print(f"\nDownload error: {e}")
