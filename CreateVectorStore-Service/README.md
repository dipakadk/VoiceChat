Run with 
create venv 
  - python3 -m venv venv
  - source venv/bin/activate

Install dipendency
  - pip3 install -r requirements.txt

To start application
  - uvicorn server:app --reload

Check is app working or not
  - http://127.0.0.1:8000/vectorstore/test