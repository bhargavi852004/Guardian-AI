import os
import logging
import numpy as np
from PIL import Image
import onnxruntime as ort

# Configure logger
logger = logging.getLogger(__name__)

# Optional: Set logging level globally
logging.basicConfig(level=logging.INFO)

# Load ONNX session once with CPU execution provider fallback
ONNX_MODEL_PATH = "Dl_model/classifier_model.onnx"

try:
    session = ort.InferenceSession(ONNX_MODEL_PATH, providers=["CPUExecutionProvider"])
    logger.info(" ONNX model loaded successfully.")
except Exception as e:
    logger.exception(f" Failed to load ONNX model from {ONNX_MODEL_PATH}")
    raise


def preprocess_image(image_path):
    """
    Preprocess image for ONNX model input: (1, 256, 256, 3)
    """
    try:
        image = Image.open(image_path).convert("RGB")
        image = image.resize((256, 256))  # Adjust size
        arr = np.array(image).astype(np.float32) / 255.0
        return arr.reshape(1, 256, 256, 3)
    except Exception as e:
        logger.exception(f"❌ Error preprocessing image: {image_path}")
        raise



def get_nsfw_score(image_path):
    """
    Returns NSFW probability score from ONNX model.
    """
    if not os.path.exists(image_path):
        logger.error(f"❌ Image not found: {image_path}")
        return 0.0

    try:
        input_array = preprocess_image(image_path)
        input_name = session.get_inputs()[0].name
        outputs = session.run(None, {input_name: input_array})

        if not outputs or outputs[0].shape != (1, 2):
            logger.warning(f"⚠️ Unexpected output shape from model for {image_path}: {outputs[0].shape}")
            return 0.0

        score = float(outputs[0][0][1])  # Assumes NSFW at index 1
        logger.info(f"NSFW score for {os.path.basename(image_path)}: {score:.4f}")

        return round(score, 4)

    except Exception as e:
        logger.exception(f"❌ Error during NSFW model inference for: {image_path}")
        return 0.0
