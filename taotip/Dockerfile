FROM nvidia/cuda:11.2.1-base-ubuntu20.04

ARG DEBIAN_FRONTEND=noninteractive

# apt update and Install dependencies
RUN apt-get update && \
    apt-get install --no-install-recommends --no-install-suggests -y apt-utils wget software-properties-common \
    build-essential curl git cmake unzip iproute2 python3-pip 
    
RUN add-apt-repository ppa:deadsnakes/ppa
RUN apt-get update && apt-get upgrade -y
RUN apt-get install python3.9 python3.9-dev python3.9-distutils -y
RUN python3.9 -m pip install --upgrade pip

RUN apt-get install git -y

RUN rm /usr/bin/python3
RUN ln -s //usr/bin/python3.9 /usr/bin/python3

RUN pip install --upgrade wheel
RUN pip install setuptools

# Install bittensor
RUN pip install git+https://github.com/opentensor/bittensor.git#bittensor@master

WORKDIR /usr/app/

ADD . /usr/app/

# Install requirements.txt
RUN pip install -r requirements.txt --no-cache-dir

ENTRYPOINT [ "/usr/bin/python3" ]
CMD [ "main.py" ]