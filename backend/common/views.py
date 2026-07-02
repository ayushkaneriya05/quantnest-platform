import logging
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

logger = logging.getLogger(__name__)

@api_view(['POST'])
@permission_classes([AllowAny])
def log_frontend_error(request):
    """
    Endpoint for the frontend ErrorBoundary to log React crashes.
    """
    data = request.data
    error_id = data.get('errorId', 'UNKNOWN')
    message = data.get('message', 'No message provided')
    
    logger.error(f"Frontend Error [{error_id}]: {message}", extra={
        'frontend_error': data
    })
    
    return Response({"status": "logged", "errorId": error_id})
