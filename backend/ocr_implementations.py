"""
Alternative OCR implementation using EasyOCR (no system dependencies required).

This is a drop-in replacement for the Tesseract-based OCR in retriever.py.
Use this if Tesseract installation fails on your remote server.

To use:
1. Add to backend/requirements.txt: easyocr==1.7.0
2. Replace the _extract_text_from_images_ocr function in retriever.py with this one
3. Rebuild container: docker-compose build pfas_fastapi
"""

import logging
from typing import List

# Cache the reader to avoid reloading model for each call
_easyocr_reader = None

def _extract_text_from_images_ocr(page, image_list: list) -> str:
    """Extract text from images using EasyOCR (alternative to Tesseract).
    
    EasyOCR is a pure Python OCR library that doesn't require system binaries.
    It's slower than Tesseract but works in restricted Docker environments.
    
    Args:
        page: PyMuPDF page object
        image_list: List of images from page.get_images()
    
    Returns:
        Combined OCR text from all images
    """
    global _easyocr_reader
    
    try:
        import easyocr
        import numpy as np
        from PIL import Image
        import io
        
        # Initialize reader once (cached)
        if _easyocr_reader is None:
            logging.info("🔧 Initializing EasyOCR reader (one-time setup)...")
            _easyocr_reader = easyocr.Reader(['en'], gpu=False, verbose=False)
            logging.info("✅ EasyOCR reader ready")
        
        ocr_texts = []
        for img_index, img_info in enumerate(image_list):
            try:
                xref = img_info[0]
                base_image = page.parent.extract_image(xref)
                image_bytes = base_image["image"]
                
                # Convert to PIL Image, then to numpy array
                image = Image.open(io.BytesIO(image_bytes))
                image_np = np.array(image)
                
                # Run OCR with EasyOCR
                # Returns list of (bbox, text, confidence)
                result = _easyocr_reader.readtext(image_np, detail=1)
                
                # Extract text with confidence > 0.3
                texts = [detection[1] for detection in result if detection[2] > 0.3]
                ocr_text = ' '.join(texts).strip()
                
                if ocr_text and len(ocr_text) > 10:  # Minimum 10 chars
                    ocr_texts.append(ocr_text)
                    logging.debug(f"📸 EasyOCR extracted {len(ocr_text)} chars from image {img_index}")
                    
            except Exception as e_img:
                logging.warning(f"Failed EasyOCR on image {img_index}: {e_img}")
                continue
        
        combined_text = "\n".join(ocr_texts)
        if combined_text:
            logging.info(f"✅ EasyOCR total: {len(combined_text)} chars from {len(image_list)} images")
        
        return combined_text
        
    except ImportError:
        logging.debug("EasyOCR not installed, skipping OCR")
        return ""
    except Exception as e:
        logging.warning(f"EasyOCR extraction failed: {e}")
        return ""


def _extract_text_from_images_ocr_tesseract(page, image_list: list) -> str:
    """Original Tesseract-based OCR implementation.
    
    Use this if Tesseract is successfully installed in your Docker container.
    This is faster than EasyOCR but requires system binary installation.
    
    Args:
        page: PyMuPDF page object
        image_list: List of images from page.get_images()
    
    Returns:
        Combined OCR text from all images
    """
    try:
        from PIL import Image
        import pytesseract
        import io
        
        ocr_texts = []
        for img_index, img_info in enumerate(image_list):
            try:
                xref = img_info[0]
                base_image = page.parent.extract_image(xref)
                image_bytes = base_image["image"]
                
                # Convert to PIL Image
                image = Image.open(io.BytesIO(image_bytes))
                
                # Run OCR (pytesseract)
                ocr_text = pytesseract.image_to_string(image, lang='eng')
                if ocr_text and len(ocr_text.strip()) > 10:  # Minimum 10 chars
                    ocr_texts.append(ocr_text.strip())
                    
            except Exception as e_img:
                logging.warning(f"Failed OCR on image {img_index}: {e_img}")
                continue
        
        return "\n".join(ocr_texts)
        
    except ImportError:
        logging.debug("pytesseract not installed, skipping OCR")
        return ""
    except Exception as e:
        logging.warning(f"OCR extraction failed: {e}")
        return ""


def _extract_text_from_images_ocr_cloud(page, image_list: list, provider: str = 'google') -> str:
    """Cloud-based OCR implementation (Google Vision or Azure).
    
    Use this for best accuracy with pay-per-use model.
    Requires API credentials to be configured.
    
    Args:
        page: PyMuPDF page object
        image_list: List of images from page.get_images()
        provider: 'google' or 'azure'
    
    Returns:
        Combined OCR text from all images
    """
    try:
        from PIL import Image
        import io
        
        if provider == 'google':
            from google.cloud import vision
            client = vision.ImageAnnotatorClient()
            
            ocr_texts = []
            for img_index, img_info in enumerate(image_list):
                try:
                    xref = img_info[0]
                    base_image = page.parent.extract_image(xref)
                    image_bytes = base_image["image"]
                    
                    # Send to Google Vision API
                    image = vision.Image(content=image_bytes)
                    response = client.text_detection(image=image)
                    
                    if response.text_annotations:
                        ocr_text = response.text_annotations[0].description
                        if ocr_text and len(ocr_text.strip()) > 10:
                            ocr_texts.append(ocr_text.strip())
                            
                except Exception as e_img:
                    logging.warning(f"Failed cloud OCR on image {img_index}: {e_img}")
                    continue
            
            return "\n".join(ocr_texts)
            
        elif provider == 'azure':
            # Azure Computer Vision implementation
            # Add Azure credentials and client setup here
            logging.warning("Azure OCR not yet implemented")
            return ""
            
    except ImportError as e:
        logging.debug(f"Cloud OCR library not installed: {e}")
        return ""
    except Exception as e:
        logging.warning(f"Cloud OCR extraction failed: {e}")
        return ""


# Export the recommended implementation
# Change this to switch between OCR backends
def get_ocr_function():
    """Return the appropriate OCR function based on environment."""
    import os
    
    # Check environment variable for OCR preference
    ocr_backend = os.getenv('OCR_BACKEND', 'easyocr')  # default to easyocr
    
    if ocr_backend == 'tesseract':
        return _extract_text_from_images_ocr_tesseract
    elif ocr_backend == 'cloud':
        return _extract_text_from_images_ocr_cloud
    else:  # default: easyocr
        return _extract_text_from_images_ocr


if __name__ == "__main__":
    # Test the OCR implementation
    print("Testing OCR implementations...")
    
    # Test EasyOCR
    try:
        import easyocr
        print("✅ EasyOCR is installed")
    except ImportError:
        print("❌ EasyOCR not installed. Run: pip install easyocr")
    
    # Test Tesseract
    try:
        import pytesseract
        pytesseract.get_tesseract_version()
        print("✅ Tesseract is installed")
    except Exception as e:
        print(f"❌ Tesseract not available: {e}")
    
    print("\nRecommended: Use EasyOCR for Docker environments")
