# init a base image (Alpine is small Linux distro)
FROM python:3.8
# define the present working directory
WORKDIR /DemoFlask2
# copy the contents into the working dir
ADD . /DemoFlask2
# run pip to install the dependencies of the flask app
RUN pip install --upgrade pip
RUN pip install -r requirements.txt
# define the command to start the container


CMD ["python","main.py"]