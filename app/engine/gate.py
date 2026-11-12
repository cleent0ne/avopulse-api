from PIL import Image, ImageStat
import io

def check_photo_quality(image_bytes: bytes) -> dict:
    """
    Checks photo quality (brightness and blur) using Pillow.
    Returns:
        dict: {"passed": bool, "message": str, "brightness": float}
    """
    try:
        img = Image.open(io.BytesIO(image_bytes)).convert("L")
    except Exception as e:
        return {
            "passed": False,
            "message": "Invalid image file. Please upload a clear photo of the cut avocado.",
            "brightness": 0.0
        }

    # Brightness check: mean pixel value
    stat = ImageStat.Stat(img)
    brightness = stat.mean[0]

    # Too dark (< 40) or excessively washed out (> 245)
    if brightness < 40:
        return {
            "passed": False,
            "message": "Photo is too dark. Retake in daylight, flesh facing the camera.",
            "brightness": brightness
        }
    if brightness > 248:
        return {
            "passed": False,
            "message": "Photo is overexposed. Retake in even natural light.",
            "brightness": brightness
        }

    # Basic contrast check: standard deviation
    stddev = stat.stddev[0]
    if stddev < 15:
        return {
            "passed": False,
            "message": "Photo lacks contrast or is blurry. Retake in daylight, flesh facing the camera.",
            "brightness": brightness
        }

    return {
        "passed": True,
        "message": "Photo quality verified.",
        "brightness": brightness
    }

