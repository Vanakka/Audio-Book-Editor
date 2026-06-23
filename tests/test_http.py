import unittest
from unittest.mock import Mock, patch

from scrapers.http import get_with_retry


class HttpRetryTests(unittest.TestCase):
    @patch("scrapers.http.time.sleep")
    def test_retries_429_then_returns_success(self, sleep):
        throttled = Mock(status_code=429, headers={"Retry-After": "0"})
        success = Mock(status_code=200)
        success.raise_for_status.return_value = None
        requester = Mock(side_effect=[throttled, success])

        result = get_with_retry("https://example.test", requester=requester)

        self.assertIs(result, success)
        self.assertEqual(requester.call_count, 2)


if __name__ == "__main__":
    unittest.main()
