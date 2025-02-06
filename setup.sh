#!/bin/bash

echo "Setting up the Flask application..."

# Create a virtual environment
if [ ! -d "venv" ]; then
  python3 -m venv venv
fi

# Activate the virtual environment
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Initialize the database
python3 -c "from app import create_app; app = create_app(); with app.app_context(): from app.models import db, Role; db.create_all(); db.session.add(Role(name='Admin')); db.session.add(Role(name='Editor')); db.session.add(Role(name='User')); db.session.commit()"

echo "Setup complete. Run the app with 'flask run'."
