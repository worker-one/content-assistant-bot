import logging

from sqlalchemy.orm import Session

from ..auth.models import User
from ..database.core import get_session

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def debit_balance(user_id: int, quantity: int = 1) -> bool:
    """ Use text generation from the active subscription """
    db: Session = get_session()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        # Check if user has enough balance
        if user.balance < quantity:
            return False
        else:
            user.balance -= quantity
            db.commit()
            return True
    finally:
        db.close()
