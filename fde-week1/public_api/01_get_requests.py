import requests

url = "https://jsonplaceholder.typicode.com/users"

response = requests.get(url)
data = response.json()

for item in data:
    
    print(f"Username: {item['username']} | Email: {item['email']} | Company: {item['company']['name']}")

    phone = item['phone']
    extension = phone.split('x')[-1].strip() if 'x' in phone else None
    print(f"Phone Extension: {extension}")
