## INTRODUCTION
This is my project for using a chatbot. In this repo, I will use **Qwen2.5-1.5-Instruct** model. This is a public model on hugging face, it is trained with **1.5B parameters**. I can eat in range **2-3GB RAM**, suitable for edge device.
This project will using work flow is: Using a camera detect pose for warning alert in elevator. After this, computer will push data to database (mongoDB Atlas Cloud) realtime. Model Qwen is prompted by user for asking alert or something. AI model will create a query and get data from database. Finally, the data of database will push in model and return the prompt for user.

- The `src/` folder is main source of project.
- The `test/` folder is using for testing.

## How to use this code
**Clone my repo:**
```bash
git clone https://github.com/minhthong2514/elevator-chatbot.git
```
**Move to src folder:**
```bash
cd src/
```
File **`test_connect.py`** is testing connection to mongoDB:
```bash
python3 test_connect.py
```
File **`engine.py`** and **`app.py`** are initialize and config server api. You need only app.py:
```bash
python3 engine.py
python3 app.py
```
File **`main.py`** is used for calling to api server and prompt user:
```bash
python3 main.py
```