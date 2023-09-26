# Start from a base Python 3.10 image
FROM python:3.10.12-alpine3.17

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Copy requirements file to the container
COPY requirements.txt .

# Install requirements
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code to the container
COPY . .

# Command to run when the container is started
CMD python src/main.py -t 20 -s R_100 -p 1 -a 4