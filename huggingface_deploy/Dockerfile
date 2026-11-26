FROM python:3.11-slim

# Hugging Face Spaces 1000 numaralı kullanıcıyla çalıştırır
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH \
    KMP_DUPLICATE_LIB_OK=TRUE
WORKDIR /home/user/app

# PyTorch'un küçük CPU sürümü (GPU sürümü gereksiz ve çok büyük)
RUN pip install --no-cache-dir --user torch torchvision --index-url https://download.pytorch.org/whl/cpu

COPY --chown=user requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# EasyOCR modelini derleme sırasında indir -> ilk fotoğrafta beklemesin
RUN python -c "import easyocr; easyocr.Reader(['en'], gpu=False)"

COPY --chown=user . .

EXPOSE 7860
CMD ["streamlit", "run", "app_frontend.py", \
     "--server.port=7860", "--server.address=0.0.0.0", \
     "--server.headless=true", \
     "--server.enableCORS=false", "--server.enableXsrfProtection=false"]
