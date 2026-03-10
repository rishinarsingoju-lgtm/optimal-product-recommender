from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

Base = declarative_base()

class Product(Base):
    __tablename__ = 'products'
    id = Column(Integer, primary_key=True)
    search_query = Column(String)
    platform = Column(String)       # e.g. amazon, ebay, etc.
    name = Column(String)
    price = Column(Float)
    rating = Column(String)
    url = Column(String)
    image_url = Column(String)
    searched_at = Column(DateTime, default=datetime.utcnow)

engine = create_engine('sqlite:///products.db')
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)

def save_products(products):
    session = Session()
    for p in products:
        product = Product(**p)
        session.add(product)
    session.commit()
    session.close()

def get_history(query):
    session = Session()
    results = session.query(Product).filter(
        Product.search_query.ilike(f'%{query}%')
    ).order_by(Product.searched_at.desc()).limit(50).all()
    session.close()
    return results