import datetime
import logging
import os
from pathlib import Path

from dotenv import find_dotenv, load_dotenv
from omegaconf import OmegaConf
from telebot.types import LabeledPrice

from ..database.core import get_session
from .service import create_payment, create_subscription, get_subscription_plans, get_subscription_plan, credit_balance

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


# load environment variables
load_dotenv(find_dotenv(usecwd=True))
PROVIDER_TOKEN = os.getenv("PROVIDER_TOKEN")

# Load configuration
CURRENT_DIR = Path(__file__).parent
config = OmegaConf.load(CURRENT_DIR / "config.yaml")
strings = config.strings

db_session = get_session()

def register_handlers(bot):

    @bot.callback_query_handler(func=lambda call: call.data == "subscription")
    def purchase(call):
        subscription_plans = get_subscription_plans(db_session)
        for subscription_plan in subscription_plans:
            if subscription_plan.price > 0:
                prices = [LabeledPrice(label=subscription_plan.name, amount=int(subscription_plan.price*100))]
                provider_data = json.dumps({
                  "receipt": {
                    "items": [
                      {
                        "description": subscription_plan.name,
                        "quantity": 1,
                        "amount": {
                          "value": int(subscription_plan.price),
                          "currency": subscription_plan.currency
                        },
                        "vat_code": 1,
                        "payment_mode": "full_payment",
                        "payment_subject": "service"
                      }
                    ]
                  }
                })
                bot.send_invoice(
                    chat_id = call.message.chat.id,
                    provider_data = provider_data,
                    title = subscription_plan.name,
                    description = subscription_plan.description or " ",
                    provider_token = PROVIDER_TOKEN,
                    currency = subscription_plan.currency,
                    prices = prices,
                    invoice_payload = subscription_plan.id,
                    need_email=True,
                    send_email_to_provider=True,
                    is_flexible=False,
                    start_parameter='premium-example'
                )


    @bot.pre_checkout_query_handler(func=lambda query: True)
    def checkout(pre_checkout_query):
        bot.answer_pre_checkout_query(
            pre_checkout_query.id, ok=True,
            error_message="Try to pay again in a few minutes, we need a small rest."
        )


    @bot.message_handler(content_types=['successful_payment'])
    def successful_payment(message):
        user_id = message.from_user.id
        subscription_plan_id = message.successful_payment.invoice_payload
        subscription = create_subscription(db_session, user_id, subscription_plan_id)
        create_payment(
            db_session=db_session,
            subscription_id=subscription.id,
            amount=message.successful_payment.total_amount/100,
            currency=message.successful_payment.currency,
            payment_date=datetime.datetime.now(),
            payment_method=message.successful_payment.provider_payment_charge_id
        )

        # Credit user balance
        subscription_plan = get_subscription_plan(db_session, subscription_plan_id)
        credit_balance(db_session, user_id, subscription_plan.credits)

        bot.send_message(
            user_id,
            strings.ru.payment_successful.format(
                balance_update=subscription_plan.credits
            )
            )
        logger.info(f"User {user_id} has successfully paid for subscription {subscription_plan_id}")
