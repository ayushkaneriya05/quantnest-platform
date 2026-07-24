import logging
from celery import shared_task
from .services import TradingOrderService

logger = logging.getLogger(__name__)

