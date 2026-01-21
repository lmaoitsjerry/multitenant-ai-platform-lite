"""
SendGrid Admin Service - Platform-wide SendGrid Management

Provides:
- Subuser listing and management
- Email statistics retrieval
- Subuser enable/disable functionality

Uses the main SendGrid API key (not tenant subuser keys).
"""

import os
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class SendGridAdminService:
    """Service for managing SendGrid subusers and retrieving platform-wide email stats"""

    def __init__(self):
        self.api_key = os.getenv("SENDGRID_API_KEY")
        self.sg = None

        if self.api_key:
            try:
                import sendgrid
                self.sg = sendgrid.SendGridAPIClient(api_key=self.api_key)
                logger.info("SendGrid admin service initialized")
            except ImportError:
                logger.warning("SendGrid library not installed")
            except Exception as e:
                logger.error(f"Failed to initialize SendGrid: {e}")

    def is_available(self) -> bool:
        """Check if SendGrid is properly configured"""
        return self.sg is not None

    def list_subusers(self) -> List[Dict[str, Any]]:
        """
        Get all SendGrid subusers.

        Returns:
            List of subuser dictionaries with username, email, disabled status
        """
        if not self.sg:
            logger.warning("SendGrid not configured")
            return []

        try:
            response = self.sg.client.subusers.get()

            if response.status_code == 200:
                import json
                subusers = json.loads(response.body)
                return [
                    {
                        "username": su.get("username"),
                        "email": su.get("email"),
                        "disabled": su.get("disabled", False),
                        "id": su.get("id")
                    }
                    for su in subusers
                ]
            else:
                logger.error(f"SendGrid API error: {response.status_code}")
                return []

        except Exception as e:
            logger.error(f"Error listing SendGrid subusers: {e}")
            return []

    def get_subuser_stats(self, username: str, days: int = 30) -> Dict[str, Any]:
        """
        Get email statistics for a specific subuser.

        Args:
            username: SendGrid subuser username
            days: Number of days to look back

        Returns:
            Dictionary with email statistics
        """
        if not self.sg:
            return {"error": "SendGrid not configured"}

        try:
            start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
            end_date = datetime.now().strftime("%Y-%m-%d")

            response = self.sg.client.subusers._(username).stats.get(
                query_params={
                    "start_date": start_date,
                    "end_date": end_date,
                    "aggregated_by": "day"
                }
            )

            if response.status_code == 200:
                import json
                stats_data = json.loads(response.body)

                # Aggregate stats
                totals = {
                    "requests": 0,
                    "delivered": 0,
                    "opens": 0,
                    "unique_opens": 0,
                    "clicks": 0,
                    "unique_clicks": 0,
                    "bounces": 0,
                    "spam_reports": 0,
                    "unsubscribes": 0,
                    "blocks": 0,
                    "invalid_emails": 0
                }

                daily_stats = []
                for day_data in stats_data:
                    date = day_data.get("date")
                    day_metrics = day_data.get("stats", [{}])[0].get("metrics", {})

                    daily_stats.append({
                        "date": date,
                        **day_metrics
                    })

                    for key in totals:
                        totals[key] += day_metrics.get(key, 0)

                # Calculate rates
                if totals["delivered"] > 0:
                    totals["open_rate"] = round((totals["unique_opens"] / totals["delivered"]) * 100, 2)
                    totals["click_rate"] = round((totals["unique_clicks"] / totals["delivered"]) * 100, 2)
                else:
                    totals["open_rate"] = 0
                    totals["click_rate"] = 0

                if totals["requests"] > 0:
                    totals["bounce_rate"] = round((totals["bounces"] / totals["requests"]) * 100, 2)
                else:
                    totals["bounce_rate"] = 0

                return {
                    "username": username,
                    "period_days": days,
                    "totals": totals,
                    "daily": daily_stats
                }

            else:
                logger.error(f"SendGrid API error for {username}: {response.status_code}")
                return {"error": f"API error: {response.status_code}"}

        except Exception as e:
            logger.error(f"Error getting stats for subuser {username}: {e}")
            return {"error": str(e)}

    def get_global_stats(self, days: int = 30) -> Dict[str, Any]:
        """
        Get platform-wide email statistics.

        Args:
            days: Number of days to look back

        Returns:
            Aggregated email statistics
        """
        if not self.sg:
            return {"error": "SendGrid not configured"}

        try:
            start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
            end_date = datetime.now().strftime("%Y-%m-%d")

            response = self.sg.client.stats.get(
                query_params={
                    "start_date": start_date,
                    "end_date": end_date,
                    "aggregated_by": "day"
                }
            )

            if response.status_code == 200:
                import json
                stats_data = json.loads(response.body)

                totals = {
                    "requests": 0,
                    "delivered": 0,
                    "opens": 0,
                    "unique_opens": 0,
                    "clicks": 0,
                    "unique_clicks": 0,
                    "bounces": 0,
                    "spam_reports": 0,
                    "unsubscribes": 0,
                    "blocks": 0
                }

                for day_data in stats_data:
                    day_metrics = day_data.get("stats", [{}])[0].get("metrics", {})
                    for key in totals:
                        totals[key] += day_metrics.get(key, 0)

                # Calculate rates
                if totals["delivered"] > 0:
                    totals["open_rate"] = round((totals["unique_opens"] / totals["delivered"]) * 100, 2)
                    totals["click_rate"] = round((totals["unique_clicks"] / totals["delivered"]) * 100, 2)
                else:
                    totals["open_rate"] = 0
                    totals["click_rate"] = 0

                if totals["requests"] > 0:
                    totals["bounce_rate"] = round((totals["bounces"] / totals["requests"]) * 100, 2)
                    totals["delivery_rate"] = round((totals["delivered"] / totals["requests"]) * 100, 2)
                else:
                    totals["bounce_rate"] = 0
                    totals["delivery_rate"] = 0

                return {
                    "period_days": days,
                    "totals": totals
                }

            else:
                logger.error(f"SendGrid API error: {response.status_code}")
                return {"error": f"API error: {response.status_code}"}

        except Exception as e:
            logger.error(f"Error getting global SendGrid stats: {e}")
            return {"error": str(e)}

    def disable_subuser(self, username: str) -> bool:
        """
        Disable a SendGrid subuser (stop them from sending emails).

        Args:
            username: SendGrid subuser username

        Returns:
            True if successful, False otherwise
        """
        if not self.sg:
            return False

        try:
            response = self.sg.client.subusers._(username).patch(
                request_body={"disabled": True}
            )

            if response.status_code in [200, 204]:
                logger.info(f"Disabled SendGrid subuser: {username}")
                return True
            else:
                logger.error(f"Failed to disable subuser {username}: {response.status_code}")
                return False

        except Exception as e:
            logger.error(f"Error disabling subuser {username}: {e}")
            return False

    def enable_subuser(self, username: str) -> bool:
        """
        Enable a SendGrid subuser.

        Args:
            username: SendGrid subuser username

        Returns:
            True if successful, False otherwise
        """
        if not self.sg:
            return False

        try:
            response = self.sg.client.subusers._(username).patch(
                request_body={"disabled": False}
            )

            if response.status_code in [200, 204]:
                logger.info(f"Enabled SendGrid subuser: {username}")
                return True
            else:
                logger.error(f"Failed to enable subuser {username}: {response.status_code}")
                return False

        except Exception as e:
            logger.error(f"Error enabling subuser {username}: {e}")
            return False


# Singleton instance
_sendgrid_admin_service: Optional[SendGridAdminService] = None


def get_sendgrid_admin_service() -> SendGridAdminService:
    """Get or create SendGrid admin service singleton"""
    global _sendgrid_admin_service
    if _sendgrid_admin_service is None:
        _sendgrid_admin_service = SendGridAdminService()
    return _sendgrid_admin_service
