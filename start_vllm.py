import subprocess
import os

def launch_vllm():
    # --- [參數設定] ---
    # 使用絕對路徑避免解析錯誤
    model_path = os.path.abspath(os.path.expanduser("~/models/Qwen2.5-7B-GPTQ"))
    
    # 針對 RTX 5060 的優化設定
    params = [
        "/home/bensontien/Agents/.venv/bin/python3", "-m", "vllm.entrypoints.openai.api_server",
        "--model", model_path,
        # 【重要修正】給模型一個簡單的別名，讓 .env 容易設定
        "--served-model-name", "qwen2.5-7b", 
        
        # 量化設定：若模型是 GPTQ，vLLM 通常會自動偵測，
        # 若手動指定 gptq_marlin 失敗，請改回 "gptq" 或移除此行
        "--quantization", "gptq", 
        
        "--gpu-memory-utilization", "0.85", # 稍微調高，8GB 卡需要斤斤計較
        "--max-model-len", "8192",          # 語意分析需要稍微大一點的 context
        "--max-num-seqs", "5",              # 降低併發數，確保單次推論速度與穩定
        "--port", "8000",
        "--trust-remote-code",
        # 針對 Ada Lovelace/Blackwell 架構最佳化 (RTX 50 系列)
        "--enforce-eager"                   # 顯存較小時，使用 Eager mode 有時比 CUDA Graph 更穩
    ]

    print(f"🚀 ILLUMINA vLLM 伺服器準備啟動...")
    print(f"📦 載入模型: {model_path}")
    print(f"🔗 API 名稱: qwen2.5-7b")
    print("-" * 50)

    try:
        # 使用 subprocess.run 會阻塞在這裡直到伺服器關閉
        subprocess.run(params, check=True)
    except KeyboardInterrupt:
        print("\n🛑 vLLM 伺服器已手動關閉。")
    except Exception as e:
        print(f"❌ 啟動失敗: {e}")

if __name__ == "__main__":
    launch_vllm()