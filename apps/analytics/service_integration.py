"""
Service integration for HTTP communication with other SyncScope services.
Handles authentication and data retrieval from Monitoring, Management, and Auth services.
"""

import logging
import requests
from datetime import datetime
from typing import Dict, List, Optional, Any
from django.conf import settings
from django.core.cache import cache

from .authentication import get_auth_headers

logger = logging.getLogger(__name__)


class BaseServiceClient:
    """
    Base class for service clients with common functionality
    """

    def __init__(self, service_url: str, service_name: str):
        self.service_url = service_url.rstrip('/')
        self.service_name = service_name
        self.timeout = 30  # 30 second timeout

    def _make_request(self, method: str, endpoint: str, data: Optional[Dict] = None,
                     params: Optional[Dict] = None, use_cache: bool = True,
                     cache_timeout: int = 300) -> Optional[Dict]:
        """
        Make HTTP request to service with authentication and error handling
        """
        try:
            url = f"{self.service_url}{endpoint}"
            headers = get_auth_headers()

            # Check cache first for GET requests
            cache_key = None
            if method.upper() == 'GET' and use_cache:
                cache_key = f"service_request:{self.service_name}:{endpoint}:{str(params)}"
                cached_result = cache.get(cache_key)
                if cached_result:
                    logger.debug(f"Cache hit for {self.service_name} request: {endpoint}")
                    return cached_result

            # Make request
            response = requests.request(
                method=method,
                url=url,
                headers=headers,
                json=data,
                params=params,
                timeout=self.timeout
            )

            if response.status_code == 200:
                result = response.json()

                # Cache successful GET responses
                if method.upper() == 'GET' and use_cache and cache_key:
                    cache.set(cache_key, result, cache_timeout)

                return result

            elif response.status_code == 404:
                logger.warning(f"{self.service_name} returned 404 for {endpoint}")
                return None

            else:
                logger.error(f"{self.service_name} request failed: {response.status_code} - {response.text}")
                return None

        except requests.exceptions.Timeout:
            logger.error(f"Timeout requesting {self.service_name} endpoint: {endpoint}")
            return None
        except requests.exceptions.ConnectionError:
            logger.error(f"Connection error to {self.service_name}: {endpoint}")
            return None
        except Exception as e:
            logger.error(f"Error requesting {self.service_name} endpoint {endpoint}: {e}")
            return None

    def _format_datetime(self, dt: datetime) -> str:
        """Format datetime for API requests"""
        return dt.strftime('%Y-%m-%dT%H:%M:%SZ')

    def get_health_status(self) -> Dict[str, Any]:
        """Check service health"""
        return self._make_request('GET', '/health/', use_cache=False) or {"status": "unavailable"}


class MonitoringServiceClient(BaseServiceClient):
    """
    Client for interacting with the Monitoring Service
    """

    def __init__(self):
        super().__init__(
            service_url=settings.MONITORING_SERVICE_URL,
            service_name="monitoring"
        )

    def get_user_sessions(self, user_id: str, start_date: datetime, end_date: datetime) -> List[Dict]:
        """
        Get user development sessions from monitoring service
        """
        params = {
            'user_id': user_id,
            'start_date': self._format_datetime(start_date),
            'end_date': self._format_datetime(end_date)
        }

        result = self._make_request('GET', '/api/sessions/', params=params)
        return result.get('results', []) if result else []

    def get_team_sessions(self, team_id: str, start_date: datetime, end_date: datetime) -> List[Dict]:
        """
        Get team development sessions from monitoring service
        """
        params = {
            'team_id': team_id,
            'start_date': self._format_datetime(start_date),
            'end_date': self._format_datetime(end_date)
        }

        result = self._make_request('GET', '/api/sessions/team/', params=params)
        return result.get('results', []) if result else []

    def get_user_git_activity(self, user_id: str, start_date: datetime, end_date: datetime) -> List[Dict]:
        """
        Get user git activity from monitoring service
        """
        params = {
            'user_id': user_id,
            'start_date': self._format_datetime(start_date),
            'end_date': self._format_datetime(end_date)
        }

        result = self._make_request('GET', '/api/git-events/', params=params)
        return result.get('results', []) if result else []

    def get_team_git_activity(self, team_id: str, start_date: datetime, end_date: datetime) -> List[Dict]:
        """
        Get team git activity from monitoring service
        """
        params = {
            'team_id': team_id,
            'start_date': self._format_datetime(start_date),
            'end_date': self._format_datetime(end_date)
        }

        result = self._make_request('GET', '/api/git-events/team/', params=params)
        return result.get('results', []) if result else []

    def get_code_metrics(self, user_id: Optional[str] = None, project_id: Optional[str] = None,
                        start_date: Optional[datetime] = None, end_date: Optional[datetime] = None) -> List[Dict]:
        """
        Get code metrics from monitoring service
        """
        params = {}
        if user_id:
            params['user_id'] = user_id
        if project_id:
            params['project_id'] = project_id
        if start_date:
            params['start_date'] = self._format_datetime(start_date)
        if end_date:
            params['end_date'] = self._format_datetime(end_date)

        result = self._make_request('GET', '/api/code-metrics/', params=params)
        return result.get('results', []) if result else []

    def get_activity_logs(self, user_id: Optional[str] = None, session_id: Optional[str] = None,
                         start_date: Optional[datetime] = None, end_date: Optional[datetime] = None) -> List[Dict]:
        """
        Get activity logs from monitoring service
        """
        params = {}
        if user_id:
            params['user_id'] = user_id
        if session_id:
            params['session_id'] = session_id
        if start_date:
            params['start_date'] = self._format_datetime(start_date)
        if end_date:
            params['end_date'] = self._format_datetime(end_date)

        result = self._make_request('GET', '/api/activity-logs/', params=params)
        return result.get('results', []) if result else []

    def get_user_summary(self, user_id: str, period: str = '30d') -> Dict[str, Any]:
        """
        Get user activity summary from monitoring service
        """
        params = {'period': period}
        result = self._make_request('GET', f'/api/users/{user_id}/summary/', params=params)
        return result or {}


class ManagementServiceClient(BaseServiceClient):
    """
    Client for interacting with the Management Service
    """

    def __init__(self):
        super().__init__(
            service_url=settings.MANAGEMENT_SERVICE_URL,
            service_name="management"
        )

    def get_team_members(self, team_id: str) -> List[Dict]:
        """
        Get team members from management service
        """
        result = self._make_request('GET', f'/api/teams/{team_id}/members/')
        return result.get('results', []) if result else []

    def get_user_teams(self, user_id: str) -> List[Dict]:
        """
        Get teams that a user belongs to
        """
        params = {'user_id': user_id}
        result = self._make_request('GET', '/api/teams/', params=params)
        return result.get('results', []) if result else []

    def get_team_projects(self, team_id: str) -> List[Dict]:
        """
        Get projects for a team
        """
        result = self._make_request('GET', f'/api/teams/{team_id}/projects/')
        return result.get('results', []) if result else []

    def get_project_details(self, project_id: str) -> Optional[Dict]:
        """
        Get project details
        """
        return self._make_request('GET', f'/api/projects/{project_id}/')

    def get_team_details(self, team_id: str) -> Optional[Dict]:
        """
        Get team details
        """
        return self._make_request('GET', f'/api/teams/{team_id}/')

    def get_company_teams(self, company_id: str) -> List[Dict]:
        """
        Get all teams for a company
        """
        params = {'company_id': company_id}
        result = self._make_request('GET', '/api/teams/', params=params)
        return result.get('results', []) if result else []

    def get_integrations(self, project_id: str) -> List[Dict]:
        """
        Get integrations for a project
        """
        result = self._make_request('GET', f'/api/projects/{project_id}/integrations/')
        return result.get('results', []) if result else []

    def get_github_integration(self, project_id: str) -> Optional[Dict]:
        """
        Get GitHub integration for a project
        """
        return self._make_request('GET', f'/api/projects/{project_id}/github-integration/')


class AuthServiceClient(BaseServiceClient):
    """
    Client for interacting with the Auth Service
    """

    def __init__(self):
        super().__init__(
            service_url=settings.AUTH_SERVICE_URL,
            service_name="auth"
        )

    def get_user_details(self, user_id: str) -> Optional[Dict]:
        """
        Get user details from auth service
        """
        return self._make_request('GET', f'/api/users/{user_id}/')

    def get_company_details(self, company_id: str) -> Optional[Dict]:
        """
        Get company details from auth service
        """
        return self._make_request('GET', f'/api/companies/{company_id}/')

    def get_company_users(self, company_id: str) -> List[Dict]:
        """
        Get all users for a company
        """
        params = {'company_id': company_id}
        result = self._make_request('GET', '/api/users/', params=params)
        return result.get('results', []) if result else []

    def get_supervised_users(self, supervisor_id: str) -> List[Dict]:
        """
        Get users supervised by a supervisor
        """
        params = {'supervisor_id': supervisor_id}
        result = self._make_request('GET', '/api/supervised-users/', params=params)
        return result.get('results', []) if result else []

    def verify_user_permissions(self, user_id: str, resource_type: str, resource_id: str) -> bool:
        """
        Verify if user has permissions for a resource
        """
        data = {
            'resource_type': resource_type,
            'resource_id': resource_id
        }
        result = self._make_request('POST', f'/api/users/{user_id}/verify-permissions/', data=data, use_cache=False)
        return result.get('has_permission', False) if result else False


class ServiceIntegrationManager:
    """
    Manager class to coordinate interactions with multiple services
    """

    def __init__(self):
        self.monitoring = MonitoringServiceClient()
        self.management = ManagementServiceClient()
        self.auth = AuthServiceClient()

    def get_user_context(self, user_id: str) -> Dict[str, Any]:
        """
        Get comprehensive user context from all services
        """
        context = {
            'user_id': user_id,
            'user_details': None,
            'teams': [],
            'projects': [],
            'company_id': None
        }

        # Get user details
        user_details = self.auth.get_user_details(user_id)
        if user_details:
            context['user_details'] = user_details
            context['company_id'] = user_details.get('company_id')

        # Get user teams
        teams = self.management.get_user_teams(user_id)
        context['teams'] = teams

        # Get projects for each team
        projects = []
        for team in teams:
            team_projects = self.management.get_team_projects(team['id'])
            projects.extend(team_projects)
        context['projects'] = projects

        return context

    def get_team_context(self, team_id: str) -> Dict[str, Any]:
        """
        Get comprehensive team context from all services
        """
        context = {
            'team_id': team_id,
            'team_details': None,
            'members': [],
            'projects': []
        }

        # Get team details
        team_details = self.management.get_team_details(team_id)
        if team_details:
            context['team_details'] = team_details

        # Get team members
        members = self.management.get_team_members(team_id)
        context['members'] = members

        # Get team projects
        projects = self.management.get_team_projects(team_id)
        context['projects'] = projects

        return context

    def get_company_context(self, company_id: str) -> Dict[str, Any]:
        """
        Get comprehensive company context from all services
        """
        context = {
            'company_id': company_id,
            'company_details': None,
            'teams': [],
            'users': []
        }

        # Get company details
        company_details = self.auth.get_company_details(company_id)
        if company_details:
            context['company_details'] = company_details

        # Get company teams
        teams = self.management.get_company_teams(company_id)
        context['teams'] = teams

        # Get company users
        users = self.auth.get_company_users(company_id)
        context['users'] = users

        return context

    def check_service_health(self) -> Dict[str, Any]:
        """
        Check health of all integrated services
        """
        return {
            'monitoring': self.monitoring.get_health_status(),
            'management': self.management.get_health_status(),
            'auth': self.auth.get_health_status()
        }

    def get_user_analytics_data(self, user_id: str, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """
        Get comprehensive analytics data for a user
        """
        return {
            'user_context': self.get_user_context(user_id),
            'sessions': self.monitoring.get_user_sessions(user_id, start_date, end_date),
            'git_activity': self.monitoring.get_user_git_activity(user_id, start_date, end_date),
            'activity_logs': self.monitoring.get_activity_logs(user_id=user_id, start_date=start_date, end_date=end_date),
            'summary': self.monitoring.get_user_summary(user_id)
        }

    def get_team_analytics_data(self, team_id: str, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """
        Get comprehensive analytics data for a team
        """
        return {
            'team_context': self.get_team_context(team_id),
            'sessions': self.monitoring.get_team_sessions(team_id, start_date, end_date),
            'git_activity': self.monitoring.get_team_git_activity(team_id, start_date, end_date)
        }


# Global service integration manager instance
service_manager = ServiceIntegrationManager()