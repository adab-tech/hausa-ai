import onnxruntime as ort
session = ort.InferenceSession("models/vits/best_model.onnx")
for i in session.get_inputs():
    print(f"Input: {i.name}, Type: {i.type}, Shape: {i.shape}")
for o in session.get_outputs():
    print(f"Output: {o.name}, Type: {o.type}, Shape: {o.shape}")
