# lib/cloudflare.py
import sys
import requests


class CFKVUploader:
    def __init__(self, account_id, api_token, namespace_id, worker_domain):
        self.base_url = (
            f"https://api.cloudflare.com/client/v4/accounts"
            f"/{account_id}/storage/kv/namespaces/{namespace_id}"
        )
        self.headers = {"Authorization": f"Bearer {api_token}"}
        self.worker_domain = worker_domain.rstrip('/')

    def upload(self, key, content):
        response = requests.put(
            f"{self.base_url}/values/{key}",
            headers={**self.headers, "Content-Type": "text/plain"},
            data=content.encode('utf-8')
        )
        if not response.ok:
            print(f"KV upload error: {response.status_code} {response.text}",
                  file=sys.stderr)
            response.raise_for_status()
        return f"https://{self.worker_domain}/{key}"

    def delete(self, key):
        requests.delete(
            f"{self.base_url}/values/{key}", headers=self.headers
        ).raise_for_status()

    def list_keys(self, prefix='', cursor=None):
        params = {}
        if prefix:
            params['prefix'] = prefix
        if cursor:
            params['cursor'] = cursor
        response = requests.get(
            f"{self.base_url}/keys", headers=self.headers, params=params
        )
        response.raise_for_status()
        data = response.json()
        return data.get('result', []), data.get('result_info', {}).get('cursor', '')

    def list_all_keys(self, prefix=''):
        all_keys = []
        cursor = None
        while True:
            keys, cursor = self.list_keys(prefix=prefix, cursor=cursor)
            all_keys.extend(keys)
            if not cursor:
                break
        return all_keys

    def delete_by_prefix(self, prefix):
        keys = self.list_all_keys(prefix=prefix)
        deleted = []
        for key_info in keys:
            key_name = key_info['name']
            self.delete(key_name)
            deleted.append(key_name)
        return deleted


def create_uploader(secrets):
    cf = secrets.get('cloudflare', {})
    required = [cf.get('account_id'), cf.get('api_token'),
                cf.get('kv_namespace_id'), cf.get('worker_domain')]
    if not all(required):
        return None
    return CFKVUploader(
        cf['account_id'], cf['api_token'],
        cf['kv_namespace_id'], cf['worker_domain']
    )
