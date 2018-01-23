#!/usr/bin/env bash

[[ -z "${INSTANCE}" ]] && echo 'The variable INSTANCE must be defined' 1>&2 && exit 1

########################################################
# Loading the instance's settings

if [[ -f ${SETTINGS}/${INSTANCE} ]]; then
    source ${SETTINGS}/${INSTANCE}
else
    echo "No settings found for ${INSTANCE}"
    exit 1
fi

[[ -x $(readlink ${GPG}) ]] && echo "${GPG} is not executable. Adjust the setting with --gpg" && exit 2
[[ -x $(readlink ${OPENSSL}) ]] && echo "${OPENSSL} is not executable. Adjust the setting with --openssl" && exit 3

if [ -z "${DB_USER}" -o "${DB_USER}" == "postgres" ]; then
    echo "Choose a database user (but not 'postgres')"
    exit 4
fi

#########################################################################
# And....cue music
#########################################################################

mkdir -p $PRIVATE/${INSTANCE}/{gpg,rsa,certs,logs}
chmod 700 $PRIVATE/${INSTANCE}/{gpg,rsa,certs,logs}

echomsg "\t* the GnuPG key"

cat > ${PRIVATE}/${INSTANCE}/gen_key <<EOF
%echo Generating a basic OpenPGP key
Key-Type: RSA
Key-Length: 4096
Name-Real: ${GPG_NAME}
Name-Comment: ${GPG_COMMENT}
Name-Email: ${GPG_EMAIL}
Expire-Date: 0
Passphrase: ${GPG_PASSPHRASE}
# Do a commit here, so that we can later print "done" :-)
%commit
%echo done
EOF

${GPG} --homedir ${PRIVATE}/${INSTANCE}/gpg --batch --generate-key ${PRIVATE}/${INSTANCE}/gen_key
${GPG} --homedir ${PRIVATE}/${INSTANCE}/gpg --armor --export -a "${GPG_NAME}" > ${PRIVATE}/${INSTANCE}/gpg/public.key
chmod 755 ${PRIVATE}/${INSTANCE}/gpg
chmod 744 ${PRIVATE}/${INSTANCE}/gpg/public.key
rm -f ${PRIVATE}/${INSTANCE}/gen_key
${GPG_CONF} --kill gpg-agent

#########################################################################

echomsg "\t* the RSA public and private key"
${OPENSSL} genpkey -algorithm RSA -out ${PRIVATE}/${INSTANCE}/rsa/ega.sec -pkeyopt rsa_keygen_bits:2048
${OPENSSL} rsa -pubout -in ${PRIVATE}/${INSTANCE}/rsa/ega.sec -out ${PRIVATE}/${INSTANCE}/rsa/ega.pub

#########################################################################

echomsg "\t* the SSL certificates"
${OPENSSL} req -x509 -newkey rsa:2048 -keyout ${PRIVATE}/${INSTANCE}/certs/ssl.key -nodes -out ${PRIVATE}/${INSTANCE}/certs/ssl.cert -sha256 -days 1000 -subj ${SSL_SUBJ}

#########################################################################

echomsg "\t* keys.conf"
cat > ${PRIVATE}/${INSTANCE}/keys.conf <<EOF
[DEFAULT]
active_master_key = 1

[master.key.1]
seckey = /etc/ega/rsa/sec.pem
pubkey = /etc/ega/rsa/pub.pem
EOF

echomsg "\t* ega.conf"
cat > ${PRIVATE}/${INSTANCE}/ega.conf <<EOF
[DEFAULT]
log = /etc/ega/logger.yml

[ingestion]
gpg_cmd = gpg2 --decrypt %(file)s

# Keyserver communication
keyserver_host = ega-keys-${INSTANCE}

## Connecting to Local EGA
[broker]
host = ega-mq-${INSTANCE}

[db]
host = ega-db-${INSTANCE}
username = ${DB_USER}
password = ${DB_PASSWORD}
try = ${DB_TRY}
EOF

echomsg "\t* SFTP Inbox port"
cat >> ${DOT_ENV} <<EOF
DOCKER_INBOX_${INSTANCE}_PORT=${DOCKER_INBOX_PORT}
EOF

echomsg "\t* db.sql"
# cat > ${PRIVATE}/${INSTANCE}/db.sql <<EOF
# -- DROP USER IF EXISTS lega;
# -- CREATE USER ${DB_USER} WITH password '${DB_PASSWORD}';
# DROP DATABASE IF EXISTS lega;
# CREATE DATABASE lega WITH OWNER ${DB_USER};

# EOF
if [[ -f /tmp/db.sql ]]; then
    # Running in a container
    cat /tmp/db.sql >> ${PRIVATE}/${INSTANCE}/db.sql
else
    # Running on host, outside a container
    cat ${HERE}/../../../extras/db.sql >> ${PRIVATE}/${INSTANCE}/db.sql
fi
# cat >> ${PRIVATE}/${INSTANCE}/db.sql <<EOF

# -- Changing the owner there too
# ALTER TABLE files OWNER TO ${DB_USER};
# ALTER TABLE users OWNER TO ${DB_USER};
# ALTER TABLE errors OWNER TO ${DB_USER};
# EOF

echomsg "\t* logger.yml"
_LOG_LEVEL=${LOG_LEVEL:-DEBUG}

cat > ${PRIVATE}/${INSTANCE}/logger.yml <<EOF
version: 1
root:
  level: NOTSET
  handlers: [noHandler]

loggers:
  connect:
    level: ${_LOG_LEVEL}
    handlers: [logstash,console]
  ingestion:
    level: ${_LOG_LEVEL}
    handlers: [logstash,console]
  keyserver:
    level: ${_LOG_LEVEL}
    handlers: [logstash,console]
  vault:
    level: ${_LOG_LEVEL}
    handlers: [logstash,console]
  verify:
    level: ${_LOG_LEVEL}
    handlers: [logstash,console]
  socket-utils:
    level: ${_LOG_LEVEL}
    handlers: [logstash,console]
  inbox:
    level: ${_LOG_LEVEL}
    handlers: [logstash,console]
  utils:
    level: ${_LOG_LEVEL}
    handlers: [logstash,console]
  amqp:
    level: ${_LOG_LEVEL}
    handlers: [logstash,console]
  db:
    level: ${_LOG_LEVEL}
    handlers: [logstash,console]
  crypto:
    level: ${_LOG_LEVEL}
    handlers: [logstash,console]
  asyncio:
    level: ${_LOG_LEVEL}
    handlers: [logstash]
  aiopg:
    level: ${_LOG_LEVEL}
    handlers: [logstash]
  aiohttp.access:
    level: ${_LOG_LEVEL}
    handlers: [logstash]
  aiohttp.client:
    level: ${_LOG_LEVEL}
    handlers: [logstash]
  aiohttp.internal:
    level: ${_LOG_LEVEL}
    handlers: [logstash]
  aiohttp.server:
    level: ${_LOG_LEVEL}
    handlers: [logstash]
  aiohttp.web:
    level: ${_LOG_LEVEL}
    handlers: [logstash]
  aiohttp.websocket:
    level: ${_LOG_LEVEL}
    handlers: [logstash]


handlers:
  noHandler:
    class: logging.NullHandler
    level: NOTSET
  console:
    class: logging.StreamHandler
    formatter: simple
    stream: ext://sys.stdout
  logstash:
    class: lega.utils.logging.LEGAHandler
    formatter: json
    host: ega-logstash-${INSTANCE}
    port: 5600

formatters:
  json:
    (): lega.utils.logging.JSONFormatter
    format: '(asctime) (name) (process) (processName) (levelname) (lineno) (funcName) (message)'
  lega:
    format: '[{asctime:<20}][{name}][{process:d} {processName:>15}][{levelname}] (L:{lineno}) {funcName}: {message}'
    style: '{'
    datefmt: '%Y-%m-%d %H:%M:%S'
  simple:
    format: '[{name:^10}][{levelname:^6}] (L{lineno}) {message}'
    style: '{'
EOF


#########################################################################
# Populate env-settings for docker compose
#########################################################################

echomsg "\t* the docker-compose configuration files"

cat > ${PRIVATE}/${INSTANCE}/db.env <<EOF
DB_INSTANCE=ega-db-${INSTANCE}
POSTGRES_USER=${DB_USER}
POSTGRES_PASSWORD=${DB_PASSWORD}
POSTGRES_DB=lega
EOF

cat > ${PRIVATE}/${INSTANCE}/gpg.env <<EOF
GPG_EMAIL=${GPG_EMAIL}
GPG_PASSPHRASE=${GPG_PASSPHRASE}
EOF

cat >> ${PRIVATE}/cega/env <<EOF
CEGA_REST_${INSTANCE}_PASSWORD=${CEGA_REST_PASSWORD}
EOF

cat > ${PRIVATE}/${INSTANCE}/cega.env <<EOF
#
LEGA_GREETINGS=${LEGA_GREETINGS}
#
CEGA_ENDPOINT=http://cega-users/user/
CEGA_ENDPOINT_CREDS=${INSTANCE}:${CEGA_REST_PASSWORD}
CEGA_ENDPOINT_JSON_PASSWD=.password_hash
CEGA_ENDPOINT_JSON_PUBKEY=.pubkey
EOF

echomsg "\t* Elasticsearch configuration file"
cat > ${PRIVATE}/${INSTANCE}/logs/elasticsearch.yml <<EOF
cluster.name: local-ega
network.host: 0.0.0.0
http.port: 9200
EOF

echomsg "\t* Logstash configuration files"
cat > ${PRIVATE}/${INSTANCE}/logs/logstash.yml <<EOF
path.config: /usr/share/logstash/pipeline
http.host: "0.0.0.0"
http.port: 9600
EOF

cat > ${PRIVATE}/${INSTANCE}/logs/logstash.conf <<EOF
input {
	tcp {
		port => 5600
		codec => json { charset => "UTF-8" }
	}
	rabbitmq {
   		host => "mq-${INSTANCE}"
		port => 5672
		user => "guest"
		password => "guest"
		exchange => "amq.rabbitmq.trace"
		key => "#"
	}
}
output {
       if ("_jsonparsefailure" not in [tags]) {
	        elasticsearch {
			      hosts => ["ega-elasticsearch-${INSTANCE}:9200"]
		}
		
	} else {
		file {
			path => ["logs/error-%{+YYYY-MM-dd}.log"]
		}
		# output to console for debugging purposes
		stdout { 
			codec => rubydebug
		}
	}
}
EOF

echomsg "\t* Kibana configuration file"
cat > ${PRIVATE}/${INSTANCE}/logs/kibana.yml <<EOF
server.port: 5601
server.host: "0.0.0.0"
elasticsearch.url: "http://ega-elasticsearch-${INSTANCE}:9200"
EOF


# For the moment, still using guest:guest
echomsg "\t* Local broker to Central EGA broker credentials"
cat > ${PRIVATE}/${INSTANCE}/mq.env <<EOF
CEGA_CONNECTION=amqp://cega_${INSTANCE}:${CEGA_MQ_PASSWORD}@cega-mq:5672/${INSTANCE}
EOF


#########################################################################
# Keeping a trace of if
#########################################################################

cat >> ${PRIVATE}/${INSTANCE}/.trace <<EOF
#####################################################################
#
# Generated by bootstrap/instance.sh for INSTANCE ${INSTANCE}
#
#####################################################################
#
GPG_PASSPHRASE            = ${GPG_PASSPHRASE}
GPG_NAME                  = ${GPG_NAME}
GPG_COMMENT               = ${GPG_COMMENT}
GPG_EMAIL                 = ${GPG_EMAIL}
SSL_SUBJ                  = ${SSL_SUBJ}
#
DB_USER                   = ${DB_USER}
DB_PASSWORD               = ${DB_PASSWORD}
DB_TRY                    = ${DB_TRY}
#
LEGA_GREETINGS            = ${LEGA_GREETINGS}
#
CEGA_MQ_USER              = cega_${INSTANCE}
CEGA_MQ_PASSWORD          = ${CEGA_MQ_PASSWORD}
CEGA_REST_PASSWORD        = ${CEGA_REST_PASSWORD}
CEGA_PASSWORD             = ${CEGA_PASSWORD}
#
DOCKER_INBOX_PORT         = ${DOCKER_INBOX_PORT}
EOF