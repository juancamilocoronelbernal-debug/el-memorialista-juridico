"""OCR local acotado: Tesseract y Poppler, sin enviar escaneos a terceros."""
from __future__ import annotations

import copy
import io
import re
import shutil
import subprocess
import tempfile
import time
from functools import lru_cache
from pathlib import Path

from fastapi import HTTPException
from app.config import get_settings


@lru_cache(maxsize=1)
def _installed_languages() -> tuple[str, ...]:
    binary = shutil.which("tesseract")
    if not binary:
        return ()
    try:
        result = subprocess.run([binary, "--list-langs"], capture_output=True, text=True, timeout=5, check=True)
        return tuple(line.strip() for line in result.stdout.splitlines() if re.fullmatch(r"[a-zA-Z0-9_]+", line.strip()))
    except (subprocess.SubprocessError, OSError):
        return ()


def ocr_status() -> dict:
    s = get_settings()
    installed = _installed_languages()
    requested = [lang for lang in s.DESPACHO_OCR_LANGUAGES.split("+") if re.fullmatch(r"[a-zA-Z0-9_]+", lang)]
    selected = [lang for lang in requested if lang in installed]
    return {"enabled": s.DESPACHO_OCR_ENABLED, "available": bool(s.DESPACHO_OCR_ENABLED and selected and shutil.which("tesseract")),
            "pdf_available": bool(s.DESPACHO_OCR_ENABLED and selected and shutil.which("pdftoppm")),
            "languages": selected, "missing_languages": [lang for lang in requested if lang not in installed],
            "engine": "Tesseract local", "max_pages": s.DESPACHO_OCR_MAX_PAGES}


def _read_image(path: Path, *, timeout: float, languages: list[str]) -> str:
    try:
        result = subprocess.run([shutil.which("tesseract"), str(path), "stdout", "-l", "+".join(languages), "--psm", "3"],
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout, check=True)
        if len(result.stdout) > 1_000_000:
            raise HTTPException(413, "La salida OCR de una imagen supera el límite de lectura.")
        return result.stdout.decode("utf-8", errors="replace").replace("\x00", "")
    except subprocess.TimeoutExpired:
        raise HTTPException(504, "La página alcanzó el límite de tiempo de OCR.") from None
    except (OSError, subprocess.CalledProcessError):
        raise HTTPException(422, "El motor OCR no pudo interpretar esta imagen.") from None


def extract_image(content: bytes, filename: str) -> dict:
    try:
        from PIL import Image
        with Image.open(io.BytesIO(content)) as image:
            if image.width * image.height > 30_000_000 or image.format not in {"PNG", "JPEG", "TIFF", "WEBP"}:
                raise HTTPException(413, "Usa una imagen PNG/JPEG/TIFF/WebP de hasta 30 megapíxeles.")
            image.verify()
        with Image.open(io.BytesIO(content)) as image:
            if getattr(image, "n_frames", 1) != 1:
                raise HTTPException(422, "Convierte la imagen multipágina a PDF antes de subirla.")
            image.load()
            image_format = image.format
            normalized = image.convert("RGB")
    except ImportError:
        raise HTTPException(503, "Instala Pillow para procesar imágenes.") from None
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(422, "El archivo no es una imagen válida.") from None
    status = ocr_status()
    text, warnings, truncated = "", [], False
    if status["available"]:
        with tempfile.TemporaryDirectory(prefix="memorialista-ocr-") as directory:
            path = Path(directory) / "pagina.png"
            normalized.save(path, format="PNG")
            text = _read_image(path, timeout=get_settings().DESPACHO_OCR_PAGE_TIMEOUT_SECONDS, languages=status["languages"])
            truncated = len(text) > 500_000
            text = text[:500_000]
            if truncated:
                warnings.append("El texto OCR alcanzó 500.000 caracteres; falta parte de la imagen por revisar.")
        warnings.append("Texto obtenido mediante OCR local. Comprueba nombres, cifras, fechas y signos contra el original.")
        if status["missing_languages"]:
            warnings.append("Idiomas OCR no instalados: " + ", ".join(status["missing_languages"]) + ".")
    else:
        warnings.append("La imagen se conserva, pero no hay OCR disponible. Instala Tesseract y los idiomas configurados.")
    mime = {"PNG": "image/png", "JPEG": "image/jpeg", "TIFF": "image/tiff", "WEBP": "image/webp"}[image_format]
    return {"filename": filename, "mime": mime, "text": text, "pages": [{"page": 1, "text": text}],
            "page_count": 1, "pagination": "pages", "warnings": warnings, "truncated": truncated,
            "extracted_chars": len(text), "ocr": {"engine": status["engine"], "processed_pages": [1] if text else []},
            "extraction_coverage": {"pages_total": 1, "pages_with_text": int(bool(text.strip())), "truncated": truncated, "complete": bool(text.strip()) and not truncated}}


def supplement_pdf(content: bytes, pages: list[dict]) -> tuple[list[dict], list[str], dict]:
    status = ocr_status()
    empty = [page for page in pages if not str(page.get("text", "")).strip() or page.get("ocr_candidate")]
    if not empty:
        return pages, [], {"processed_pages": []}
    if not status["pdf_available"]:
        return pages, [f"{len(empty)} página(s) sin texto suficiente. El OCR de PDF necesita Tesseract, Poppler y los idiomas configurados."], {"processed_pages": [], "unresolved_pages": len(empty)}
    s = get_settings()
    output = copy.deepcopy(pages)
    processed, warnings, truncated = [], [], False
    deadline = time.monotonic() + 120
    remaining = max(0, 500_000 - sum(len(page.get("text", "")) for page in pages))
    with tempfile.TemporaryDirectory(prefix="memorialista-ocr-") as directory:
        original = Path(directory) / "original.pdf"
        original.write_bytes(content)
        for page in [p for p in output if not str(p.get("text", "")).strip() or p.get("ocr_candidate")][:s.DESPACHO_OCR_MAX_PAGES]:
            if time.monotonic() >= deadline or remaining <= 0:
                warnings.append("El OCR alcanzó su presupuesto de tiempo o texto; parte del archivo queda pendiente.")
                truncated = True
                break
            number = page["page"]
            prefix = Path(directory) / ("pagina-" + str(number))
            timeout = min(s.DESPACHO_OCR_PAGE_TIMEOUT_SECONDS, max(1, deadline - time.monotonic()))
            try:
                subprocess.run([shutil.which("pdftoppm"), "-f", str(number), "-l", str(number), "-singlefile",
                                "-scale-to", "2600", "-r", "160", "-png", str(original), str(prefix)],
                               capture_output=True, timeout=timeout, check=True)
                image = prefix.with_suffix(".png")
                if not image.is_file() or image.stat().st_size > 40 * 1024 * 1024:
                    raise HTTPException(413, "La representación de una página es demasiado grande.")
                text = _read_image(image, timeout=min(s.DESPACHO_OCR_PAGE_TIMEOUT_SECONDS, max(1, deadline-time.monotonic())), languages=status["languages"])
                before = len(page.get("text", ""))
                allowance = remaining + before
                truncated = truncated or len(text) > allowance
                if text.strip() and len(text.strip()) >= len(page.get("text", "").strip()):
                    page["text"] = text[:allowance]
                    remaining -= max(0, len(page["text"])-before)
                    page.pop("ocr_candidate", None)
                    processed.append(number)
                image.unlink(missing_ok=True)
            except (HTTPException, subprocess.SubprocessError, OSError):
                warnings.append(f"No se pudo completar el OCR de la página {number}; revisa el original.")
    unresolved = sum(not p.get("text", "").strip() or bool(p.get("ocr_candidate")) for p in output)
    warnings.append(f"OCR local aplicado a {len(processed)} página(s); {unresolved} página(s) permanecen sin texto. Revisa cifras, nombres y fechas.")
    if status["missing_languages"]:
        warnings.append("Idiomas OCR no instalados: " + ", ".join(status["missing_languages"]) + ".")
    if truncated:
        warnings.append("El resultado OCR es parcial por su límite de texto o tiempo.")
    return output, warnings, {"engine": status["engine"], "processed_pages": processed, "unresolved_pages": unresolved, "truncated": truncated}
