# Configure Apache Pulsar Standalone Image with Configuration Details

FROM apachepulsar/pulsar-standalone:2.7.0

WORKDIR /pulsar

#using workdir /pulsar we copy public key and it's path will be /pulsar/oauth_public.key and this value must be same as in properties for standalone
# COPY oauth_public.key oauth_public.key

#note oauth2.json is being copied from into workdir /pulsar which is linked in brokerClientAuthenticationParameters
# COPY oauth2.json oauth2.json

#client for CLI tools
COPY conf/client.conf conf/client.conf

#

COPY conf/standalone.conf conf/standalone.conf

# this should run automatically...
CMD [ "/pulsar/bin/pulsar", "standalone"]