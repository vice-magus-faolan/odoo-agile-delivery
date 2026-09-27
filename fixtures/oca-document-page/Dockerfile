FROM odoo@sha256:144175ec0039d52daff1d79f7e51c9281ca3c98b96c830feb49d09764a9f5d7c

USER root

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates git \
    && git init /opt/oca-knowledge \
    && git -C /opt/oca-knowledge remote add origin https://github.com/OCA/knowledge.git \
    && git -C /opt/oca-knowledge fetch --depth=1 origin e4a12c0c99866a5850840941d6f7ae3b3b27280d \
    && git -C /opt/oca-knowledge checkout --detach FETCH_HEAD \
    && test "$(git -C /opt/oca-knowledge rev-parse HEAD)" = "e4a12c0c99866a5850840941d6f7ae3b3b27280d" \
    && chmod -R a+rX /opt/oca-knowledge

USER odoo
