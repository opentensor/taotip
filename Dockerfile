FROM nvidia/cuda:11.2.1-base-ubuntu18.04

ARG DEBIAN_FRONTEND=noninteractive

# Nvidia Key Rotation
## https://forums.developer.nvidia.com/t/notice-cuda-linux-repository-key-rotation/212772
## Remove old Nvidia GPG key and source list
## Prevents apt from failing to find the key
RUN rm /etc/apt/sources.list.d/cuda.list \
    && rm /etc/apt/sources.list.d/nvidia-ml.list 
RUN apt-key del 7fa2af80

# apt update and Install dependencies
RUN apt-get update && \
    apt-get install --no-install-recommends --no-install-suggests -y apt-utils wget software-properties-common \
    build-essential curl git cmake unzip iproute2 python3-pip 

# Nvidia Key Rotation
## https://forums.developer.nvidia.com/t/notice-cuda-linux-repository-key-rotation/212772
## Add new Nvidia GPG key
RUN apt-key adv --fetch-keys https://developer.download.nvidia.com/compute/cuda/repos/ubuntu1804/x86_64/3bf863cc.pub
RUN apt-key adv --fetch-keys https://developer.download.nvidia.com/compute/machine-learning/repos/ubuntu1804/x86_64/7fa2af80.pub
RUN wget https://developer.download.nvidia.com/compute/cuda/repos/ubuntu1804/x86_64/cuda-keyring_1.0-1_all.deb
RUN dpkg -i cuda-keyring_1.0-1_all.deb

RUN add-apt-repository ppa:deadsnakes/ppa
RUN apt-get update && apt-get upgrade -y
RUN apt-get install python3.7 python3.7-dev -y
RUN python3.7 -m pip install --upgrade pip

RUN apt-get install git -y

RUN rm /usr/bin/python3
RUN ln -s //usr/bin/python3.7 /usr/bin/python3

WORKDIR /usr/app/

ADD . /usr/app/

RUN pip install --upgrade wheel
RUN pip install setuptools

RUN pip install -r requirements.txt --no-cache-dir

ENTRYPOINT [ "/usr/bin/python3" ]
CMD [ "main.py" ]