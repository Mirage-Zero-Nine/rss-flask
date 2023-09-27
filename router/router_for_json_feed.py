import requests

from router.base_router_new import BaseRouterNew


class RouterForJsonFeed(BaseRouterNew):
    def _load_json_response(self):
        response = requests.get(self.articles_link)
        return response.json()
