# Use an official lightweight Python image as a parent image
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Copy requirements file and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire application code
COPY . /app

# Expose the port the app will run on
ENV PORT 8080

# The command to run the application using Gunicorn.
CMD exec gunicorn --bind :$PORT --workers 2 app:app