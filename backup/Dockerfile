FROM postgres:16-alpine

COPY backup.sh /backup.sh
RUN chmod +x /backup.sh

# Sleep loop: wait 7 days between each backup run
CMD ["sh", "-c", "while true; do /backup.sh; sleep 604800; done"]