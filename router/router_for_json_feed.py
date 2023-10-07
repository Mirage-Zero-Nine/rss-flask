import requests

from router.base_router import BaseRouter


class RouterForJsonFeed(BaseRouter):
    def _load_json_response(self):
        response = requests.get(self.articles_link)
        return response.json()
