import os
import requests

ROBOFLOW_API_KEY = os.getenv("ROBOFLOW_API_KEY")
ROBOFLOW_MODEL = os.getenv("ROBOFLOW_MODEL")

def detect_damage(image_path):
    if not ROBOFLOW_API_KEY or not ROBOFLOW_MODEL:
        raise RuntimeError("Roboflow API key or model ID is not configured")

    with open(image_path, "rb") as image:
        response = requests.post(
            f"https://detect.roboflow.com/{ROBOFLOW_MODEL}",
            params={
                "api_key": ROBOFLOW_API_KEY,
                "confidence": 40,
                "overlap": 30,
            },
            files={"file": image},
            timeout=30,
        )
    response.raise_for_status()
    data = response.json()
    predictions = data.get("predictions", [])
    if not predictions:
        return None
    best = max(predictions, key=lambda item: item["confidence"])
    width = data["image"]["width"]
    height = data["image"]["height"]
    area_pct = best["width"] * best["height"] / (width * height) * 100
    return {
        "damage_type": best["class"].capitalize(),
        "confidence": best["confidence"],
        "area_pct": area_pct,
    }

def get_severity(area_pct):
    if area_pct >= 4:
        return "High"
    if area_pct >= 1.5:
        return "Medium"
    return "Low"