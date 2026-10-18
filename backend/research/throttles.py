from rest_framework.throttling import UserRateThrottle
from commercial.usage import get_account_policy


class ResearchAdmissionThrottle(UserRateThrottle):
    scope = "research-admission"
    def get_rate(self):
        return "6/hour"
    def allow_request(self, request, view):
        policy = get_account_policy(request.user)
        if not policy["limits_enforced"]:
            return True
        self.rate = "6/hour" if policy["plan"]["code"] == "explore" else "30/hour"
        self.num_requests, self.duration = self.parse_rate(self.rate)
        return super().allow_request(request, view)
