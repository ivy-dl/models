FROM unifyai/ivy:latest

# Install Ivy
RUN rm -rf ivy && \
    git clone https://github.com/unifyai/ivy && \
    cd ivy && \
    cat requirements.txt | grep -v "ivy-" | pip3 install --no-cache-dir -r /dev/stdin && \
    cat optional.txt | grep -v "ivy-" | pip3 install --no-cache-dir -r /dev/stdin && \
    python3 setup.py develop --no-deps

# Install Ivy Models
RUN git clone https://github.com/rush2406/models.git && \
    cd models && \
    ls &&\
    git checkout ivy_update && \
    git pull && \
    cat requirements.txt | grep -v "ivy-" | pip3 install --no-cache-dir -r /dev/stdin && \
    python3 setup.py develop --no-deps

COPY requirements.txt /
RUN cat requirements.txt | grep -v "ivy-" | pip3 install --no-cache-dir -r /dev/stdin

#RUN python3 test_dependencies.py -fp requirements.txt && \
#    rm -rf requirements.txt

WORKDIR /models