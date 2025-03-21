from sqlalchemy import Column, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from ..auth.models import User
from ..models import Base, TimeStampMixin


class Style(Base, TimeStampMixin):
    """ Style model for storing post generation styles """
    __tablename__ = "styles"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    examples = Column(Text, nullable=True)  # JSON-serialized examples or references
    owner_id = Column(Integer, ForeignKey("users.id"))

    #owner = relationship("User")
    #posts = relationship("Post", back_populates="style")
