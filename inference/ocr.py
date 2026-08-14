"""
OCR on plate crops using PaddleOCR (pretrained — no training needed initially).
If accuracy on Indian plates is poor, revisit with preprocessing
(deskew, contrast enhancement) before considering fine-tuning.

Written against PaddleOCR 3.x, whose Python API changed from 2.x:
    - PaddleOCR(use_angle_cls=..., show_log=...)  ->  PaddleOCR(use_textline_orientation=...)
      (show_log no longer exists as a parameter)
    - ocr.ocr(img, cls=True) returning nested [[box, (text, score)], ...] lists
      ->  ocr.predict(img) returning result objects indexable like dicts:
          res["rec_texts"]  (list[str])
          res["rec_scores"] (list[float])
Docs: https://paddlepaddle.github.io/PaddleOCR/main/en/version3.x/pipeline_usage/OCR.html
"""
import re
from paddleocr import PaddleOCR

# Indian plate pattern (rough): 2 letters, 1-2 digits, 1-3 letters, 4 digits
PLATE_PATTERN = re.compile(r"[A-Z]{2}[0-9]{1,2}[A-Z]{1,3}[0-9]{4}")


class PlateOCR:
    def __init__(self, lang: str = "en"):
        # Plate crops are already tightly cropped and upright, so we skip the
        # doc-orientation/unwarping stages (meant for scanned documents) to
        # keep this fast — we only need text detection + recognition.
        self.ocr = PaddleOCR(
            lang=lang,
            use_doc_orientation_classify=False,
            use_doc_unwarping=False,
            use_textline_orientation=True,   # plates can be slightly tilted
        )

    def read_plate(self, plate_crop):
        """
        Run OCR on a plate crop image (numpy BGR array, e.g. from cv2).
        Returns (plate_string, confidence) — plate_string is "" if nothing readable.
        """
        if plate_crop is None or plate_crop.size == 0:
            return "", 0.0

        results = self.ocr.predict(plate_crop)
        if not results:
            return "", 0.0

        res = results[0]
        texts = res.get("rec_texts", []) if hasattr(res, "get") else res["rec_texts"]
        scores = res.get("rec_scores", []) if hasattr(res, "get") else res["rec_scores"]

        if not texts:
            return "", 0.0

        # Concatenate all recognized text fragments (a plate may be split
        # into multiple lines/segments by the detector), keep the max score.
        combined = "".join(texts)
        best_conf = max(scores) if scores else 0.0

        cleaned = re.sub(r"[^A-Z0-9]", "", combined.upper())
        match = PLATE_PATTERN.search(cleaned)
        final_text = match.group(0) if match else cleaned

        return final_text, float(best_conf)
