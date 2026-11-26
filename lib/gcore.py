import sys
import requests

API_BASE = "https://api.gcore.com/fastedge/v1"


class GcoreKVUploader:
    def __init__(self, api_token, store_id, app_url):
        self.store_id = store_id
        self.app_url = app_url.rstrip('/')
        self.headers = {"Authorization": f"APIKey {api_token}"}

    def _data_url(self):
        return f"{API_BASE}/kv/{self.store_id}/data"

    def upload(self, key, content):
        response = requests.put(
            self._data_url(),
            headers=self.headers,
            json=[{
                "op": "add",
                "key": key,
                "datatype": "kv",
                "payload": {"encoding": "plain", "value": content},
            }],
        )
        if not response.ok:
            print(f"Gcore KV upload error: {response.status_code} {response.text}",
                  file=sys.stderr)
            response.raise_for_status()
        return f"{self.app_url}/{key}"

    def delete(self, key):
        requests.put(
            self._data_url(),
            headers=self.headers,
            json=[{"op": "del_key", "key": key, "datatype": "kv"}],
        ).raise_for_status()

    def list_all_keys(self, prefix=''):
        all_keys = []
        offset = 0
        limit = 1000
        while True:
            response = requests.get(
                self._data_url(),
                headers=self.headers,
                params={"limit": limit, "offset": offset},
            )
            response.raise_for_status()
            data = response.json()
            entries = data.get("entries", [])
            all_keys.extend(
                {"name": entry["key"]} for entry in entries
                if entry.get("key", "").startswith(prefix)
            )
            offset += len(entries)
            if not entries or offset >= data.get("count", 0):
                break
        return all_keys

    def delete_by_prefix(self, prefix):
        keys = self.list_all_keys(prefix=prefix)
        if not keys:
            return []
        names = [key["name"] for key in keys]
        requests.put(
            self._data_url(),
            headers=self.headers,
            json=[{"op": "del_key", "key": name, "datatype": "kv"}
                  for name in names],
        ).raise_for_status()
        return names


def create_uploader(secrets):
    gc = secrets.get('gcore', {})
    required = [gc.get('api_token'), gc.get('store_id'), gc.get('app_url')]
    if not all(required):
        return None
    return GcoreKVUploader(
        gc['api_token'], gc['store_id'], gc['app_url']
    )
