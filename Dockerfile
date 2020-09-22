FROM python:3.6

# system maintenance
RUN apt-get update && apt-get install -y gcc

WORKDIR /scripts

<<<<<<< HEAD
# copy over the requirements.txt and install dependencies
COPY setup.py README.md requirements.txt /opt/ark-analysis/
=======
# copy over the requirements.txt, install dependencies, and README
COPY setup.py requirements.txt README.md /opt/ark-analysis/
>>>>>>> origin/master
RUN pip install -r /opt/ark-analysis/requirements.txt

# copy the scripts over
COPY ark /opt/ark-analysis/ark

# Install the package via setup.py
RUN pip install /opt/ark-analysis

# jupyter notebook
CMD ["jupyter", "notebook", "--ip=0.0.0.0", "--allow-root"]
