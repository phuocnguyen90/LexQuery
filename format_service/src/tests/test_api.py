import requests

url = "http://127.0.0.1:8000/submit_query"
data = {
    "query_text": "Thủ tục chia thừa kế như thế nào?"
}

response = requests.post(url, json=data)

print(response.status_code)
print(response.json())
