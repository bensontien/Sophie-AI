import os
from huggingface_hub import snapshot_download

# 設定模型名稱與存放路徑
model_id = "HauhauCS/Gemma-4-E4B-Uncensored-HauhauCS-Aggressive"
local_dir = os.path.expanduser("~/models/HauhauCS/Gemma-4-E4B-Uncensored-HauhauCS-Aggressive")

print(f"🚀 開始下載模型: {model_id}")
print(f"📂 存放路徑: {local_dir}")

try:
    # 執行下載
    path = snapshot_download(
        repo_id=model_id,
        local_dir=local_dir,
        local_dir_use_symlinks=False,  # 不使用符號連結，直接存入實體檔案
        revision="main",                # 下載主要分支
        ignore_patterns=["*.msgpack", "*.h5"] # 忽略不需要的格式以節省空間
    )
    print(f"\n✅ 下載完成！模型已存放在: {path}")
    
except Exception as e:
    print(f"\n❌ 下載發生錯誤: {e}")