from fastapi import APIRouter
import logging

router = APIRouter()

@router.get("/coinbase/connection")
def get_coinbase_connection():
    logging.debug('trying to get coinbase adapter')
    return 1