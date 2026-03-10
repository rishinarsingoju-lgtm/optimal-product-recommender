import requests
import sys

q = sys.argv[1] if len(sys.argv) > 1 else 'laptop'
print('query ->', q)
r = requests.post('http://localhost:5000/search', json={'query': q})
print('status', r.status_code)
try:
    import json
    print(json.dumps(r.json(), indent=2)[:2000])
except Exception as ex:
    print('failed to parse json', ex)
    print(r.text)
