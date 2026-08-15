from modelscope.hub.snapshot_download import snapshot_download

model_dir = snapshot_download(
    model_id='BAAI/bge-m3',
    cache_dir='D:/ai_models/modelscope_cache/models',
    ignore_file_pattern=[
        '*.onnx',
        '*.onnx_data',
        'onnx/*'
    ]
)

print(f"模型已下载到：{model_dir}")