import onnx
model = onnx.load("models/vits/best_model.onnx")
# Look for initializers that correspond to embedding layer weights
for init in model.graph.initializer:
    if "emb" in init.name or "weight" in init.name:
        shape = list(init.dims)
        # Typically the embedding layer will have shape [vocab_size, hidden_dim]
        # In VITS, hidden_dim is 192 (from config.json: "hidden_channels": 192)
        if len(shape) == 2 and shape[1] == 192:
            print(f"Initializer: {init.name}, Shape: {shape}")
            print(f"Found embedding layer with vocab size: {shape[0]}")
            break
else:
    # If not found, just print first few 2D initializers
    print("Could not find matching embedding layer. Printing first few 2D initializers:")
    count = 0
    for init in model.graph.initializer:
        shape = list(init.dims)
        if len(shape) == 2:
            print(f"Initializer: {init.name}, Shape: {shape}")
            count += 1
            if count > 10:
                break
