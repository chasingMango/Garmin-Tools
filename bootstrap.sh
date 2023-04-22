sudo apt-get update
sudo apt-get install -y python3-pip

# Fix pip
pip3 install --upgrade pip

# Install app requirements
pip install --upgrade -r /vagrant/requirements.txt