#!/usr/bin/env bash
set -euo pipefail

OS_NAME="${DOCGEN_OS_NAME:-$(uname -s)}"
APP_DIR="${DOCGEN_APP_DIR:-/opt/docgen}"
VENV_PYTHON="${DOCGEN_VENV_PYTHON:-${APP_DIR%/}/.venv/bin/python}"
EXPECT_CHINESE="${DOCGEN_EXPECT_OCR_CHINESE:-0}"
SMOKE_LANG="${DOCGEN_OCR_SMOKE_LANG:-eng}"

if [[ "$OS_NAME" != "Linux" ]]; then
  echo "[ERROR] 该脚本仅用于 Linux 源站 OCR 自检。" >&2
  exit 1
fi

failures=0

print_status() {
  local label="$1"
  local ok="$2"
  local detail="$3"
  if [[ "$ok" = "1" ]]; then
    echo "[OK] ${label}: ${detail}"
  else
    echo "[FAIL] ${label}: ${detail}"
    failures=$((failures + 1))
  fi
}

if [[ -x "$VENV_PYTHON" ]]; then
  print_status "venv python" "1" "$VENV_PYTHON"
else
  print_status "venv python" "0" "$VENV_PYTHON not executable"
fi

tesseract_path="$(command -v tesseract || true)"
if [[ -n "$tesseract_path" ]]; then
  print_status "ocr binary" "1" "$tesseract_path"
else
  print_status "ocr binary" "0" "tesseract not found"
fi

lang_list="$(tesseract --list-langs 2>/dev/null || true)"
if [[ -n "$lang_list" ]]; then
  print_status "ocr lang list" "1" "$(tr '\n' ' ' <<<"$lang_list" | sed 's/[[:space:]]\+/ /g')"
else
  print_status "ocr lang list" "0" "unable to list languages"
fi

if [[ "$EXPECT_CHINESE" = "1" ]]; then
  if grep -Eq '(^|[[:space:]])chi_(sim|tra)($|[[:space:]])' <<<"$lang_list"; then
    print_status "ocr chinese langpack" "1" "chi_sim/chi_tra available"
  else
    print_status "ocr chinese langpack" "0" "chi_sim/chi_tra missing"
  fi
fi

python_probe="$(
  APP_DIR="$APP_DIR" "$VENV_PYTHON" - <<'PY' 2>/dev/null || true
from backend.zhifei_autoplan.ocr_runtime import guess_ocr_lang, is_tesseract_available

print("available=" + str(is_tesseract_available()))
print("lang=" + guess_ocr_lang(prefer_chinese=True))
PY
)"
ocr_available="$(printf '%s\n' "$python_probe" | awk -F= '/^available=/{print $2}' | tail -n1)"
ocr_lang="$(printf '%s\n' "$python_probe" | awk -F= '/^lang=/{print $2}' | tail -n1)"

if [[ "$ocr_available" = "True" ]]; then
  print_status "ocr runtime" "1" "available=True lang=${ocr_lang:-unknown}"
else
  print_status "ocr runtime" "0" "${python_probe:-python probe unavailable}"
fi

smoke_output="$(
  APP_DIR="$APP_DIR" DOCGEN_OCR_SMOKE_LANG="$SMOKE_LANG" "$VENV_PYTHON" - <<'PY' 2>/dev/null || true
from pathlib import Path
from tempfile import TemporaryDirectory
import os

from PIL import Image, ImageDraw

from backend.zhifei_autoplan.ocr_runtime import ocr_pdf_path

lang = os.environ.get("DOCGEN_OCR_SMOKE_LANG", "eng")
with TemporaryDirectory() as td:
    pdf_path = Path(td) / "ocr-smoke.pdf"
    im = Image.new("RGB", (900, 220), color="white")
    draw = ImageDraw.Draw(im)
    draw.text((30, 60), "HELLO 123", fill="black")
    im.save(str(pdf_path), "PDF")
    res = ocr_pdf_path(str(pdf_path), max_pages=1, scale=2.0, lang=lang, stop_on_catalog=False)
    print("error=" + str(res.error))
    print("pages=" + str(res.pages))
    print("text=" + (res.text or "").strip().replace("\n", " ")[:120])
PY
)"
smoke_error="$(printf '%s\n' "$smoke_output" | awk -F= '/^error=/{print $2}' | tail -n1)"
smoke_pages="$(printf '%s\n' "$smoke_output" | awk -F= '/^pages=/{print $2}' | tail -n1)"
smoke_text="$(printf '%s\n' "$smoke_output" | awk -F= '/^text=/{sub(/^text=/,""); print}' | tail -n1)"

if [[ "$smoke_error" = "None" && "${smoke_pages:-0}" -ge 1 && -n "$smoke_text" ]]; then
  print_status "ocr smoke" "1" "pages=${smoke_pages} text=${smoke_text}"
else
  print_status "ocr smoke" "0" "${smoke_output:-smoke unavailable}"
fi

if [[ "$failures" -gt 0 ]]; then
  echo "[SUMMARY] ${failures} checks failed."
  exit 1
fi

echo "[SUMMARY] all checks passed."
