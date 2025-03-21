from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from ..auth.models import User
from ..models import Base, TimeStampMixin


class Channel(Base, TimeStampMixin):
    """ Channel model for storing user's Telegram channels """
    __tablename__ = "channels"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    link = Column(String, nullable=False)
    owner_id = Column(Integer, ForeignKey("users.id"))

    #owner = relationship("User", back_populates="channels")
