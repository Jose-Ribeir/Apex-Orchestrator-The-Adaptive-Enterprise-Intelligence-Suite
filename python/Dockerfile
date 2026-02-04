# Use an official Python runtime as a parent image
# We use 3.10-slim to keep the image size reasonable while ensuring compatibility
FROM python:3.10-slim

# Set environment variables
# PYTHONDONTWRITEBYTECODE: Prevents Python from writing pyc files to disc
# PYTHONUNBUFFERED: Prevents Python from buffering stdout and stderr
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set the working directory in the container
WORKDIR /app

# Install system dependencies required for building Python packages
# git is often needed for installing packages directly from repositories (like FlashRAG)
RUN apt-get update && apt-get install -y \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy the requirements file into the container
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# --- FlashRAG Installation ---
# Since FlashRAG might not be on PyPI or requires specific setup,
# we clone it directly. Adjust the repo URL if you are using a fork.
RUN git clone https://github.com/RUC-NLPIR/FlashRAG.git /app/FlashRAG

# Install FlashRAG dependencies
RUN pip install --no-cache-dir -e /app/FlashRAG

# Copy the rest of the application code
COPY . .

# Create the data directory to ensure permissions are correct
RUN mkdir -p data

# Expose the port the app runs on
EXPOSE 8000

# Define environment variable for FlashRAG path so the code can find it
ENV FLASH_RAG_PATH=/app/FlashRAG

# Command to run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]