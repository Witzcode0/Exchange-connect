from app.base.api import BaseResource


class HealthCheckAPI(BaseResource):
    def get(self):
        result = "Server is running"
        return {'results': result}, 200